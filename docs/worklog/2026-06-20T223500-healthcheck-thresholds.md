# ワークログ: healthcheck.py におけるリソース閾値監視とステータス制御の設計

* **作成日時**: 2026-06-20T22:35:00+09:00
* **テーマ**: healthcheck.py に CPU、メモリ、ディスク使用率の閾値判定を導入し、異常時に status を `warning` や `unhealthy` に動的変更する設計。

---

## 1. 🎯 目的と変更の背景

現在の [utils/healthcheck.py](file:///Users/nabe/src/github.com/nabe126/kanon/ai-agent/workspace/src/utils/healthcheck.py) は、メトリクス収集の処理中に例外（エラー）が発生した時のみ `status: warning` と判定しており、リソースの逼迫（CPU高負荷、メモリ不足、ディスク空き容量ゼロなど）によるハングアップ予兆を検知できません。
ホスト側の [controller/monitor.py](file:///Users/nabe/src/github.com/nabe126/kanon/controller/monitor.py) が異常を検知し自動復旧（コンテナ再起動）させるためには、`/healthz` がリソース逼迫時に `unhealthy` (ステータスコード 500) を返す必要があります。
本改修により、実用的なリソース閾値監視を導入し、生存・監視基盤（Phase 1）をより強固なものにします。

---

## 2. 🛠️ 設計詳細

### ① 閾値の定義
* **ディスク使用率 (Disk Usage)**:
  * `warning`: 90% 以上
  * `unhealthy`: 95% 以上
* **メモリ使用率 (Memory Usage)**:
  * `warning`: 90% 以上
  * `unhealthy`: 95% 以上
* **CPUロードアベレージ (CPU Load Average - load_1m)**:
  * CPU コア数 (`os.cpu_count()`) を基準とします（非存在時はデフォルト 4 コアと仮定）。
  * `warning`: `load_1m` が `os.cpu_count() * 1.5` 以上
  * `unhealthy`: `load_1m` が `os.cpu_count() * 3.0` 以上

### ② ステータス判定ロジック
* `metrics` ディクショナリの初期 `status` を `"healthy"` とします。
* 各種メトリクス取得後、定義した閾値に照らし合わせ、最も深刻度の高いステータス (`unhealthy` > `warning` > `healthy`) に `metrics["status"]` を更新します。
* 例外発生時は従来通り `"warning"` にフォールバックします。

### ③ テスト設計 (L1)
* [ai-agent/workspace/tests/test_healthcheck.py](file:///Users/nabe/src/github.com/nabe126/kanon/ai-agent/workspace/tests/test_healthcheck.py) に以下のテストを追加：
  * CPU, Memory, Disk の閾値に応じたステータス判定（Mockデータを用いた単体テスト）が正しく動作すること。

---

## 3. 🔄 ロールバック手順

1. 万が一、今回の変更により `healthcheck.py` が正常にインポートできなくなったり、無限ループやクラッシュを引き起こした場合、[controller/monitor.py](file:///Users/nabe/src/github.com/nabe126/kanon/controller/monitor.py) もしくは git restore によって直前の LKG スナップショット（`backups/snapshot_20260620_222500` など）から復元します。
   ```bash
   rm -rf src/
   cp -r backups/snapshot_20260620_222500 src/
   ```

---

## 4. 🚦 現在の検証ステータスと計画

| 機能名 | 検証レベル | ステータス | 備考 |
| :--- | :--- | :--- | :--- |
| **healthcheck.py** (本件) | L1 / L2 | **Todo (L1)** | 閾値判定の実装とテスト |
| monitor.py | L1 / L2 | Pass (L1) | 世代スナップショット確認済 (Experimental) |
| discord_agent.py | L1 / L2 | Pass (L1) | モック/本物接続およびFlask /healthz 連動確認済 |
