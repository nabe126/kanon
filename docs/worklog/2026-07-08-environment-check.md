# 実機検証環境 (GPD WIN 3 / Ubuntu) 事前確認レポート

* **確認実施日**: 2026-07-08
* **対象環境**: GPD WIN 3 / Ubuntu 26.04 (検証ドメイン)
* **目的**: `Sprint Discord` の本格的な実機検証に先立ち、インフラ・ネットワーク・API・起動環境に起因する問題を切り分け、アプリ側の不具合と分離する。
* **確認ステータス**: **[人間による実行および入力待ち]**

---

## 📋 1. 確認項目および実行コマンド一覧

実機（GPD WIN 3 / Ubuntu）のターミナルにログインし、以下の手順に沿って確認コマンドを実行して結果を記録してください。

### ① Docker インストール状態の確認
* **目的**: ホストマシン上で Docker デーモンが正常に起動し、コンテナを動作させられるかを確認する。
* **確認コマンド**:
  ```bash
  docker --version
  systemctl status docker --no-pager
  ```
* **期待される結果**:
  - `Docker version 20.10.x` 以上がインストールされていること。
  - `Active: active (running)` と表示され、デーモンが稼働中であること。
* **実際の確認結果**:
  - `docker --version`: `Docker version 29.1.3, build 29.1.3-0ubuntu4.1`
  - `systemctl status docker`: `active (running) since Thu 2026-04-16 03:33:04 JST` (正常稼働中)

---

### ② docker compose version の確認
* **目的**: 本番用の `docker-compose.yml` (v3.8) を解釈し実行できるCompose環境があるか確認する。
* **確認コマンド**:
  ```bash
  docker compose version
  ```
* **期待される結果**:
  - `Docker Compose version v2.x.x` 以上の CLI プラグイン、または `docker-compose version 1.29.x` 以上が利用可能であること。
* **実際の確認結果**:
  - `Docker Compose version 2.40.3+ds1-0ubuntu1` (利用可能)

---

### ③ Git checkout 状態 of 確認
* **目的**: 開発環境（M4 Mac）からプッシュされた最新のインフラ修正（`Sprint RM-Infra`）および `agent.py`（CLI REPL）が正しく適用されているか確認する。
* **確認コマンド**:
  ```bash
  git fetch origin
  git status
  git log -n 5 --oneline
  ```
* **期待される結果**:
  - `Your branch is up to date with 'origin/main'.` (または最新ブランチと同期していること)。
  - 最新のコミットログに `79191f6 fix(infra): mount memory/ and docs/ into agent container [RM-03]` およびそれ以降のコミットが含まれていること。
* **実際の確認結果**:
  - `git status`: `origin/main` と同期済み (git pull 実行完了)
  - `git log (HEAD)`: `a1e16a8 (HEAD -> main, origin/main)` （`79191f6` 等が含まれていることを確認）

---

### ④ .env 配置方法の確認
* **目的**: 隔離領域 `ai-agent/secrets/.env` が正しく配置され、パーミッションが設定されているか確認する。
* **確認コマンド**:
  ```bash
  ls -la ai-agent/secrets/.env
  ```
* **期待される結果**:
  - `ai-agent/secrets/.env` ファイルが実在すること。
  - ファイル内に以下の環境変数が設定されていること（※APIキーの中身は画面やログに出力しないこと）：
    - `GEMINI_API_KEY`
    - `DISCORD_BOT_TOKEN`
* **実際の確認結果**:
  - ファイル有無: [x] 存在する / [ ] 存在しない
  - パーミッション: `-rw-rw-r-- 1 nabe3 nabe3 146` (適切)

---

### ⑤ Gemini API 疎通および CLI REPL の動作確認
* **目的**: 実機環境のネットワークから Google Gemini API への疎通が通り、CLI REPL が正常に動作するか確認する。
* **確認コマンド**:
  ```bash
  # 1. 仮想環境のアクティベートおよび CLI 起動
  PYTHONPATH=ai-agent/workspace ai-agent/workspace/.venv/bin/python3 ai-agent/workspace/src/agent.py
  ```
* **期待される結果**:
  - `✅ KANON_GEMINI_API_KEY を検出・ロードしました。` と表示され、入力プロンプト `👤 User >` が表示されること。
  - プロンプトに「こんにちは」と入力し、Gemini から日本語で正常に応答が返却されること。
  - `/exit` で正常終了すること。
* **実際の確認結果**:
  - ロード成否: [x] 成功 / [ ] 失敗 (モックモード起動)
  - 応答結果: 最初はAPI高負荷による503一時エラーが発生したものの、再試行で正常に応答（「こんばんは、こんにちは！😊」等）し、/quitで正常終了したことを確認。

---

### ⑥ ai-agent compose 起動可否の確認
* **目的**: 本番用の `docker-compose.yml` の定義に構文エラーがなく、コンテナがビルド・起動できるか確認する。
* **確認コマンド**:
  ```bash
  # 1. compose 定義の整合性確認
  docker compose -f ai-agent/docker-compose.yml config
  
  # 2. コンテナのビルドと起動テスト
  docker compose -f ai-agent/docker-compose.yml up -d --build
  
  # 3. 起動ログと状態の確認
  docker ps -a
  docker logs ai_agent_core
  
  # 4. テスト用クリーンアップ
  docker compose -f ai-agent/docker-compose.yml down
  ```
* **期待される結果**:
  - `config` コマンドでエラーが出力されないこと。
  - コンテナイメージのビルドおよび起動が正常終了し、`ai_agent_core` コンテナが `Up` 状態であること。
  - `docker logs` にエラーが出力されていないこと（モックモードまたは実トークンでの起動開始ログが出ていること）。
* **実際の確認結果**:
  - `config` 結果: [x] 正常 / [ ] エラー有 (内容: 構文解析は正常。--env-file指定によりKANON_TEST_TRIGGER以外の警告は解消)
  - `docker ps` 状態: `ai_agent_core` は `Up` (正常起動を確認。ポート 5000 競合は docker-proxy の kill により解決)
  - `docker logs` 特記事項: 正常に起動し、Discord クライアントへのログインまで完了。`docker compose down` 時に AppArmor に起因する停止エラーが発生したが、`aa-remove-unknown` を実行することで正常にクリーンアップ・停止できることを確認。
