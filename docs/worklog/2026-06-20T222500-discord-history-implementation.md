# ワークログ: Discord接続および会話履歴（コンテキスト追跡）機能の実装設計

* **作成日時**: 2026-06-20T22:25:00+09:00
* **テーマ**: discord.py を用いた実接続 Bot ロジックの組み込み、会話履歴管理（メモリ構造の基礎）の構築、および単体テストによる動作保証。

---

## 1. 🎯 目的と変更の背景

技術 Phase 1 (Survival & Observation) の Exit Criteria を満たすため、プレースホルダーとなっていた Discord ボット機能と、長期記憶への橋渡しとなる「会話履歴（コンテキスト追跡）機構」を実装します。
また、実機 Ubuntu やローカル Mac 環境で安全に検証するため、環境変数によるモック動作・実動作の切り替えを可能とし、テスト自動化 (pytest) に対応させます。

---

## 2. 🛠️ 設計詳細

### ① Discord Bot 接続の実装設計
* **ファイル**: [ai-agent/workspace/src/discord_agent.py](file:///Users/nabe/src/github.com/nabe126/kanon/ai-agent/workspace/src/discord_agent.py)
* **スレッド構成**:
  * Flask Web サーバー (`/healthz` 提供用) をサブスレッドで稼働させる設計は維持。
  * メインスレッドで `discord.Client` または `commands.Bot` を非同期実行 (`asyncio.run()`)。
* **フォールバックとモック制御**:
  * 環境変数 `DISCORD_BOT_TOKEN` が未設定、または `KANON_MOCK_DISCORD=true` の場合は、実接続を行わずに「モック Discord ループ」を実行し、ログ出力とステータス更新 (`agent_status = "Mock active"`) を行う。これにより、APIキーのない CI 環境やローカル開発環境での L1/L2 検証をデッドロックなしでパス可能とする。
* **Gemini 連携との繋ぎこみ**:
  * Discord 上でメンションまたはメッセージを受信した際、`google-genai` (Gemini API) を呼び出し、返答を Discord チャンネルに送信する。

### ② 会話履歴（コンテキスト追跡）の設計
* **ファイル**: 新規作成 [ai-agent/workspace/src/utils/history.py](file:///Users/nabe/src/github.com/nabe126/kanon/ai-agent/workspace/src/utils/history.py)
* **責務**:
  * 各ユーザー / チャンネルごとの対話履歴（最大N件）をスレッドセーフにインメモリで保持する。
  * 障害再起動時の継続性を考慮し、`workspace/state/conversation_history.json` へ定期的に、またはメッセージ受信時に永続化する。
  * Gemini API に履歴付きでコンテキストを渡せるように、フォーマット変換メソッドを提供する。

### ③ テスト設計 (L1/L2)
* **新規テストファイル**: [ai-agent/workspace/tests/test_history.py](file:///Users/nabe/src/github.com/nabe126/kanon/ai-agent/workspace/tests/test_history.py), [ai-agent/workspace/tests/test_discord_agent.py](file:///Users/nabe/src/github.com/nabe126/kanon/ai-agent/workspace/tests/test_discord_agent.py)
* **テストケース**:
  * `history` の上限件数制御 (LRU的ローテーション) が正しく動作すること。
  * `history` が `state/conversation_history.json` へシリアライズ・デシリアライズできること。
  * モックモードで `discord_agent` を実行した際、Flask `/healthz` やメインプロセスが正常に連動して終了できること。

---

## 3. 🔄 ロールバック手順

1. 万が一、今回の変更により `ai-agent` が起動不能になったり、ループ落ちが発生した場合、[controller/monitor.py](file:///Users/nabe/src/github.com/nabe126/kanon/controller/monitor.py) の自動復旧（LKG復元）が発動します。
2. 手動ロールバックを行う場合は、`backups/` 配下の直近のスナップショットディレクトリから `src/` へファイルをコピーして復旧します。
   ```bash
   # 例:
   rm -rf src/
   cp -r backups/snapshot_YYYYMMDD_HHMMSS src/
   ```

---

## 4. 🚦 現在の検証ステータスと計画

| 機能名 | 検証レベル | ステータス | 備考 |
| :--- | :--- | :--- | :--- |
| validator.py | L1 / L2 | Pass (L1) | 構文・インポート検証確認済 |
| logger.py | L1 / L2 | Pass (L1) | 構造化ローテーション確認済 |
| healthcheck.py | L1 / L2 | Pass (L1) | Mac/Linux両フォールバック確認済 |
| monitor.py | L1 / L2 | Pass (L1) | 世代スナップショット確認済 (Experimental) |
| **discord_agent.py** (本件) | L1 / L2 | **Todo (L1/L2)** | モック対応 Bot 実装とテスト |
| **history.py** (本件) | L1 / L2 | **Todo (L1)** | 会話コンテキスト保存とテスト |
