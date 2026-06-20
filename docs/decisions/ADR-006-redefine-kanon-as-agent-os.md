# [ADR-006] kanonの「長期記憶を持つAgent OS」への再定義

## ステータス
**提案中 (Proposed)** - 2026-06-20T21:15:56+09:00

---

## 1. 背景 (Context)

これまでの `kanon` （開発コード: `arahabaki`）は、自律的にソースコードを書き換えて進化する「自己改変エージェント」の技術実験場として設計および実装を進めてきました。その結果、安全な自己改変フローや自動ロールバックといった生存・復旧技術の設計は大きく前進しました。

しかし、エージェントを「メールアドレスを1つ渡すだけで勝手に育ち、長期的に寄り添ってくれる真の相棒（デジタルツイン）」にするという本来のビジョンに立ち返ると、現在のリポジトリ設計には決定的な欠落があります。それは、エージェントが**「何を覚え、何者として振る舞い、どのように経験を蓄積していくのか」**という、**知識と記憶の基盤（Knowledge & Memory Foundation）**が定義されていない点です。

自己改変は手段（Supporting Capability）に過ぎず、目的（Primary Goal）ではありません。目的は以下の4点にあります：
1. **長期記憶の蓄積 (Long-term Memory)**
2. **デジタルツインの構築 (Digital Twin)**
3. **半自律的な調査・提案 (Autonomous Research)**
4. **長期運用・生存 (Long-term Survival)**

よって、`kanon` リポジトリを「コード置き場」から**「知識と記憶の保管庫（Agent OS）」**へと根本的に再設計することを提案します。

---

## 2. 決定事項（設計案） (Proposed Design)

### ① リポジトリ構造の再編成 (Repository Structure Redesign)
知識、記憶、実行コード、システム管理の境界を明確にしたディレクトリツリーを提案します。新設される `memory/` 領域がこのリポジトリの心臓部となります。

```text
kanon/
├── .agents/                        # エージェント憲章・行動規範 (Agent: Read-Only)
│   └── AGENTS.md                   # 開発者向けではなく、エージェントが厳守すべき「憲法」
├── README.md                       # プロジェクトビジョンと基本設計 (Agent: Read-Only)
├── docs/                           # ドキュメント・知識ベース (Agent: Read/Write)
│   ├── architecture/               # システム構成・アーキテクチャ
│   ├── decisions/                  # 技術選定や設計決定 (ADR)
│   │   └── ADR-006-redefine-kanon-as-agent-os.md  # [本ファイル]
│   ├── lessons/                    # 障害対応・エラー回避の教訓
│   ├── guides/                     # 人間が明示するコーディングガイド
│   ├── templates/                  # 汎用テンプレート
│   │   └── handover.md             # 人間-エージェント間、エージェント間の引継ぎ用
│   └── worklog/                    # 日々の作業ログ (ISO-8601 タイムスタンプ付)
├── memory/                         # ★新規追加: 長期記憶保管庫★ (Agent: Read/Write)
│   ├── career/                     # 人間・エージェントの経歴、スキル、成果物履歴
│   ├── camera/                     # 視覚情報・観察データ、画像や動画ログ
│   ├── projects/                   # 取り組んでいる、または過去のプロジェクト情報
│   ├── health/                     # ホストマシンのリソースやエージェントのヘルススコア
│   ├── family/                     # 関連人物・外部連絡先・コンタクトリスト
│   └── decision_history/           # ライフイベントや人間による過去の重大な意思決定ログ
├── controller/                     # エージェント管理・再起動プロセス (Agent: アクセス不可)
└── ai-agent/                       # 実行コンテナ環境 (Agent: Read-Only)
    ├── docker-compose.yml          # コンテナ環境定義
    ├── Dockerfile                  # ランタイムイメージ
    ├── secrets/                    # 機密情報隔離領域 (Agent: アクセス不可)
    │   └── .env                    # APIキー、トークン類
    └── workspace/                  # コンテナマウント領域
        ├── src/                    # エージェント動的実行ソースコード (Agent: Read/Write)
        ├── tests/                  # 自律テストコード領域 (Agent: Read/Write)
        ├── state/                  # コンテナ再起動用の一時状態領域 (Agent: Read/Write)
        └── backups/                # 直近のLKG (Last Known Good) ソース退避先 (Agent: Read-Only)
```

---

### ② `README.md` の再構成 (README Structure)
現状の「動作手順（How to run）」に偏った内容から、「なぜ存在し、何を目指すのか（Vision）」を最上位に据えた構成に再定義します。

* **推奨する章立て**:
  1. **Vision**: kanonが目指す「長期記憶を持つデジタルツイン/相棒」のビジョン。
  2. **What is Kanon**: プロジェクトの基本定義と役割。
  3. **Architecture**: コントローラー・サンドボックス・メモリの協調関係。
  4. **Repository Layout**: 上記で提案した権限マトリクスとフォルダレイアウト。
  5. **Development Workflow**: Docs as Code、引継ぎ、メモリ蓄積のフロー。
  6. **Roadmap**: 修正されたフェーズ定義。
  7. **Related Docs**: 各 `docs/` および `memory/` ドキュメントへのポインタ。

---

### ③ `AGENTS.md` の再定義 (AGENTS.md Structure)
開発者向けの設計メモではなく、エージェントが自身の行動の絶対的基準として従うべき**「エージェント憲法（Agent Constitution）」**として再定義します。

* **憲法構成要素**:
  * **Survival First (生存最優先原則)**: 優先順位（Survival > Observability > Recovery > Improvement > Performance）。
  * **Never (絶対禁止事項)**:
    * 機密情報 (`secrets/`) の改変やログ出力。
    * コントローラー制御コード (`controller/`) へのアクセスや書き換え。
    * `backups/` データの削除。
    * 事前検証（Syntax / Import Check）を通さないコードの適用。
    * サマリーを伴わないドキュメントの破壊的更新。
  * **Always (必須遵守事項)**:
    * 変更時は必ず意図を説明すること。
    * 作業時は必ずISO-8601形式のタイムスタンプを持つワークログを作成すること。
    * コード変更前には必ずバックアップ（LKG）を作成すること。

---

### ④ ドキュメントのライフサイクル管理 (Documentation Lifecycle)
ドキュメントの鮮度を維持し、LLMエージェントが過去の古い仕様に従って誤った改変を行うことを防止します。

* **ステータス管理**:
  * **Proposed (提案中)**: 新規設計案やルール。人間（ユーザー）の承認待ち。
  * **Accepted (承認済)**: 承認され、現在適用されているルール・設計。
  * **Deprecated (廃止)**: 新しい決定によって置き換えられた、参照すべきではない過去の設計。

---

### ⑤ 長期記憶 (Memory Architecture) の運用方針
外部の複雑な VectorDB を最初から導入するのではなく、**「Markdown ＋ Git」**による履歴・版管理の仕組みでスタートします。

* **Markdownによるメタデータ構造化**:
  * 各メモリファイルの上部にYAMLフロントマッターを設け、更新日時（ISO-8601）、重要度、カテゴリーを明示します。
* **Git履歴による時間軸の追跡**:
  * メモリの追加や更新は、Gitのコミットログを通じてタイムラインとして管理。これにより、エージェントは過去の自分の変更履歴をGitレベルで遡って追跡できます。

---

### ⑥ 引継ぎテンプレートの運用 (Handover Template)
人間とエージェント、またはエージェント同士のセッション切り替え時に、コンテキストが失われることを防ぐための引継ぎテンプレート [docs/templates/handover.md](file:///Users/nabe/src/github.com/nabe126/kanon/docs/templates/handover.md) を定義。
作業の開始時および終了時にこのテンプレートに従った引き継ぎ用ドキュメントを作成し、バトンを渡します。

---

### ⑦ ロードマップの再編成 (Roadmap Re-phasing)
「自律自己改変」の優先順位を最終フェーズに下げ、基盤となる「知識と記憶の確立」を最優先の Phase 0 に定義し直します。

```text
Phase 0: Knowledge Foundation (知識と記憶の土台) ⏳ (最優先)
├── Docs as Code 運用の構造化・厳格化
├── Memory レイアウトの整備と Git 追跡の開始
└── AGENTS.md のエージェント憲法化

Phase 1: Survival, Observation, Recovery (生存・観測・復旧基盤)
├── ログ観測・検証ツール・LKGバックアップの実装
└── 自動ロールバック機能の実装

Phase 2: Long-term Memory (長期記憶の自律運用)
└── エージェントによる memory/ 配下への自律的な事実・経験の蓄積

Phase 3: Digital Twin (デジタルツイン基盤)
└── 人間のスケジュール、成果物、健康状態などを代行・観察しミラーリングする機能

Phase 4: Autonomous Research (自律調査・提案)
└── 外部情報のクローリング、要約、人間に向けた意思決定資料の自律的な起票

Phase 5: Self Modification (自律自己改変)
└── 最後の能力としての、エージェントコアプロセスの自律的な機能追加・拡張
```

---

## 3. 影響と次のステップ (Consequences & Next Steps)

* **メリット**:
  * エージェントが「なぜ存在するのか（ビジョン）」および「何を学習し記憶していくべきなのか」が明確になり、本来の相棒（デジタルツイン）へ成長可能となる。
  * `memory/` と `system_core/` の分離により、コード変更時に誤って蓄積した記憶データを削除するリスクが排除される。
* **次のステップ**:
  * 本提案（ADR-006）のユーザーレビューと承認。
  * 承認後、`README.md`, `AGENTS.md` の再構成を実施し、`memory/` 配下のディレクトリ構造を作成する。
