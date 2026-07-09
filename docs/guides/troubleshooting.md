# Kanon 運用トラブルシューティングガイド (実機/ホスト混在環境)

本ドキュメントは、Kanon (Arahabaki Core) を GPD WIN 3 (Ubuntu) などの実機環境、および Docker とホストプロセスの混在環境で運用する際に発生する代表的なトラブルと、その解決手順をまとめたものです。

原則として、人が手順を覚えるのではなく、ルートの **`Makefile`** にツールとしてコマンドを登録し、リポジトリに記憶させています。

---

## 📋 代表的なトラブルと解決手順

### 1. `PermissionError: [Errno 13] Permission denied: '.../state/agent.log'`
* **原因**: 
  Docker コンテナが root 権限で `/workspace/state` ディレクトリ、またはログファイルを生成したため、ホストマシンの一般ユーザー（`nabe3`）から書き込みできなくなりました。
* **解決方法**:
  ルートの `Makefile` からワンコマンドで所有権を一般ユーザーに修正します。
  ```bash
  make fix-perms
  ```
  *(手動コマンド: `sudo chown -R $(whoami):$(whoami) ai-agent/workspace/state`)*

---

### 2. `failed to bind host port 0.0.0.0:5000/tcp: address already in use`
* **原因**:
  以前起動したコンテナの残骸、テスト用の Flask プロセス、またはゾンビ状態の `docker-proxy` がホストのポート `5000` を占有（LISTEN）したままになっています。
* **解決方法**:
  ポートを占有しているプロセスを特定し、強制終了（kill）させます。
  ```bash
  # 状況確認
  make status
  
  # ポート 5000 ゾンビプロセスの強制解放
  make fix-port
  ```
  *(手動コマンド: `sudo kill -9 $(sudo lsof -t -i:5000)`)*

---

### 3. `cannot stop container: ...: permission denied` (docker compose down 時)
* **原因**:
  Ubuntu 上のセキュリティモジュールである **AppArmor** が、Docker デーモンのコンテナ停止処理（停止シグナル）を誤ってブロックしてしまっています。
* **解決方法**:
  AppArmor の不要な古いプロファイルをクリーンアップします。
  ```bash
  make fix-apparmor
  ```
  *(手動コマンド: `sudo aa-remove-unknown`)*

---

### 4. `-bash: ai-agent/workspace/.venv/bin/python3: そのようなファイルやディレクトリはありません`
* **原因**:
  ホスト側（実機側）に Python の仮想環境（`.venv`）が作成されていません。また、Debian/Ubuntu では `python3-venv`（`python3.14-venv` 等）がインストールされていないと仮想環境が作れません。
* **解決方法**:
  必要なシステムパッケージのインストールと、仮想環境の自動構築、依存関係の pip ロードを一度に実行します。
  ```bash
  make setup-venv
  ```

---

### 5. `The "GEMINI_API_KEY" variable is not set. Defaulting to a blank string.` (警告)
* **原因**:
  ホストマシンのシェル環境変数に API キーや Discord トークンが定義されていない状態で `docker compose` コマンドを叩いたため、警告が表示されています。
* **解決方法**:
  `secrets/.env` に定義された値を明示的に読み込むよう `--env-file` オプションをつけて実行します。
  `Makefile` で定義されているコマンドは、すべて自動で `--env-file` を補完するようになっています。
  ```bash
  # 起動時
  make up
  
  # 停止時
  make down
  ```
  *(手動コマンド: `docker compose -f ai-agent/docker-compose.yml --env-file ai-agent/secrets/.env up -d --build`)*
