# ロードマップとタスク管理 (Roadmap)

Kanon の開発ロードマップは、エージェントがユーザーに提供する価値の段階を示す**「能力ロードマップ (Capability Roadmap)」**と、それを支える安全・動作インフラの整備を示す**「技術ロードマップ (Technical Roadmap)」**の二重構造で定義・管理されます。

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

### Phase 1: Chat Agent (会話の確立)  (現在地)
Discord 等のインターフェースを介した基本的な会話の成立。
* **主なタスク**:
  * [x] Discord Bot と LLM (Gemini SDK) の接続・基本応答
  * [ ] 安定的な疎通維持と会話履歴の最小限のコンテキスト追跡
* **🏁 Exit Criteria (完了条件)**:
  * [ ] エージェントがコンテナ起動時に自動で立ち上がり、指定されたDiscordチャンネル/DMでユーザーと対話できること。
  * [ ] 最新のLLMモデル（Gemini-3.5-flash等）と疎通し、ユーザーの入力に対して適切な返答を返すこと。
  * [ ] 複数往復の対話において、会話の文脈（履歴）が引き継がれていること。

### Phase 2: Memory Agent (長期記憶・経験の蓄積)
会話だけではなく、認知モデル（Working Memory + Long-term Memory）に準拠した「L0〜L4 記憶階層制御」「優先度付き Read Bus」の実現。
* **主なタスク**:
  * [ ] **L0〜L4 記憶階層インフラの構築**: 各記憶レイヤ（L0感覚、L1ワーキング、L2中期、L3長期エピソード、L4長期意味）の接続と制御。
  * [ ] **Working Memory の容量制御**: L1 ワーキングメモリのアクティブトピック（3〜10個制限）のスロット制御と、あふれたトピックの L2/L3 への自動退避処理の実装。
  * [ ] **Read Bus (優先度付きフォールバックチェーン) の実装**: `L1 ➔ L3 ➔ L4 ➔ L2` の順でフォールバックして記憶を検索するクエリエンジンの構築。
  * [ ] **独立 Git リポジトリ/Submodule による記憶管理**: 安全な記憶の自動コミット・プッシュ機構の整備。
* **🏁 Exit Criteria (完了条件)**:
  * [ ] [認知モデル長期記憶設計書](file:///Users/nabe/src/github.com/nabe126/kanon/docs/architecture/phase2-cognitive-memory-design.md) に基づき、L0〜L4 記憶階層が正しく結合・機能していること。
  * [ ] L1 ワーキングメモリのトピック容量制限が正しく働き、3〜10個の上限を超えた際に古いトピックが自動退避（要約・永続化）されること。
  * [ ] 優先度付き Read Bus により、現在アクティブな文脈（L1）➔ 過去の決定（L3）➔ 一般プロファイル（L4）➔ 未整理ログ（L2）の順で適切にフォールバック検索が実行されること。
  * [ ] 記憶ファイル（L3/L4）の更新時に、独立した Git 履歴への自動コミットが実行され、履歴を遡って記憶を復元できること。

### Phase 3: Research Agent (自律調査と要約保存)
外部情報の収集・分析・知識化の自動化。ここから実用的な価値が急上昇します。
* **主なタスク**:
  * [ ] 指定されたテーマやニュース（例：新型スマートフォンの情報など）のクローリング
  * [ ] 収集データの自動要約と、`memory/inbox/` への適切な格納および他カテゴリへの振り分け
* **🏁 Exit Criteria (完了条件)**:
  * [ ] Web検索およびURLコンテンツの閲覧ツールを保有し、自律的に指定トピックの情報を収集できること。
  * [ ] 収集した複数の情報ソースから、矛盾のない統合要約を生成し、`memory/inbox/` にMarkdownファイルとして保存できること。
  * [ ] 保存されたファイルが自動で `projects/` などの適正なディレクトリに分類配置されること。

### Phase 4: Digital Twin (ユーザーの代理思考・ミラーリング)
「ユーザー自身ならどう判断するか」の再現。蓄積したパーソナルデータ（career, health, decision_history等）を利用した高度なパーソナライズ。
* **主なタスク**:
  * [ ] ユーザーの思考プロファイルや過去の判断傾向に基づく、判断のシミュレーションとドラフト作成
* **🏁 Exit Criteria (完了条件)**:
  * [ ] エージェントが人間の過去の決定事項（`decision_history/`）や経歴（`career/`）に基づき、「ユーザーの思考・価値観プロファイル」を抽出してシステム的に保持できること。
  * [ ] 複雑な選択肢や外部からの問い合わせに対して、「ユーザーならこう考える・答えるはず」という思考のドラフト（再現シミュレーション）を高い精度で提示できること。

### Phase 5: Semi-Autonomous Agent (承認付きタスク実行)
提案の起票から、人間による承認プロセスを挟んだ実際の業務執行。
* **主なタスク**:
  * [ ] GitHubのIssue/PR作成、情報収集スクリプトの実行などのワークフロー化
  * [ ] DiscordのボタンやFlask UIを用いた、人間（ユーザー）の承認ステップの統合
* **🏁 Exit Criteria (完了条件)**:
  * [ ] タスク（例: GitHub PRの作成、外部スクリプトの実行）の提案を起票し、ユーザーの承認（Approve）/却下（Reject）を待つシグナル制御ができること。
  * [ ] ユーザーが Discord のボタンまたは WebUI で「承認」を押した際にのみ、実際の書き込みや外部API実行が行われること。

### Phase 6: Autonomous / Business Agent (自律業務・経済活動)
ユーザーの判断基準に基づき、自律的に外部の仕事やタスクを獲得し、高い自律性（または高頻度承認プロセス）で実行・管理する最終段階。
* **🏁 Exit Criteria (完了条件)**:
  * [ ] エージェント自身が自律的なタスク分解（Task Breakdown）を行い、必要な外部APIキーや権限の範囲内でタスクを完了できること。
  * [ ] 新しい調査案件や外部からの仕事を獲得するシミュレーションを行い、受託判定をユーザーのプロファイルに従って自律実行できること。

---

## 🛠️ 2. 技術ロードマップ (Technical Roadmap)

能力ロードマップを安全かつ強靭に動かすための「裏方の実装」ロードマップです。

### Phase 1: Survival & Observation (生存・観測・復旧基盤) ⏳ (最優先・着手中)
「壊れても元に戻せる」「何が起きているかエージェント自身が把握できる」ための基盤。
* **主なタスク**:
  * [x] **エージェント視覚ツール (Observation Tools)** の実装 (`view_logs` 等)
  * [x] **検証機能 (Pre-apply Validation)** の実装 (`py_compile` による構文/依存チェック)
  * [x] **自動ロールバック機構 (Rollback)** の実装 (L1自動テスト合格 / L2/L3実機検証はPending)
* **🏁 Exit Criteria (完了条件)**:
  * [x] エージェントが自身のコンテナログを `view_logs` ツールで読み取り、自己エラーの分析ができること。
  * [x] コード適用前に `syntax check` と `import check` を行うスクリプトが自動実行され、失敗時に適用をブロックできること。
  * [x] Sandboxコンテナが異常終了または応答しなくなった場合、コントローラーが `backups/` の LKG から自動復旧させるテストに合格すること。 (L1結合テスト合格 / L2/L3実機検証はPending)


### Phase 2: Healthcheck & Resilience (ヘルスチェック・APIリトライ)
稼働の継続性を高めるための回復処理。
* **主なタスク**:
  * [ ] **Gemini API 503エラー対策**: 指数バックオフによる自動リトライ (最大5回) の実装
  * [ ] **ヘルスチェック (Healthcheck)** の実装: CPU, メモリ, ディスク, コンテナ状態の診断
* **🏁 Exit Criteria (完了条件)**:
  * [ ] APIリクエスト送信部で指数バックオフ（1, 2, 4, 8, 16秒）による自動リトライが実装され、一時的な503エラーを自律復旧できること。
  * [ ] FlaskダッシュボードまたはAPI経由で、ホストPCのCPU/メモリ/ディスク健康状態が JSON で返却され、エージェントがそれを監視可能なこと。

### Phase 3: Provider Abstraction (Provider の抽象化)
将来的な複数LLM対応を見据え、インターフェースを疎結合に分離。
* **主なタスク**:
  * [ ] エージェントロジックから LLM Provider を疎結合にする共通ラッパーの作成
* **🏁 Exit Criteria (完了条件)**:
  * [ ] `src/` 配下のメインロジックから特定の LLM SDK（google-genai など）のインポートが排除され、抽象ラッパー（`Provider` クラス等）を介してやり取りする設計になっていること。

### Phase 4: Multi-LLM (OpenAI / Claude の統合)
Gemini 以外の LLM への切り替え・併用・障害時フォールバック先の実装。
* **主なタスク**:
  * [ ] OpenAI / Anthropic (Claude) Provider の実装および動作検証
* **🏁 Exit Criteria (完了条件)**:
  * [ ] 設定ファイルを切り替えるだけで、Gemini以外のAPI（GPT-4oやClaude 3.5 Sonnet）を使用してエージェントが同一の対話およびツール実行を遂行できること。

### Phase 5: Sandbox System (安全な自己改変環境)
最小権限のエージェントと、特権を持つ Controller による安全なコード適用・コンテナ再起動の確立。
* **主なタスク**:
  * [ ] Controller と Sandbox コンテナ間の再起動プロキシ・通信APIの実装
* **🏁 Exit Criteria (完了条件)**:
  * [ ] エージェントコンテナに `docker.sock` がマウントされていないこと。
  * [ ] エージェントから Controller への安全な再起動通信APIが機能し、エージェントの要求に基づいて Controller 側で安全に Sandbox コンテナが再起動されること。

---

## 📋 3. 直近のタスクリスト (To-Do)

* [x] `monitor.py` ループを含む自動結合テスト（L1）の作成
* [x] Phase 2 (長期記憶基盤) の詳細アーキテクチャ設計書の起票 ➔ [Phase 2 設計提案書](file:///Users/nabe/src/github.com/nabe126/kanon/docs/architecture/phase2-design-proposal.md)
* [ ] 人間（ユーザー）による実機 (GPD) での L2/L3 ロールバック動作検証、および Discord/Gemini 実接続検証の完了
* [ ] 実機検証完了後、Phase 1 Complete の確定および Phase 2 実装フェーズへの移行

