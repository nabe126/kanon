# [ADR-009] 動作環境マトリクス (Environment Matrix) とテストレベルの定義

## ステータス
**承認済 (Accepted)** - 2026-06-20T22:09:42+09:00

---

## 1. 背景 (Context)

Kanon エージェントは Mac OS（ローカル開発環境）で開発・レビューが行われますが、最終的な本番実行環境は GPD WIN 3 (Ubuntu OS) 上の Docker コンテナ（`ai_agent_core`）です。

このため、ファイルパスのマウント状態、システムリソース（`/proc/loadavg` 等）のパース処理、Docker daemon (`/var/run/docker.sock`) へのアクセス権など、環境依存による差異が非常に大きくなっています。

開発・レビュー時に「どのテストがどこまで完了しているのか」を曖昧にすると、実機での想定外の停止（デッドロック）や誤作動を引き起こすリスクが高まります。安全性の向上とガバナンスの観点から、環境の差異とテストの成熟度レベルを明文化して管理・追跡する仕組みを定義します。

---

## 2. 動作環境マトリクス (Environment Matrix)

ローカル開発環境と本番実行環境の間の主な差異は以下の通りです。

| 項目 | 開発環境 (Mac OS / Darwin) | 本番環境 (GPD WIN 3 / Ubuntu / Docker) | エージェントコードでの対処方針 |
| :--- | :--- | :--- | :--- |
| **CPUメトリクス** | `/proc/loadavg` 非存在。 | `/proc/loadavg` が存在し読み取り可能。 | パス非存在時はダミーロード値 (0.0) を返却するフォールバックを実装。 |
| **メモリメトリクス** | `/proc/meminfo` 非存在。 | `/proc/meminfo` が存在し読み取り可能。 | パス非存在時はダミーメモリ値 (8GB / 50% 使用) を返却するフォールバックを実装。 |
| **ディスク容量** | カレントディレクトリの容量を取得。 | マウントされた `/workspace` 領域の容量を取得。 | `shutil.disk_usage` に渡すパスを、存在有無に基づいて動的に切り替える。 |
| **Docker Socket** | `docker` / `docker-compose` コマンド使用不可。 | `/var/run/docker.sock` がマウントされ、特権コマンド実行可能。 | コントローラー以外の非特権エージェントからの直接実行は制限する。 |
| **秘密情報 (.env)** | ローカルの [ai-agent/secrets/.env](file:///Users/nabe/src/github.com/nabe126/kanon/ai-agent/secrets/.env)。 | コンテナ環境変数に注入。 | エージェントプロセスからはファイルアクセスを遮断し、`os.environ` 経由でのみ参照。 |

---

## 3. テスト成熟度レベルの定義 (Test Levels)

各機能（コンポーネント）の信頼性を検証するために、3段階の検証レベルを定義します。

### 🧬 L1: Unit Test (単体テストレベル)
* **定義**: ローカル（Mac / venv 等）の Python 実行環境下における自動テスト（`pytest`）。
* **基準**:
  * 外部依存（Dockerデーモン、外部API等）をモック（Mock）で擬似化。
  * 正常系および異常系（ファイル破損、構文エラー等）の分岐を自動テストで Pass すること。

### 🌐 L2: Integration Test (コンテナ・結合テストレベル)
* **定義**: ローカルの Docker 環境、または準じたコンテナ環境における複数モジュール間の連携テスト。
* **基準**:
  * コントローラーと Sandbox エージェントコンテナが連動し、マウントディレクトリの権限にエラーが出ないこと。
  * HTTP `/healthz` の疎通とローテーションログがコンテナを跨いで正常出力されること。

### 👑 L3: Production Validation (実機・本番検証レベル)
* **定義**: ターゲット実機（GPD WIN 3 / Ubuntu）上での、本物の API 鍵および Docker socket 通信を含む実稼働確認。
* **基準**:
  * 実際に意図したエラーコードを仕込み、Controller (`monitor.py`) が異常を検知して LKG バックアップからファイルを自動書き戻し、`docker restart` でコンテナを正常復旧させるロールバックシナリオに合格すること。

---

## 4. 機能別テスト成熟度管理表

現時点（Phase 1 設計・実装完了時）における各機能の検証状況は以下の通りです。

| 機能名 | ファイルパス | L1 (Unit) | L2 (Integration) | L3 (Prod) | 状況・次回検証メモ |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **logger.py** | [workspace/src/utils/logger.py](file:///Users/nabe/src/github.com/nabe126/kanon/ai-agent/workspace/src/utils/logger.py) | **✓ Pass** | Todo | Todo | 正常にローテーションファイルが生成されることをL1で確認済。 |
| **validator.py** | [workspace/src/utils/validator.py](file:///Users/nabe/src/github.com/nabe126/kanon/ai-agent/workspace/src/utils/validator.py) | **✓ Pass** | — | Todo | 構文エラー、インポート・依存ライブラリエラーの自動検知をL1でパス。 |
| **healthcheck.py** | [workspace/src/utils/healthcheck.py](file:///Users/nabe/src/github.com/nabe126/kanon/ai-agent/workspace/src/utils/healthcheck.py) | **✓ Pass** | Todo | Todo | Mac環境でのフォールバック動作をL1で確認。本番GPDでの数値取得はL3待ち。 |
| **monitor.py** | [controller/monitor.py](file:///Users/nabe/src/github.com/nabe126/kanon/controller/monitor.py) | Todo | Todo | Todo | **Experimental (実験的) 扱い。** バックアップの世代管理の欠如がレビューで指摘されたため、改修後にL1〜L3テストを順次実施する。 |
