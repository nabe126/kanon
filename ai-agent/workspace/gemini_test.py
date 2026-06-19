import os
from google import genai

def main():
    # 環境変数からAPIキーを取得
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_key_here":
        print("[Error] GEMINI_API_KEY が設定されていません。")
        return

    print("Gemini API にリクエストを送信中...")
    client = genai.Client(api_key=api_key)
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents='「GPDマシンにUbuntuを入れて、AIエージェントの基地を作ったよ」と報告してください。短く一言で。',
    )
    
    print("\n=== Geminiからの応答 ===")
    print(response.text)
    print("=========================")

if __name__ == "__main__":
    main()
