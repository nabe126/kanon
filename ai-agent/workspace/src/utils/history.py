import os
import json
import threading
from typing import Dict, List, Any

class ConversationHistory:
    """ユーザーまたはチャンネルごとの会話履歴（コンテキスト）をスレッドセーフに管理し、永続化します。"""
    def __init__(self, filepath: str, max_messages: int = 20):
        self.filepath = filepath
        self.max_messages = max_messages
        self.histories: Dict[str, List[Dict[str, Any]]] = {}
        self.lock = threading.Lock()
        self.load()

    def load(self) -> None:
        """ディスクから会話履歴をロードします。"""
        with self.lock:
            if os.path.exists(self.filepath):
                try:
                    with open(self.filepath, "r", encoding="utf-8") as f:
                        self.histories = json.load(f)
                except Exception:
                    self.histories = {}
            else:
                self.histories = {}

    def save(self) -> None:
        """会話履歴をディスクに保存します。"""
        with self.lock:
            try:
                os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
                with open(self.filepath, "w", encoding="utf-8") as f:
                    json.dump(self.histories, f, ensure_ascii=False, indent=4)
            except Exception:
                pass

    def add_message(self, key: str, role: str, content: str) -> None:
        """履歴にメッセージを追加し、自動保存します。"""
        with self.lock:
            if key not in self.histories:
                self.histories[key] = []
            
            self.histories[key].append({
                "role": role,  # 'user' or 'model' (or 'system')
                "content": content
            })
            
            # 最大件数を超えたら古いものを削除
            if len(self.histories[key]) > self.max_messages:
                self.histories[key] = self.histories[key][-self.max_messages:]
        
        self.save()

    def get_messages(self, key: str) -> List[Dict[str, Any]]:
        """指定されたキー（ユーザーIDやチャンネルID）のメッセージ履歴を返します。"""
        with self.lock:
            return list(self.histories.get(key, []))

    def clear(self, key: str) -> None:
        """指定されたキーの履歴をクリアします。"""
        with self.lock:
            if key in self.histories:
                del self.histories[key]
        self.save()
