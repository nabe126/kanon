# ワークログ: テストハーネス用環境変数マッピングの追加と実機検証前修正

* **作成日時**: 2026-06-27T06:35:00+09:00
* **テーマ**: 実機 (GPD WIN 3) でのロールバック結合テストで `/healthz/fail` が 403 Forbidden になった不具合の修正、および `docker-compose.yml` での環境変数 `KANON_TEST_TRIGGER` 伝播の定義。

---

## 1. 🎯 目的と変更の背景

実機検証中に発見された「テストハーネス無効化（`/healthz/fail` が 403 Forbidden を返す）」問題を解決するため、ホスト側の環境変数をコンテナ内へ引き渡すための設定漏れを解消します。
* **原因**: `docker-compose.yml` の `environment:` セクションに `KANON_TEST_TRIGGER` が定義されていなかったため、ホスト側で起動コマンド時に環境変数を指定しても、コンテナ内の Flask アプリに値が伝わっていなかった。
* **対策**: `docker-compose.yml` に `KANON_TEST_TRIGGER=${KANON_TEST_TRIGGER}` のマッピングを追加し、実行時に動的に有効化できるようにする。

---

## 2. 🛠️ 修正内容

### ① docker-compose.yml の修正
* **ファイル**: [ai-agent/docker-compose.yml](file:///Users/nabe/src/github.com/nabe126/kanon/ai-agent/docker-compose.yml)
* **内容**:
  `environment:` セクションへ `- KANON_TEST_TRIGGER=${KANON_TEST_TRIGGER}` を追加。

---

## 3. 🔄 ロールバック手順

1. 本修正により docker 起動等に不具合が出た場合は、直前のスナップショット（`backups/snapshot_20260624_234500` など）から復旧します。
   ```bash
   git restore ai-agent/docker-compose.yml
   ```

---

## 4. 🚦 現在の検証ステータス

* **環境変数設定の修正**: **Pass (L1)**

---

## 5. 📝 追記: 2026-06-27T06:38:29+09:00 - 開発環境およびワークログ運用ルールの改定
* **開発環境の固定**:
  * 連続稼働（実機検証）の必要がない単体テストは、すべて M4 Mac 上で行うことを決定。
* **ワークログの運用変更**:
  * 毎回新規にワークログファイルを起票するのを廃止。
  * トピックや日付単位で同一のファイルへ極力簡潔に追記する運用へシフト。
* **実施した修正**:
  * [.agents/AGENTS.md](file:///Users/nabe/src/github.com/nabe126/kanon/.agents/AGENTS.md) および [docs/bootstrap.md](file:///Users/nabe/src/github.com/nabe126/kanon/docs/bootstrap.md) を上記方針に沿ってアップデート。

---

## 6. 📝 追記: 2026-06-27T06:55:00+09:00 - `monitor.py` の `main()` 結合ライフサイクルテスト追加
* **目的**:
  * ロールバック監視プロセス (`monitor.py`) の `main()` 無限ループをシミュレートするテストを追加し、Mac ローカル上での L1 検証を完了。
* **実装内容**:
  * [tests/test_monitor.py](file:///Users/nabe/src/github.com/nabe126/kanon/ai-agent/workspace/tests/test_monitor.py) に `test_monitor_lifecycle` を追加。
  * `time.sleep` のモック内にループ終了フックを仕込み、`check_health` の順次戻り値 (`side_effect`) を利用して「一時的失敗からの回復」および「連続失敗時のロールバック」の両方の状態遷移をモック検証。
* **検証結果**:
  * Mac 開発機（L1）上で `pytest` を実行し、全 24 件（新規含む）のテストが 100% 正常終了（**24 passed**）することを確認。

---

## 7. 📝 追記: 2026-06-27T07:00:00+09:00 - Phase 1 進捗バックログ整理および Phase 2 設計提案書の構築
* **目的**:
  * 人間による実機（L2/L3）検証を Pending とする方針を受け、ドキュメント・バックログの整理、および実機検証後に即時移行可能なように Phase 2 の詳細設計を整備。
* **実施内容**:
  * **設計書の新規起票**: [docs/architecture/phase2-design-proposal.md](file:///Users/nabe/src/github.com/nabe126/kanon/docs/architecture/phase2-design-proposal.md) を作成。「思考ログ処理パイプライン (inbox ➔ processor ➔ output)」の詳細、YAML Frontmatter、Git による記憶バージョン管理手法を定義。
  * **進捗・バックログ更新**: [docs/bootstrap.md](file:///Users/nabe/src/github.com/nabe126/kanon/docs/bootstrap.md) および [docs/roadmap.md](file:///Users/nabe/src/github.com/nabe126/kanon/docs/roadmap.md) を更新。ロールバックに関する L1 テスト合格のステータス反映、および Phase 2 設計書へのリンクと To-Do を最新化。

---

## 8. 📝 追記: 2026-06-27T07:55:00+09:00 - Phase 2 長期記憶基盤の設計レビュー資料の作成
* **目的**:
  * Phase 2 実装着手前の設計合意・レビューのため、主要な技術的論点（責務、API、パイプライン、リポジトリ分離、検索方式、将来像）に関する整理資料を構築。
* **実施内容**:
  * [docs/architecture/phase2-design-review.md](file:///Users/nabe/src/github.com/nabe126/kanon/docs/architecture/phase2-design-review.md) を新規作成。各論点のトレードオフ、推奨案をまとめ、ADR-010/ADR-011 の起票候補を提案。
  * `bootstrap.md` の Read Next に参照リンクを追記。

---

## 9. 📝 追記: 2026-06-27T08:20:00+09:00 - 人間の認知モデルに基づく長期記憶構造への設計再構成
* **目的**:
  * 人間の認知制約（Working Memory容量制限、Baddeley/Tulvingモデル、優先度付き Read Bus）に準拠したエージェント記憶サブシステムへの設計再構成。
* **実施内容**:
  * **設計書の新規起票**: [docs/architecture/phase2-cognitive-memory-design.md](file:///Users/nabe/src/github.com/nabe126/kanon/docs/architecture/phase2-cognitive-memory-design.md) を作成。L0〜L4記憶階層、Working Memory（3〜10個制限）、フォールバック優先検索経路（Read Bus）、および日本十進分類法（NDC）を参考モデルとした Agent Decimal Classification (ADC) の適用評価を明文化。
  * **他ドキュメントの同期**: `bootstrap.md` と `roadmap.md` の Phase 2 マイルストーン、タスクリスト、Exit Criteria をこの認知モデルに基づき全面的に更新。

---

## 10. 📝 追記: 2026-06-27T08:30:00+09:00 - Phase 2 統合マスター仕様書 (Master Spec) の起票とドキュメントツリー整理
* **目的**:
  * 設計文書のスパゲッティ化を防止するため、Phase 2 の全設計ドキュメントを統括するシングルエントリポイント「Master Spec」を構築し、他の詳細設計書を従属（ぶら下げ）マッピング。
* **実施内容**:
  * **Master Spec 新規起票**: [docs/architecture/phase2-master-spec.md](file:///Users/nabe/src/github.com/nabe126/kanon/docs/architecture/phase2-master-spec.md) を作成。
  * **詳細設計書の従属関係明記**: `phase2-cognitive-memory-design.md`, `phase2-design-proposal.md`, `phase2-design-review.md` の各ヘッダーに親ドキュメントへのリンクを追記。
  * **リンクの集約**: `bootstrap.md` および `roadmap.md` からの個別設計へのリンクを、新設した `phase2-master-spec.md` への単一リンクへ集約。

---

## 11. 📝 追記: 2026-06-27T09:20:00+09:00 - L3 実機依存の排除および完全自動テスト基盤の段階的構築
* **目的**:
  * 実機 Ubuntu での人手による L3 検証を廃止し、CI やローカルで再現可能な「閉じた L3 自動テストシミュレーション環境」を段階的に構築。
* **実施内容 (コミット分割順)**:
  * **Phase 1 (インフラコンテナ化)**: [docker-compose.test-l3.yml](file:///Users/nabe/src/github.com/nabe126/kanon/docker-compose.test-l3.yml) と [controller/Dockerfile.monitor](file:///Users/nabe/src/github.com/nabe126/kanon/controller/Dockerfile.monitor) を作成。セキュリティを重視し、`docker.sock` はマウントしない。
  * **Phase 2 (シミュレーター・オートリロード)**: [run_l3_simulation.py](file:///Users/nabe/src/github.com/nabe126/kanon/ai-agent/workspace/tests/run_l3_simulation.py) を「観測型」として実装。`KANON_TEST_TRIGGER=true` 時に Flask の debug / autoreload モードを有効化し、`monitor.py` が LKG のファイルを書き戻した際に Flask が自動再起動して `healthz` が 200 に戻ることをシミュレート。
  * **Phase 3 (Makefile統合)**: [Makefile](file:///Users/nabe/src/github.com/nabe126/kanon/Makefile) を作成し、`make test-l3` で自動テストが走るように統合。
  * **Phase 4 (CI化)**: [.github/workflows/test-l3.yml](file:///Users/nabe/src/github.com/nabe126/kanon/.github/workflows/test-l3.yml) を作成し、GitHub Actions 上で全 L3 結合テストが PR/Push ごとに自動で実行される仕組みを構築。

---

## 12. 📝 追記: 2026-06-27T09:40:00+09:00 - L3 自動テスト検証結果とCI失敗の深層分析
* **目的**:
  * 構築したテスト環境でのローカル実行および CI (GitHub Actions) 実行を行い、終了コードと実行ログを収集。
* **検証結果**:
  * **ローカル (Mac)**: `docker compose config` / `make test-l3` はホストに Docker が未導入のためエラー終了 (Exit Code 127/2)。
  * **GitHub Actions (CI)**: `Run L3 Integration Simulation` ステップでタイムアウト失敗 (Exit Code 2/1、実行時間約67秒)。
* **失敗原因の特定**:
  * `monitor.py` が LKG バックアップから `src/` へファイルを書き戻す際、`shutil.copytree` がファイルタイムスタンプ (`mtime`) を過去の状態で保持したままコピーするため、Flask (Werkzeug) オートリローダーがファイルの変更を検知せず再起動しなかった。結果として、メモリ上の障害状態がリセットされずタイムアウトした。
* **対策案**:
  * `monitor.py` 内でファイルを復元した直後に、すべての Python ファイルを `os.utime` などで更新 (`touch`) してオートリロードを確実にトリガーさせる。
