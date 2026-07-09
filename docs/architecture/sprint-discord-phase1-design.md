# Sprint Discord Phase 1 実装・設計計画書 (Design Document)

* **作成日時**: 2026-07-09T23:10:00+09:00
* **ステータス**: Proposed (提案中 / 承認待ち)
* **対象機能**: `discord_agent.py` のエンドツーエンド動作、例外自動復旧、監視連携

---

## 1. 🎯 目的 (Goal)

実機（GPD WIN 3 / Ubuntu）にて24時間安定稼働し、一時的なネットワーク断や Gemini API 503 等の障害から自律的に復帰できる強靭な Discord Agent の構築。

---

## 2. 🚦 課題と設計アプローチ

### P1: エンドツーエンド会話動作の確立とテスト容易性の向上
* **現状**: 
  - `discord_agent.py` の `on_message` イベントハンドラ内に、コンテキスト構築、Gemini API コール、Discord返信処理が密結合で記述されており、ユニットテスト（L1）が困難。
* **設計アプローチ**:
  - メッセージ処理のコアロジックを `discord_agent.py` から `src/agent_logic.py` (または `discord_agent.py` 内の独立した非同期関数 `generate_agent_reply`) に分離。
  - `genai_client` などの外部API呼び出しモジュールを抽象化、あるいはモック注入（DI）可能にし、L1 テストコード (`tests/test_discord_agent.py`) でメッセージ受信 ➔ 応答生成のフローをテスト可能にする。

### P2: API 一時エラーおよび接続断に対する自動復旧 (Resilience)
* **設計アプローチ**:
  - **Gemini API のリトライ**: `tenacity` ライブラリを用いて、Gemini API 呼び出しに指数バックオフ付きリトライ（最大5回）を組み込む。
    - 対象エラー: 503 (Unavailable), 429 (Resource Exhausted), 504 等の一過性エラー。
  - **Discord 接続断対策**: `discord.py` の標準の自動再接続機能（`reconnect=True`）が有効であることを確認し、接続が失われた場合にもイベントループを維持する。
  - **致命的エラー時の Healthz 連携**: 回復不能な例外をキャッチした場合は、グローバル状態 `agent_status` を `"Error: ..."` に変更し、`/healthz` エンドポイントが `500 unhealthy` を返すようにする。

### P3: 運用監視と自動再起動・ロールバックの連携
* **設計アプローチ**:
  - **健康状態監視 (`monitor.py`)**: `monitor` コンテナが `ai_agent_core` の `/healthz` をポーリング（例: 10秒おき）し、連続失敗時に `docker restart` を実行。
  - **自動再起動の検証**: テストハーネスエンドポイント `/healthz/fail` を用いて、意図的に unhealthy 状態を作り出し、`monitor` が自動再起動を実行することを確認する。

### P4: 24時間連続運転試験の観測計画
* **設計アプローチ**:
  - リソース使用状況（CPU, メモリ, ディスク空き容量）は `/healthz` で取得される `get_system_metrics()` の結果を監視ログとして保存。
  - `RotatingFileHandler` によりログファイルを 1MB × 5世代で管理し、ストレージ圧迫を防止。

---

## 3. 🚀 スモールステップ開発・PR 計画 (Implementation Steps)

段階的なリリースと実機検証のため、以下の PR 単位に細分化して進めます。

### Step 1: 設計の合意と P1 テスト容易化のためのリファクタリング (本ターン対象)
* **作業内容**: 
  - メッセージ応答生成ロジックの分離 (`generate_agent_reply` 関数の切り出し)。
  - Gemini API コール部分のモック化、および `generate_agent_reply` に対する L1 ユニットテストの追加。
* **検証内容**: `pytest tests/test_discord_agent.py` が開発環境で通過すること。

### Step 2: P2 指数バックオフリトライと例外防御の実装
* **作業内容**:
  - `tenacity` を用いた API リトライ処理の追加。
  - イベントループ全体の例外ハンドリング強化。
* **検証内容**: モックテストでリトライが期待通り機能すること。

### Step 3: P3 実機での `monitor.py` 連携と自動再起動検証
* **作業内容**:
  - 実機上に `monitor` コンテナを起動し、`/healthz/fail` による自動再起動のテスト検証。
* **検証内容**: 自動再起動と健康状態の復帰。

---

## 4. 📝 意思決定ログ (Decision Log)

* **設計アプローチの決定**: ユニットテスト容易化のため、Discord クライアントのイベントループからビジネスロジック（応答生成）を分離する方針を決定。
* **リトライライブラリの採用**: 実機にインストール済みの `tenacity` を用いて、Gemini API コールを安全にラッピングすることを決定。
