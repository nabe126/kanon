import os
import sys
import time
import asyncio
from google.genai import types

# 自作モジュールのパス解決
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils.history import ConversationHistory
from utils.logger import get_logger
from memory.core import remember, recall, parse_markdown_with_frontmatter
from utils.asep_middleware import ASEPMiddleware, STATUS_EXECUTED

logger = get_logger("cli_agent")

STATE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../state"))
os.makedirs(STATE_DIR, exist_ok=True)
HISTORY_FILE = os.path.join(STATE_DIR, "cli_conversation_history.json")

def load_env_file():
    """secrets/.env から環境変数をパースして自動ロードします（外部ライブラリ不要）"""
    possible_paths = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../../secrets/.env")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../secrets/.env")),
        "/workspace/secrets/.env"
    ]
    for path in possible_paths:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip('"').strip("'")
                            if k not in os.environ:
                                os.environ[k] = v
                break
            except Exception as e:
                logger.error(f"Failed to load env file {path}: {e}")

def print_help():
    print("""
==== 💡 使用可能なコマンド一覧 ====
  /remember <topic> <content>   : 記憶領域（L1）にトピックと内容を保存します。
  /recall <query>              : 保存された記憶を Grep 検索し返却します。
  /plan <command>              : 実行計画 (ASEP PLAN) を起票します。
  /run <plan_id>               : 計画を承認（YES）してシェルコマンドを実行します。
  * /run <plan_id> NO          : 計画を却下（NO）します。
  /status <plan_id>            : 計画の現在のステータスを確認します。
  /logs <plan_id>              : 計画ファイル（Markdown）の内容を表示します。
  /help                        : このヘルプを表示します。
  /exit または /quit            : CLI を終了します。
=================================
""")

async def handle_cli_command(command_str):
    parts = command_str.split(" ", 1)
    cmd = parts[0].lower()
    args = parts[1].strip() if len(parts) > 1 else ""

    if cmd == "/remember":
        if not args:
            print("❌ 使用法: `/remember <topic> <content>`")
            return
        subparts = args.split(" ", 1)
        if len(subparts) < 2:
            print("❌ エラー: トピックと内容の両方を入力してください。")
            return
        topic, content = subparts[0], subparts[1]
        
        if remember(topic, content):
            print(f"✅ 記憶しました！\n  * トピック: {topic}\n  * レベル: L1 (Working Memory)")
        else:
            print("❌ 記憶の保存に失敗しました。")

    elif cmd == "/recall":
        if not args:
            print("❌ 使用法: `/recall <クエリ>`")
            return
        res = recall(args)
        if res.get("status") == "success":
            print(f"\n🧠 **記憶を発見しました！** (レベル: {res['level']})")
            print(f"  * **トピック**: {res['topic']}")
            print(f"  * **内容**:\n{res['content']}\n")
        else:
            print(f"🔍 クエリ '{args}' に一致する記憶は見つかりませんでした。")

    elif cmd == "/plan":
        if not args:
            print("❌ 使用法: `/plan <操作コマンド>`")
            return
        asep = ASEPMiddleware()
        plan = asep.create_plan(args, "L2", "CLI User request", f"User triggered CLI command: {args}")
        if plan:
            print(f"📋 **実行計画 (PLAN) を起票しました！**")
            print(f"  * **計画ID**: {plan['plan_id']}")
            print(f"  * **操作**: {plan['operation']}")
            print(f"  * **ステータス**: {plan['status']}")
            print(f"👉 実行するには `/run {plan['plan_id']}` を入力してください。")
        else:
            print("❌ 実行計画の起票に失敗しました。")

    elif cmd == "/run":
        if not args:
            print("❌ 使用法: `/run <計画ID> [YES/NO]`")
            return
        subparts = args.split(" ")
        plan_id = subparts[0]
        decision = subparts[1] if len(subparts) > 1 else "YES"

        asep = ASEPMiddleware()
        app_res = asep.approve_plan(plan_id, decision)
        if app_res.get("status") == "error":
            print(f"❌ 承認処理に失敗しました: {app_res.get('message')}")
            return

        if decision.upper() == "NO":
            print(f"🛑 計画 `{plan_id}` を却下しました。")
            return

        print(f"⚙️ 計画 `{plan_id}` の実行を開始します...")
        
        def run_op(command):
            import subprocess
            res = subprocess.run(command, shell=True, capture_output=True, text=True)
            return f"STDOUT:\n{res.stdout}\n\nSTDERR:\n{res.stderr}"

        file_path = asep._find_plan_file(plan_id)
        if not file_path:
            print(f"❌ 計画 `{plan_id}` のファイルが見つかりません。")
            return
            
        metadata, _ = parse_markdown_with_frontmatter(file_path)
        op_cmd = metadata.get("title", "").replace("ASEP Plan: ", "")

        exec_res = asep.execute_plan(plan_id, run_op, op_cmd)
        
        if exec_res.get("status") == STATUS_EXECUTED:
            print(f"✅ **計画 `{plan_id}` の実行が完了しました！**")
            print(f"【実行結果】\n{exec_res['result'][:1500]}")
        else:
            print(f"❌ **計画 `{plan_id}` の実行に失敗しました。**")
            print(f"エラー: {exec_res.get('error')}")

    elif cmd == "/status":
        if not args:
            print("❌ 使用法: `/status <計画ID>`")
            return
        asep = ASEPMiddleware()
        file_path = asep._find_plan_file(args)
        if not file_path:
            print(f"🔍 計画 `{args}` は見つかりませんでした。")
            return
        metadata, _ = parse_markdown_with_frontmatter(file_path)
        print(f"📊 **計画 `{args}` ステータス**")
        print(f"  * **ステータス**: {metadata.get('status')}")
        print(f"  * **リスクレベル**: {metadata.get('risk')}")
        print(f"  * **操作**: {metadata.get('title', '').replace('ASEP Plan: ', '')}")

    elif cmd == "/logs":
        if not args:
            print("❌ 使用法: `/logs <計画ID>`")
            return
        asep = ASEPMiddleware()
        file_path = asep._find_plan_file(args)
        if not file_path:
            print(f"🔍 計画 `{args}` は見つかりませんでした。")
            return
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        print(f"📄 **計画 `{args}` 実行履歴**\n```markdown\n{content}\n```")

async def chat_loop():
    load_env_file() # 環境変数の自動ロードを実行

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("⚠️ 警告: GEMINI_API_KEY 環境変数が設定されていません。対話機能はモックになります。")
    else:
        print("✅ GEMINI_API_KEY を検出・ロードしました。")

    history = ConversationHistory(HISTORY_FILE)
    history_key = "cli_session"

    print("\n==================================================")
    print("🤖 Kanon CLI Interactive REPL (Arahabaki Core)")
    print("==================================================")
    print("対話を開始します。終了するには '/exit' または '/quit' を入力してください。")
    print("コマンドの確認をするには '/help' を入力してください。")
    
    while True:
        try:
            user_input = input("\n👤 User > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n👋 終了します。")
            break

        if not user_input:
            continue

        if user_input.lower() in ("/exit", "/quit"):
            print("👋 終了します。")
            break

        if user_input.lower() == "/help":
            print_help()
            continue

        # 特殊コマンドフック (ASEP / Memory)
        if user_input.startswith("/"):
            await handle_cli_command(user_input)
            continue

        # Geminiとの対話処理
        if not api_key:
            print(f"🤖 Agent (Mock) > Gemini APIキーが設定されていません。入力されたプロンプト: '{user_input}'")
            continue

        print("🤖 Agent > 思考中...", end="", flush=True)

        try:
            # 履歴の取得と組み立て
            past_messages = history.get_messages(history_key)
            contents = []
            for msg in past_messages:
                contents.append(
                    types.Content(
                        role=msg["role"],
                        parts=[types.Part.from_text(text=msg["content"])]
                    )
                )

            # 今回の入力を追加
            history.add_message(history_key, "user", user_input)
            contents.append(
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=user_input)]
                )
            )

            # Gemini クライアント初期化とリクエスト
            from google import genai
            genai_client = genai.Client(api_key=api_key)
            
            # API呼び出し
            response = genai_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=contents
            )
            
            response_text = response.text or "(空の応答)"
            
            # 応答の記録と出力
            history.add_message(history_key, "model", response_text)
            print(f"\r🤖 Agent > {response_text}")

        except Exception as e:
            print(f"\r❌ 内部エラーが発生しました: {e}")

def main():
    asyncio.run(chat_loop())

if __name__ == "__main__":
    main()
