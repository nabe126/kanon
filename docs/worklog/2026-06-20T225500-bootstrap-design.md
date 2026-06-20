# ワークログ: ブートストラップドキュメント (bootstrap.md) の作成設計

* **作成日時**: 2026-06-20T22:55:00+09:00
* **テーマ**: 新規参画した AI エージェントが 5分でプロジェクト理解と生産性を獲得できる単一のスタートアップコンテキスト `docs/bootstrap.md` の設計。

---

## 1. 🎯 目的と設計意図

新規にセッションを開始したエージェント、あるいは新参の AI が、膨大な README、AGENTS、ADR、過去の履歴や引継ぎファイル等を一つずつ走査するコストを削減し、コンテキスト圧縮が起きた直後でも「何が目的で、どのような制約があり、何から着手すべきか」を即座に把握できるようにします。
これは開発速度の向上だけでなく、コンテキストウィンドウの節約およびエージェントの生存性（Survival First）を高めるための運用的工夫です。

---

## 2. 🛠️ 構成と要約

* **ファイルパス**: [docs/bootstrap.md](file:///Users/nabe/src/github.com/nabe126/kanon/docs/bootstrap.md)
* **ドキュメント構造**:
  1. **Project Summary**: Kanon (arahabaki) の定義、デジタルツイン ＋ 生存 OS のビジョン、Phase 1 (Survival & Observation) の位置付け。
  2. **Current Status**: L1単体テスト（21 passed）などの実装状況、現在のフォーカス、および未決の検証レベル。
  3. **Architecture Snapshot**: Monorepo 維持判断、Sandbox（コントローラー監視）構造、メモリ分離（長期記憶設計の基礎）の概要。
  4. **Agent Collaboration Model**: 人間（承認者/指示者）、AGY (本エージェント / 設計・実装)、Copilot (ボイラープレート・小規模な委譲タスク担当)、ChatGPT (アーキテクチャ・設計レビュー・説明) の連携構造。
  5. **Critical Constraints**: secrets の変更・漏洩禁止、`apply_candidate_code` の本番適用禁止（5つの解除条件）、`monitor.py` の Experimental 扱い、ADR量産制限。
  6. **Current Priorities**: 直近のアクションプラン（優先順位順）。
  7. **Read Next**: より詳細な背景を知るための主要ドキュメントへのディープリンク。

---

## 3. 🚦 現在の検証ステータスと計画

| 機能名 | 検証レベル | ステータス | 備考 |
| :--- | :--- | :--- | :--- |
| **bootstrap.md** (本件) | L1 / L2 | **Todo (Doc)** | ドキュメントの新規作成 |
