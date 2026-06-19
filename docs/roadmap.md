# ロードマップとタスク管理 (Roadmap)

『GPD-Agent 基本設計メモ v0.1』に基づく開発フェーズおよび進捗状況の管理ドキュメントです。

---

## 🗺️ 開発マイルストーン (Milestones)

### Phase 1: 生存・観測・復旧基盤の構築 ⏳ (最優先)
「壊れても元に戻せる」「何が起きているかエージェント自身が把握できる」ための基盤を作ります。
- [x] プロジェクト運用の設計とドキュメンテーション (Docs as Code 導入)
- [ ] **エージェント視覚ツール (Observation Tools)** の実装
  - `read_file`, `list_files`, `view_logs` (Docker logs の取得)
- [ ] **安全な自己改変フロー (Safe Update Flow)** の実装
  - `write_file` 呼び出し時の検証フロー (candidate保存 -> syntax check -> import check)
  - `backup` 機構の実装 (タイムスタンプ管理、最低5世代保持)
- [ ] **自動ロールバック機構 (Rollback)** の実装
  - 起動失敗検知時の最新バックアップへの自動復帰
  - エージェント自身がトリガー可能なロールバックコマンド

### Phase 2: 健康診断とリトライの自動化 (Healthcheck & Resilience)
稼働の継続性を高めるための回復処理を追加します。
- [ ] **Gemini API 503エラー対策**:
  - 指数バックオフによるリトライ機構 (1, 2, 4, 8, 16秒) の実装。
- [ ] **ヘルスチェック (Healthcheck)** の実装:
  - CPU, Memory, Disk, コンテナ状態, API接続状態の診断機能。

### Phase 3: Providerの抽象化
将来的な複数LLM対応を見据え、インターフェースを分離します。
- [ ] エージェントロジックからLLM Providerを疎結合にするラッパーの作成。
- [ ] エージェントがモデル名やProvider詳細を意識せずに利用できる構造への移行。

### Phase 4: OpenAIの追加
- [ ] OpenAI Providerの実装および動作検証。

### Phase 5: Claudeの追加
- [ ] Claude Providerの実装および動作検証。

---

## 📋 直近のタスクリスト (To-Do)

* [ ] `docs/architecture.md` および `docs/decisions.md` への基本設計メモ v0.1 反映の完了
* [ ] ログ・検証・バックアップ機能（Phase 1）を実装するための開発アプローチの決定
