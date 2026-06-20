# ワークログ: apply_candidate_code の Experimental 制約定義と L2/L3 検証計画

* **作成日時**: 2026-06-20T22:50:00+09:00
* **テーマ**: `apply_candidate_code` の本番適用禁止および解除条件（5項目）の明文化、L2/L3 検証計画の策定。

---

## 1. 🎯 目的と変更の背景

技術 Phase 1 の成果物として実装された候補コード自動検証適用エンジン (`apply_candidate_code`) について、自律改変に伴う無限ループや予期せぬ破壊を防ぐため、人間（ユーザー）の指示に基づき「本番環境（`discord_agent.py`等）への適用・呼び出しを禁止する」という Experimental 制約を設定しました。
本制約はシステム全体の安全確保（Survival First）のために極めて重要であり、5つの解除条件が満たされるまで、検証エンジンはテストコード (pytest) からのみ呼び出されるテスト対象機能として厳格に扱います。

---

## 2. 🚦 Experimental 解除条件

以下の実機（GPD WIN 3 / Ubuntu / Docker）環境における検証がすべて成功した場合のみ、本番経路での適用禁止を解除します。

1. **Discord実接続確認**:
   * 本物の `DISCORD_BOT_TOKEN` を設定し、Discord クライアントが疎通して管理者からのメッセージを送受信できること。
2. **Gemini実疎通確認**:
   * 実際の `GEMINI_API_KEY` を介して Google GenAI SDK で推論が行われ、メッセージに対して応答が返ること。
3. **`monitor.py` 実機ロールバック成功**:
   * 実機上の Docker デーモンおよび Docker ソケットを介して、`monitor.py` が異常検知時に `docker restart ai_agent_core` を呼び出して正常に復旧できること。
4. **LKG復元成功の実証**:
   * 異常発生時に `LKG.json` から過去のスナップショットディレクトリが正しく読み取られ、`src/` 配下に正確に復旧・上書き展開されること。
5. **healthcheck閾値の実機チューニング**:
   * 実機の CPU コア数および平常時のリソース使用量（CPU、メモリ、ディスク）に基づき、ヘルスチェックの warning / unhealthy 閾値が適切であり、不要な再起動（偽陽性）を発生させないことを確認・チューニングすること。

---

## 3. 🚦 今後の L2/L3 検証計画

優先タスクとして、以下の順序で L2/L3 実機検証を推進します。

### ステップ1: 実機環境のセットアップと Flask /healthz の確認 (L2)
* `secrets/.env` に本物の API キーを一時的に配置。
* Docker Compose を使ってコンテナを起動し、ホスト側から `curl http://localhost:5000/healthz` を叩いてメトリクスが正しくパースされ、ステータスが `healthy` を返すか確認する。

### ステップ2: モニター（`monitor.py`）の動作確認 (L2/L3)
* ホスト側で `python controller/monitor.py` を起動し、コンテナを監視させる。
* コンテナの停止や意図的な無応答（ポート遮断等）により、最大失敗回数に達した後に `execute_rollback()` が実行され、コンテナが再起動されるか確認する。

---

## 4. 🔄 ロールバック手順

1. `AGENTS.md` の記述に不整合が生じた、または記述を以前の状態に戻す場合は、git コマンドにより `git restore .agents/AGENTS.md` を実行します。

---

## 5. 🚦 現在の検証ステータス

| 機能名 | 検証レベル | ステータス | 備考 |
| :--- | :--- | :--- | :--- |
| **apply_candidate_code** | L1 / L2 | **Todo (Experimental)** | テスト時のみ実行、本番接続は禁止 |
| healthcheck.py (閾値判定) | L1 / L2 | Pass (L1) | 実機でのチューニングが必要 |
| monitor.py | L1 / L2 | Pass (L1) | 実機ロールバック実証が必要 |
