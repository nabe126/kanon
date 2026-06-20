import os
import time
from google import genai

def ask_gemini(client, prompt):
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        return f"Error: {e}"

def main():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_key_here":
        print("[Error] GEMINI_API_KEY が正しく認識されていません。")
        return

    client = genai.Client(api_key=api_key)
    print("=== 自律型エージェント・ループを起動しました ===")
    
    loop_count = 0
    while True:
        loop_count += 1
        print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] サイクル #{loop_count} 開始")
        
        # 思考フェーズのプロンプト
        # 実際のエージェントでは、ここに現在のシステムログや未処理タスクのリストを結合します
        prompt = (
            f"あなたは省電力Linuxサーバー（GPD WIN 3）上で動く自律型エージェントです。\n"
            f"現在、起動から {loop_count} 回目の定期巡回を行っています。\n"
            f"サーバーの健康状態を維持しつつ、自律稼働している旨をアピールする短いログメッセージ（1行）を出力してください。"
        )
        
        # Geminiに思考を要請
        log_message = ask_gemini(client, prompt)
        print(f"Agent思考結果: {log_message}")
        
        # 次の巡回まで待機（テスト用に10秒に設定。実運用時は数分〜数時間）
        print("次のサイクルまで10秒待機します...")
        time.sleep(10)

if __name__ == "__main__":
    main()
