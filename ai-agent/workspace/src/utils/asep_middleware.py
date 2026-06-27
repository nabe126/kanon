import os
import time
import uuid
import logging
import traceback
from src.memory.core import L3_DIR, git_auto_commit, write_markdown_with_frontmatter, parse_markdown_with_frontmatter

logger = logging.getLogger("discord_agent")

# ASEP 実行権限レベルの定義
LEVEL_L0 = "L0"  # 読み取り専用（常時許可）
LEVEL_L1 = "L1"  # ローカル変更（差分出力とGitコミット、計画自動承認）
LEVEL_L2 = "L2"  # システム操作（REQUESTが必要、ログ必須）
LEVEL_L3 = "L3"  # 自律修復・再起動（人間による明示YES/NO必須）

# ASEP 計画ステータス
STATUS_PLANNING = "PLANNING"
STATUS_PENDING = "PENDING_APPROVAL"
STATUS_APPROVED = "APPROVED"
STATUS_REJECTED = "REJECTED"
STATUS_EXECUTED = "EXECUTED"
STATUS_FAILED = "FAILED"

class ASEPMiddleware:
    def __init__(self, l3_dir=L3_DIR):
        self.l3_dir = l3_dir
        os.makedirs(self.l3_dir, exist_ok=True)

    def _find_plan_file(self, plan_id):
        """plan_id に対応する Markdown ファイルのパスを検索します。"""
        if not os.path.exists(self.l3_dir):
            return None
        # plan_id (PLAN-xxxx) から uuid (xxxx) を抽出して比較
        uuid_part = plan_id.replace("PLAN-", "").lower()
        for filename in os.listdir(self.l3_dir):
            if filename.endswith(".md") and uuid_part in filename.lower():
                return os.path.join(self.l3_dir, filename)
        return None

    def create_plan(self, operation, risk_level, reason, details=""):
        """操作の実行計画 (PLAN) を起票し、L3 ディレクトリに Markdown として保存します。"""
        plan_uuid = str(uuid.uuid4())[:8]
        plan_id = f"PLAN-{plan_uuid}"
        timestamp = time.strftime('%Y-%m-%dT%H:%M:%S')
        
        # L0 (読み取り専用) の場合は、計画起票をスキップ（常時自動承認）
        if risk_level == LEVEL_L0:
            return {
                "plan_id": "PLAN-L0-AUTO",
                "status": STATUS_APPROVED,
                "risk": risk_level,
                "operation": operation
            }
            
        # L1 の場合は、計画起票後に自動で APPROVED へ遷移可能 (ただしログ記録は行う)
        status = STATUS_APPROVED if risk_level == LEVEL_L1 else STATUS_PENDING
        
        # ファイル名の定義 (タイムスタンプ_plan_uuid.md)
        filename = f"{time.strftime('%Y%m%d')}_plan_{plan_uuid}.md"
        file_path = os.path.join(self.l3_dir, filename)
        
        metadata = {
            "id": plan_id,
            "title": f"ASEP Plan: {operation}",
            "status": status,
            "risk": risk_level,
            "reason": reason,
            "created_at": timestamp,
            "updated_at": timestamp
        }
        
        body = (
            f"## 📋 実行計画詳細 (Execution Plan Details)\n\n"
            f"* **対象操作 (Operation)**: {operation}\n"
            f"* **リスクレベル (Risk Level)**: {risk_level}\n"
            f"* **起票理由 (Reason)**: {reason}\n\n"
            f"### 🔍 具体的な内容・手順\n{details}\n"
        )
        
        if write_markdown_with_frontmatter(file_path, metadata, body):
            git_auto_commit(file_path)
            return {
                "plan_id": plan_id,
                "status": status,
                "risk": risk_level,
                "operation": operation,
                "file_path": file_path
            }
        return None

    def approve_plan(self, plan_id, decision="YES"):
        """計画に対する人間の意思決定（YES/NO）を適用し、承認ステータスを更新します。"""
        if plan_id == "PLAN-L0-AUTO":
            return {"status": STATUS_APPROVED, "message": "L0 Operations are auto-approved."}
            
        file_path = self._find_plan_file(plan_id)
        if not file_path:
            return {"status": "error", "message": f"Plan ID {plan_id} not found."}
            
        metadata, body = parse_markdown_with_frontmatter(file_path)
        current_status = metadata.get("status")
        
        if current_status not in (STATUS_PENDING, STATUS_APPROVED):
            return {"status": "error", "message": f"Plan is already in status {current_status} and cannot be modified."}
            
        new_status = STATUS_APPROVED if decision.upper() == "YES" else STATUS_REJECTED
        
        metadata["status"] = new_status
        metadata["updated_at"] = time.strftime('%Y-%m-%dT%H:%M:%S')
        
        decision_body = (
            f"\n## ⚖️ 承認ゲート決定 (Decision Gate)\n\n"
            f"* **決定 (Decision)**: {decision.upper()} ({'APPROVED' if decision.upper() == 'YES' else 'REJECTED'})\n"
            f"* **判定日時**: {metadata['updated_at']}\n"
        )
        full_body = body + "\n" + decision_body
        
        if write_markdown_with_frontmatter(file_path, metadata, full_body):
            git_auto_commit(file_path)
            return {"status": new_status, "plan_id": plan_id}
        return {"status": "error", "message": "Failed to write updated plan file."}

    def execute_plan(self, plan_id, execute_fn, *args, **kwargs):
        """承認された計画を実行し、実行ログ・結果を Markdown 履歴に追記します。"""
        if plan_id == "PLAN-L0-AUTO":
            # L0 の場合は直接実行
            try:
                result = execute_fn(*args, **kwargs)
                return {"status": STATUS_EXECUTED, "result": result}
            except Exception as e:
                return {"status": STATUS_FAILED, "error": str(e)}
                
        file_path = self._find_plan_file(plan_id)
        if not file_path:
            return {"status": "error", "message": f"Plan ID {plan_id} not found."}
            
        metadata, body = parse_markdown_with_frontmatter(file_path)
        status = metadata.get("status")
        
        if status != STATUS_APPROVED:
            return {"status": "error", "message": f"Execution blocked. Plan status is {status} (Expected: APPROVED)."}
            
        logger.info(f"[ASEP] Starting execution for plan {plan_id}...")
        start_time = time.time()
        
        try:
            # 実処理の実行
            result = execute_fn(*args, **kwargs)
            duration = time.time() - start_time
            execution_status = STATUS_EXECUTED
            error_msg = None
            result_str = str(result)
        except Exception as e:
            duration = time.time() - start_time
            execution_status = STATUS_FAILED
            error_msg = str(e)
            result_str = traceback.format_exc()
            logger.error(f"[ASEP] Plan {plan_id} execution failed: {e}")
            
        metadata["status"] = execution_status
        metadata["updated_at"] = time.strftime('%Y-%m-%dT%H:%M:%S')
        
        log_body = (
            f"\n## ⚙️ 実行履歴とログ (Execution Logs)\n\n"
            f"* **実行ステータス**: {execution_status}\n"
            f"* **実行時間**: {duration:.2f} 秒\n"
            f"* **完了日時**: {metadata['updated_at']}\n\n"
            f"### ログ出力 (Logs/Result)\n"
            f"```\n{result_str}\n```\n"
        )
        if error_msg:
            log_body += f"\n> [!CAUTION]\n> **実行エラー**: {error_msg}\n"
            
        full_body = body + "\n" + log_body
        
        if write_markdown_with_frontmatter(file_path, metadata, full_body):
            git_auto_commit(file_path)
            
        return {
            "status": execution_status,
            "plan_id": plan_id,
            "result": result_str if execution_status == STATUS_EXECUTED else None,
            "error": error_msg
        }
