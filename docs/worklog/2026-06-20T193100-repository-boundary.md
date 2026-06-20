# ワークログ: リポジトリ境界設計 (Worklog: Repository Boundary Design)

* **作成日時**: 2026-06-20T19:31:00+09:00
* **目的**: 自己改変を行う自律AIエージェントが安全かつ自律的に進化できるよう、ディレクトリ構成と権限境界を再設計し、適用した記録。

---

## 1. 権限境界マトリクス (Permission Matrix)

エージェント自身が動作するコンテナ（非特権ユーザー実行）と、システム全体を監視・管理する Controller（特権/Docker socketマウント）におけるアクセス権限を以下のように定義します。

| ディレクトリ / ファイル | エージェント (Agent) | 管理プロセス (Controller) | 設計・分離の意図 |
| :--- | :--- | :--- | :--- |
| `ai-agent/secrets/.env` | **アクセス不可 (No Access)** | 読込のみ (Read-Only) | APIキー、トークンの完全隔離。エージェント自身による誤編集、漏洩、Git誤コミットを防ぐ。 |
| `ai-agent/docker-compose.yml`<br>`ai-agent/Dockerfile` | 読込のみ (Read-Only) | 読込・書込可 (Read/Write) | インフラの定義。エージェントによるDocker設定や起動コマンドの書き換えを防止。 |
| `controller/` | **アクセス不可 (No Access)** | 読込・書込可 (Read/Write) | 監視・再起動制御を行う Controller の配置ディレクトリ。エージェントからのアクセスを遮断。 |
| `ai-agent/workspace/src/` | **読込・書込可 (Read/Write)** | 読込・書込可 (Read/Write) | **自己改変の対象領域（ソースコード）。** エージェントはこの中にあるロジックのみを書き換える。 |
| `ai-agent/workspace/tests/` | **読込・書込可 (Read/Write)** | 読込・書込可 (Read/Write) | **テストコード領域。** 自律テストの作成・実行を行うための領域。 |
| `ai-agent/workspace/state/` | **読込・書込可 (Read/Write)** | **読込・書込可 (Read/Write)** | **状態永続化領域。** 再起動を跨いだタスクの記憶や、実行ステータスを保存する（詳細は3章）。 |
| `ai-agent/workspace/backups/` | **読込のみ (Read-Only)** | **読込・書込可 (Read/Write)** | バックアップデータの改ざん・削除の防止。エージェント自身はバックアップファイルを消去できない。 |
| `docs/` | **読込・書込可 (Read/Write)** | 読込・書込可 (Read/Write) | Docs as Code 運用の維持。エージェント自身によるドキュメントの更新・起票を許可。 |

---

## 2. 📂 適用されたディレクトリ構成

再設計が適用された実際のリポジトリのディレクトリ構成です。

```text
kanon/
├── .agents/                        # 【エージェント: Read-Only】
│   └── AGENTS.md                   # 開発ルール
├── docs/                           # 【エージェント: Read/Write】Docs as Code 領域（構造化済）
│   ├── architecture/               # システム構成図やインフラ設計書
│   │   └── architecture.md
│   ├── decisions/                  # 技術選定や設計決定 (ADR)
│   │   └── decisions.md
│   ├── lessons/                    # 知見やトラブルシューティング (Lessons Learned)
│   │   └── lessons.md
│   ├── guides/                     # エージェント自身が従うべきオペレーションガイド
│   └── worklog/                    # 日々の開発記録・ログ
│       └── 2026-06-20T193100-repository-boundary.md  # [本ファイル]
├── controller/                     # 【エージェント: アクセス不可】監視・再起動スクリプト等の配置ディレクトリ
└── ai-agent/                       # デプロイ・実行環境
    ├── docker-compose.yml          # 【エージェント: Read-Only】※ secrets/.env を env_file に指定
    ├── Dockerfile                  # 【エージェント: Read-Only】エージェント実行コンテナの定義
    ├── Dockerfile.bk               # 【エージェント: Read-Only】Dockerfileのバックアップ
    ├── secrets/                    # 【エージェント: アクセス不可】★機密情報隔離フォルダ★
    │   └── .env                    # APIキー、トークンなどの環境変数
    └── workspace/                  # コンテナマウント領域
        ├── src/                    # 【エージェント: Read/Write】★自己改変ロジック領域★
        │   ├── agent.py            # コンテナ初期化・動作テスト用
        │   ├── autonomous_agent.py # 自律巡回ループのプロトタイプ
        │   └── discord_agent.py    # Flaskダッシュボードとエージェントメインプロセスの枠組み
        ├── tests/                  # 【エージェント: Read/Write】★テストコード領域★
        │   └── gemini_test.py      # Gemini API接続テストスクリプト
        ├── state/                  # 【エージェント: Read/Write】★状態管理領域★
        ├── backups/                # 【エージェント: Read-Only】LKG退避領域
        │   └── discord_agent.bk    # ソースファイルのバックアップ
        └── requirements.txt        # 【エージェント: Read-Only】ライブラリ依存定義
```

---

## 3. 追加要素の設計詳細

### ① エージェント状態管理領域 (`workspace/state/`)
* **役割**:
  エージェントが自己改変や不意のエラーでコンテナ再起動した際、**「再起動前に自分は何のタスクを行っていたか」「次に再開すべき処理は何か」**を記憶し、復元するためのシリアライズされたデータを保存します。
* **運用**:
  * エージェントは各実行ステップの開始/終了時に、現在のタスクID、実行ログの要約、コンテキスト情報を `current_task.json` に書き出します。
  * 再起動直後、システム側の起動エントリポイント（`src/agent.py`等）は `state/current_task.json` を読み込み、エージェントへ以前のコンテキストをインジェクションしてシームレスに処理を再開させます。

### ② ドキュメント（docs/）の細分化と知識ベース化
エージェントが自己矛盾のない意思決定を行えるよう、`docs/` 以下を以下の目的別に整理しました。
* **docs/architecture/**: システム全体のブロック図やデータフロー。
* **docs/decisions/**: ADR（アーキテクチャ意思決定レコード）を格納。
* **docs/lessons/**: 障害対応や失敗の知見をテンプレート化して蓄積。
* **docs/guides/**: エージェント向けに「git commitのプレフィックスルール」や「コードスタイルのガイド」など、コーディング規約を記述。

### ③ `requirements.txt` の権限制御とパッケージ追加フロー
エージェントが動的にライブラリを拡張したい場合、無制限にシステム全体にパッケージを追加させると、依存関係の競合や悪意あるパッケージのロードによりエージェントが永続的に起動不能になるリスクがあります。

* **二重管理方式の採用**:
  * ベースパッケージ（`ai-agent/requirements.txt`）: discord.py, google-genai 等のシステム基盤に必要なライブラリ。エージェントは**読み込み専用**。
  * 動的追加パッケージ（`workspace/requirements.txt`）: エージェントが追加したいパッケージのみを記述。エージェントは**書き込み可能**。
* **検証・反映フロー**:
  1. エージェントが `workspace/requirements.txt` に新規パッケージ名を追記。
  2. エージェントが再起動を要求。
  3. コントローラーはコンテナを再起動する際、インストール検証を実行し、問題がなければ本番に反映。
