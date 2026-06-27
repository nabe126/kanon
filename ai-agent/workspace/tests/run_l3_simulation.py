import os
import subprocess
import time
import urllib.request
import urllib.error
import json
import hashlib

# スクリプトの位置から docker-compose.test-l3.yml の絶対パスを解決
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
COMPOSE_FILE = os.path.abspath(os.path.join(SCRIPT_DIR, "../../../docker-compose.test-l3.yml"))
SRC_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "../src"))
EVIDENCE_FILE = os.path.abspath(os.path.join(SCRIPT_DIR, "../l3_evidence.txt"))

AGENT_URL = "http://localhost:5001/healthz"
AGENT_FAIL_URL = "http://localhost:5001/healthz/fail"

def run_cmd(cmd):
    # stdout と stderr をマージして取得する
    return subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

def get_sha256(filepath):
    h = hashlib.sha256()
    try:
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception as e:
        return f"Error: {e}"

def get_src_state():
    state = {}
    if not os.path.exists(SRC_DIR):
        return state
    for root, _, files in os.walk(SRC_DIR):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                rel_path = os.path.relpath(path, SRC_DIR)
                try:
                    mtime = os.path.getmtime(path)
                    mtime_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mtime))
                    sha = get_sha256(path)
                    state[rel_path] = {"mtime": mtime_str, "sha256": sha}
                except Exception as e:
                    state[rel_path] = {"error": str(e)}
    return state

def format_state(state):
    lines = []
    for path, info in sorted(state.items()):
        if "error" in info:
            lines.append(f"  {path}: {info['error']}")
        else:
            lines.append(f"  {path} -> mtime: {info['mtime']}, sha256: {info['sha256']}")
    return "\n".join(lines)

def main():
    evidence = []
    evidence.append("=== L3 Integration Simulation Evidence ===")
    evidence.append(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    print("[L3 Sim] Starting L3 integration simulation (Observation Mode)...")
    
    # 1. 前回のクリーンアップ
    print("[L3 Sim] Cleaning up previous containers...")
    run_cmd(f"docker compose -f {COMPOSE_FILE} down -v")
    
    # 2. テストコンテナの起動
    print("[L3 Sim] Starting test environment via docker compose...")
    res = run_cmd(f"docker compose -f {COMPOSE_FILE} up -d --build")
    if res.returncode != 0:
        print(f"[L3 Sim] Error starting containers: {res.stdout}")
        evidence.append(f"Error starting containers: {res.stdout}")
        # 証拠保存して終了
        with open(EVIDENCE_FILE, "w") as f:
            f.write("\n".join(evidence))
        return False
        
    success = False
    try:
        # 3. 起動完了 (healthy: 200) 待ち
        print("[L3 Sim] Waiting for ai-agent to become healthy...")
        healthy = False
        for _ in range(25):
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
            evidence.append("Timeout waiting for healthy state.")
            agent_logs = run_cmd("docker logs kanon-test-agent-core").stdout
            evidence.append("--- Agent Logs ---")
            evidence.append(agent_logs)
            return False
            
        # monitor コンテナの初期 LKG 保存時間を確保
        print("[L3 Sim] Waiting for monitor to initialize LKG...")
        time.sleep(6)
        
        # ロールバック前の状態（正常状態）を記録
        pre_rollback_state = get_src_state()
        evidence.append("--- 1 & 2. Pre-Rollback src/ State ---")
        evidence.append(format_state(pre_rollback_state))
        evidence.append("")
        
        # 4. 障害注入 (500 への移行)
        print("[L3 Sim] Triggering health check failure via /healthz/fail...")
        try:
            with urllib.request.urlopen(AGENT_FAIL_URL, timeout=3) as resp:
                if resp.status == 200:
                    print("[L3 Sim] Simulated failure state has been set on agent.")
        except Exception as e:
            print(f"[L3 Sim] Failed to trigger simulated failure: {e}")
            evidence.append(f"Failed to trigger simulated failure: {e}")
            return False
            
        # 5. monitor がロールバック処理を完了するまで待つ
        print("[L3 Sim] Waiting for monitor.py to perform rollback...")
        rollback_detected = False
        for _ in range(25):
            time.sleep(2)
            monitor_logs = run_cmd("docker logs kanon-test-monitor").stdout
            if "Restored: snapshot_" in monitor_logs or "Rollback failed." in monitor_logs:
                rollback_detected = True
                print("[L3 Sim] Rollback detection logged by monitor!")
                break
        
        if not rollback_detected:
            print("[L3 Sim] Timeout waiting for monitor rollback logs.")
            evidence.append("Timeout waiting for monitor rollback logs.")
            monitor_logs = run_cmd("docker logs kanon-test-monitor").stdout
            evidence.append("--- Monitor Logs (Timeout) ---")
            evidence.append(monitor_logs)
            return False

        # ロールバック直後の状態を記録
        post_rollback_state = get_src_state()
        evidence.append("--- 1 & 2. Post-Rollback src/ State ---")
        evidence.append(format_state(post_rollback_state))
        evidence.append("")

        # 3. monitor.pyのログ
        monitor_logs = run_cmd("docker logs kanon-test-monitor").stdout
        evidence.append("--- 3. Monitor Logs ---")
        evidence.append(monitor_logs)
        evidence.append("")

        # 4. Flask autoreloaderのログ (ロールバック後)
        agent_logs_pre = run_cmd("docker logs kanon-test-agent-core").stdout
        evidence.append("--- 4. Agent Logs (Post-Rollback / Pre-Recovery) ---")
        evidence.append(agent_logs_pre)
        evidence.append("")

        # 5. ロールバック後の自動復旧監視 (monitorによるtouch ➔ オートリロード復旧)
        print("[L3 Sim] Observing auto-recovery after rollback...")
        recovered = False
        for i in range(15):
            time.sleep(2)
            try:
                with urllib.request.urlopen(AGENT_URL, timeout=3) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode('utf-8'))
                        if data.get("status") == "healthy":
                            recovered = True
                            print(f"[L3 Sim] ai-agent successfully recovered (200 OK)!")
                            break
            except Exception:
                pass
                
        # 6. オートリロード復帰後の最終ログ
        agent_logs_post = run_cmd("docker logs kanon-test-agent-core").stdout
        evidence.append("\n--- 6. Agent Logs (Post-Recovery) ---")
        evidence.append(agent_logs_post)
        evidence.append("")
        
        success = recovered
        evidence.append(f"Auto-Recovery Verification: {'PASSED' if success else 'FAILED'}")
        
        # 最終判定
        evidence.append(f"\nSimulation Result: {'SUCCESS' if success else 'FAILED'}")
        evidence.append("==========================================")
        
        # アサーション失敗時は例外
        if not success:
            evidence_text = "\n".join(evidence)
            raise AssertionError(f"L3 Simulation validation failed. Auto-recovery failure.\n{evidence_text[:1000]}")
            
        print("[L3 Sim] Simulation completed SUCCESSFULLY!")
        return True
        
    finally:
        # コンテナ状態も証拠に含める
        try:
            ps_out = run_cmd("docker ps -a").stdout
            evidence.append("--- Docker PS State (Finally) ---")
            evidence.append(ps_out)
            
            evidence_text = "\n".join(evidence)
            with open(EVIDENCE_FILE, "w") as f:
                f.write(evidence_text)
            print(f"[L3 Sim] Evidence file written to {EVIDENCE_FILE}")
        except Exception as e:
            print(f"[L3 Sim] Failed to write evidence file in finally: {e}")

        # クリーンアップ
        print("[L3 Sim] Cleaning up test containers...")
        run_cmd(f"docker compose -f {COMPOSE_FILE} down -v")

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
