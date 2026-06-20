import os
import sys
import py_compile
import subprocess
import shutil
from typing import Tuple

def check_syntax(file_path: str) -> Tuple[bool, str | None]:
    """指定されたPythonファイルの構文エラー（SyntaxError）をチェックします (Task-001)"""
    try:
        py_compile.compile(file_path, doraise=True)
        return True, None
    except py_compile.PyCompileError as e:
        return False, str(e).strip()
    except Exception as e:
        return False, f"Unexpected error during syntax check: {e}"

def check_import(file_path: str) -> Tuple[bool, str | None]:
    """指定されたファイルをサブプロセス経由でインポートテストし、依存エラーをチェックします (Task-002)"""
    try:
        cmd = [
            sys.executable, 
            "-c", 
            f"import sys; import os; sys.path.insert(0, os.path.dirname('{file_path}')); "
            f"import importlib.util; "
            f"spec = importlib.util.spec_from_file_location('test_module', '{file_path}'); "
            f"module = importlib.util.module_from_spec(spec); "
            f"spec.loader.exec_module(module)"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return True, None
        else:
            return False, (result.stderr or result.stdout or "Unknown import error").strip()
            
    except subprocess.TimeoutExpired:
        return False, "Validation timeout: Import check took longer than 10 seconds."
    except Exception as e:
        return False, f"Unexpected error during import check: {e}"

def apply_candidate_code(candidate_path: str, target_path: str, backup_dir: str) -> Tuple[bool, str | None]:
    """
    一時保存された候補コード (candidate) を検証し、合格すれば LKG バックアップを作成した上で本番コードに適用します。
    """
    # 1. 構文チェック
    success, err_msg = check_syntax(candidate_path)
    if not success:
        return False, f"Syntax verification failed: {err_msg}"
        
    # 2. インポートチェック
    success, err_msg = check_import(candidate_path)
    if not success:
        return False, f"Import verification failed: {err_msg}"
        
    # 3. 現行コードのバックアップ退避
    try:
        os.makedirs(backup_dir, exist_ok=True)
        if os.path.exists(target_path):
            backup_file = os.path.join(backup_dir, os.path.basename(target_path) + ".bk")
            shutil.copy2(target_path, backup_file)
    except Exception as e:
        return False, f"Failed to create pre-update backup: {e}"
        
    # 4. 新しいコードを本番パスに適用
    try:
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        shutil.copy2(candidate_path, target_path)
    except Exception as e:
        return False, f"Failed to apply new code: {e}"
        
    return True, None
