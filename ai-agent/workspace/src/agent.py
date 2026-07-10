import os
import sys
import time
import asyncio
from google.genai import types
from google.genai.errors import APIError, ServerError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

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
            res = subprocess.run(command, shell=True, capture_output=True, text=True, cwd="/workspace")
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

            # API呼び出し
            response_text = await generate_agent_reply(contents, api_key=api_key)
            
            # 応答の記録と出力
            history.add_message(history_key, "model", response_text)
            print(f"\r🤖 Agent > {response_text}")

        except Exception as e:
            print(f"\r❌ 内部エラーが発生しました: {e}")

def _is_transient_error(exception):
    """一過性のエラー（5xx系、または429レートリミットなど）であるか判定します"""
    if isinstance(exception, ServerError):
        return True
    if isinstance(exception, APIError):
        return exception.code in [429, 503, 504]
    return False

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception(_is_transient_error),
    reraise=True
)
async def generate_agent_reply(contents: list, api_key: str = None, genai_client = None) -> str:
    """Gemini API を呼び出して応答テキストを生成します。自律エージェントとして開発用ツールを実行するループを持ちます。"""
    if not api_key and not genai_client:
        logger.error("GEMINI_API_KEY is not set and genai_client is not provided.")
        return "エラー: GEMINI_API_KEY 環境変数が設定されていません。"

    try:
        if not genai_client:
            from google import genai
            genai_client = genai.Client(api_key=api_key)

        # ツール関数のマッピング
        from utils import agent_tools
        tool_map = {
            "list_dir": agent_tools.list_dir,
            "grep_search": agent_tools.grep_search,
            "read_file": agent_tools.read_file,
            "replace_file_content": agent_tools.replace_file_content,
            "write_to_file": agent_tools.write_to_file,
            "request_command_execution": agent_tools.request_command_execution,
        }
        
        tools = list(tool_map.values())
        
        system_instruction = (
            "You are Kanon Arahabaki Agent (Antigravity), a powerful autonomous coding assistant.\n"
            "You have access to tools that allow you to read and write files in the workspace, search code, and request command execution.\n"
            "Your goal is to help the user with coding, refactoring, and debugging tasks.\n"
            "CRITICAL: If the user asks you to run a command (such as 'make status', 'make test', etc.), do NOT reply with 'I cannot run commands' or ask the user to run it for you. You MUST call the `request_command_execution` tool to request its execution.\n"
            "Similarly, to view file contents or list directories, you MUST use the corresponding tools (`read_file`, `list_dir`) instead of asking the user to do it.\n"
            "When modifying files, always verify syntax and logic.\n"
            "Keep your responses concise and update the user on what you did."
        )

        max_iterations = 8
        model_name = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
        for iteration in range(max_iterations):
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                tools=tools
            )
            response = genai_client.models.generate_content(
                model=model_name,
                contents=contents,
                config=config
            )
            
            # モデルのレスポンスを履歴に追加
            if response.candidates and response.candidates[0].content:
                model_content = response.candidates[0].content
                contents.append(model_content)
            else:
                break

            function_calls = response.function_calls
            if not function_calls:
                return response.text or "(空の応答)"

            tool_responses = []
            for function_call in function_calls:
                name = function_call.name
                args = function_call.args
                
                logger.info(f"[AgentLoop] Tool call: {name} with args {args}")
                
                if name in tool_map:
                    try:
                        result = tool_map[name](**args)
                    except Exception as exec_err:
                        result = f"Error executing tool {name}: {exec_err}"
                else:
                    result = f"Error: Tool {name} is not registered."

                logger.info(f"[AgentLoop] Tool result: {result[:200]}")
                
                tool_responses.append(
                    types.Part.from_function_response(
                        name=name,
                        response={"result": result}
                    )
                )

            contents.append(
                types.Content(
                    role="tool",
                    parts=tool_responses
                )
            )

        return "警告: エージェントの自律実行ループの最大回数に達しました。ここまでの結果を報告します。"

    except Exception as e:
        logger.error(f"Failed to generate content from Gemini API: {e}")
        raise e

def main():
    asyncio.run(chat_loop())

if __name__ == "__main__":
    main()
