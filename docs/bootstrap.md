# Kanon Bootstrap (arahabaki)

本ドキュメントは、新規にアサインされた AI エージェントが **5分で現在のコンテキストを理解し、安全かつ生産的に稼働を開始する** ための単一ファイル・スタートアップ・リファレンスです。
他の README や ADR、AGENTS などを巡回する前に、本ドキュメントの制約と優先事項を必ず頭に入れてください。

---

## 1. Project Summary

* **Kanon とは**: 長期記憶を持つデジタルツイン基盤 ＋ 生存可能な自律 Agent OS（開発コード: `arahabaki`）。
* **プロジェクトビジョン**: エージェントが外部環境と安全に連携し、自律的に機能検証と安全な自己改変（Self-Modification）を繰り返しながら生存・成長し続けること。
* **現在の Phase**: **Phase 1 (Survival & Observation / 生存・観測・復旧基盤)**
  * **価値**: エージェント自身が死なない、ログを出す、健康状態を知らせる、壊れたら自動でロールバックするインフラの構築。
* **Next Major Milestone (今後のマイルストーン)**:
  * **Phase 2 (Long-term Memory Foundation / 長期記憶基盤)**:
    記憶モジュール (`memory/`) の構築に着手し、時間軸を持った会話履歴や構造化されたデジタルツイン状態の長期的な記憶・再利用のアーキテクチャを確立する。

---

## 2. Current Status

* **Phase 完成度**: Phase 1 の基礎コンポーネント（検証、ヘルスチェック、ログ、世代管理モニター、テストハーネス）の実装および L1 単体テスト（pytest 23件）が完了。
* **実機検証実績**: GPD WIN 3 (Ubuntu 26.04) 実機にて、Docker ビルド・起動・Flaskヘルスチェック（`/healthz`）・Mock動作の検証を完了（**L2検証合格**）。
* **現在のフォーカス**: `monitor.py` による実再起動・LKG復元（ロールバック結合テスト）および Discord/Gemini の本物接続検証（L2/L3）。
* **Phase 1 Exit Criteria (完了判定基準) と現在の進捗**:
  1. **Docker デプロイ検証**: コンテナ起動、Flask健康診断（`/healthz`）応答が正常であること。➔ **Pass (L2)** (Ubuntu 26.04 実機にて実証)
  2. **Discord 接続**: 実トークンでの Discord ゲートウェイ実接続成功。➔ **Todo (Pending)**
  3. **Gemini 疎通**: 実 API キーでの Gemini API 実疎通および返答成功。➔ **Todo (Pending)**
  4. **monitor.py 自動復旧実証**: `/healthz` 異常時の自動ロールバックおよびコンテナ再起動の成功。➔ **Todo (Pending)**
  5. **LKG 復元実証**: 異常コード混入時に LKG ディレクトリからの完全復元成功。➔ **Todo (Pending)**
  6. **healthcheck チューニング**: 実機での平常負荷に適した閾値パラメータの確定。➔ **Todo (Pending)**

---

## 3. Architecture Snapshot

* **リポジトリ構造**:
  * [ai-agent/](file:///Users/nabe/src/github.com/nabe126/kanon/ai-agent/): エージェントの実行コンテナ環境（Sandbox）。
    * `workspace/src/`: Discord接続や会話履歴などのメインロジック。
    * `workspace/tests/`: pytest による自動テストスイート。
  * [controller/](file:///Users/nabe/src/github.com/nabe126/kanon/controller/): エージェント監視用のホスト側スクリプト。
  * [memory/](file:///Users/nabe/src/github.com/nabe126/kanon/memory/): 将来的な記憶モジュール（未着手）。
* **Monorepo の決定**: 現在は「脳 (Core)」「記憶 (Memory)」「仕事 (Workhub)」の論理境界を維持したまま、単一リポジトリを維持。
* **記憶戦略 (Memory Strategy)**: 現時点では外部の VectorDB/GraphDB は使用せず、軽量なインメモリ ＋ 永続ファイル（`workspace/state/conversation_history.json`）によるシンプルな会話履歴追跡を行う。
* **Memory Subsystem (Phase 2 構想)**: 常駐ループではなく「思考ログ処理パイプライン（inbox ➔ processor ➔ output）」として自立稼働を定義。定期的な集約バッチを実行し、過去の対話や思考ログから自動的に Lessons や ADR 提案を抽出・要約起票する。
* **Sandbox & コントローラーモデル**: 
  * `ai-agent` コンテナは独立して稼働。
  * ホスト側で動作する `controller/monitor.py` が、コンテナの `/healthz` API にポーリング監視を実行。
  * 異常検知（タイムアウトやエラー）が一定回数連続した場合、ホスト側モニターがコンテナの `src/` を LKG (Last Known Good) バックアップから復旧し、`docker restart` で強制生存させるモデル。

---

## 4. Agent Collaboration Model

Kanon は複数の主体およびエージェントのコラボレーションにより開発・運用されます。

| 開発主体 | 役割 / 責務 | 権限境界 |
| :--- | :--- | :--- |
| **Human (ユーザー)** | 最終承認者、大局指示、ADR承認。 | 唯一の破壊的操作の承認者。 |
| **AGY (Antigravity)** | メインエンジニア。設計と実装。 | 安全な検証・実装および L1/L2 テスト。 |
| **Copilot** | ボイラープレート、単機能テスト。 | 部分的かつ小規模なコーディングタスクの委譲先。 |
| **ChatGPT** | アドバイザー、設計レビュー、仕様整理。 | 主に説明書やコードレビュー等のサポート要員。 |

---

## 5. Critical Constraints (最重要ルール)

エージェント憲章（`AGENTS.md`）に規定された、絶対に遵守すべきルールです。

* **自己改変の制限 (Self Modification)**:
  * 自己更新エンジンである `apply_candidate_code()` は、現時点で **Experimental（実験的）扱い** とする。
  * 以下の5つの条件がすべて満たされるまで、本番経路（`discord_agent.py` など）から呼び出してはならない（テストコードからの呼び出しのみ許可）。
    1. Discord実接続確認
    2. Gemini実疎通確認
    3. `monitor.py` 実機ロールバック成功
    4. LKG復元成功の実証
    5. healthcheck閾値の実機チューニング
* **機密情報の秘匿**:
  * [ai-agent/secrets/.env](file:///Users/nabe/src/github.com/nabe126/kanon/ai-agent/secrets/.env) などの secrets ファイルは絶対に書き換えない。
  * トークンや API キーをチャットやログに出力しない。
* **設計と実装の分離**:
  * 対話の冒頭で必ず **`[Design]`** または **`[Implementation]`** モードを明記し、検証レベル（L1/L2/L3）を要約報告すること。
* **バックアップとワークログ**:
  * ロジックを変更する前に、必ず正常稼働版のコピーを `backups/` へ退避する。
  * 変更時は ISO-8601 形式のタイムスタンプ付きワークログを `docs/worklog/` に残す。
  * セッション終了時は [handover テンプレート](file:///Users/nabe/src/github.com/nabe126/kanon/docs/templates/handover.md) に従い引継ぎログを残す。

---

## 6. Current Priorities (直近のアクションプラン)

以下の優先順位に従って作業を進めてください。

1. **実機（GPD WIN 3 / Ubuntu / Docker）環境のセットアップ (L2)**:
   * コンテナを起動し、ホスト側から `/healthz` 疎通を確認する。
2. **`monitor.py` の実機ロールバック実証 (L2/L3)**:
   * 意図的に `/healthz` を無応答（または 500）にさせ、`monitor.py` が LKG (Last Known Good) ディレクトリからコードを復元し、`docker restart` でコンテナを強制再起動させる結合テストを行う。
3. **ヘルスチェック閾値の実機チューニング (L3)**:
   * 実コア数や平常時リソース（CPU, Memory, Disk）に合わせ、偽陽性による再起動を防ぐよう閾値を調整する。
4. **Discord Bot & Gemini API の実疎通テスト (L3)**:
   * `secrets/.env` に本物のトークンを配置し、対話と履歴永続化を実機で実証する。

---

## 7. Maintenance Rule (保守運用規約)

本ブートストラップドキュメントは、以下の契機で必ずレビューおよび更新を行わなければなりません。
* 開発・技術 **Phase が遷移** した時
* ADR や**アーキテクチャ上の設計決定** が変更された時
* 物理的な**リポジトリ境界** が変更・分離された時
* 各主体（Human, AGY, Copilot 等）の**役割・権限境界** が更新された時
* **自己改変（Self-Modification）の Experimental 制約** の解除条件に変更があった時

**【責任の所在】**:
セッション終了時に **最新の handover ドキュメントを作成するエージェント** が、`bootstrap.md` の記述と現在の開発ステータス・ルールの整合性を検証し、必要に応じて更新する責任を負います。

---

## 8. Read Next (推奨資料)

さらに深く把握したい場合は、以下のファイルをこの順で読み進めてください。

1. [AGENTS.md (エージェント憲章)](file:///Users/nabe/src/github.com/nabe126/kanon/.agents/AGENTS.md) - エージェント行動規範。
2. [docs/roadmap.md](file:///Users/nabe/src/github.com/nabe126/kanon/docs/roadmap.md) - ロードマップと各フェーズの Exit Criteria。
3. [docs/worklog/](file:///Users/nabe/src/github.com/nabe126/kanon/docs/worklog/) 内の最新の handover ファイル - 直前の開発ステータスの詳細。
