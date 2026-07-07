# 進捗監査レポート (Project Progress Audit)

* **監査対象プロジェクト**: Kanon (Project Code: Arahabaki)
* **監査実施日**: 2026-07-07
* **監査基準**: 設計書やREADMEの記述ではなく、実際のリポジトリ内のコード、テスト、および検証ログ（実証データ）

---

## 1. Executive Summary

Kanonプロジェクトは現在、**Phase 1 (会話の確立)** の最終検証、および **Phase 2 (長期記憶基盤)** の初期実装段階にあります。
`pytest` による L1 結合テストや、Docker Compose を用いた L3 統合シミュレーション環境が構築され、自動ロールバック監視（`monitor.py`）やコードの安全実行プロトコル（`asep_middleware.py`）の骨格が動作可能なレベルで実装されていることを確認しました。
しかし、検証ログ（`l3_evidence.txt`）から、**「コンテナの自動再起動（`docker restart`）処理が、特権やコマンドの不在により実際には失敗しており、エージェント側のホットリロード機能によって偶然復旧していた」** という重大な不整合が確認されました。また、本番用の `docker-compose.yml` において Sandbox化の設計と相反する `docker.sock` のマウントや、長期記憶領域のマウント漏れが発見され、本番適用には依然としてインフラ構成上の大きな課題が残されています。

---

## 2. Completed (実装・動作確認済み)

実際のコードおよびテストから、以下の機能が動作可能な形で実装されていることを確認しました。

* **Discord 対話機能と会話履歴管理**:
  * メンションまたはDM受信時に `gemini-2.5-flash` を呼び出して応答する Bot のコア機能。
  * `ConversationHistory` クラスによるセッションごとの会話履歴の JSON 保存。
  * **証拠コード**: 
    * [ai-agent/workspace/src/discord_agent.py](file:///Users/nabe/src/github.com/nabe126/kanon/ai-agent/workspace/src/discord_agent.py)
    * [ai-agent/workspace/src/utils/history.py](file:///Users/nabe/src/github.com/nabe126/kanon/ai-agent/workspace/src/utils/history.py)
* **エージェントプロセスのホットリロード機能**:
  * ファイル変更を検知してエージェントの Python 子プロセスを自動再起動する親プロセスリローダー。
  * **証拠コード**: [ai-agent/workspace/src/discord_agent.py#L338-L393](file:///Users/nabe/src/github.com/nabe126/kanon/ai-agent/workspace/src/discord_agent.py#L338-L393)
* **システムリソースの健康監視ユーティリティ**:
  * Linux の `/proc` 情報（CPU負荷・メモリ）および Python 標準の `shutil.disk_usage` を用いて、ホストPCのCPU/メモリ/ディスク健康状態を判定（healthy/warning/unhealthy）する機能（Mac等の非Linux環境向けのダミーフォールバック処理も内包）。
  * **証拠コード**: [ai-agent/workspace/src/utils/healthcheck.py](file:///Users/nabe/src/github.com/nabe126/kanon/ai-agent/workspace/src/utils/healthcheck.py)
* **ソースコードの構文・依存関係検証ユーティリティ**:
  * `py_compile` による文法チェック（Syntax check）、および別プロセスでの `importlib` によるモジュール読込テスト（Import check）。
  * **証拠コード**: [ai-agent/workspace/src/utils/validator.py](file:///Users/nabe/src/github.com/nabe126/kanon/ai-agent/workspace/src/utils/validator.py)
* **記憶サブシステム (Memory MVP - L1/L3/L4)**:
  * L1（ワーキングメモリ）における最大5スロットのアクティブトピック容量制限と、溢れた最古トピックの L3 Markdown ファイルへの自動退避（Flashing）。
  * 記憶 Markdown ファイル更新時の自動 Git コミット処理（`git_auto_commit`）。
  * `L1 ➔ L3 ➔ L4` の優先順位に従うフォールバックキーワード Grep 検索（Read Bus）。
  * **証拠コード**: [ai-agent/workspace/src/memory/core.py](file:///Users/nabe/src/github.com/nabe126/kanon/ai-agent/workspace/src/memory/core.py)
* **安全実行プロトコル (ASEP - Agent Safe Execution Protocol)**:
  * 操作リスク（L0〜L3）に応じた実行計画（PLAN）の起票、人間による承認ゲート、実処理の評価と実行結果（STDOUT/STDERR/スタックトレース等）の Markdown 追記。
  * **証拠コード**: [ai-agent/workspace/src/utils/asep_middleware.py](file:///Users/nabe/src/github.com/nabe126/kanon/ai-agent/workspace/src/utils/asep_middleware.py)
* **テスト環境（L1/L3 テスト）**:
  * `pytest` による健康監視、コード検証、ロールバック等の単体・結合テスト群（L1検証）。
  * Docker Compose を用いた、障害注入から自動復旧・ロールバックを検証する統合シミュレーション（L3検証）。
  * **証拠コード**: 
    * [ai-agent/workspace/tests/test_monitor.py](file:///Users/nabe/src/github.com/nabe126/kanon/ai-agent/workspace/tests/test_monitor.py)
    * [ai-agent/workspace/tests/run_l3_simulation.py](file:///Users/nabe/src/github.com/nabe126/kanon/ai-agent/workspace/tests/run_l3_simulation.py)

---

## 3. In Progress (実装途中・検証待ち)

設計書に存在するが、実装が途中であるか、または検証が完了していない項目です。

* **自動ロールバックにおける「コンテナ再起動処理」 [実装バグあり・修正待ち]**:
  * L3シミュレーションの検証ログ（`l3_evidence.txt`）から、`monitor.py` が LKG (Last Known Good) ディレクトリから `src/` を復元する処理には成功しているものの、**`docker restart` コマンドを実行した際に `[Errno 2] No such file or directory: 'docker'` というエラーで失敗している** ことが確認されました。
  * 現在のテスト環境（L3）が合格（SUCCESS）と判定されているのは、`monitor.py` が LKG を復元し Python ファイルを `touch` したことで、`discord_agent.py` の**ホットリロード機能が動作し、たまたまエージェントが healthy 状態に復帰したため**です。本来設計されている「コンテナの Docker レベルでの強制再起動」は機能していません。
  * **証拠ログ**: [ai-agent/workspace/l3_evidence.txt#L49-L51](file:///Users/nabe/src/github.com/nabe126/kanon/ai-agent/workspace/l3_evidence.txt#L49-L51)
* **コードの自動検証本番適用 (apply_candidate_code) [実機検証待ち]**:
  * `validator.py` にコード適用機能が実装されていますが、本番経路（`discord_agent.py` など）からはインポート・使用されていません。エージェント憲章の指示に従い、実機検証（Discord/Gemini実接続など）が完了するまで意図的に本番適用が保留（Pending）されています。
* **長期記憶（L2 - 中期記憶 / 未整理ログバッファ）[設計のみ・未着手]**:
  * ロードマップや設計資料には、L2（中期記憶）の存在や `L1 ➔ L3 ➔ L4 ➔ L2` のフォールバック検索（Read Bus）が明記されていますが、[core.py](file:///Users/nabe/src/github.com/nabe126/kanon/ai-agent/workspace/src/memory/core.py) 内には L2 用のディレクトリ定義や、Grep検索フォールバックの対象として L2 を走査する処理が一切実装されていません。

---

## 4. Not Started (未着手)

READMEやロードマップに定義されていますが、ソースコード上で実装が確認できない項目です。

* **Gemini API 503エラー対策 (指数バックオフ自動リトライ)**:
  * ADR-004 にて「最大5回リトライ」が承認されていますが、[discord_agent.py](file:///Users/nabe/src/github.com/nabe126/kanon/ai-agent/workspace/src/discord_agent.py) および [autonomous_agent.py](file:///Users/nabe/src/github.com/nabe126/kanon/ai-agent/workspace/src/autonomous_agent.py) の API 呼び出し部分にリトライや指数バックオフのコードは実装されていません。
* **LLMプロバイダ抽象化レイヤー (Provider Abstraction) / Multi-LLM 対応**:
  * ADR-003 で定義されている、特定の LLM SDK に依存しない「Providerクラス」等の共通インターフェースの実装。現在のコードは `from google import genai` を直接インポートして Gemini専用の処理が密結合しています。
* **Sandbox System (エージェント ➔ コントローラー間の特権再起動通信API)**:
  * 技術ロードマップ（Technical Phase 5）の完了条件として挙げられている、「コンテナ内に `docker.sock` をマウントせず、エージェントからの再起動要求を安全に中継する Controller 側の API / プロキシ」。現状、このような中継通信APIの実装コードは存在しません。

---

## 5. Repository Health (リポジトリの健全性評価)

* **README/設計書との整合性**:
  * **不整合 (セキュリティリスク)**: READMEには「エージェントコンテナに `docker.sock` がマウントされていないこと」とありますが、実際の [ai-agent/docker-compose.yml](file:///Users/nabe/src/github.com/nabe126/kanon/ai-agent/docker-compose.yml)（本番用）では `volumes: - /var/run/docker.sock:/var/run/docker.sock` と、エージェントに直接マウントされています。
  * **不整合**: `monitor` の L3 テスト環境（[docker-compose.test-l3.yml](file:///Users/nabe/src/github.com/nabe126/kanon/docker-compose.test-l3.yml)）で、`monitor` コンテナに `docker.sock` がマウントされておらず、[Dockerfile.monitor](file:///Users/nabe/src/github.com/nabe126/kanon/controller/Dockerfile.monitor) でも `docker` CLI が入っていないため、再起動処理が失敗しています。
* **ドキュメントの不足**:
  * `discord_agent.py` に実装されているホットリロード機能（`start_parent_reloader_process`）の動作や、それがロールバック監視とどのように協調するのかに関する設計ドキュメントが存在しません。
* **ADR (設計決定レコード) のステータスと不足**:
  * [ADR-010-memory-mvp-architecture.md](file:///Users/nabe/src/github.com/nabe126/kanon/docs/decisions/ADR-010-memory-mvp-architecture.md) のステータスが **`Proposed (提案中)`** のままですが、コード実装は先行して完了しています。
  * すでに `asep_middleware.py` として実装されている「ASEP (安全実行プロトコル)」に関する ADR が存在しません。
* **テストの不足**:
  * `discord_agent.py` が公開している API（`/memory/remember`, `/memory/recall`, `/asep/plan`, `/asep/approve`）に対する正常系・異常系の統合的な自動テスト（L1/L2）が存在しません。
* **Dead code (不要ファイル・未使用コード)**:
  * [ai-agent/workspace/src/agent.py](file:///Users/nabe/src/github.com/nabe126/kanon/ai-agent/workspace/src/agent.py): 起動確認用のプリント文があるのみで、本番では使用されていません。
  * [ai-agent/workspace/src/autonomous_agent.py](file:///Users/nabe/src/github.com/nabe126/kanon/ai-agent/workspace/src/autonomous_agent.py): 10秒ごとのダミーループを回すだけの実験用コードであり、本番の Discord 接続 Bot からは使用されていません。
  * [ai-agent/Dockerfile.bk](file:///Users/nabe/src/github.com/nabe126/kanon/ai-agent/Dockerfile.bk): 古いバックアップファイルが残存しています。
* **ディレクトリ構成とボリュームマウントの問題**:
  * **致命的欠陥**: 本番用の [ai-agent/docker-compose.yml](file:///Users/nabe/src/github.com/nabe126/kanon/ai-agent/docker-compose.yml) において、ルートにある長期記憶領域 `memory/` およびドキュメント領域 `docs/` がコンテナにマウントされていません（`volumes: - ./workspace:/workspace` のみ）。これでは、コンテナ内のエージェントが記憶をフラッシュしたり、引継ぎドキュメントを作成したりする際に、親ディレクトリを参照できずエラーになるか、コンテナ内の揮発的な領域に書き込まれてデータが消失します。

---

## 6. Risks (今後のリスクと詰まりそうなポイント)

* **ホットリロードとコンテナ再起動の二重トリガー・競合**:
  * ロールバック発生時に `monitor.py` が LKG ファイルを `src/` に復元すると、ファイルのタイムスタンプ更新によってエージェントのホットリロードが走り、ほぼ同時に `monitor` 側が `docker restart` を実行しようとします。この時、プロセスの強制終了とコンテナ再起動のタイミングが重なり、状態ファイル（`conversation_history.json` 等）の破損や予期せぬ接続エラーを引き起こすリスクがあります。
* **本番運用時の長期記憶・引継ぎドキュメントの保存失敗**:
  * 前述の通り、本番用コンテナに `memory/` と `docs/` がマウントされていないため、実機（GPD WIN 3）上でエージェントを本番起動した際、記憶の書き込みや `handover.md` の作成時に書き込み失敗でシステムがクラッシュする、あるいはデータが永続化されない問題が確実に発生します。
* **特権隔離が機能しない状態での本番運用**:
  * `ai_agent_core` コンテナに `docker.sock` が直接マウントされている現在の構成は、エージェント憲章および Sandbox 化の基本設計に反しています。もしエージェントが乗っ取られたり、予期せぬコード生成エラーを起こした場合、ホストマシンの Docker デーモンを完全に掌握されるセキュリティリスクがあります。

---

## 7. Recommended Next Sprint (推奨タスク)

次回のスプリントで優先的に取り組むべき5件のタスクです。

1. **【最優先】Dockerマウントおよび特権の適正化（セキュリティとバグ修正）**
   * エージェントコンテナ（`ai_agent_core`）から `/var/run/docker.sock` のマウントを削除する。
   * テスト用 `monitor` コンテナ（またはホスト上の monitor 実行環境）に `/var/run/docker.sock` をマウントし、`controller/Dockerfile.monitor` に `docker` CLI をインストールして、`docker restart` によるロールバックが正常に動作するよう修正する。
2. **【最優先】本番コンテナへの `memory/` および `docs/` マウントの追加**
   * `ai-agent/docker-compose.yml` に `memory/` と `docs/` をボリュームマウントとして追加し、エージェントが長期記憶の書き込みおよび Git 自動コミットを正常に実行できるようにインフラ設定を整備する。
3. **【優先】ADR-010 の Accepted 承認と ASEP の新規 ADR 起票**
   * 提案中 (Proposed) の `ADR-010` をレビュー・承認し Accepted に更新する。
   * `asep_middleware.py` に実装されている安全実行プロトコル（リスク判定と承認フロー）の仕様を `ADR-011` として新規起票し、ドキュメントの整合性を保つ。
4. **【優先】API エンドポイントに対するテストコード (L1/L2) の追加**
   * `discord_agent.py` が提供する `/memory/*` および `/asep/*` エンドポイントに対し、正常に記憶・検索・計画承認ができることを検証する自動テストを追加し、テスト成熟度を高める。
5. **【通常】デッドコードの整理と削除**
   * 未使用の `agent.py` および `autonomous_agent.py` を廃止・削除（あるいは `tests/` 配下に隔離）し、`Dockerfile.bk` を削除してリポジトリをクリーンにする。
