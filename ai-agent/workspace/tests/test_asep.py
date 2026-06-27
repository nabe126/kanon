import os
import shutil
import pytest
from src.utils.asep_middleware import (
    ASEPMiddleware, LEVEL_L0, LEVEL_L1, LEVEL_L2, LEVEL_L3,
    STATUS_PENDING, STATUS_APPROVED, STATUS_REJECTED, STATUS_EXECUTED, STATUS_FAILED
)
from src.memory.core import L3_DIR, MEMORY_DIR, STATE_DIR, parse_markdown_with_frontmatter

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

def test_asep_l2_lifecycle():
    asep = ASEPMiddleware()
    operation = "cat /etc/hosts"
    reason = "Test network config check"
    
    # 1. 計画起票
    plan = asep.create_plan(operation, LEVEL_L2, reason, "Step 1: Run cat command\nStep 2: Check output")
    assert plan is not None
    plan_id = plan["plan_id"]
    assert plan["status"] == STATUS_PENDING
    
    # ファイルが L3 に存在すること
    file_path = plan["file_path"]
    assert os.path.exists(file_path) == True
    
    # 2. 承認前実行のブロッキング
    blocked_res = asep.execute_plan(plan_id, lambda: "Run!")
    assert blocked_res["status"] == "error"
    assert "blocked" in blocked_res["message"]
    
    # 3. 計画承認 (YES)
    app_res = asep.approve_plan(plan_id, decision="YES")
    assert app_res["status"] == STATUS_APPROVED
    
    # ファイルステータスが APPROVED になっていること
    metadata, body = parse_markdown_with_frontmatter(file_path)
    assert metadata["status"] == STATUS_APPROVED
    assert "Decision Gate" in body
    
    # 4. 実行
    def test_run_fn(val):
        return f"Executed successfully with value: {val}"
        
    exec_res = asep.execute_plan(plan_id, test_run_fn, "Kanon OS")
    assert exec_res["status"] == STATUS_EXECUTED
    assert "Executed successfully" in exec_res["result"]
    
    # ファイルステータスが EXECUTED になっていること
    metadata_final, body_final = parse_markdown_with_frontmatter(file_path)
    assert metadata_final["status"] == STATUS_EXECUTED
    assert "Execution Logs" in body_final

def test_asep_l0_auto_approve():
    asep = ASEPMiddleware()
    
    # L0 は計画ファイルを作らず、直接 APPROVED ステータスとして返される
    plan = asep.create_plan("grep 'error' log.txt", LEVEL_L0, "Read log")
    assert plan["plan_id"] == "PLAN-L0-AUTO"
    assert plan["status"] == STATUS_APPROVED
    
    # 実行
    exec_res = asep.execute_plan("PLAN-L0-AUTO", lambda: "Read only output")
    assert exec_res["status"] == STATUS_EXECUTED
    assert exec_res["result"] == "Read only output"

def test_asep_rejection():
    asep = ASEPMiddleware()
    plan = asep.create_plan("rm -rf /", LEVEL_L3, "Dangerous command")
    plan_id = plan["plan_id"]
    
    # 却下 (NO)
    app_res = asep.approve_plan(plan_id, decision="NO")
    assert app_res["status"] == STATUS_REJECTED
    
    # 却下後の実行不可チェック
    blocked_res = asep.execute_plan(plan_id, lambda: "Danger!")
    assert blocked_res["status"] == "error"
