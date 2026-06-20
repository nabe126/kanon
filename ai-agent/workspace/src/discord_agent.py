import os
import sys
import time
import asyncio
from flask import Flask, jsonify
from threading import Thread
import discord
from google.genai import types

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
    # warningステータスでもコンテナ自体は生きて応答しているので200、致命的エラー時のみ500
    code = 200 if metrics["status"] in ["healthy", "warning"] else 500
    return jsonify(metrics), code

def start_flask_app():
    logger.info(f"Starting Flask app on port {WEB_SERVER_PORT}...")
    try:
        app.run(host='0.0.0.0', port=WEB_SERVER_PORT, debug=False, use_reloader=False)
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
                if not api_key:
                    logger.error("GEMINI_API_KEY is not set.")
                    response_text = "エラー: GEMINI_API_KEY 環境変数が設定されていません。"
                else:
                    from google import genai
                    genai_client = genai.Client(api_key=api_key)
                    # 履歴付きで推論を実行
                    response = genai_client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=contents
                    )
                    response_text = response.text or "(空の応答)"

                # Botの応答を履歴に追加
                history.add_message(history_key, "model", response_text)
                
                # Discordへ応答
                await message.reply(response_text)
                
            except Exception as e:
                logger.error(f"Error while processing message and calling Gemini API: {e}")
                await message.reply(f"内部エラーが発生しました: {e}")

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
    # Flaskアプリを別スレッドで開始
    flask_thread = Thread(target=start_flask_app)
    flask_thread.daemon = True  # メインスレッドが終了したらFlaskスレッドも終了
    flask_thread.start()

    # エージェントのメインロジックを開始
    main()
