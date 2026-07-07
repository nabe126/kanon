# 修正計画書 (Remediation Plan)

* **起票日**: 2026-07-07
* **起票者**: Antigravity
* **目的**: 進捗監査で判明したバグ、セキュリティ上の不整合、マウントの不備、不要コード、および設計ドキュメントの不足を整理し、安全かつ段階的に修正するための実行計画。

---

## 🛠️ 分類表 (Categorization)

| 項目ID | 修正項目 | 分類 | 理由 |
|---|---|---|---|
| **RM-01** | `monitor` コンテナの `docker` CLI 修復 & ソケットマウント | **完全自動で修正可能** | 設定ファイルの修正とシミュレーションによる自動検証が可能。 |
| **RM-02** | `ai-agent` 本番 compose の `docker.sock` 排除（Sandbox化） | **完全自動で修正可能** | `docker-compose.yml` の記述削除とコンテナの起動検証で完結するため。 |
| **RM-03** | `ai-agent` 本番 compose への `memory/` と `docs/` のマウント追加 | **完全自動で修正可能** | ボリュームマウントの設定修正とアクセス検証で完結するため。 |
| **RM-04** | デッドコード（`agent.py`/`autonomous_agent.py`等）の削除・整理 | **人間確認が必要** | 実験用コードの完全廃止とコード削除の最終確認は人間に委ねるため。 |
| **RM-05** | ADR-010 の Accepted 化 & ASEP 新規 ADR 起票 | **人間確認が必要** | 設計決定（ADR）の承認権限は人間に帰属する（エージェント憲章の Non-Goals）。 |
| **RM-06** | API エンドポイントに対する L1/L2 テストの追加 | **完全自動で修正可能** | テストコードの新規作成と pytest 実行による成否判定。 |

---

## 🔍 各項目の詳細計画 (Remediation Details)

### 📌 RM-01: `monitor` コンテナの `docker` CLI 修復 & ソケットマウント
* **問題**:
  L3統合シミュレーションにおいて、`monitor.py` が異常検知した際に `docker restart` コマンドを実行しようとするが、`[Errno 2] No such file or directory: 'docker'` エラーで失敗している。
* **原因**:
  1. [controller/Dockerfile.monitor](file:///Users/nabe/src/github.com/nabe126/kanon/controller/Dockerfile.monitor) で `docker` CLI のインストールが行われていない。
  2. [docker-compose.test-l3.yml](file:///Users/nabe/src/github.com/nabe126/kanon/docker-compose.test-l3.yml) でホストの Docker デーモンソケット `/var/run/docker.sock` がマウントされていないため、コマンドがインストールされても Docker デーモンを操作できない。
* **修正方針**:
  1. `Dockerfile.monitor` を修正し、`apt-get` 経由で Docker CLI のみをインストールする（軽量化のためデーモン本体は入れない）。
  2. `docker-compose.test-l3.yml` の `monitor` サービスボリュームに `- /var/run/docker.sock:/var/run/docker.sock` を追加する。
* **修正対象ファイル**:
  * [controller/Dockerfile.monitor](file:///Users/nabe/src/github.com/nabe126/kanon/controller/Dockerfile.monitor)
  * [docker-compose.test-l3.yml](file:///Users/nabe/src/github.com/nabe126/kanon/docker-compose.test-l3.yml)
* **テスト方法**:
  * `python3 ai-agent/workspace/tests/run_l3_simulation.py` を実行。
  * [ai-agent/workspace/l3_evidence.txt](file:///Users/nabe/src/github.com/nabe126/kanon/ai-agent/workspace/l3_evidence.txt) を参照し、`docker` コマンドエラーが消え、`[Monitor] Docker container restarted successfully.` の成功ログが残ることを確認する。
* **人間が確認すべき点**:
  * テスト検証後に自動生成される `l3_evidence.txt` の内容を確認し、エラーが発生していないことを目視確認する。

---

### 📌 RM-02: `ai-agent` 本番 compose の `docker.sock` 排除
* **問題**:
  本番運用の `ai-agent/docker-compose.yml` において、`docker.sock` が直接エージェントコンテナにマウントされており、特権分離・サンドボックス設計に違反している。
* **原因**:
  初期の自己コンテナ再起動設計（ADR-002）の名残として、`agent` サービスに直接マウントされた状態が残っていた。
* **修正方針**:
  * [ai-agent/docker-compose.yml](file:///Users/nabe/src/github.com/nabe126/kanon/ai-agent/docker-compose.yml) の `volumes` から `- /var/run/docker.sock:/var/run/docker.sock` の行を削除する。
* **修正対象ファイル**:
  * [ai-agent/docker-compose.yml](file:///Users/nabe/src/github.com/nabe126/kanon/ai-agent/docker-compose.yml)
* **テスト方法**:
  * コンテナ起動後、`docker inspect ai_agent_core` を実行し、ボリュームマウント設定（Binds）に `docker.sock` が含まれていないことを確認する。
* **人間が確認すべき点**:
  * エージェントのセキュリティレベルが Sandbox 条件を満たしていることの承認。

---

### 📌 RM-03: `ai-agent` 本番 compose への `memory/` と `docs/` のマウント追加
* **問題**:
  本番用の `ai-agent/docker-compose.yml` において、エージェントが長期記憶の保存やドキュメント（handoverなど）を書き込む対象である `memory/` および `docs/` ディレクトリがコンテナにマウントされていない。
* **原因**:
  コンテナ起動定義が `./workspace:/workspace` のみになっており、ルートにある記憶領域やドキュメント領域へのパス参照が考慮されていなかった。
* **修正方針**:
  * `ai-agent/docker-compose.yml` の `volumes` に、ルートの `./memory` と `./docs` のマウント定義を追加し、コンテナ内の `/workspace/memory` および `/workspace/docs` にマッピングする。
* **修正対象ファイル**:
  * [ai-agent/docker-compose.yml](file:///Users/nabe/src/github.com/nabe126/kanon/ai-agent/docker-compose.yml)
* **テスト方法**:
  * 修正後に本番 compose でコンテナを起動し、コンテナ内から `/workspace/memory` および `/workspace/docs` に対する読み書きが機能し、ホスト側のディレクトリに変更が即座に反映されることを確認する。
* **修正コードイメージ**:
  ```yaml
  volumes:
    - ./workspace:/workspace
    - ../memory:/workspace/memory
    - ../docs:/workspace/docs
  ```
* **人間が確認すべき点**:
  * ホスト側とコンテナ側でファイルの同期が正常に行われているかどうかの検証結果。

---

### 📌 RM-04: デッドコードの削除・整理
* **問題**:
  リポジトリ内に、現在は使用されていない過去の実験用スクリプトやバックアップファイルが残存している。
* **原因**:
  開発初期のモック実装（`agent.py`/`autonomous_agent.py`）が放置されていたため。
* **修正方針**:
  * `src/agent.py` および `src/autonomous_agent.py` をリポジトリから削除、またはモック用のコードとして `tests/` 配下に退避する。
  * 不要なバックアップファイルである `Dockerfile.bk` を削除する。
* **修正対象ファイル**:
  * `ai-agent/workspace/src/agent.py` (削除)
  * `ai-agent/workspace/src/autonomous_agent.py` (削除)
  * `ai-agent/Dockerfile.bk` (削除)
* **テスト方法**:
  * 削除後、pytest を実行してテスト全体の正常終了を確認し、既存のテストがこれらのデッドコードに依存していないことを実証する。
* **人間が確認すべき点**:
  * `autonomous_agent.py` に書かれていた Gemini への定期ループメッセージアピール処理を完全に廃止（またはテストコードへ統合）してよいかの意思決定。

---

### 📌 RM-05: ADR-010 の Accepted 化 & ASEP 新規 ADR 起票
* **問題**:
  1. `ADR-010-memory-mvp-architecture.md` のステータスが `Proposed (提案中)` のまま、実装だけが完了している。
  2. 実装済みの安全実行プロトコル（ASEP - `asep_middleware.py`）に関する設計決定レコード（ADR）が存在しない。
* **原因**:
  実装が先行し、設計決定ライフサイクル（ドキュメントステータス）の追従が漏れていたため。
* **修正方針**:
  1. `ADR-010-memory-mvp-architecture.md` および `decisions.md` のステータスを `Accepted (承認済)` に書き換える。
  2. 新規に `ADR-011-asep-protocol-specification.md` を作成し、リスクレベル（L0〜L3）の定義や承認フローを公式記録する。
* **修正対象ファイル**:
  * [docs/decisions/ADR-010-memory-mvp-architecture.md](file:///Users/nabe/src/github.com/nabe126/kanon/docs/decisions/ADR-010-memory-mvp-architecture.md)
  * [docs/decisions/decisions.md](file:///Users/nabe/src/github.com/nabe126/kanon/docs/decisions/decisions.md)
  * `docs/decisions/ADR-011-asep-protocol-specification.md` (新規作成)
* **テスト方法**:
  * Markdown 構文に問題がないか、リンターやマークダウンビューアで表示確認する。
* **人間が確認すべき点**:
  * ADR-010 の承認（Accepted化）への最終同意。
  * 新規に起票される ADR-011 (ASEPプロトコル仕様) の内容のレビューと承認。

---

### 📌 RM-06: API エンドポイントに対する L1/L2 テストの追加
* **問題**:
  `discord_agent.py` が公開している API エンドポイント（`/memory/*`、`/asep/*`）に対する自動テストコードが実装されておらず、API 接続レベルの動作の堅牢性が担保されていない。
* **原因**:
  テスト対象がユーティリティクラス（`core.py`、`asep_middleware.py`）単体に留まり、Flask API コントローラー側のテストが未構築であったため。
* **修正方針**:
  * Flask の `test_client` を利用し、API に対する POST/GET リクエストと JSON 応答、およびヘルスチェック（`/healthz`）の正常・警告時のステータスコードを自動検証するテストコードを新規作成する。
* **修正対象ファイル**:
  * `ai-agent/workspace/tests/test_api_endpoints.py` (新規作成)
* **テスト方法**:
  * `pytest ai-agent/workspace/tests/test_api_endpoints.py` を実行し、すべてのテストケースがパスすることを確認する。
* **人間が確認すべき点**:
  * 新規追加されたテストケースの内容およびテスト結果。
