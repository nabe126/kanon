import os
import sys
import json
import time
import subprocess
import logging
from threading import Lock

# ロガーの取得
logger = logging.getLogger("discord_agent")

# パスの定義
# ファイル位置: workspace/src/memory/core.py
# WORKSPACE_DIR = workspace/
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "../.."))
STATE_DIR = os.path.join(WORKSPACE_DIR, "state")
L1_FILE = os.path.join(STATE_DIR, "working_memory.json")
MEMORY_DIR = os.path.join(WORKSPACE_DIR, "memory")
L3_DIR = os.path.join(MEMORY_DIR, "decision_history")
L4_DIR = os.path.join(MEMORY_DIR, "semantic")

# ワーキングメモリ (L1) の最大アクティブスロット数制限 (3〜10)
MAX_L1_SLOTS = 5

# スレッド安全性を確保するためのロック
memory_lock = Lock()

def git_auto_commit(file_path):
    """記憶ファイルの変更を Git で追跡し自動コミットします (ADR-010)"""
    try:
        res_status = subprocess.run(
            ["git", "status", "--porcelain", file_path],
            capture_output=True,
            text=True,
            cwd=WORKSPACE_DIR
        )
        if res_status.stdout.strip():
            subprocess.run(["git", "add", file_path], check=True, cwd=WORKSPACE_DIR)
            subprocess.run(
                ["git", "commit", "-m", f"chore(memory): auto-save {os.path.basename(file_path)} [skip ci]"],
                check=True,
                cwd=WORKSPACE_DIR
            )
            logger.info(f"[Memory] Git auto-committed: {os.path.basename(file_path)}")
    except Exception as e:
        logger.error(f"[Memory] Git auto-commit failed for {file_path}: {e}")

def parse_markdown_with_frontmatter(file_path):
    """YAML Frontmatter 付き Markdown ファイルを安全にパースします (依存関係排除)"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter_text = parts[1]
                body = parts[2].strip()
                
                metadata = {}
                for line in frontmatter_text.splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        k = k.strip()
                        v = v.strip()
                        if v.startswith("[") and v.endswith("]"):
                            v = [tag.strip() for tag in v[1:-1].split(",") if tag.strip()]
                        else:
                            if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                                v = v[1:-1]
                        metadata[k] = v
                return metadata, body
    except Exception as e:
        logger.error(f"[Memory] Failed to parse Markdown Frontmatter {file_path}: {e}")
    return {}, ""

def write_markdown_with_frontmatter(file_path, metadata, body):
    """YAML Frontmatter 付き Markdown ファイルを書き出します"""
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        frontmatter_lines = ["---"]
        for k, v in metadata.items():
            if isinstance(v, list):
                frontmatter_lines.append(f"{k}: [{', '.join(v)}]")
            else:
                frontmatter_lines.append(f"{k}: {v}")
        frontmatter_lines.append("---")
        
        content = "\n".join(frontmatter_lines) + "\n\n" + body
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    except Exception as e:
        logger.error(f"[Memory] Failed to write Markdown Frontmatter {file_path}: {e}")
        return False

def remember(topic, content, level="L1", category="general", tags=[]):
    """新しい記憶を作成または更新します。L1 容量超過時は L3 へ自動退避します。"""
    with memory_lock:
        os.makedirs(STATE_DIR, exist_ok=True)
        os.makedirs(L3_DIR, exist_ok=True)
        os.makedirs(L4_DIR, exist_ok=True)
        
        timestamp = time.strftime('%Y-%m-%dT%H:%M:%S')
        mem_id = f"MEM-{time.strftime('%Y%m%d-%H%M%S')}"
        
        if level == "L1":
            wm_data = []
            if os.path.exists(L1_FILE):
                try:
                    with open(L1_FILE, "r", encoding="utf-8") as f:
                        wm_data = json.load(f)
                except Exception:
                    wm_data = []
            
            # 既存トピックがあれば上書き
            existing_idx = -1
            for idx, item in enumerate(wm_data):
                if item["topic"] == topic:
                    existing_idx = idx
                    break
            
            new_item = {
                "id": mem_id,
                "topic": topic,
                "content": content,
                "category": category,
                "tags": tags,
                "updated_at": timestamp
            }
            
            if existing_idx != -1:
                wm_data[existing_idx] = new_item
            else:
                wm_data.append(new_item)
                
            # 容量制限チェック (フラッシュの実行)
            flashed_item = None
            if len(wm_data) > MAX_L1_SLOTS:
                wm_data.sort(key=lambda x: x["updated_at"])
                flashed_item = wm_data.pop(0) # 最古をフラッシュ
                
            # L1 の保存
            try:
                with open(L1_FILE, "w", encoding="utf-8") as f:
                    json.dump(wm_data, f, indent=2, ensure_ascii=False)
            except Exception as e:
                logger.error(f"[Memory] Failed to save working memory: {e}")
                return False
                
            # 長期エピソード記憶 (L3) へのフラッシュ
            if flashed_item:
                logger.warning(f"[Memory] Working memory limit exceeded. Flashing oldest topic '{flashed_item['topic']}' to L3.")
                safe_topic_name = "".join([c if c.isalnum() or c in ("_", "-") else "_" for c in flashed_item["topic"]])
                filename = f"{time.strftime('%Y%m%d')}_{safe_topic_name}.md"
                file_path = os.path.join(L3_DIR, filename)
                
                metadata = {
                    "id": flashed_item["id"],
                    "title": flashed_item["topic"],
                    "category": flashed_item["category"],
                    "tags": flashed_item["tags"],
                    "created_at": flashed_item["updated_at"],
                    "updated_at": timestamp
                }
                if write_markdown_with_frontmatter(file_path, metadata, flashed_item["content"]):
                    git_auto_commit(file_path)
            
            return True
            
        elif level in ("L3", "L4"):
            target_dir = L3_DIR if level == "L3" else L4_DIR
            safe_topic_name = "".join([c if c.isalnum() or c in ("_", "-") else "_" for c in topic])
            filename = f"{time.strftime('%Y%m%d')}_{safe_topic_name}.md" if level == "L3" else f"{safe_topic_name}.md"
            file_path = os.path.join(target_dir, filename)
            
            metadata = {
                "id": mem_id,
                "title": topic,
                "category": category,
                "tags": tags,
                "created_at": timestamp,
                "updated_at": timestamp
            }
            if write_markdown_with_frontmatter(file_path, metadata, content):
                git_auto_commit(file_path)
                return True
                
        return False

def recall(query, level=None):
    """優先度付き Read Bus (L1 -> L3 -> L4) に基づいて記憶をキーワード検索します。"""
    with memory_lock:
        levels_to_search = [level] if level else ["L1", "L3", "L4"]
        
        for search_level in levels_to_search:
            if search_level == "L1":
                if os.path.exists(L1_FILE):
                    try:
                        with open(L1_FILE, "r", encoding="utf-8") as f:
                            wm_data = json.load(f)
                        for item in wm_data:
                            if query.lower() in item["topic"].lower() or query.lower() in item["content"].lower():
                                return {
                                    "status": "success",
                                    "level": "L1",
                                    "topic": item["topic"],
                                    "content": item["content"],
                                    "category": item["category"],
                                    "tags": item["tags"],
                                    "updated_at": item["updated_at"]
                                }
                    except Exception as e:
                        logger.error(f"[Memory] Error searching L1: {e}")
                        
            elif search_level == "L3":
                if os.path.exists(L3_DIR):
                    for filename in sorted(os.listdir(L3_DIR)):
                        if filename.endswith(".md"):
                            path = os.path.join(L3_DIR, filename)
                            metadata, body = parse_markdown_with_frontmatter(path)
                            title = metadata.get("title", "")
                            tags = metadata.get("tags", [])
                            if (query.lower() in title.lower() or 
                                query.lower() in body.lower() or 
                                any(query.lower() in tag.lower() for tag in tags)):
                                return {
                                    "status": "success",
                                    "level": "L3",
                                    "topic": title,
                                    "content": body,
                                    "category": metadata.get("category", ""),
                                    "tags": tags,
                                    "updated_at": metadata.get("updated_at", "")
                                }
                                
            elif search_level == "L4":
                if os.path.exists(L4_DIR):
                    for filename in sorted(os.listdir(L4_DIR)):
                        if filename.endswith(".md"):
                            path = os.path.join(L4_DIR, filename)
                            metadata, body = parse_markdown_with_frontmatter(path)
                            title = metadata.get("title", "")
                            tags = metadata.get("tags", [])
                            if (query.lower() in title.lower() or 
                                query.lower() in body.lower() or 
                                any(query.lower() in tag.lower() for tag in tags)):
                                return {
                                    "status": "success",
                                    "level": "L4",
                                    "topic": title,
                                    "content": body,
                                    "category": metadata.get("category", ""),
                                    "tags": tags,
                                    "updated_at": metadata.get("updated_at", "")
                                }
                                
        return {
            "status": "not_found",
            "message": f"Query '{query}' not found in specified memory levels."
        }
