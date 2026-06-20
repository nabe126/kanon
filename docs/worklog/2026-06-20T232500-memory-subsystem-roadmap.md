# ワークログ: Memory Subsystem 思考パイプラインおよび自律要約バッチのロードマップ設計統合

* **作成日時**: 2026-06-20T23:25:00+09:00
* **テーマ**: 本スレッドで発生した設計思想（inbox/processor/outputパイプライン、定期要約バッチによるADR提案）の公式設計書（bootstrap.md, roadmap.md, README.md）へのキャノニカライズ（統合・固定化）。

---

## 1. 🎯 目的と背景

Kanon の本質的ビジョンである「長期記憶を持つデジタルツイン基盤」へ接続するため、Phase 1 完了後に着手する **Phase 2 (Memory Agent)** の核心概念として、以下を統合します。
* **思考パイプライン (Pipeline-based Autonomy)**: 常駐ループ（デーモン）ではなく、「inbox ➔ processor ➔ output」のデータ処理として自律性を定義。
* **定期バッチと自己監査**: 過去ログから自動で ADR や Lessons を抽出・要約起票する自律提案の仕組み。

本設計をドキュメントに固定することで、Phase 2 の開発スコープと設計意思を単一リファレンス上に明確に定義します。

---

## 2. 🛠️ 変更計画と設計箇所

1. **[docs/bootstrap.md](file:///Users/nabe/src/github.com/nabe126/kanon/docs/bootstrap.md)**
   * 「3. Architecture Snapshot」に `Memory Subsystem` と `思考パイプライン` の要約を追加（1セクション以内）。
2. **[docs/roadmap.md](file:///Users/nabe/src/github.com/nabe126/kanon/docs/roadmap.md)**
   * 能力ロードマップの `Phase 2: Memory Agent` に「Memory Subsystem」および「定期集約バッチによるADR/Lessons起票」をタスク・完了条件として追記。
3. **[README.md](file:///Users/nabe/src/github.com/nabe126/kanon/README.md)**
   * 「3. アーキテクチャ概要 (Architecture Overview)」に `Memory Subsystem & 思考パイプライン (Phase 2 構想)` セクションを追加し、Mermaid 概念図を交えて記述。

---

## 3. 🔄 ロールバック手順

1. ドキュメントの不整合や変更の差し戻しを行う場合、git を使用して変更前コミットにリストアします。
   ```bash
   git restore docs/bootstrap.md docs/roadmap.md README.md
   ```

---

## 4. 🚦 現在の検証ステータス

* **本設計の統合**: **Todo (Doc update)**
