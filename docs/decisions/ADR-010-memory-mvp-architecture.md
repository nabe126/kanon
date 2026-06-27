# ADR-010: Memory MVP 階層ストレージと API の設計決定

* **ステータス**: Proposed (提案中)
* **作成日時**: 2026-06-27T15:10:00+09:00
* **作成者**: Antigravity
* **対象機能**: Phase 2 Sprint 1: Memory MVP

---

## 1. 背景 (Context)

Kanon Phase 2 (Long-term Memory Foundation) の Sprint 1 において、チャットおよび CLI から記憶・検索が完結する Memory MVP を構築する必要があります。これにあたり、以下の認知制約と設計要件を生存最優先の原則に準拠しつつ、シンプルに実装する方法を決定する必要があります。

1. **L0〜L4 階層構造**: 特に L1 (Working Memory) と L3/L4 (Long-term Memory) のデータ分離。
2. **Working Memory 容量制限**: LLM のコンテキスト肥大化を防ぐため、L1 スロット数を 3〜10 個に制限し、超過時に自動退避する機構。
3. **優先度付き Read Bus**: $L1 \rightarrow L3 \rightarrow L4$ の順で検索するフォールバックチェーン。
4. **Git バージョニング境界**: 記憶の変更履歴を Git で追跡可能にし、差分可読性を高める。
5. **記憶操作インターフェース**: remember/recall を行う REST API、内部 Python API、および CLI の提供。

---

## 2. 意思決定 (Decision)

生存最優先（外部インフラ非依存・軽量化）と Git 差分可読性（Docs as Code）の両立のため、**「L1 (JSON) ＋ L3/L4 (Markdown with Frontmatter) ＋ ローカル Grep 検索」** のハイブリッドストレージ構造を採用することを決定しました。

### ① 記憶階層とストレージ実体
* **L1 (Working Memory)**: 
  - 実体: `ai-agent/workspace/state/working_memory.json` (JSONファイル)
  - 容量制限: **最大 5 スロット** (`MAX_L1_SLOTS = 5`)。
  - 自動退避 (Flashing): `remember` により L1 に追加されスロット数が 5 を超えた場合、最も古くに更新された（`updated_at` が最小の）トピックを L1 から削除し、L3 (Episodic) に Markdown ファイルとして自動的にフラッシュ（退避・永続化）します。
* **L3 (長期エピソード記憶 / 意思決定・教訓)**:
  - 実体: `ai-agent/workspace/memory/decision_history/YYYYMMDD_topic_name.md`
* **L4 (長期意味記憶 / プロファイル・事実)**:
  - 実体: `ai-agent/workspace/memory/semantic/topic_name.md`

### ② 記憶 Markdown ファイルフォーマット
L3 および L4 の長期記憶は、共通の YAML Frontmatter と Markdown 本文で構成します。
```markdown
---
id: MEM-YYYYMMDD-HHMMSS
title: <トピック名>
category: <ADC分類コード (例: 100=決定, 500=教訓)>
tags: [tag1, tag2]
created_at: YYYY-MM-DDTHH:MM:SS
updated_at: YYYY-MM-DDTHH:MM:SS
---
<記憶の具体的な内容>
```

### ③ remember / recall API 仕様

#### 1. remember API (`/memory/remember`)
* **引数**:
  - `topic` (str, 必須): トピック名。
  - `content` (str, 必須): 記憶内容。
  - `level` (str, オプション): `"L1"`, `"L3"`, `"L4"` (デフォルト: `"L1"`)。
  - `category` (str, オプション): ADC分類コード (デフォルト: `"general"` / `"100"` / `"500"`)。
  - `tags` (list, オプション): タグのリスト。
* **動作**:
  1. `level="L1"` の場合、`working_memory.json` に追加。スロット数が 5 個を超過した場合は、最古のトピックを L3 Markdown へ書き出して L1 から削除。
  2. `level="L3"` または `"L4"` の場合、対応するディレクトリに Markdown ファイルを新規作成。
  3. 新規に Markdown ファイルが作成または更新された場合は、Git 自動コミットを実行。

#### 2. recall API (`/memory/recall`)
* **引数**:
  - `query` (str, 必須): 検索クエリ。
  - `level` (str, オプション): 検索階層を指定（指定なしの場合は Read Bus 優先度検索）。
* **優先検索経路 (Read Bus)**:
  指定なしの場合、以下のフォールバックチェーンで部分一致（キーワード部分一致）検索を実行：
  1. **L1 (Working Memory)**: `working_memory.json` 内の `topic` または `content` を検索。発見されれば即時返却。
  2. **L3 (長期エピソード)**: `memory/decision_history/*.md` の Frontmatter および本文を Grep 検索。発見されれば即時返却。
  3. **L4 (長期意味)**: `memory/semantic/*.md` を Grep 検索。発見されれば即時返却。

#### 3. CLI インターフェース
CLI から直接記憶の作成・検索を実行できるようにします。
```bash
# 記憶
python3 -m src.memory.cli remember --topic "L3テスト成功" --content "Actions上のL3テストが完全自動化されてパスした。" --tags "l3,ci"

# 検索
python3 -m src.memory.cli recall --query "L3テスト"
```

---

## 3. 影響と結果 (Consequences)

* **メリット**:
  * データベースサーバーや外部 VectorDB 等の追加インフラが一切不要で、軽量かつ堅牢（生存最優先）。
  * 長期記憶がプレーンテキスト（Markdown）として保存されるため、Git 履歴で差分がクリアに記録され、人間が直接エディタで閲覧・修正・マージすることも容易。
  * Working Memory の容量制限により、プロンプト肥大化による LLM コンテキストの浪費を防止できる。
* **デメリット**:
  * 記憶件数が数千〜数万件に増大した場合、ファイル走査（Grep）のパフォーマンスが低下する。
    - *対策*: 将来のフェーズ (Phase 2 後期) で、SQLite-FTS5（全文検索インデックス）やローカル Vector 検索へ透過的にアップグレードするロードマップを ADR-011 にて規定する。
