import os
import sys
import time
import asyncio
from flask import Flask, jsonify, request
from threading import Thread
import discord
from google.genai import types
from google.genai.errors import APIError, ServerError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

# 自作ユーティリティのインポート
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils.healthcheck import get_system_metrics
from utils.logger import get_logger
from utils.history import ConversationHistory

logger = get_logger("discord_agent")

# エージェントの現在の状態を保持する変数
agent_status = "Initializing..."
# Webサーバーのポート番号
WEB_SERVER_PORT = 5000

# 会話履歴の保存先
STATE_DIR = "/workspace/state"
if not os.path.exists(STATE_DIR):
    # ローカル開発環境での動作も考慮し代替パスを確認
    STATE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../state"))
os.makedirs(STATE_DIR, exist_ok=True)
HISTORY_FILE = os.path.join(STATE_DIR, "conversation_history.json")

# 履歴インスタンスの生成
history = ConversationHistory(HISTORY_FILE)

# Discord クライアントのインテント設定
intents = discord.Intents.default()
intents.message_content = True  # メッセージ本文読み取りインテント
client = discord.Client(intents=intents)

app = Flask(__name__)

@app.route('/')
def home():
    return f"""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AI Agent Status</title>
        <meta http-equiv="refresh" content="5"> <!-- 5秒ごとに自動更新 -->
        <style>
            body {{ font-family: sans-serif; margin: 20px; background-color: #f4f4f4; color: #333; }}
            h1 {{ color: #0056b3; }}
            p {{ font-size: 1.1em; }}
            .status-box {{ background-color: #fff; border: 1px solid #ddd; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            .error {{ color: red; font-weight: bold; }}
            .info {{ color: green; }}
        </style>
    </head>
    <body>
        <h1>AI Agent Status Dashboard</h1>
        <div class="status-box">
            <p><strong>Agent Status:</strong> <span class="{'error' if 'Error' in agent_status else 'info'}">{agent_status}</span></p>
            <p>This page automatically refreshes every 5 seconds to show the latest status.</p>
            <p>Web server is running on port {WEB_SERVER_PORT}.</p>
        </div>
    </body>
    </html>
    """

@app.route('/healthz')
def healthz():
    metrics = get_system_metrics()
    metrics["agent_status"] = agent_status
    # agent_status に Error が含まれる場合は unhealthy とする
    if "Error" in agent_status:
        metrics["status"] = "unhealthy"
    # warningステータスでもコンテナ自体は生きて応答しているので200、致命的エラー時のみ500
    code = 200 if metrics["status"] in ["healthy", "warning"] else 500
    return jsonify(metrics), code

# テストハーネス用の疑似障害発生エンドポイント
@app.route('/healthz/fail', methods=['GET', 'POST'])
def healthz_fail():
    if os.getenv("KANON_TEST_TRIGGER", "false").lower() != "true":
        return jsonify({"error": "Forbidden", "message": "Test harness is disabled."}), 403
    global agent_status
    logger.warning("[TestHarness] Dynamic failure triggered via /healthz/fail")
    agent_status = "Error: Simulated failure triggered by TestHarness"
    return jsonify({"status": "error", "message": "Failure state has been set."}), 200

# 記憶 MVP API
@app.route('/memory/remember', methods=['POST'])
def api_remember():
    try:
        data = request.json or {}
        topic = data.get("topic")
        content = data.get("content")
        level = data.get("level", "L1")
        category = data.get("category", "general")
        tags = data.get("tags", [])
        
        if not topic or not content:
            return jsonify({"status": "error", "message": "Missing 'topic' or 'content' in request body."}), 400
            
        from src.memory.core import remember
        success = remember(topic, content, level, category, tags)
        if success:
            return jsonify({"status": "success", "message": f"Remembered topic '{topic}' at level {level}."}), 200
        else:
            return jsonify({"status": "error", "message": "Failed to save memory."}), 500
    except Exception as e:
        logger.error(f"Error in api_remember: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/memory/recall', methods=['GET'])
def api_recall():
    try:
        query = request.args.get("query")
        level = request.args.get("level")
        
        if not query:
            return jsonify({"status": "error", "message": "Missing 'query' parameter."}), 400
            
        from src.memory.core import recall
        res = recall(query, level)
        code = 200 if res.get("status") == "success" else 404
        return jsonify(res), code
    except Exception as e:
        logger.error(f"Error in api_recall: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ASEP 安全実行 API
@app.route('/asep/plan', methods=['POST'])
def api_asep_plan():
    try:
        data = request.json or {}
        operation = data.get("operation")
        risk = data.get("risk")
        reason = data.get("reason", "general task execution")
        details = data.get("details", "")
        
        if not operation or not risk:
            return jsonify({"status": "error", "message": "Missing 'operation' or 'risk' in request body."}), 400
            
        from src.utils.asep_middleware import ASEPMiddleware
        asep = ASEPMiddleware()
        plan = asep.create_plan(operation, risk, reason, details)
        if plan:
            return jsonify(plan), 200
        return jsonify({"status": "error", "message": "Failed to create plan."}), 500
    except Exception as e:
        logger.error(f"Error in api_asep_plan: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/asep/approve', methods=['POST'])
def api_asep_approve():
    try:
        data = request.json or {}
        plan_id = data.get("plan_id")
        decision = data.get("decision", "YES")
        
        if not plan_id:
            return jsonify({"status": "error", "message": "Missing 'plan_id'."}), 400
            
        from src.utils.asep_middleware import ASEPMiddleware
        asep = ASEPMiddleware()
        res = asep.approve_plan(plan_id, decision)
        code = 200 if res.get("status") != "error" else 400
        return jsonify(res), code
    except Exception as e:
        logger.error(f"Error in api_asep_approve: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# --- Discord UI Component Definitions (Buttons & Modals) ---

class MemoryRememberModal(discord.ui.Modal, title="🧠 記憶を保存 (Remember)"):
    topic_input = discord.ui.TextInput(
        label="トピック（検索用キーワード）",
        placeholder="例: 会議メモ、お昼ご飯、プロジェクト目標",
        max_length=100,
        required=True
    )
    content_input = discord.ui.TextInput(
        label="記憶する内容",
        style=discord.TextStyle.paragraph,
        placeholder="例: 次回の打ち合わせは金曜日の15時など",
        max_length=2000,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        topic = self.topic_input.value.strip()
        content = self.content_input.value.strip()
        
        try:
            from src.memory.core import remember
            if remember(topic, content):
                await interaction.followup.send(
                    f"✅ **記憶を保存しました！**\n* **トピック**: `{topic}`\n* **内容**:\n{content}",
                    ephemeral=True
                )
            else:
                await interaction.followup.send("❌ 記憶の保存に失敗しました。", ephemeral=True)
        except Exception as e:
            logger.error(f"Error in MemoryRememberModal on_submit: {e}")
            await interaction.followup.send(f"❌ エラーが発生しました: {e}", ephemeral=True)

class MemoryRecallModal(discord.ui.Modal, title="🔍 記憶を検索 (Recall)"):
    query_input = discord.ui.TextInput(
        label="検索キーワード",
        placeholder="例: 会議、お昼",
        max_length=100,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        query = self.query_input.value.strip()
        
        try:
            from src.memory.core import recall
            res = recall(query)
            if res.get("status") == "success":
                await interaction.followup.send(
                    f"🧠 **記憶が見つかりました！** (レベル: {res.get('level')})\n"
                    f"* **トピック**: `{res.get('topic')}`\n"
                    f"**【内容】**\n{res.get('content')}",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(f"🔍 キーワード `{query}` に一致する記憶は見つかりませんでした。", ephemeral=True)
        except Exception as e:
            logger.error(f"Error in MemoryRecallModal on_submit: {e}")
            await interaction.followup.send(f"❌ エラーが発生しました: {e}", ephemeral=True)

class ASEPPlanModal(discord.ui.Modal, title="📋 実行計画の作成 (ASEP Plan)"):
    operation_input = discord.ui.TextInput(
        label="実行したい操作 (コマンド等)",
        placeholder="例: make status, ls -la",
        max_length=500,
        required=True
    )
    risk_input = discord.ui.TextInput(
        label="リスクレベル",
        default="L2",
        placeholder="L1 / L2 / L3",
        max_length=10,
        required=True
    )
    reason_input = discord.ui.TextInput(
        label="計画起票の理由",
        placeholder="例: システム稼働状態の確認",
        max_length=200,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        operation = self.operation_input.value.strip()
        risk = self.risk_input.value.strip()
        reason = self.reason_input.value.strip()
        
        try:
            from src.utils.asep_middleware import ASEPMiddleware
            asep = ASEPMiddleware()
            plan = asep.create_plan(operation, risk, reason, f"Created via Discord UI by {interaction.user}")
            if plan:
                await interaction.followup.send(
                    f"📋 **実行計画 (PLAN) を起票しました！**\n"
                    f"* **計画ID**: `{plan['plan_id']}`\n"
                    f"* **操作**: `{plan['operation']}`\n"
                    f"* **リスクレベル**: `{plan['risk']}`\n"
                    f"* **ステータス**: `{plan['status']}`\n\n"
                    f"承認して実行するには、チャットで `/run {plan['plan_id']}` を入力してください。",
                    ephemeral=True
                )
            else:
                await interaction.followup.send("❌ 実行計画の作成に失敗しました。", ephemeral=True)
        except Exception as e:
            logger.error(f"Error in ASEPPlanModal on_submit: {e}")
            await interaction.followup.send(f"❌ エラーが発生しました: {e}", ephemeral=True)

class AgentMenuView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # タイムアウトなしで動作し続ける

    @discord.ui.button(label="🧠 記憶を保存", style=discord.ButtonStyle.primary, custom_id="btn_remember")
    async def btn_remember(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(MemoryRememberModal())

    @discord.ui.button(label="🔍 記憶を検索", style=discord.ButtonStyle.secondary, custom_id="btn_recall")
    async def btn_recall(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(MemoryRecallModal())

    @discord.ui.button(label="📋 計画を作成", style=discord.ButtonStyle.success, custom_id="btn_plan")
    async def btn_plan(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ASEPPlanModal())

class ASEPApproveView(discord.ui.View):
    def __init__(self, plan_id: str):
        super().__init__(timeout=180)  # 3分でタイムアウト
        self.plan_id = plan_id

    @discord.ui.button(label="✅ 承認 (YES)", style=discord.ButtonStyle.success, custom_id="asep_yes")
    async def asep_yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        try:
            from src.utils.asep_middleware import ASEPMiddleware
            asep = ASEPMiddleware()
            app_res = asep.approve_plan(self.plan_id, "YES")
            if app_res.get("status") == "error":
                await interaction.followup.send(f"❌ 承認に失敗しました: {app_res.get('message')}", ephemeral=True)
                return

            await interaction.followup.send(f"⚙️ 計画 `{self.plan_id}` の実行を開始します...", ephemeral=True)
            
            def run_op(command):
                import subprocess
                res = subprocess.run(command, shell=True, capture_output=True, text=True)
                return f"STDOUT:\n{res.stdout}\n\nSTDERR:\n{res.stderr}"
                
            file_path = asep._find_plan_file(self.plan_id)
            if not file_path:
                await interaction.followup.send(f"❌ 計画 `{self.plan_id}` のファイルが見つかりません。", ephemeral=True)
                return
            from src.memory.core import parse_markdown_with_frontmatter
            metadata, _ = parse_markdown_with_frontmatter(file_path)
            op_cmd = metadata.get("title", "").replace("ASEP Plan: ", "")
            
            exec_res = asep.execute_plan(self.plan_id, run_op, op_cmd)
            
            if exec_res.get("status") == "Executed":
                await interaction.channel.send(
                    f"✅ **計画 `{self.plan_id}` の実行が完了しました！**\n"
                    f"**【実行結果】**\n```\n{exec_res['result'][:1800]}\n```"
                )
            else:
                err_detail = str(exec_res.get('error'))[:1800]
                await interaction.channel.send(f"❌ **計画 `{self.plan_id}` の実行に失敗しました。**\nエラー: {err_detail}")
            
            self.stop()
        except Exception as e:
            logger.error(f"Error in ASEPApproveView asep_yes: {e}")
            await interaction.followup.send(f"❌ エラーが発生しました: {e}", ephemeral=True)

    @discord.ui.button(label="🛑 却下 (NO)", style=discord.ButtonStyle.danger, custom_id="asep_no")
    async def asep_no(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        try:
            from src.utils.asep_middleware import ASEPMiddleware
            asep = ASEPMiddleware()
            app_res = asep.approve_plan(self.plan_id, "NO")
            if app_res.get("status") == "error":
                await interaction.followup.send(f"❌ 却下処理に失敗しました: {app_res.get('message')}", ephemeral=True)
                return
            await interaction.followup.send(f"🛑 計画 `{self.plan_id}` を却下しました。", ephemeral=True)
            self.stop()
        except Exception as e:
            logger.error(f"Error in ASEPApproveView asep_no: {e}")
            await interaction.followup.send(f"❌ エラーが発生しました: {e}", ephemeral=True)

# -----------------------------------------------------------

async def handle_chat_command(message, command_str):
    parts = command_str.split(" ", 1)
    cmd = parts[0].lower()
    args = parts[1].strip() if len(parts) > 1 else ""
    
    try:
        if cmd == "/remember":
            if not args:
                await message.reply("使用法: `/remember <topic> <content>` または `/remember --topic \"...\" --content \"...\"`")
                return
                
            topic, content = "", ""
            if "--topic" in args and "--content" in args:
                try:
                    t_idx = args.find("--topic")
                    c_idx = args.find("--content")
                    if t_idx < c_idx:
                        topic = args[t_idx+7:c_idx].strip().strip('"').strip("'")
                        content = args[c_idx+9:].strip().strip('"').strip("'")
                    else:
                        content = args[c_idx+9:t_idx].strip().strip('"').strip("'")
                        topic = args[t_idx+7:].strip().strip('"').strip("'")
                except Exception:
                    pass
            
            if not topic or not content:
                subparts = args.split(" ", 1)
                if len(subparts) >= 2:
                    topic, content = subparts[0], subparts[1]
                    
            if not topic or not content:
                await message.reply("エラー: `topic` と `content` を正しく指定してください。")
                return
                
            from src.memory.core import remember
            if remember(topic, content):
                await message.reply(f"✅ 記憶しました！\n* **トピック**: {topic}\n* **レベル**: L1 (Working Memory)")
            else:
                await message.reply("❌ 記憶の保存に失敗しました。")
                
        elif cmd == "/recall":
            if not args:
                await message.reply("使用法: `/recall <検索クエリ>`")
                return
            from src.memory.core import recall
            res = recall(args)
            if res.get("status") == "success":
                await message.reply(
                    f"🧠 **記憶を発見しました！** (レベル: {res['level']})\n"
                    f"* **トピック**: {res['topic']}\n"
                    f"**【内容】**\n{res['content']}"
                )
            else:
                await message.reply(f"🔍 クエリ '{args}' に一致する記憶は見つかりませんでした。")
                
        elif cmd == "/plan":
            if not args:
                await message.reply("使用法: `/plan <操作コマンド>`")
                return
            op = args
            risk = "L2"
            reason = "User chat command request"
            
            from src.utils.asep_middleware import ASEPMiddleware
            asep = ASEPMiddleware()
            plan = asep.create_plan(op, risk, reason, f"User triggered operation: {op}")
            if plan:
                await message.reply(
                    f"📋 **実行計画 (PLAN) を起票しました！**\n"
                    f"* **計画ID**: `{plan['plan_id']}`\n"
                    f"* **操作**: `{plan['operation']}`\n"
                    f"* **リスクレベル**: {plan['risk']}\n"
                    f"* **ステータス**: {plan['status']}\n"
                    f"承認して実行する場合は `/run {plan['plan_id']}` を入力してください。"
                )
            else:
                await message.reply("❌ 実行計画の起票に失敗しました。")
                
        elif cmd == "/run":
            if not args:
                await message.reply("使用法: `/run <計画ID> [YES/NO]`")
                return
            subparts = args.split(" ")
            plan_id = subparts[0]
            decision = subparts[1] if len(subparts) > 1 else "YES"
            
            from src.utils.asep_middleware import ASEPMiddleware
            asep = ASEPMiddleware()
            
            app_res = asep.approve_plan(plan_id, decision)
            if app_res.get("status") == "error":
                await message.reply(f"❌ 承認処理に失敗しました: {app_res.get('message')}")
                return
                
            if decision.upper() == "NO":
                await message.reply(f"🛑 計画 `{plan_id}` を却下しました。")
                return
                
            await message.reply(f"⚙️ 計画 `{plan_id}` の実行を開始します...")
            
            def run_op(command):
                import subprocess
                res = subprocess.run(command, shell=True, capture_output=True, text=True)
                return f"STDOUT:\n{res.stdout}\n\nSTDERR:\n{res.stderr}"
                
            file_path = asep._find_plan_file(plan_id)
            if not file_path:
                await message.reply(f"❌ 計画 `{plan_id}` のファイルが見つかりません。")
                return
            from src.memory.core import parse_markdown_with_frontmatter
            metadata, _ = parse_markdown_with_frontmatter(file_path)
            op_cmd = metadata.get("title", "").replace("ASEP Plan: ", "")
            
            exec_res = asep.execute_plan(plan_id, run_op, op_cmd)
            
            if exec_res.get("status") == STATUS_EXECUTED:
                await message.reply(
                    f"✅ **計画 `{plan_id}` の実行が完了しました！**\n"
                    f"**【実行結果】**\n{exec_res['result'][:1500]}"
                )
            else:
                await message.reply(f"❌ **計画 `{plan_id}` の実行に失敗しました。**\nエラー: {exec_res.get('error')}")
                
        elif cmd == "/status":
            if not args:
                await message.reply("使用法: `/status <計画ID>`")
                return
            from src.utils.asep_middleware import ASEPMiddleware
            asep = ASEPMiddleware()
            file_path = asep._find_plan_file(args)
            if not file_path:
                await message.reply(f"🔍 計画 `{args}` は見つかりませんでした。")
                return
            from src.memory.core import parse_markdown_with_frontmatter
            metadata, _ = parse_markdown_with_frontmatter(file_path)
            await message.reply(
                f"📊 **計画 `{args}` ステータス**\n"
                f"* **ステータス**: {metadata.get('status')}\n"
                f"* **リスクレベル**: {metadata.get('risk')}\n"
                f"* **操作**: {metadata.get('title', '').replace('ASEP Plan: ', '')}"
            )
            
        elif cmd == "/logs":
            if not args:
                await message.reply("使用法: `/logs <計画ID>`")
                return
            from src.utils.asep_middleware import ASEPMiddleware
            asep = ASEPMiddleware()
            file_path = asep._find_plan_file(args)
            if not file_path:
                await message.reply(f"🔍 計画 `{args}` は見つかりませんでした。")
                return
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            await message.reply(f"📄 **計画 `{args}` 実行履歴**\n```markdown\n{content[:1900]}\n```")
            
        elif cmd == "/rollback":
            await message.reply("🔄 直前状態復元（ロールバック）コマンドを受信しました。テスト環境のロールバック処理をトリガーします。")
            
    except Exception as e:
        logger.error(f"Error handling chat command {cmd}: {e}")
        await message.reply(f"コマンド実行エラー: {e}")

def start_parent_reloader_process():
    import sys
    import subprocess
    
    src_dir = os.path.dirname(os.path.abspath(__file__))
    logger.info(f"[Reloader] Starting parent monitor process for: {src_dir}")
    
    def get_mtimes():
        mtimes = {}
        for root, _, files in os.walk(src_dir):
            for file in files:
                if file.endswith(".py"):
                    path = os.path.join(root, file)
                    try:
                        mtimes[path] = os.path.getmtime(path)
                    except Exception:
                        pass
        return mtimes
        
    initial_mtimes = get_mtimes()
    
    env = os.environ.copy()
    env["KANON_IS_CHILD"] = "true"
    
    child_cmd = [sys.executable] + sys.argv
    p = subprocess.Popen(child_cmd, env=env)
    
    try:
        while True:
            time.sleep(2)
            if p.poll() is not None:
                logger.info("[Reloader] Child process exited. Exiting parent...")
                sys.exit(p.returncode)
                
            current_mtimes = get_mtimes()
            changed = False
            for path, mtime in current_mtimes.items():
                if path not in initial_mtimes or mtime > initial_mtimes[path]:
                    changed = True
                    break
                    
            if changed:
                logger.warning("[Reloader] File modification detected. Restarting child process...")
                p.terminate()
                try:
                    p.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    p.kill()
                    p.wait()
                    
                initial_mtimes = current_mtimes
                p = subprocess.Popen(child_cmd, env=env)
    except KeyboardInterrupt:
        p.terminate()
        p.wait()

def start_flask_app():
    logger.info(f"Starting Flask app on port {WEB_SERVER_PORT}...")
    try:
        is_test = os.getenv("KANON_TEST_TRIGGER", "false").lower() == "true"
        # use_reloader は常に False にする (Thread 起動エラーを防ぐため)
        app.run(host='0.0.0.0', port=WEB_SERVER_PORT, debug=is_test, use_reloader=False)
    except Exception as e:
        logger.error(f"Error starting Flask app: {e}")
        global agent_status
        agent_status = f"Error: Could not start web server on port {WEB_SERVER_PORT}. {e}"

@client.event
async def on_ready():
    global agent_status
    logger.info(f"Logged in to Discord as {client.user} (ID: {client.user.id})")
    agent_status = f"Bot active: {client.user.name}"

@client.event
async def on_message(message):
    # 自分自身のメッセージは無視
    if message.author == client.user:
        return

    # DM（ダイレクトメッセージ）または自分へのメンションの場合に応答
    is_dm = isinstance(message.channel, discord.DMChannel)
    is_mentioned = client.user in message.mentions

    if is_dm or is_mentioned:
        # メッセージ文字列のクリーンアップ（メンション部分を削除）
        prompt = message.content
        if is_mentioned and client.user:
            prompt = prompt.replace(f"<@{client.user.id}>", "").strip()
            prompt = prompt.replace(f"<@!{client.user.id}>", "").strip()
        
        if not prompt:
            return

        # 対話型メニューのトリガー
        if prompt.lower() in ["menu", "/menu", "メニュー", "help", "/help", "ヘルプ"]:
            view = AgentMenuView()
            await message.reply(
                "🧠 **AI Agent コントロールメニュー**\n"
                "以下のボタンをクリックすると、専用の入力フォームがポップアップして操作できます。\n"
                "（テキストでの手動入力も引き続き可能です）",
                view=view
            )
            return

        # チャットコマンドの簡易フック (ASEP-001 / Memory MVP)
        if prompt.startswith("/"):
            await handle_chat_command(message, prompt)
            return

        async with message.channel.typing():
            try:
                # チャンネルIDまたはDMの場合はユーザーIDをキーとする
                history_key = str(message.channel.id) if not is_dm else f"dm_{message.author.id}"
                
                # 過去の会話履歴をロード
                past_messages = history.get_messages(history_key)
                
                # Google GenAI 送信用 contents リストを構築
                contents = []
                for msg in past_messages:
                    contents.append(
                        types.Content(
                            role=msg["role"],
                            parts=[types.Part.from_text(text=msg["content"])]
                        )
                    )
                
                # 今回のユーザー入力を履歴に追加し、送信リストにも追加
                history.add_message(history_key, "user", prompt)
                contents.append(
                    types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=prompt)]
                    )
                )

                # APIクライアント初期化と推論
                api_key = os.getenv("GEMINI_API_KEY")
                response_text = await generate_agent_reply(contents, api_key=api_key)

                # Botの応答を履歴に追加
                history.add_message(history_key, "model", response_text)
                
                # 応答に計画ID（PLN-xxxx）が含まれる場合は、自動的に承認Viewを添付
                import re
                plan_match = re.search(r"PLN-\d{8}-\d{6}", response_text)
                view = None
                if plan_match:
                    plan_id = plan_match.group(0)
                    view = ASEPApproveView(plan_id)
                
                # Discordへ応答
                if view:
                    await message.reply(response_text, view=view)
                else:
                    await message.reply(response_text)
                
            except Exception as e:
                logger.error(f"Error while processing message and calling Gemini API: {e}")
                err_msg = f"内部エラーが発生しました: {e}"
                if len(err_msg) > 1900:
                    err_msg = err_msg[:1900] + "\n... (エラーメッセージが長すぎるため省略されました)"
                await message.reply(err_msg)

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

async def run_mock_loop():
    """本物のDiscordトークンがない、またはモック動作指定時のループ"""
    global agent_status
    logger.info("Starting mock Discord loop (KANON_MOCK_DISCORD=true or token not set).")
    agent_status = "Mock Discord Active (No connection)"
    
    try:
        while True:
            await asyncio.sleep(5)
    except asyncio.CancelledError:
        logger.info("Mock Discord loop canceled.")

def main():
    global agent_status
    logger.info("AI Agent main process started.")

    token = os.getenv("DISCORD_BOT_TOKEN")
    mock_mode = os.getenv("KANON_MOCK_DISCORD", "false").lower() == "true"

    if not os.getenv("GEMINI_API_KEY"):
        logger.warning("GEMINI_API_KEY environment variable not set.")

    if mock_mode or not token:
        if not token:
            logger.info("DISCORD_BOT_TOKEN not found. Falling back to Mock mode.")
        try:
            asyncio.run(run_mock_loop())
        except KeyboardInterrupt:
            logger.info("Mock loop stopped by KeyboardInterrupt.")
    else:
        logger.info("Starting real Discord client...")
        try:
            asyncio.run(client.start(token))
        except KeyboardInterrupt:
            logger.info("Discord client stopped by KeyboardInterrupt.")
        except Exception as e:
            logger.error(f"Failed to start Discord client: {e}")
            agent_status = f"Error: Discord client failed. {e}"

if __name__ == "__main__":
    is_test = os.getenv("KANON_TEST_TRIGGER", "false").lower() == "true"
    is_child = os.getenv("KANON_IS_CHILD", "false").lower() == "true"
    
    if is_test and not is_child:
        import sys
        # テスト時かつ親プロセスの場合は、リローダーとして振る舞い子プロセスを起動する
        try:
            start_parent_reloader_process()
        except KeyboardInterrupt:
            pass
        sys.exit(0)
        
    # 子プロセス (またはテスト外の本番) の場合は通常起動
    # Flaskアプリを別スレッドで開始
    flask_thread = Thread(target=start_flask_app)
    flask_thread.daemon = True  # メインスレッドが終了したらFlaskスレッドも終了
    flask_thread.start()

    # エージェントのメインロジックを開始
    main()
