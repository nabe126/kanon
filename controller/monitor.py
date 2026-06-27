import os
import time
import shutil
import urllib.request
import subprocess
import json

# 設定パラメータ（環境変数からの取得、フォールバック付き）
HEALTHZ_URL = os.getenv("KANON_HEALTHZ_URL", "http://localhost:5000/healthz")
CHECK_INTERVAL = int(os.getenv("KANON_CHECK_INTERVAL", "15"))  # 監視間隔 (秒)
MAX_FAILURES = int(os.getenv("KANON_MAX_FAILURES", "3"))     # 許容する連続失敗回数
MAX_BACKUP_GENERATIONS = 5

WORKSPACE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../ai-agent/workspace"))
SRC_DIR = os.path.join(WORKSPACE_DIR, "src")
BACKUP_DIR = os.path.join(WORKSPACE_DIR, "backups")
LKG_INFO_PATH = os.path.join(BACKUP_DIR, "LKG.json")
CONTAINER_NAME = os.getenv("KANON_CONTAINER_NAME", "ai_agent_core")

def check_health() -> bool:
    """エージェントコンテナのヘルスチェックエンドポイントへポーリングします (Task-005)"""
    try:
        with urllib.request.urlopen(HEALTHZ_URL, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                return data.get("status") in ["healthy", "warning"]
    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [Monitor] Healthcheck request failed: {e}")
    return False

def clean_old_snapshots():
    """最大保持世代数を超えた最も古いスナップショットを削除します。"""
    if not os.path.exists(BACKUP_DIR):
        return
    
    snapshots = sorted([
        d for d in os.listdir(BACKUP_DIR) 
        if d.startswith("snapshot_") and os.path.isdir(os.path.join(BACKUP_DIR, d))
    ])
    
    while len(snapshots) > MAX_BACKUP_GENERATIONS:
        oldest = snapshots.pop(0)
        oldest_dir = os.path.join(BACKUP_DIR, oldest)
        try:
            shutil.rmtree(oldest_dir)
            print(f"[Monitor] Deleted oldest snapshot due to generation limit: {oldest}")
        except Exception as e:
            print(f"[Monitor] Failed to delete oldest snapshot {oldest}: {e}")

def create_snapshot() -> str:
    """現在の src/ の状態をタイムスタンプ付きで backups/ に保存し、世代管理を行います。"""
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    snapshot_name = f"snapshot_{timestamp}"
    dest_dir = os.path.join(BACKUP_DIR, snapshot_name)
    
    os.makedirs(BACKUP_DIR, exist_ok=True)
    if os.path.exists(SRC_DIR):
        try:
            shutil.copytree(SRC_DIR, dest_dir)
            print(f"[Monitor] Created snapshot: {snapshot_name}")
            clean_old_snapshots()
            return dest_dir
        except Exception as e:
            print(f"[Monitor] Failed to create snapshot: {e}")
    return ""

def save_lkg(snapshot_path: str):
    """正常起動が確認されたスナップショットを LKG (Last Known Good) として設定します。"""
    try:
        lkg_data = {
            "lkg_snapshot_path": os.path.relpath(snapshot_path, BACKUP_DIR),
            "updated_at": time.strftime('%Y-%m-%dT%H:%M:%S%z')
        }
        os.makedirs(BACKUP_DIR, exist_ok=True)
        with open(LKG_INFO_PATH, "w") as f:
            json.dump(lkg_data, f, indent=4)
        print(f"[Monitor] Updated LKG reference to: {os.path.basename(snapshot_path)}")
    except Exception as e:
        print(f"[Monitor] Failed to save LKG info: {e}")

def get_lkg_path() -> str:
    """LKG情報ファイルから、復元対象のディレクトリパスを取得します。"""
    if os.path.exists(LKG_INFO_PATH):
        try:
            with open(LKG_INFO_PATH, "r") as f:
                data = json.load(f)
                rel_path = data.get("lkg_snapshot_path")
                if rel_path:
                    abs_path = os.path.join(BACKUP_DIR, rel_path)
                    if os.path.exists(abs_path):
                        return abs_path
        except Exception as e:
            print(f"[Monitor] Failed to read LKG info: {e}")
            
    # LKG.jsonがない、または破損している場合は、存在する最新のスナップショットで代用
    if os.path.exists(BACKUP_DIR):
        snapshots = sorted([
            d for d in os.listdir(BACKUP_DIR) 
            if d.startswith("snapshot_") and os.path.isdir(os.path.join(BACKUP_DIR, d))
        ])
        if snapshots:
            return os.path.join(BACKUP_DIR, snapshots[-1])
    return ""

def execute_rollback() -> bool:
    """異常発生時に LKG ディレクトリから src/ を復元してコンテナを再起動します (Task-006)"""
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [Monitor] Initiating automatic rollback procedure...")
    
    lkg_path = get_lkg_path()
    if not lkg_path:
        print("[Monitor] Error: No valid LKG or snapshots found to restore.")
        return False
        
    try:
        # デバッグ分析用に、壊れた可能性のある現在の src/ も snapshot として退避
        print("[Monitor] Preserving failed src/ state...")
        create_snapshot()
        
        # 復旧元の存在確認
        if not os.path.exists(lkg_path):
            print(f"[Monitor] Error: LKG path {lkg_path} does not exist.")
            return False
            
        # 現在の src/ をクリーンアップした上で復元
        if os.path.exists(SRC_DIR):
            shutil.rmtree(SRC_DIR)
            
        shutil.copytree(lkg_path, SRC_DIR)
        print(f"[Monitor] Restored: {os.path.basename(lkg_path)} -> src/")
        
        # 復元した Python ファイルのタイムスタンプを現在時刻に更新 (touch) してオートリロードをトリガー
        for root, _, files in os.walk(SRC_DIR):
            for file in files:
                if file.endswith(".py"):
                    path = os.path.join(root, file)
                    try:
                        os.utime(path, None)
                    except Exception as e:
                        print(f"[Monitor] Failed to touch {file}: {e}")
            
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
    
    # 起動時、現在の src/ がすでにhealthyならそれをLKGの初期スナップショットとして固定
    if check_health():
        print("[Monitor] Agent is healthy at startup. Registering initial LKG snapshot...")
        initial_snap = create_snapshot()
        if initial_snap:
            save_lkg(initial_snap)
            
    failure_count = 0
    
    while True:
        if check_health():
            if failure_count > 0:
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [Monitor] Agent recovered. Resetting counter.")
                # 回復直後の正常な状態を新たな LKG として固定
                new_snap = create_snapshot()
                if new_snap:
                    save_lkg(new_snap)
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
