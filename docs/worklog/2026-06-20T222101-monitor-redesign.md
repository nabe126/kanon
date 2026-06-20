# ワークログ: monitor.py 世代管理実装と自動ロールバック設計の高度化

* **作成日時**: 2026-06-20T22:21:01+09:00
* **更新日時**: 2026-06-20T22:21:01+09:00
* **テーマ**: monitor.py におけるバックアップの複数世代管理および LKG (Last Known Good) 復旧ロジックの実装、テストコード拡充。

---

## 1. 🔍 背景と課題

[controller/monitor.py](file:///Users/nabe/src/github.com/nabe126/kanon/controller/monitor.py) の初期実装では、バックアップが1世代のみの直接上書き保存であったため、以下のような「エラーコードの上書き・固定化による無限ロールバックループ（デッドロック）」を引き起こす致命的な設計欠陥が存在していました。

* エージェントが構文チェックを通り抜けた致命的な不具合を持つコード (`bad.py`) を適用し再起動。
* 再起動失敗時にモニターが `bad.py` をロールバック元のバックアップに上書き退避させてしまい、結果的に `bad.py` を復旧し続ける。

このデッドロックを完全に回避するため、タイムスタンプ形式の複数世代管理、および最後に正常動作が確認された時点のスナップショットを特定する「LKG (Last Known Good)」管理構造を導入しました。

---

## 2. 🛠️ 実施された実装内容

### ① monitor.py の改修
* **ファイル**: [controller/monitor.py](file:///Users/nabe/src/github.com/nabe126/kanon/controller/monitor.py)
* **改修ポイント**:
  * **スナップショットの世代化**: バックアップ保存時、`snapshot_YYYYMMDD_HHMMSS/` ディレクトリを動的に作成し、`src/` 配下を丸ごと退避。最大5世代保持し、超えた場合は最も古い世代を自動ローテーション削除 (`clean_old_snapshots()`)。
  * **LKG参照の導入**: 起動成功時、または再起動エラーから healthy に回復した瞬間に、その時のスナップショットを `backups/LKG.json` にパス情報とタイムスタンプとしてシリアライズ保存。
  * **自動ロールバックの安全化**: 異常検知時、`LKG.json` に記録されたスナップショットからコードを `src/` 配下に復旧。同時に、何が原因でエラーになったかを解析できるよう、現在の壊れた `src/` 自体もデバッグ用スナップショットとして自動でバックアップ退避してから消去・上書き。
  * **環境パラメータ設定化**: `HEALTHZ_URL` や `CONTAINER_NAME` などのパラメータをホスト側の環境変数から取得可能（フォールバック付）に修正。

### ② monitor 用単体テストの新規作成
* **ファイル**: [ai-agent/workspace/tests/test_monitor.py](file:///Users/nabe/src/github.com/nabe126/kanon/ai-agent/workspace/tests/test_monitor.py)
* **テストケース**:
  * `test_create_snapshot_and_rotation()`: 世代ローテーションが働き最大5世代に抑えられること。
  * `test_save_and_get_lkg()`: `LKG.json` が期待通り保存・読み取りできること。
  * `test_check_health_healthy()` / `test_check_health_failed()`: モックを用いた `/healthz` API 判定。
  * `test_execute_rollback()`: 異常コードを配置した状態から、自動で LKG から正常コードが復帰・配置され、サブプロセスの docker コマンドが呼ばれること。

---

## 3. テストと動作検証

仮想環境（`.venv/`）内でテストランナーを実行。

* **コマンド**: `python -m pytest tests/`
* **結果**: **11 passed, 1 warning in 7.45s**
  * `test_healthcheck.py` .. Pass (2)
  * `test_monitor.py` ..... Pass (5 / 新規追加)
  * `test_validator.py` .... Pass (4)

これにより、`monitor.py` のローカル動作設計が完全に保障され、**L1 (Unit) レベルでの検証が合格**となりました。
（依然として実機連動検証前であるため、本番での自動起動は禁止し `Experimental` の位置付けを継続）。
