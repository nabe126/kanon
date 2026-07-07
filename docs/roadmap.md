# ロードマップとタスク管理 (Roadmap)

Kanon の開発ロードマップは、エージェントがユーザーに提供する価値の段階を示す**「能力ロードマップ (Capability Roadmap)」**と、それを支える安全・動作インフラの整備を示す**「技術ロードマップ (Technical Roadmap)」**の二重構造で定義・管理されます。
これらに基づき、具体的な開発実行計画を「スプリントスケジュール」として管理します。

---

## 🚀 1. 能力ロードマップ (Capability Roadmap)

エージェントが「何者になり、どのような価値を提供するのか」の成長段階を示します。

### Phase 0: Foundation (基盤)  [完了]
リポジトリの境界、開発・ドキュメント規約、記憶レイアウトの定義。
* **主なタスク**:
  * [x] リポジトリ境界設計の策定および実施
  * [x] Docs as Code 運用の構造化・厳格化
  * [x] エージェント憲法（AGENTS.md）の整備
  * [x] memory/ ディレクトリレイアウトの作成
* **🏁 Exit Criteria (完了条件)**:
  * [x] [README.md](file:///Users/nabe/src/github.com/nabe126/kanon/README.md), [.agents/AGENTS.md](file:///Users/nabe/src/github.com/nabe126/kanon/.agents/AGENTS.md), [docs/templates/handover.md](file:///Users/nabe/src/github.com/nabe126/kanon/docs/templates/handover.md) が整備され、ユーザーの承認を得ていること。
  * [x] `memory/` ディレクトリ配下に `inbox`, `projects`, `career`, `health`, `people`, `decision_history` ディレクトリが生成され、Git 追跡（`.gitkeep`）が開始されていること。
  * [x] `.env` の `secrets/` 隔離等の物理再配置が完了していること。

### Phase 1: Chat Agent (会話の確立)  (現在地 - 実機検証待ち)
Discord 等のインターフェースを介した基本的な会話の成立。
* **主なタスク**:
  * [x] Discord Bot と LLM (Gemini SDK) の接続・基本応答
  * [x] 会話履歴の最小限のコンテキスト追跡（ConversationHistory）
  * [⏳] 安定的な疎通維持と実機（GPD WIN 3）での接続稼働（Sprint 2 で実施）
* **🏁 Exit Criteria (完了条件)**:
  * [ ] エージェントがコンテナ起動時に自動で立ち上がり、指定されたDiscordチャンネル/DMでユーザーと対話できること。
  * [ ] 最新のLLMモデル（Gemini-3.5-flash等）と疎通し、ユーザーの入力に対して適切な返答を返すこと。
  * [ ] 複数往復の対話において、会話の文脈（履歴）が引き継がれていること。

### Phase 2: Memory Agent (長期記憶・経験の蓄積)
会話だけではなく、認知モデル（Working Memory + Long-term Memory）に準拠した「L0〜L4 記憶階層制御」「優先度付き Read Bus」の実現。
* **主なタスク**:
  * [x] **L1 ワーキングメモリの容量制御**: アクティブトピック（5個）のスロット制御の実装
  * [x] **L1 から L3 への自動退避（フラッシュ）**: 容量制限超過時の自動Markdown書き出し
  * [x] **Read Bus (優先度付きフォールバックチェーン) の実装**: `L1 ➔ L3 ➔ L4` の Grep 検索エンジンの構築
  * [x] **独立 Git 履歴による記憶管理**: 記憶ファイルの自動コミット機構の実装
  * [⏳] **L2 中期記憶（未整理バッファ）および自動整理（Import/Processor）の実装**（Sprint 3 で実施）
* **🏁 Exit Criteria (完了条件)**:
  * [ ] [Phase 2 統合マスター仕様書 (phase2-master-spec.md)](file:///Users/nabe/src/github.com/nabe126/kanon/docs/architecture/phase2-master-spec.md) に基づき、L0〜L4 記憶階層が正しく結合・機能していること。
  * [ ] L1 ワーキングメモリのトピック容量制限が正しく働き、上限（5個）を超えた際に古いトピックが自動退避（要約・永続化）されること。
  * [ ] 優先度付き Read Bus により、現在アクティブな文脈（L1）➔ 過去の決定（L3）➔ 一般プロファイル（L4）➔ 未整理ログ（L2/Inbox）の順でフォールバック検索が実行されること。
  * [ ] 記憶ファイル（L3/L4）の更新時に、独立した Git 履歴への自動コミットが実行され、履歴を遡って記憶を復元できること。

### Phase 3: Research Agent (自律調査と要約保存)
外部情報の収集・分析・知識化の自動化。
* **主なタスク**:
  * [ ] 指定されたテーマやニュースのクローリング
  * [ ] 収集データの自動要約と、`memory/inbox/` への適切な格納および他カテゴリへの振り分け

### Phase 4: Digital Twin (ユーザーの代理思考・ミラーリング)
パーソナルデータ（career, health, decision_history等）を利用した高度なパーソナライズ。
* **主なタスク**:
  * [ ] ユーザーの思考プロファイルや過去の判断傾向に基づく、判断のシミュレーションとドラフト作成

### Phase 5: Semi-Autonomous Agent (承認付きタスク実行)
提案の起票から、人間による承認プロセスを挟んだ実際の業務執行。

### Phase 6: Autonomous / Business Agent (自律業務・経済活動)

---

## 🛠️ 2. 技術ロードマップ (Technical Roadmap)

能力ロードマップを安全かつ強靭に動かすための「裏方の実装」ロードマップです。

### Phase 1: Survival & Observation (生存・観測・復旧基盤) ⏳ (着手中)
「壊れても元に戻せる」「何が起きているかエージェント自身が把握できる」ための基盤。
* **主なタスク**:
  * [x] **エージェント視覚ツール (Observation Tools)** の実装 (`view_logs` 等)
  * [x] **検証機能 (Pre-apply Validation)** の実装 (`py_compile` による構文/依存チェック)
  * [x] **自動ロールバック機構 (Rollback) の基本実装**: LKG退避・復元およびホットリロード連携
  * [⏳] **自動ロールバックコンテナ再起動の修正**: `docker` コマンド不在エラーの解決（Sprint 1 で実施）
  * [⏳] **実機での L2/L3 動作検証**: ロールバック成功の実証（Sprint 2 で実施）

### Phase 2: Healthcheck & Resilience (健康診断・APIリトライ)
稼働の継続性を高めるための回復処理。
* **主なタスク**:
  * [x] **ヘルスチェック (Healthcheck) の実装**: CPU, メモリ, ディスク, コンテナ状態の診断
  * [⏳] **Gemini API 503エラー対策**: 指数バックオフによる自動リトライ (最大5回) の実装（Sprint 2 で実施）

### Phase 3: Provider Abstraction (Provider の抽象化) ⏳ (Sprint 4 で実施)
将来的な複数LLM対応を見据え、インターフェースを疎結合に分離。
* **主なタスク**:
  * [ ] エージェントロジックから LLM Provider を疎結合にする共通ラッパーの作成

### Phase 4: Multi-LLM (OpenAI / Claude の統合) ⏳ (Sprint 4 で実施)
Gemini 以外の LLM への切り替え・併用・障害時フォールバック先の実装。
* **主なタスク**:
  * [ ] OpenAI / Anthropic (Claude) Provider の実装および動作検証

### Phase 5: Sandbox System (安全な自己改変環境)
最小権限のエージェントと、特権を持つ Controller による安全なコード適用・コンテナ再起動の確立。
* **主なタスク**:
  * [⏳] **特権マウントの適正化**: `docker.sock` のエージェントコンテナからの排除（Sprint 1 で実施）
  * [ ] Controller と Sandbox コンテナ間の再起動プロキシ・通信APIの実装

---

## 📋 3. スプリント実行計画 (Sprint Schedule)

ユーザーから提示された計画に基づき、各スプリントで達成するコミットメントを以下に定義します。

### 🏃 Sprint 1: インフラ構成適正化・Docker修正 (現在地)
* **目標**: 進捗監査によって判明した、インフラ設定のセキュリティ不整合およびロールバック再起動時のバグを完全に修正し、基盤を健全化する。
* **タスク**:
  * [ ] **docker.sock マウントの適正化**: 
    - `ai-agent` コンテナから `docker.sock` を排除（Sandbox化）。
    - 特権監視を行う `monitor` サービス（または実行環境）にのみ `docker.sock` をマウントする。
  * [ ] **`monitor` コンテナの Docker コマンド修復**:
    - `controller/Dockerfile.monitor` に Docker CLI コマンドをインストールし、`monitor.py` 内の `subprocess.run(["docker", "restart", ...])` が正常に動くようにする。
  * [ ] **ボリュームマウントの修正**:
    - 本番用の `ai-agent/docker-compose.yml` にルートの `./memory` および `./docs` をボリュームマウントとして追加し、エージェントから長期記憶のフラッシュやドキュメント自動生成が永続的に行えるようにする。

### 🏃 Sprint 2: 実機検証・安定運用化 (GPD & Discord & Gemini)
* **目標**: GPD WIN 3 実機での検証を完了し、モックではなく実API・実トークンを用いて24時間連続運転に耐える安全な対話Bot環境を確立する。
* **タスク**:
  * [ ] **実機（GPD WIN 3）での L2/L3 ロールバック動作検証の完了**:
    - Sprint 1 で修正した `docker restart` が実機コンテナ環境で正常に作動し、障害から自動復旧することを実証。
  * [ ] **Discord / Gemini の実接続**:
    - 実トークン・APIキーを用いて、実用環境での Discord 接続と Gemini 3.5 Flash での対話を稼働させる。
  * [ ] **APIリトライ対策の実装**:
    - Gemini API 503エラーなどの一過性障害を克服するための指数バックオフ（最大5回リトライ）の実装。
  * [ ] **24時間運転試験**:
    - 24時間以上の連続運転を行い、リソースリークやプロセス停止が発生しないことを健康状態監視ログから実証。

### 🏃 Sprint 3: 記憶処理の自動化 (Processor & Import & Memory自動整理)
* **目標**: 長期記憶（Phase 2）を本格稼働させ、メモリの自動的な整理・要約・階層移動をバックグラウンドで自律実行する仕組みを実装する。
* **タスク**:
  * [ ] **Processor (思考・要約・整理プロセッサ) の構築**:
    - 蓄積されたチャット履歴や一時ログ（Inbox）を解析し、構造化・要約する LLM バックグラウンドエンジンの実装。
  * [ ] **Memory自動整理・階層移動 (Import / Move)**:
    - 収集された一時データを適切なカテゴリ（projects, career, decision_history 等）へ自動的に割り振り（Import）、インデックス化する処理の実装。
    - L2（中期記憶）の明確な定義と、`L1 ➔ L3 ➔ L4 ➔ L2` の Read Bus 統合の完成。

### 🏃 Sprint 4: 複数LLMプロバイダ対応 (Multi-LLM & Provider抽象化)
* **目標**: 特定の LLM に依存するコードを排除し、Gemini 以外のプロバイダに対してもプラグイン式で接続・フォールバックできるようにする。
* **タスク**:
  * [ ] **Provider抽象化レイヤーの実装**:
    - `google.genai` の依存コードをエージェントのメイン処理から引き剥がし、LLM ラッパーを構築。
  * [ ] **Claude / OpenAI / Codex 統合**:
    - Anthropic (Claude 3.5 Sonnet 等) および OpenAI (GPT-4o 等) 用のプロバイダプラグインを実装。
    - 各LLMプロバイダでの対話およびツール実行（コード解釈等）の互換性を検証。
