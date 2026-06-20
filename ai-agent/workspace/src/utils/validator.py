import sys
import py_compile
import subprocess
from typing import Tuple

def check_syntax(file_path: str) -> Tuple[bool, str | None]:
    """指定されたPythonファイルの構文エラー（SyntaxError）をチェックします (Task-001)"""
    try:
        py_compile.compile(file_path, doraise=True)
        return True, None
    except py_compile.PyCompileError as e:
        # py_compileのエラーメッセージを抽出
        return False, str(e).strip()
    except Exception as e:
        return False, f"Unexpected error during syntax check: {e}"

def check_import(file_path: str) -> Tuple[bool, str | None]:
    """指定されたファイルをサブプロセス経由でインポートテストし、依存エラーをチェックします (Task-002)"""
    try:
        # 依存ライブラリのロードや未定義エラーの検出のため、独立したサブプロセスでロードを試みる
        # sys.path にファイルのあるディレクトリを追加してインポートをシミュレート
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
