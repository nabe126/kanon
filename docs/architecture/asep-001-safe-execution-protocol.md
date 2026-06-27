# AGY Safe Execution Protocol (ASEP-001)

* **ステータス**: Proposed (提案中)
* **作成日時**: 2026-06-27T17:23:35+09:00
* **作成者**: Human / Antigravity

---

## 1. 目的

AGY（自律実行エージェント）が、チャット経由でタスクを実行する際に：

* 暴走実行の防止
* 人間確認ポイントの明示
* 実行権限の段階制御
* ロールバック可能性の担保

を満たすための安全実行プロトコルを定義する。

---

## 2. 基本原則

### 2.1 実行は必ず「3段階構造」

すべての実行は以下に分解される：

$$\text{[PLAN]} \rightarrow \text{[REQUEST]} \rightarrow \text{[EXECUTE]}$$

| 段階 | 内容 | 人間介入 |
| :--- | :--- | :--- |
| **PLAN** | 何をやるか設計 | 必須（デフォルト停止点） |
| **REQUEST** | 実行許可要求 | 条件付き |
| **EXECUTE** | 実処理実行 | 制限付き自動 |

---

## 3. 実行権限レベル

### L0: 読み取り専用（安全）
* **対象操作**: `grep` / `read` / `list` / `recall`
* 外部副作用なし
* 常時許可

### L1: ローカル変更（安全だが記録必要）
* **対象操作**: ファイル編集、Markdown更新、JSON更新
* **条件**: 
  - 変更前後差分を必ず出力
  - Git commit前にPLAN生成

### L2: システム操作（制御対象）
* **対象操作**: `docker` / `make` / `test` / CI実行
* **条件**:
  - 必ず REQUEST フェーズ必要
  - 成功/失敗ログ保存必須

### L3: 自律修復・再起動（危険）
* **対象操作**: `rollback` / `restart` / `self-modification` / `memory rewrite`
* **条件**:
  - 人間の明示許可（YES/NO）
  - または事前承認ADRに基づく場合のみ

---

## 4. 実行フロー

### 4.1 標準フロー
1. **PLAN生成**: 行う操作と影響範囲の設計を起票
2. **人間レビュー**: 人間によるレビューと方針の確認
3. **REQUEST送信**: レベルに応じた実行要求の送信
4. **承認 or 却下**: ゲートウェイでの可否判定
5. **EXECUTE**: 実際のコマンド・コード適用
6. **RESULT報告**: 実行結果の出力と差分チェック
7. **LOG保存**: 意思決定と実行ログの永続化

---

## 5. ブロッキングルール

AGYは以下を禁止：

### ❌ 即時実行禁止
* ADR未承認の仕様変更
* CI設定変更
* テスト構造変更
* Docker構成変更

### ❌ 推測実行禁止
* 「たぶんこれで動くので修正しました」
* 「エラーっぽいので自己修復しました」

---

## 6. 自己修復ルール（重要）

自己修復は以下条件を満たす場合のみ実行できます：

### 👉 条件
* 事前に L3障害として検出されている
* 修復方法がADRまたはRunbookに存在する
* 差分が局所（1モジュール以内）

### ❌ 禁止
* システム構造変更を伴う修復
* 新規アーキテクチャ導入

---

## 7. チャット操作コマンド（最小セット）

AGYは以下のコマンドのみ標準サポートします：

* `/plan`      → 実行計画生成
* `/ask`       → 人間確認要求
* `/run`       → 実行
* `/rollback`  → 直前状態復元
* `/status`    → 状態確認
* `/logs`      → 実行履歴

---

## 8. 承認ゲート仕様

### 8.1 YES/NOゲート
```yaml
REQUEST:
  operation: docker restart
  risk: L2
  reason: test-l3 failure recovery
Approve? (YES / NO)
```

### 8.2 タイムアウトルール
* 60秒応答なし → 自動NO扱い
* NO扱い時 → EXECUTE禁止

---

## 9. ログ義務

すべての実行は以下のデータを保存します：
* input plan
* decision (YES/NO)
* execution logs
* result status
* rollback info

* **保存先**: `memory/decision_history/`

---

## 10. 重要設計思想

本プロトコルの本質：
> **「AGYは実行者ではなく、常に“提案者”である」**

実行権限は段階的に委譲されますが、最終的な破壊的操作は必ず外部の明示的承認を必要とします。

---

## 11. Phase 2との関係

本プロトコルは以下に依存します：
* [ADR-010](file:///Users/nabe/src/github.com/nabe126/kanon/docs/decisions/ADR-010-memory-mvp-architecture.md) Memory MVP
* L1/L3/L4 memory architecture
* Read Bus（L1→L3→L4）
