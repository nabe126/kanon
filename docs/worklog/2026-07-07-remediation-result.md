# インフラ修正実施結果レポート (Remediation Result Report)

* **実施日**: 2026-07-07
* **実施者**: Antigravity
* **対象スプリント**: Sprint RM-Infra
* **検証レベル**: L1/L2 (ローカル Mac 開発環境での単体テスト 31 個合格、実機シミュレーション実行環境は Docker 不在のため実機検証待ち)

---

## 📋 各RM項目の修正結果

### 📌 RM-01: `monitor` コンテナの `docker` CLI 修復 & ソケットマウント
* **Before**:
  * L3統合シミュレーションにおいて、`monitor.py` が異常検知した際に `docker restart` コマンドを実行しようとしたが、`[Errno 2] No such file or directory: 'docker'` エラーで失敗していた。
  * `controller/Dockerfile.monitor` に Docker CLI 自体がインストールされておらず、かつ `docker-compose.test-l3.yml` にホストの Docker デーモンソケット（`docker.sock`）がマウントされていなかったため、ホスト上のコンテナを操作することが不可能だった。
* **After**:
  * [controller/Dockerfile.monitor](file:///Users/nabe/src/github.com/nabe126/kanon/controller/Dockerfile.monitor) を修正し、`apt-get` を用いて監視コンテナ内に `docker.io`（Docker CLI）をインストールする記述を追加した。
  * [docker-compose.test-l3.yml](file:///Users/nabe/src/github.com/nabe126/kanon/docker-compose.test-l3.yml) の `monitor` サービスの `volumes:` 定義に `- /var/run/docker.sock:/var/run/docker.sock` を追加した。
* **Evidence**:
  * **修正ファイル**: 
    * `controller/Dockerfile.monitor`
    * `docker-compose.test-l3.yml`
  * **コミットID**: `4b77e3c`
  * **pytest結果**: `test_monitor.py` を含む 31 テストケースがすべて正常にパス（合格）していることをローカル環境で確認。
* **Remaining Issues (残課題)**:
  * 開発環境（M4 Mac）上に Docker ランタイムが存在しないため、`run_l3_simulation.py` を用いた実機統合シミュレーションは Mac上では未実施。
  * **対応**: 次のスプリントである **Sprint 2** において、検証環境（GPD WIN 3 / Ubuntu 26.04）上での実機 L3 シミュレーションを実行し、自動ロールバック（`docker restart`）がエラーなく完了することを確認する。

---

### 📌 RM-02: `ai-agent` 本番 compose の `docker.sock` 排除
* **Before**:
  * 本番用のコンテナ起動定義である `ai-agent/docker-compose.yml` において、`volumes` に `- /var/run/docker.sock:/var/run/docker.sock` が直接マウントされていた。これは、エージェント憲章の Sandbox 設計（最小権限、特権操作の排除）に違反し、エージェント乗っ取り時にホストマシンの Docker デーモンを掌握されるセキュリティホールとなっていた。
* **After**:
  * [ai-agent/docker-compose.yml](file:///Users/nabe/src/github.com/nabe126/kanon/ai-agent/docker-compose.yml) の `agent` サービスの `volumes` 定義から `- /var/run/docker.sock:/var/run/docker.sock` の行を削除した。これによりエージェントは完全に Sandbox 内に隔離された。
* **Evidence**:
  * **修正ファイル**: `ai-agent/docker-compose.yml`
  * **コミットID**: `3061b56`
  * **pytest結果**: 31 テストケースが正常にパス。
* **Remaining Issues (残課題)**:
  * 特権マウントを排除したことで、将来的にエージェントが自己更新を要求した際にコンテナを再起動するための「再起動プロキシ / API」が未実装。
  * **対応**: 技術ロードマップの Phase 5 で規定されている通り、特権を持たないエージェントから安全な通信API経由で `controller` 側に再起動を委譲する仕組みを、将来のスプリント (Sprint 4 以降) で実装する。

---

### 📌 RM-03: `ai-agent` 本番 compose への `memory/` と `docs/` のマウント追加
* **Before**:
  * 本番用の `ai-agent/docker-compose.yml` において、エージェントが記憶を追跡する長期記憶領域である `memory/` およびドキュメント領域 `docs/` がボリュームマウントされておらず（`./workspace` のみマウント）、コンテナ内のエージェントが記憶の自動コミットや引継ぎ（handover）のドキュメント生成を行う際に親ディレクトリへのパスが解決できず、エラーになるか、書き込まれたデータがコンテナ終了時に消失する状態だった。
* **After**:
  * [ai-agent/docker-compose.yml](file:///Users/nabe/src/github.com/nabe126/kanon/ai-agent/docker-compose.yml) の `agent` サービスの `volumes` 定義に `- ../memory:/workspace/memory` および `- ../docs:/workspace/docs` を追加し、ホスト側の永続フォルダへ適切にマッピングした。
* **Evidence**:
  * **修正ファイル**: `ai-agent/docker-compose.yml`
  * **コミットID**: `79191f6`
  * **pytest結果**: 31 テストケースが正常にパス。
* **Remaining Issues (残課題)**:
  * ボリュームマウントの定義は修正されたが、検証環境（GPD WIN 3 実機）上で起動した際に、マウントされたフォルダ（`memory/`, `docs/`）に対してコンテナ内の非特権ユーザーからの書き込み権限（UID/GID の不一致）によるパーミッションエラーが起きないかを、Sprint 2 の実機検証のタイミングで確認する必要がある。
