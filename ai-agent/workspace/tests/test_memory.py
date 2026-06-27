import os
import shutil
import json
import pytest
from src.memory.core import remember, recall, L1_FILE, L3_DIR, L4_DIR, STATE_DIR, MEMORY_DIR, MAX_L1_SLOTS
from src.memory.cli import main as cli_main
import sys
from unittest.mock import patch

@pytest.fixture(autouse=True)
def setup_and_teardown_memory():
    # 既存のメモリディレクトリとステートを一時退避しテスト終了後に復元
    state_backup = STATE_DIR + "_test_backup"
    memory_backup = MEMORY_DIR + "_test_backup"
    
    if os.path.exists(STATE_DIR):
        shutil.move(STATE_DIR, state_backup)
    if os.path.exists(MEMORY_DIR):
        shutil.move(MEMORY_DIR, memory_backup)
        
    os.makedirs(STATE_DIR, exist_ok=True)
    os.makedirs(L3_DIR, exist_ok=True)
    os.makedirs(L4_DIR, exist_ok=True)
    
    yield
    
    # テストデータのクリーンアップ
    if os.path.exists(STATE_DIR):
        shutil.rmtree(STATE_DIR)
    if os.path.exists(MEMORY_DIR):
        shutil.rmtree(MEMORY_DIR)
        
    # バックアップから状態を復元
    if os.path.exists(state_backup):
        shutil.move(state_backup, STATE_DIR)
    if os.path.exists(memory_backup):
        shutil.move(memory_backup, MEMORY_DIR)

def test_remember_and_recall_l1():
    # 1. 記憶 (L1)
    topic = "テストトピックA"
    content = "これはワーキングメモリのテスト内容です。"
    assert remember(topic, content, level="L1", category="100", tags=["test"]) == True
    
    # L1 ファイルが存在すること
    assert os.path.exists(L1_FILE) == True
    
    # 2. 検索 (Read Bus / L1 からの取得)
    res = recall("テストトピックA")
    assert res["status"] == "success"
    assert res["level"] == "L1"
    assert res["topic"] == topic
    assert res["content"] == content
    assert "test" in res["tags"]
    
    # 部分一致検索
    res_partial = recall("ワーキングメモリ")
    assert res_partial["status"] == "success"
    assert res_partial["level"] == "L1"

def test_working_memory_limit_flashing():
    # MAX_L1_SLOTS = 5 なので、6つのトピックを追加する
    for i in range(MAX_L1_SLOTS + 1):
        topic = f"トピック番号_{i}"
        content = f"内容_{i} です。"
        remember(topic, content, level="L1")
        if i < MAX_L1_SLOTS:
            # updated_at を過去に手動でずらして順序を確定する
            with open(L1_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            data[-1]["updated_at"] = f"2026-06-27T12:00:0{i}"
            with open(L1_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f)
                
    # 6番目を追加した時点で、最古の「トピック番号_0」が L1 から削除され、L3 にフラッシュされているはず
    with open(L1_FILE, "r", encoding="utf-8") as f:
        l1_data = json.load(f)
        
    assert len(l1_data) == MAX_L1_SLOTS
    topics_in_l1 = [item["topic"] for item in l1_data]
    assert "トピック番号_0" not in topics_in_l1
    assert "トピック番号_5" in topics_in_l1
    
    # L3 ディレクトリにフラッシュされたファイルが存在すること
    l3_files = os.listdir(L3_DIR)
    assert len(l3_files) == 1
    assert "トピック番号_0" in l3_files[0]
    
    # L3 からの検索 (Read Bus フォールバック)
    res_l3 = recall("トピック番号_0")
    assert res_l3["status"] == "success"
    assert res_l3["level"] == "L3"
    assert res_l3["topic"] == "トピック番号_0"
    assert "内容_0 です。" in res_l3["content"]

def test_remember_l3_l4():
    # 直接 L3 と L4 に保存
    assert remember("エピソード記憶", "決定事項の内容", level="L3", category="100") == True
    assert remember("意味記憶", "不変のプロファイル事実", level="L4", category="300") == True
    
    # 検索
    res_l3 = recall("エピソード記憶")
    assert res_l3["status"] == "success"
    assert res_l3["level"] == "L3"
    
    res_l4 = recall("意味記憶")
    assert res_l4["status"] == "success"
    assert res_l4["level"] == "L4"

def test_cli_interface():
    # CLI の remember 動作確認
    test_args = ["cli.py", "remember", "--topic", "CLIトピック", "--content", "CLIから記憶した内容", "--level", "L1"]
    with patch.object(sys, 'argv', test_args):
        with pytest.raises(SystemExit) as e:
            cli_main()
        assert e.value.code == 0
        
    # CLI の recall 動作確認
    test_args_recall = ["cli.py", "recall", "--query", "CLIトピック"]
    with patch.object(sys, 'argv', test_args_recall):
        with pytest.raises(SystemExit) as e:
            cli_main()
        assert e.value.code == 0
