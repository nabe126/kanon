from flask import Flask, jsonify
from threading import Thread
import os
import time
import sys

# 自作ユーティリティのインポート
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils.healthcheck import get_system_metrics
from utils.logger import get_logger

logger = get_logger("discord_agent")

# エージェントの現在の状態を保持する変数
agent_status = "Initializing..."
# Webサーバーのポート番号
WEB_SERVER_PORT = 5000

def start_flask_app():
    global agent_status
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

    logger.info(f"Starting Flask app on port {WEB_SERVER_PORT}...")
    try:
        app.run(host='0.0.0.0', port=WEB_SERVER_PORT)
    except Exception as e:
        logger.error(f"Error starting Flask app: {e}")
        global agent_status
        agent_status = f"Error: Could not start web server on port {WEB_SERVER_PORT}. {e}"

def main():
    global agent_status
    logger.info("AI Agent main process started.")

    # GenAI クライアントの初期化
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY environment variable not set.")
        agent_status = "Error: GEMINI_API_KEY environment variable not set."
        return

    try:
        # google-genaiのインポートを内部で行う（テスト容易性のため）
        from google import genai
        client = genai.Client(api_key=api_key)
        logger.info("Google GenAI Client initialized successfully.")
        agent_status = "Google GenAI Client initialized and ready."
        # ここにエージェントのメインロジック（Discordとの連携など）が来る
        logger.info("Agent is performing its tasks... (Placeholder for actual agent logic)")
        # 例: Discordボットの起動など
        # discord_bot.run(os.getenv("DISCORD_BOT_TOKEN"))
        agent_status = "Agent is active and monitoring Discord (placeholder)."

    except Exception as e:
        logger.error(f"Failed to initialize Google GenAI Client or run agent logic: {e}")
        agent_status = f"Error: Failed to initialize Google GenAI Client or run agent logic. {e}"
        return

if __name__ == "__main__":
    # Flaskアプリを別スレッドで開始
    flask_thread = Thread(target=start_flask_app)
    flask_thread.daemon = True # メインスレッドが終了したらFlaskスレッドも終了
    flask_thread.start()

    # エージェントのメインロジックを開始
    main()

    # メインスレッドが終了しないように、無限ループでプロセスを維持
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("AI Agent and Web Server shutting down due to KeyboardInterrupt.")
    except Exception as e:
        logger.error(f"AI Agent encountered an unexpected error: {e}")
