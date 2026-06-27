import os
import subprocess
import time
import urllib.request
import urllib.error
import json

# スクリプトの位置から docker-compose.test-l3.yml の絶対パスを解決
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
COMPOSE_FILE = os.path.abspath(os.path.join(SCRIPT_DIR, "../../../docker-compose.test-l3.yml"))

AGENT_URL = "http://localhost:5001/healthz"
AGENT_FAIL_URL = "http://localhost:5001/healthz/fail"

def run_cmd(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)

def main():
    print("[L3 Sim] Starting L3 integration simulation (Observation Mode)...")
    
    # 1. 前回のクリーンアップ
    print("[L3 Sim] Cleaning up previous containers...")
    run_cmd(f"docker compose -f {COMPOSE_FILE} down -v")
    
    # 2. テストコンテナの起動
    print("[L3 Sim] Starting test environment via docker compose...")
    res = run_cmd(f"docker compose -f {COMPOSE_FILE} up -d --build")
    if res.returncode != 0:
        print(f"[L3 Sim] Error starting containers: {res.stderr}")
        return False
        
    try:
        # 3. 起動完了 (healthy: 200) 待ち
        print("[L3 Sim] Waiting for ai-agent to become healthy...")
        healthy = False
        for _ in range(15):
            time.sleep(2)
            try:
                with urllib.request.urlopen(AGENT_URL, timeout=3) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode('utf-8'))
                        if data.get("status") == "healthy":
                            healthy = True
                            print("[L3 Sim] ai-agent is healthy!")
                            break
            except Exception:
                pass
        
        if not healthy:
            print("[L3 Sim] Timeout waiting for healthy state.")
            return False
            
        # monitor コンテナの初期 LKG 保存時間を確保
        print("[L3 Sim] Waiting for monitor to initialize initial LKG...")
        time.sleep(6)
        
        # 4. 障害注入 (500 への移行)
        print("[L3 Sim] Triggering health check failure via /healthz/fail...")
        try:
            # テストハーネス有効時は /healthz/fail は 200 を返す
            with urllib.request.urlopen(AGENT_FAIL_URL, timeout=3) as resp:
                if resp.status == 200:
                    print("[L3 Sim] simulated failure state has been set on agent.")
        except Exception as e:
            print(f"[L3 Sim] Failed to trigger simulated failure: {e}")
            return False
            
        # 5. ロールバックおよびオートリロード回復の観測
        # monitor 設定: CHECK_INTERVAL=2, MAX_FAILURES=3
        # 失敗検知 (2秒*3) ➔ ロールバック ➔ ファイル書き戻し ➔ オートリロード復帰を待つ (最大45秒)
        print("[L3 Sim] Observing monitor logging and auto-recovery...")
        recovered = False
        for i in range(25):
            time.sleep(2)
            try:
                with urllib.request.urlopen(AGENT_URL, timeout=3) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode('utf-8'))
                        if data.get("status") == "healthy":
                            recovered = True
                            print(f"[L3 Sim] ai-agent successfully recovered (200 OK) after {i*2} seconds!")
                            break
            except Exception:
                pass
                
        if not recovered:
            print("[L3 Sim] Error: ai-agent did not recover to healthy state.")
            print("--- Monitor Logs ---")
            print(run_cmd("docker logs kanon-test-monitor").stdout)
            return False
            
        # 6. monitor コンテナのログ検証
        # docker.sock なしのため、再起動コマンド試行 ➔ エラーログ発生のフローが正常に行われたことを検証する
        monitor_logs = run_cmd("docker logs kanon-test-monitor").stdout
        
        # ロールバック手続きの開始と、LKG書き戻し、再起動コマンドが試行されたログをアサート
        has_rollback = "Initiating automatic rollback procedure..." in monitor_logs
        has_restore = "Restored: snapshot_" in monitor_logs
        has_restart_attempt = "Failed to restart container via Docker socket" in monitor_logs or "Docker container restarted successfully" in monitor_logs
        
        if has_rollback and has_restore and has_restart_attempt:
            print("[L3 Sim] Assertion PASSED: Rollback & restore logs detected successfully!")
        else:
            print("[L3 Sim] Assertion FAILED: Missing expected monitor workflow logs.")
            print(f"Rollback: {has_rollback}, Restore: {has_restore}, Restart Attempt: {has_restart_attempt}")
            print("--- Monitor Logs ---")
            print(monitor_logs)
            return False
            
        print("[L3 Sim] Simulation completed SUCCESSFULLY!")
        return True
        
    finally:
        # 7. クリーンアップ
        print("[L3 Sim] Cleaning up test containers...")
        run_cmd(f"docker compose -f {COMPOSE_FILE} down -v")

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
