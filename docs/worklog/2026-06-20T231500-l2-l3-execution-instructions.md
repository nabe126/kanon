# ワークログ: 実機 L2/L3 検証実行コマンドと手動確認手順

* **作成日時**: 2026-06-20T23:15:00+09:00
* **テーマ**: AI エージェントの SSH 権限不足に伴う、人間（ユーザー）による実機（GPD WIN 3）での検証手順とコマンドリスト。

---

## 1. 🎯 目的

AI エージェント（Mac）から実機（GPD WIN 3 / 192.168.10.204）への SSH 接続が認証制限（Permission denied）のため自動実行できません。
そのため、実機上で人間（ユーザー）が実行すべき検証コマンド群と、確認すべき期待出力をチェックリスト化し、実機検証の完了判定をコラボレーション形式で実施します。

---

## 2. 🛠️ 実機検証コマンドと確認項目

ユーザーは GPD WIN 3 (Ubuntu) にて、以下のコマンドを順次実行し、その出力を本チャットにフィードバックしてください。

### ① Docker デプロイ・起動検証 (L2)
* **実行コマンド**:
  ```bash
  cd kanon/ai-agent
  docker-compose up --build -d
  ```
* **確認事項**:
  * `ai_agent_core` コンテナが正常にビルド・起動し、`State: Running` になること。

### ② healthz エンドポイント疎通＆メトリクス検証 (L2/L3)
* **実行コマンド**:
  ```bash
  curl -s http://localhost:5000/healthz | jq .
  ```
* **確認事項**:
  * CPUロードアベレージ、メモリ使用率、ディスク空き容量のリアルタイム値が JSON で正しく返却されること。
  * `status` が `healthy` になっていること。
  * （※ `jq` コマンドがない場合は、`curl -s http://localhost:5000/healthz` だけで構いません）

### ③ monitor.py の自動ロールバックおよび LKG 復元検証 (L2/L3)
1. **モニターの起動**:
   * ホスト側でモニターを起動。
     ```bash
     cd kanon/controller
     python monitor.py
     ```
   * **期待出力**: `[Monitor] Agent is healthy at startup. Registering initial LKG snapshot...` と表示され、`backups/` 以下に初期 LKG スナップショットが作られること。
2. **疑似障害のトリガー**:
   * 別ターミナルからテストハーネスを叩いて疑似障害を発生させる。
     ```bash
     curl http://localhost:5000/healthz/fail
     ```
3. **ロールバックの確認**:
   * `monitor.py` のターミナルに以下が表示されることを確認する。
     * `Healthcheck failed (1/3)` ... `(3/3)` のカウントアップ。
     * `Initiating automatic rollback procedure...` の出力。
     * LKG から `src/` へのファイルコピー完了ログ。
     * `docker restart ai_agent_core` の実行および成功ログ。
4. **自動回復の確認**:
   * 60秒のクールダウン後、モニターが `Agent recovered. Resetting counter.` と表示し、新たな正常状態のスナップショットが作成・固定されること。

---

## 3. 🚦 現在の検証状況（Exit Criteria）

ユーザーから実機実行のフィードバックを受け取り次第、以下の判定を更新します。

| Exit Criteria 項目 | 期待動作 | 判定 (Pass/Fail) | 備考 |
| :--- | :--- | :---: | :--- |
| **1. Discord実接続確認** | Botがログインし ready ログが出る | 未検証 | ユーザー実機確認待ち |
| **2. Gemini実疎通確認** | API呼び出しで応答が返る | 未検証 | ユーザー実機確認待ち |
| **3. monitor.py ロールバック成功** | unhealthy 3回で復元処理が走る | 未検証 | ユーザー実機確認待ち |
| **4. LKG復元成功の実証** | ロールバック時に LKG からコードが復元される | 未検証 | ユーザー実機確認待ち |
| **5. healthcheck閾値の実機確認** | 実機の負荷に対して誤動作しない | 未検証 | ユーザー実機確認待ち |
