import os
from src.utils.history import ConversationHistory

def test_history_basic(tmp_path) -> None:
    """メッセージ追加と取得の基本機能テスト"""
    history_file = os.path.join(tmp_path, "test_history.json")
    history = ConversationHistory(history_file, max_messages=3)
    
    # メッセージ追加
    history.add_message("user_1", "user", "hello")
    history.add_message("user_1", "model", "hi there")
    
    messages = history.get_messages("user_1")
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "hello"
    assert messages[1]["role"] == "model"
    assert messages[1]["content"] == "hi there"

def test_history_max_messages(tmp_path) -> None:
    """最大メッセージ数上限に達した時のローテーションテスト"""
    history_file = os.path.join(tmp_path, "test_history.json")
    history = ConversationHistory(history_file, max_messages=2)
    
    # 3つのメッセージを追加
    history.add_message("user_1", "user", "msg1")
    history.add_message("user_1", "model", "msg2")
    history.add_message("user_1", "user", "msg3")
    
    messages = history.get_messages("user_1")
    # 古い msg1 が消え、msg2, msg3 のみが残る
    assert len(messages) == 2
    assert messages[0]["content"] == "msg2"
    assert messages[1]["content"] == "msg3"

def test_history_persistence(tmp_path) -> None:
    """ディスクへの永続化と再ロードのテスト"""
    history_file = os.path.join(tmp_path, "test_history.json")
    history = ConversationHistory(history_file, max_messages=5)
    
    history.add_message("user_1", "user", "persist test")
    
    # 別インスタンスで同じファイルをロード
    history2 = ConversationHistory(history_file, max_messages=5)
    messages = history2.get_messages("user_1")
    assert len(messages) == 1
    assert messages[0]["content"] == "persist test"

def test_history_clear(tmp_path) -> None:
    """履歴削除機能のテスト"""
    history_file = os.path.join(tmp_path, "test_history.json")
    history = ConversationHistory(history_file, max_messages=5)
    
    history.add_message("user_1", "user", "msg")
    assert len(history.get_messages("user_1")) == 1
    
    history.clear("user_1")
    assert len(history.get_messages("user_1")) == 0
