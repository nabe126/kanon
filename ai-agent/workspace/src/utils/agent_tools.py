import os
import sys
import fnmatch
from typing import Optional
from utils.logger import get_logger

logger = get_logger("agent_tools")

def list_dir(directory_path: str) -> str:
    """指定されたディレクトリのファイルおよびサブディレクトリ一覧を返します。"""
    try:
        # 相対パスの場合は /workspace を基準にする
        if not os.path.isabs(directory_path):
            directory_path = os.path.abspath(os.path.join("/workspace", directory_path))
            
        if not os.path.exists(directory_path):
            return f"Error: Directory {directory_path} does not exist."
        if not os.path.isdir(directory_path):
            return f"Error: Path {directory_path} is not a directory."
        
        items = os.listdir(directory_path)
        result = []
        for item in items:
            path = os.path.join(directory_path, item)
            is_dir = os.path.isdir(path)
            size = os.path.getsize(path) if not is_dir else 0
            type_str = "DIR" if is_dir else "FILE"
            result.append(f"[{type_str}] {item} ({size} bytes)" if not is_dir else f"[{type_str}] {item}")
        return "\n".join(result)
    except Exception as e:
        return f"Error listing directory: {e}"

def grep_search(query: str, search_path: str) -> str:
    """指定されたディレクトリ内のファイルから、クエリに一致する行を検索します。"""
    try:
        if not os.path.isabs(search_path):
            search_path = os.path.abspath(os.path.join("/workspace", search_path))

        if not os.path.exists(search_path):
            return f"Error: Path {search_path} does not exist."
        
        results = []
        if os.path.isfile(search_path):
            files = [search_path]
        else:
            files = []
            for root, _, filenames in os.walk(search_path):
                for filename in filenames:
                    files.append(os.path.join(root, filename))
        
        match_count = 0
        for file in files:
            # 巨大なバイナリや.venv等は避ける
            if any(p in file for p in [".venv", ".git", ".pytest_cache", "__pycache__"]):
                continue
            try:
                with open(file, "r", encoding="utf-8", errors="ignore") as f:
                    for line_num, line in enumerate(f, 1):
                        if query in line:
                            results.append(f"{os.path.basename(file)}:{line_num}: {line.strip()}")
                            match_count += 1
                            if match_count >= 50:
                                results.append("... (Too many matches, truncated)")
                                return "\n".join(results)
            except Exception:
                pass
        return "\n".join(results) if results else "No matches found."
    except Exception as e:
        return f"Error in grep_search: {e}"

def read_file(absolute_path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> str:
    """指定されたファイルの内容を読み込みます。行数を指定して範囲読み込みも可能です。"""
    try:
        if not os.path.isabs(absolute_path):
            absolute_path = os.path.abspath(os.path.join("/workspace", absolute_path))

        if not os.path.exists(absolute_path):
            return f"Error: File {absolute_path} does not exist."
        if not os.path.isfile(absolute_path):
            return f"Error: Path {absolute_path} is not a file."
        
        with open(absolute_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            
        total_lines = len(lines)
        start = max(1, start_line) if start_line is not None else 1
        end = min(total_lines, end_line) if end_line is not None else min(total_lines, start + 800)
        
        selected_lines = lines[start-1:end]
        result = [f"{i}: {line}" for i, line in enumerate(selected_lines, start)]
        return "".join(result)
    except Exception as e:
        return f"Error reading file: {e}"

def replace_file_content(target_file: str, target_content: str, replacement_content: str, start_line: int, end_line: int) -> str:
    """指定したファイルの内容を置換します。変更ポリシーに従い、検証を行って適用します。"""
    try:
        if not os.path.isabs(target_file):
            target_file = os.path.abspath(os.path.join("/workspace", target_file))

        if not os.path.exists(target_file):
            return f"Error: File {target_file} does not exist."
        
        with open(target_file, "r", encoding="utf-8") as f:
            content = f.read()
            
        if target_content not in content:
            return "Error: Target content not found in the file. Ensure whitespace and line endings match exactly."
        
        # 部分置換を実行
        new_content = content.replace(target_content, replacement_content, 1)
        
        # 変更ポリシーに基づく静的検証（py_compile）を適用前に実施するため、一旦一時ファイルへ書き込む
        temp_file = target_file + ".tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(new_content)
            
        # 静的検証
        if target_file.endswith(".py"):
            import py_compile
            try:
                py_compile.compile(temp_file, doraise=True)
            except Exception as compile_err:
                os.remove(temp_file)
                return f"Error: Python compilation failed for modified code. Change rejected.\nDetails: {compile_err}"
        
        # 検証成功したので上書き適用
        os.replace(temp_file, target_file)
        return "Success: File content replaced successfully and verified."
    except Exception as e:
        return f"Error replacing file content: {e}"

def write_to_file(target_file: str, code_content: str, overwrite: bool = False) -> str:
    """ファイルを新規に作成し、内容を書き込みます。"""
    try:
        if not os.path.isabs(target_file):
            target_file = os.path.abspath(os.path.join("/workspace", target_file))

        if os.path.exists(target_file) and not overwrite:
            return f"Error: File {target_file} already exists. Set overwrite=True to replace it."
        
        # 変更ポリシーに基づく静的検証
        temp_file = target_file + ".tmp"
        # ディレクトリ作成
        os.makedirs(os.path.dirname(target_file), exist_ok=True)
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(code_content)
            
        if target_file.endswith(".py"):
            import py_compile
            try:
                py_compile.compile(temp_file, doraise=True)
            except Exception as compile_err:
                os.remove(temp_file)
                return f"Error: Python compilation failed for new file. Creation rejected.\nDetails: {compile_err}"
                
        os.replace(temp_file, target_file)
        return f"Success: File {target_file} written and verified."
    except Exception as e:
        return f"Error writing to file: {e}"

def request_command_execution(command_line: str, reason: str) -> str:
    """シェルコマンドの実行を要求します。裏でASEP計画を自動起票し、ユーザーに承認を促します。"""
    try:
        from utils.asep_middleware import ASEPMiddleware
        asep = ASEPMiddleware()
        plan = asep.create_plan(command_line, "L2", reason, f"Requested via agent tool execution.")
        if plan:
            return f"Success: Created ASEP Plan '{plan['plan_id']}' for command '{command_line}'. User must approve this command in the chat before execution."
        else:
            return "Error: Failed to create ASEP Plan."
    except Exception as e:
        return f"Error creating ASEP Plan: {e}"
