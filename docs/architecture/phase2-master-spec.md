# Phase 2 統合マスター仕様書 (Phase 2 Master Spec)

* **ステータス**: Proposed (設計レビュー待ち)
* **作成日時**: 2026-06-27T08:20:00+09:00
* **作成者**: Antigravity

---

## 1. 🎯 概要と基本コンセプト

本ドキュメントは、Kanon Phase 2 (Long-term Memory Foundation) の設計および仕様を一元管理する**マスター仕様書**です。

Phase 2 では、従来の単純なテキストファイル書き出しによる履歴管理から脱却し、**「人間の認知制約に準拠した強靭かつ効率的な記憶システム」**を構築します。

---

## 2. 🗂️ 従属設計ドキュメント (Sitemap)

Phase 2 の詳細な設計要素は、本マスター仕様書を親とし、以下の3つのドキュメントに分割・従属しています。

1. **[認知モデル長期記憶設計書 (phase2-cognitive-memory-design.md)](file:///Users/nabe/src/github.com/nabe126/kanon/docs/architecture/phase2-cognitive-memory-design.md)**
   - Alan Baddeley のワーキングメモリモデルと Endel Tulving の長期記憶分類モデルの適用。
   - L0〜L4 の記憶階層構造。
   - 3〜10個のアクティブトピックに制限された Working Memory 容量制限。
   - 優先度付き Read Bus (フォールバックチェーン)。
   - 日本十進分類法 (NDC) にインスパイアされた Agent Decimal Classification (ADC) の適用評価。
2. **[長期記憶パイプライン設計書 (phase2-design-proposal.md)](file:///Users/nabe/src/github.com/nabe126/kanon/docs/architecture/phase2-design-proposal.md)**
   - 思考ログ処理パイプライン (inbox ➔ processor ➔ output) のデータフロー。
   - YAML Frontmatter 付き Markdown ファイルのフォーマット仕様。
   - Git 自動コミットによるバージョン管理と差分追跡境界。
3. **[技術検討・設計レビュー資料 (phase2-design-review.md)](file:///Users/nabe/src/github.com/nabe126/kanon/docs/architecture/phase2-design-review.md)**
   - Memory の責務、API 構成案、バッチ処理ロック、検索エンジン選定のトレードオフと推奨案。
   - ADR 起票候補 (ADR-010: memory リポジトリ物理分離 / ADR-011: 段階的検索エンジン)。
   - デジタルツインへの将来の拡張ポイント。

---

## 3. 📐 記憶システム全体の基本構成

```
[感覚器/感覚記憶: L0] ➔ (一時保持) ➔ [ワーキングメモリ: L1] (アクティブトピック: 3〜10個)
                                               │
                                       (容量超過時にフラッシュ)
                                               │
                                               ▼
[長期エピソード記憶: L3] ◄──(自動コミット)─── [中期記憶/インボックス: L2]
[長期意味記憶: L4]                          (Processor による要約・整理)
```

### ① 優先検索経路 (Read Bus)
情報要求に対して、最もアクティブな文脈から順にドリルダウンし、APIコストとLLM迷子を防止します。
$$\text{Read Bus Fallback Chain} : L1 \rightarrow L3 \rightarrow L4 \rightarrow L2$$

### ② 境界分離の厳守
- **Working Memory / 階層制御 / 永続化インフラ**: 本フェーズ (Phase 2) の実装対象。
- **Knowledge Model (知識グラフ/概念オントロジー)**: 次期フェーズ (Phase 3 以降) の実装対象として分離。

---

## 4. 🚀 タスクリスト & 完了条件 (Exit Criteria)

* [ ] **L0〜L4 記憶階層制御インフラの実装**: 各記憶領域の入出力ハンドラ開発。
* [ ] **Working Memory の容量制御 (3〜10スロット) の実装**: トピック容量超過時の自動退避・要約ロジックの開発。
* [ ] **優先度付き Read Bus の実装**: 優先順位に基づきフォールバック検索を行うクエリエンジンの構築。
* [ ] **記憶 Git リポジトリの物理分離**: ADR-010 に基づき `memory/` ディレクトリを独立したリポジトリ（または Submodule）に分離し、安全な自動コミット機構を構築。
* [ ] **実機 L2/L3 動作テストの完了**: 上記すべてが Mac および GPD実機で正常に動作し、テストスイートが 100% 合格すること。
