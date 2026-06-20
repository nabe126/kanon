# ワークログ: validator.py における候補コードの検証・適用エンジンの設計

* **作成日時**: 2026-06-20T22:40:00+09:00
* **テーマ**: 候補コード（candidates）に対する構文・依存検証、バックアップ退避、および本番コードへの自動適用を行う `apply_candidate_code` API の設計。

---

## 1. 🎯 目的と変更の背景

技術 Phase 1 (Survival & Observation) における重要な要件は「無検証でのコード適用禁止」です。
エージェントが自律的または指示により自己改変を行う際、構文チェックとインポートチェックを必ず通し、合格した場合のみ現行安定版（LKG）をバックアップにコピーして適用する「安全な自己改変適用エンジン」が必要です。
このプロセスをユーティリティ化することで、将来的な Phase 2 / Phase 3 での自律改変時におけるコード破壊や無限再起動デッドロックを未然に防ぎます。

---

## 2. 🛠️ 設計詳細

### ① `apply_candidate_code` 関数の設計
* **配置場所**: [utils/validator.py](file:///Users/nabe/src/github.com/nabe126/kanon/ai-agent/workspace/src/utils/validator.py)
* **引数**:
  * `candidate_path`: 一時保存された検証対象の Python コードのパス
  * `target_path`: 適用先（本番）の Python コードのパス
  * `backup_dir`: 更新直前に退避するバックアップ保存先ディレクトリ
* **処理フロー**:
  1. `check_syntax(candidate_path)` による構文エラー検証。
  2. `check_import(candidate_path)` による依存関係インポート・未定義変数検証。
  3. 検証合格時、`target_path` に既存ファイルがあれば `backup_dir` 配下に `.bk` の拡張子でバックアップコピーを作成。
  4. `candidate_path` の内容を `target_path` に上書きコピー。

### ② テスト設計 (L1)
* [ai-agent/workspace/tests/test_validator.py](file:///Users/nabe/src/github.com/nabe126/kanon/ai-agent/workspace/tests/test_validator.py) に以下のテストを追加：
  * 正常な Python コードが検証を通って正しく適用され、バックアップが作成されること。
  * 異常な Python コード（構文エラー、インポートエラー）が検証で弾かれ、適用されない（本番コードが破壊されない）こと。

---

## 3. 🔄 ロールバック手順

1. 万が一、今回の変更により `validator.py` にバグが発生した場合、事前退避した LKG スナップショット（`backups/snapshot_20260620_223500` など）から復元します。
   ```bash
   rm -rf src/
   cp -r backups/snapshot_20260620_223500 src/
   ```

---

## 4. 🚦 現在の検証ステータスと計画

| 機能名 | 検証レベル | ステータス | 備考 |
| :--- | :--- | :--- | :--- |
| **validator.py** (本件) | L1 / L2 | **Todo (L1)** | 検証適用機能の実装とテスト |
| healthcheck.py | L1 / L2 | Pass (L1) | 閾値判定実装・テストパス済 |
| monitor.py | L1 / L2 | Pass (L1) | 世代スナップショット確認済 (Experimental) |
| discord_agent.py | L1 / L2 | Pass (L1) | モック/本物接続およびFlask /healthz 連動確認済 |
