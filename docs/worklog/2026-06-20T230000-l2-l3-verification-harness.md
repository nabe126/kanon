# ワークログ: 実機 L2/L3 検証用テストハーネスの設計と実機検証手順

* **作成日時**: 2026-06-20T23:00:00+09:00
* **テーマ**: 実機（GPD WIN 3 / Ubuntu / Docker）における `monitor.py` および `LKG復元` のロールバック結合試験を安全に実施するためのテストハーネス（疑似障害発生エンドポイント）の設計と、検証手順書の策定。

---

## 1. 🎯 目的と検証の背景

技術 Phase 1 の Exit Criteria（特に「monitor.py実機ロールバック成功」「LKG復元成功の実証」）をクリアするためには、実機上で意図的に障害を発生させ、自動復旧が動作することを確認する必要があります。
しかし、本番コードを直接破壊してテストするのは危険であり、また復旧失敗時にデッドロックするリスクもあります。
そこで、環境変数 `KANON_TEST_TRIGGER=true` が有効な場合のみ機能する「擬似障害発生用デバッグエンドポイント（`/healthz/fail`）」を [discord_agent.py](file:///Users/nabe/src/github.com/nabe126/kanon/ai-agent/workspace/src/discord_agent.py) に実装し、安全かつ再現性のある実機ロールバック試験を可能にします。

---

## 2. 🛠️ 設計詳細

### ① テストハーネス (擬似障害トリガー) の実装設計
* **ファイル**: [ai-agent/workspace/src/discord_agent.py](file:///Users/nabe/src/github.com/nabe126/kanon/ai-agent/workspace/src/discord_agent.py)
* **仕様**:
  * 環境変数 `KANON_TEST_TRIGGER` が `"true"`（大文字小文字不問）の場合のみ、Flask に `@app.route('/healthz/fail', methods=['POST', 'GET'])` を追加定義。
  * このエンドポイントが呼び出されると、グローバル変数 `agent_status` を `"Error: Simulated failure triggered"` に書き換える。
  * `/healthz` は `agent_status` に `"Error"` が含まれているため、自動的に HTTP ステータスコード `500` および `status: unhealthy` を返却するようになる。
  * これにより、ホスト側の `monitor.py` が 3 回連続で失敗を検知し、ロールバックを起動します。

### ② 実機検証手順の策定
* 実機上でのデプロイ・監視起動・障害トリガー・自動再起動確認のステップを [docs/bootstrap.md](file:///Users/nabe/src/github.com/nabe126/kanon/docs/bootstrap.md) や手順書に記載し、ユーザーがスムーズに実機実行できるようにします。

---

## 3. 🔄 ロールバック手順

1. テストハーネスの追加により `discord_agent.py` が起動しなくなった場合は、直前のスナップショット（`backups/snapshot_20260620_224000` など）から復旧します。
   ```bash
   rm -rf src/
   cp -r backups/snapshot_20260620_224000 src/
   ```

---

## 4. 🚦 現在の検証ステータスと計画

| 機能名 | 検証レベル | ステータス | 備考 |
| :--- | :--- | :--- | :--- |
| **テストハーネス (healthz/fail)** | L1 / L2 | **Todo (L1)** | テストトリガーの実装と単体テスト |
| monitor.py | L1 / L2 | Pass (L1) | 実機でのロールバック試験待ち |
| discord_agent.py | L1 / L2 | Pass (L1) | 実トークン接続試験待ち |
