# ロードマップとタスク管理 (Roadmap)

Kanon の開発ロードマップは、エージェントがユーザーに提供する価値の段階を示す**「能力ロードマップ (Capability Roadmap)」**と、それを支える安全・動作インフラの整備を示す**「技術ロードマップ (Technical Roadmap)」**の二重構造で定義・管理されます。

---

## 🚀 1. 能力ロードマップ (Capability Roadmap)

エージェントが「何者になり、どのような価値を提供するのか」の成長段階を示します。

### Phase 0: Foundation (基盤)  [完了]
リポジトリの境界、開発・ドキュメント規約、記憶レイアウトの定義。
* [x] リポジトリ境界設計の策定および実施
* [x] Docs as Code 運用の構造化・厳格化
* [x] エージェント憲法（AGENTS.md）の整備
* [x] memory/ ディレクトリレイアウトの作成

### Phase 1: Chat Agent (会話の確立)  (現在地)
Discord 等のインターフェースを介した基本的な会話の成立。
* [x] Discord Bot と LLM (Gemini SDK) の接続・基本応答
* [ ] 安定的な疎通維持と会話履歴の最小限のコンテキスト追跡

### Phase 2: Memory Agent (長期記憶・経験の蓄積)
会話だけではなく、「覚える」「検索する」「判断履歴を参照する」ことの実現。
* [ ] `memory/` ディレクトリ（Markdown ＋ Git）の読み書き・検索
* [ ] 「前回どう決めたか？」「あのイベント時の約束は何か？」に対する回答能力の獲得

### Phase 3: Research Agent (自律調査と要約保存)
外部情報の収集・分析・知識化の自動化。ここから実用的な価値が急上昇します。
* [ ] 指定されたテーマやニュース（例：新型スマートフォンの情報など）のクローリング
* [ ] 収集データの自動要約と、`memory/inbox/` への適切な格納および他カテゴリへの振り分け

### Phase 4: Digital Twin (ユーザーの代理思考・ミラーリング)
「ユーザー自身ならどう判断するか」の再現。蓄積したパーソナルデータ（career, health, decision_history等）を利用した高度なパーソナライズ。
* [ ] ユーザーの思考プロファイルや過去の判断傾向に基づく、判断のシミュレーションとドラフト作成

### Phase 5: Semi-Autonomous Agent (承認付きタスク実行)
提案の起票から、人間による承認プロセスを挟んだ実際の業務執行。
* [ ] GitHubのIssue/PR作成、情報収集スクリプトの実行などのワークフロー化
* [ ] DiscordのボタンやFlask UIを用いた、人間（ユーザー）の承認ステップの統合

### Phase 6: Autonomous / Business Agent (自律業務・経済活動)
ユーザーの判断基準に基づき、自律的に外部の仕事やタスクを獲得し、高い自律性（または高頻度承認プロセス）で実行・管理する最終段階。

---

## 🛠️ 2. 技術ロードマップ (Technical Roadmap)

能力ロードマップを安全かつ強靭に動かすための「裏方の実装」ロードマップです。

### Phase 1: Survival & Observation (生存・観測・復旧基盤) ⏳ (最優先・着手中)
「壊れても元に戻せる」「何が起きているかエージェント自身が把握できる」ための基盤。
* [ ] **エージェント視覚ツール (Observation Tools)** の実装 (`view_logs` 等)
* [ ] **検証機能 (Pre-apply Validation)** の実装 (`py_compile` による構文/依存チェック)
* [ ] **自動ロールバック機構 (Rollback)** の実装 (起動失敗時の LKG への書き戻し)

### Phase 2: Healthcheck & Resilience (ヘルスチェック・APIリトライ)
稼働の継続性を高めるための回復処理。
* [ ] **Gemini API 503エラー対策**: 指数バックオフによる自動リトライ (最大5回) の実装
* [ ] **ヘルスチェック (Healthcheck)** の実装: CPU, メモリ, ディスク, コンテナ状態の診断

### Phase 3: Provider Abstraction (Provider の抽象化)
将来的な複数LLM対応を見据え、インターフェースを疎結合に分離。
* [ ] エージェントロジックから LLM Provider を疎結合にする共通ラッパーの作成

### Phase 4: Multi-LLM (OpenAI / Claude の統合)
Gemini 以外の LLM への切り替え・併用・障害時フォールバック先の実装。
* [ ] OpenAI / Anthropic (Claude) Provider の実装および動作検証

### Phase 5: Sandbox System (安全な自己改変環境)
最小権限のエージェントと、特権を持つ Controller による安全なコード適用・コンテナ再起動の確立。
* [ ] Controller と Sandbox コンテナ間の再起動プロキシ・通信APIの実装

---

## 📋 3. 直近のタスクリスト (To-Do)

* [ ] ログ・検証・バックアップ機能（技術 Phase 1）を実装するための開発アプローチの決定
* [ ] `docs/architecture/` および `docs/decisions/` への詳細設計の反映
