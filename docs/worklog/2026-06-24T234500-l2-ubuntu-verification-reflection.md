# ワークログ: Ubuntu実機L2検証結果の反映とコンテナ構成の正式修正

* **作成日時**: 2026-06-24T23:45:00+09:00
* **テーマ**: GPD WIN 3 (Ubuntu 26.04) での実機L2検証成功（コンテナビルド・起動・healthz応答・monitor.py起動）の公式記録、`Dockerfile` の apt-key エラー修正および `CMD` 起動要件の明文化。

---

## 1. 🎯 目的と変更の背景

人間（ユーザー）が実機 (GPD WIN 3 / Ubuntu 26.04) で実行した L2/L3検証結果を受け、以下の問題と結果をプロジェクトの公式設計および構成に反映します。
* **課題**: `Dockerfile` 内で古い Docker CLI 導入手順（`apt-key` 経由）を使用していたため、Debian buster 前提のパッケージが Ubuntu 26.04 で build エラーを引き起こしていた。また、`CMD` 定義が欠落していた。
* **対策**: `Dockerfile` から Docker CLI 導入処理を完全に削除し、安全かつ軽量な python ランタイムに修正。起動コマンド `CMD ["python3", "src/discord_agent.py"]` を明示する。
* **実績**: 実機でのビルド、コンテナ起動、Flask健康診断（`/healthz`）、Mock Discord Bot の動作成功、およびホスト側での `monitor.py` の起動と初期 LKG スナップショットの作成成功を公式の進捗（L2検証合格 ＆ L3起動成功）として記録。

---

## 2. 🛠️ 設計および修正点

### ① Dockerfile の更新
* **ファイル**: [ai-agent/Dockerfile](file:///Users/nabe/src/github.com/nabe126/kanon/ai-agent/Dockerfile)
* **内容**:
  ```dockerfile
  FROM python:3.11-slim
  WORKDIR /workspace
  COPY workspace/requirements.txt .
  RUN pip install --no-cache-dir -r requirements.txt
  COPY workspace /workspace
  CMD ["python3", "src/discord_agent.py"]
  ```

### ② docker-compose.yml の整理
* **ファイル**: [ai-agent/docker-compose.yml](file:///Users/nabe/src/github.com/nabe126/kanon/ai-agent/docker-compose.yml)
* **内容**: 不要なコメントや記述を整理し、マウントおよび環境変数の注入設定をスッキリと整備します。

### ③ README.md の更新
* **ファイル**: [README.md](file:///Users/nabe/src/github.com/nabe126/kanon/README.md)
* **内容**:
  * 実機起動時の動作要件（Docker CLI 依存の排除と python3 起動）を「起動構成の要件」としてドキュメント化し、今後 `CMD` が誤って消失しないよう明記。
  * Ubuntu 26.04 での L2 実証完了の事実を記載。

### ④ bootstrap.md の進捗反映
* **ファイル**: [docs/bootstrap.md](file:///Users/nabe/src/github.com/nabe126/kanon/docs/bootstrap.md)
* **内容**:
  * `Current Status` および `Phase 1 Exit Criteria` の「Docker デプロイ検証」と「healthcheck チューニング」の進捗を `Pass (L2)` または `L2実証完了` に更新。
  * `monitor.py 起動・LKG初期作成` を `Pass (L3-Step1)` に追加。

---

## 3. 🔍 実機検証中に発見した追加事項

### ① docker-proxy 孤児プロセス問題の解消
* **事象**: `docker compose build --no-cache` 成功後、ホストの `5000` 番ポート競合によりコンテナ起動に失敗。`docker ps` は空で、他のコンテナは起動していなかった。
* **原因**: 以前のコンテナまたは別プロセスの `docker-proxy` が孤児プロセスとしてホスト側に残存していた。
* **解消手順**:
  ```bash
  # 5000番ポートを使用しているプロセスを調査
  sudo ss -ltnp | grep :5000
  
  # docker-proxy の PID を強制終了
  sudo kill <docker-proxy_pid>
  
  # その後、正常に起動成功
  docker compose up -d
  ```

### ② テストハーネス無効化の検知と未完了事項
* **事象**: `curl http://localhost:5000/healthz/fail` を実行した際、`403 Forbidden` (`Test harness is disabled.`) が返却された。
* **原因**: 現在の実装では、環境変数 `KANON_TEST_TRIGGER=true` がコンテナに正しく認識されていないか、または無効化されているため。
* **残件**:
  1. `KANON_TEST_TRIGGER` の有効化方法と環境変数注入経路の調査。
  2. 有効化後の `monitor.py` ロールバック実機結合テスト。
  3. 本物の Discord トークンおよび Gemini API キーの接続疎通確認。

---

## 4. 🔄 ロールバック手順

1. 今回の変更によりビルド不具合等が発生した場合、直前の安定バージョン（LKGスナップショット `backups/snapshot_20260620_230000` など）から復旧します。
   ```bash
   rm -rf src/
   cp -r backups/snapshot_20260620_230000 src/
   git restore ai-agent/Dockerfile ai-agent/docker-compose.yml README.md docs/bootstrap.md
   ```

---

## 5. 🚦 現在の検証ステータス

| Exit Criteria 項目 | 期待動作 | 判定結果 | 備考 |
| :--- | :--- | :---: | :--- |
| **Dockerデプロイ検証** | コンテナ起動、Flask疎通、Mock起動 | **Pass (L2)** | Ubuntu 26.04 実機にて実証完了 |
| **healthcheckパース検証** | metrics 取得、healthz応答 | **Pass (L2)** | Ubuntu 26.04 実機にて実証完了 |
| **monitor.py 起動・LKG初期作成** | monitor.py が起動し LKG が保存される | **Pass (L3-Step1)** | Ubuntu 26.04 実機にて実証完了 |
| **Discord実接続確認** | BotがDiscordへログインし ready ログが出る | **Pending** | 次回以降に検証予定 |
| **Gemini実疎通確認** | API呼び出しで応答が正しく返る | **Pending** | 次回以降に検証予定 |
| **monitor.py ロールバック成功** | unhealthy 3回検知後に再起動が走る | **Pending** | 次回以降に検証予定 |
| **LKG復元成功の実証** | ロールバック時に LKG からコードが復元される | **Pending** | 次回以降に検証予定 |
| **healthcheck閾値の実機確認** | 実機の平常負荷で warning/unhealthy に誤動作しない | **Pending** | 次回以降に検証予定 |
