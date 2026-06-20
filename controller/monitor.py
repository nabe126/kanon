import os
import time
import shutil
import urllib.request
import subprocess
import json

# 設定パラメータ
HEALTHZ_URL = "http://localhost:5000/healthz"
CHECK_INTERVAL = 15  # 監視間隔 (秒)
MAX_FAILURES = 3     # 許容する連続失敗回数
WORKSPACE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../ai-agent/workspace"))
SRC_DIR = os.path.join(WORKSPACE_DIR, "src")
BACKUP_DIR = os.path.join(WORKSPACE_DIR, "backups")
CONTAINER_NAME = "ai_agent_core"

def check_health() -> bool:
    """エージェントコンテナのヘルスチェックエンドポイントへポーリングします (Task-005)"""
    try:
        # urllib を使用し依存ライブラリを最小化
        with urllib.request.urlopen(HEALTHZ_URL, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                # システムヘルスが healthy または warning なら正常とみなす
                return data.get("status") in ["healthy", "warning"]
    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [Monitor] Healthcheck request failed: {e}")
    return False

def execute_rollback() -> bool:
    """異常発生時に backups/ から LKG ファイルを復元してコンテナを再起動します (Task-006)"""
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [Monitor] Initiating automatic rollback procedure...")
    
    if not os.path.exists(BACKUP_DIR):
        print(f"[Monitor] Error: Backup directory {BACKUP_DIR} not found.")
        return False
        
    backups = [f for f in os.listdir(BACKUP_DIR) if f.endswith(".py") or f.endswith(".bk")]
    if not backups:
        print("[Monitor] Error: No LKG backups found in backups/ directory.")
        return False
        
    try:
        # バックアップファイルを src/ へ上書きコピー
        for backup_file in backups:
            src_name = backup_file.replace(".bk", ".py") if backup_file.endswith(".bk") else backup_file
            src_path = os.path.join(SRC_DIR, src_name)
            backup_path = os.path.join(BACKUP_DIR, backup_file)
            shutil.copy2(backup_path, src_path)
            print(f"[Monitor] Restored: {backup_file} -> {src_name}")
            
        # Dockerコンテナの再起動を実行
        print(f"[Monitor] Restarting Docker container: {CONTAINER_NAME}")
        result = subprocess.run(["docker", "restart", CONTAINER_NAME], capture_output=True, text=True)
        if result.returncode == 0:
            print("[Monitor] Docker container restarted successfully.")
            return True
        else:
            print(f"[Monitor] Failed to restart container via Docker socket: {result.stderr}")
    except Exception as e:
        print(f"[Monitor] Error during rollback execution: {e}")
        
    return False

def main():
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [Monitor] Starting Kanon Rollback Monitor loop...")
    failure_count = 0
    
    while True:
        if check_health():
            if failure_count > 0:
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [Monitor] Agent recovered. Resetting counter.")
            failure_count = 0
        else:
            failure_count += 1
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [Monitor] Healthcheck failed ({failure_count}/{MAX_FAILURES})")
            
            if failure_count >= MAX_FAILURES:
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [Monitor] Maximum failures reached! Triggering rollback...")
                if execute_rollback():
                    print("[Monitor] Rollback completed. Cooling down for 60 seconds to allow start up...")
                    time.sleep(60)
                    failure_count = 0
                else:
                    print("[Monitor] Rollback failed. Retrying in next interval.")
                    time.sleep(10)
                    
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
