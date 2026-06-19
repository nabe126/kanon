# 開発・運用ルール (Project Rules)

本プロジェクト（arahabaki）における開発およびドキュメント運用のルールです。
AIアシスタント（Antigravity、およびその他のエージェント）は、すべての作業において本ルールを厳格に遵守してください。

## 1. Docs as Code 運用の徹底
* ドキュメントはすべて `docs/` ディレクトリ配下に Markdown 形式で配置し、コードと同様に Git でバージョン管理します。
* ユーザーは「ドキュメントを整理する人」ではなく**「意思決定および承認を行う人」**です。
* AIはユーザーとの会話やコードの変更履歴から、以下のドキュメントを主導して更新・整理し、提案してください。
  * [docs/architecture.md](file:///Users/nabe/src/github/nabe126/arahabaki/docs/architecture.md) : システムの構造とコンポーネントの設計
  * [docs/decisions.md](file:///Users/nabe/src/github/nabe126/arahabaki/docs/decisions.md) : 技術選定や設計方針の意思決定履歴 (ADR)
  * [docs/lessons.md](file:///Users/nabe/src/github/nabe126/arahabaki/docs/lessons.md) : 障害、失敗、トラブルから得た知見
  * [docs/roadmap.md](file:///Users/nabe/src/github/nabe126/arahabaki/docs/roadmap.md) : ロードマップとタスクの進捗管理

## 2. 自己改変（自己進化）の安全性
* GPD-Agent（自律型エージェント）が自ら動作不能（デッドロック）に陥らないよう、以下の検証を徹底します。
  * エージェントコードの上書き前に、静的解析（`py_compile` や `ruff` など）による構文・型チェックを必須とします。
  * Discord接続やアップデート機能など、エージェントの基盤となるコアロジックを破壊または削除する変更案を拒否するガードレールを設けます。
  * 万が一起動に失敗した場合、前回の稼働可能バージョンに自動ロールバックする仕組みを設けます。
