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
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)

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
    
    print("[L3 Sim] Starting L3 integration simulation (Evidence Gathering Mode)...")
    
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
            return False
            
        # 5. monitor がロールバック処理を完了するまで待つ
        print("[L3 Sim] Waiting for monitor.py to perform rollback...")
        rollback_detected = False
        for _ in range(20):
            time.sleep(2)
            monitor_logs = run_cmd("docker logs kanon-test-monitor").stdout
            if "Restored: snapshot_" in monitor_logs or "Rollback failed." in monitor_logs:
                rollback_detected = True
                print("[L3 Sim] Rollback detection logged by monitor!")
                break
        
        if not rollback_detected:
            print("[L3 Sim] Timeout waiting for monitor rollback logs.")
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

        # 4. Flask autoreloaderのログ (ロールバック後直後)
        agent_logs_pre = run_cmd("docker logs kanon-test-agent-core").stdout
        evidence.append("--- 4. Agent Logs (Pre-Touch) ---")
        evidence.append(agent_logs_pre)
        evidence.append("")

        # 5. ロールバック後も500になる直接理由の確認（A側：touch前）
        print("[L3 Sim] Verifying healthy recovery (Touch-A)...")
        time.sleep(5) # リロードがあれば完了している時間を確保
        try:
            with urllib.request.urlopen(AGENT_URL, timeout=3) as resp:
                resp_code = resp.status
                resp_body = resp.read().decode('utf-8')
        except urllib.error.HTTPError as e:
            resp_code = e.code
            resp_body = e.read().decode('utf-8')
        except Exception as e:
            resp_code = "Error"
            resp_body = str(e)
            
        evidence.append("--- 5. Health Check Response (Pre-Touch / Touch-A) ---")
        evidence.append(f"HTTP Status Code: {resp_code}")
        evidence.append(f"Response Body: {resp_body}")
        evidence.append("")

        # A/B 比較アサーション (A側：touch前は 500 であること)
        is_touch_a_500 = (resp_code == 500)
        evidence.append(f"Verification [A] (Should be 500 error): {'PASSED' if is_touch_a_500 else 'FAILED'}")
        
        # 6. touch の追加による B 側検証の実行
        print("[L3 Sim] Executing touch to trigger autoreload (Touch-B)...")
        target_file = os.path.join(SRC_DIR, "discord_agent.py")
        if os.path.exists(target_file):
            try:
                os.utime(target_file, None)
                evidence.append(f"Executed touch on: {os.path.basename(target_file)}")
            except Exception as e:
                evidence.append(f"Failed to touch: {e}")
        else:
            evidence.append("Error: target_file does not exist.")
            
        # touch後、Flask オートリロードによる復帰を待つ (最大15秒)
        recovered = False
        print("[L3 Sim] Observing recovery after touch...")
        for i in range(10):
            time.sleep(2)
            try:
                with urllib.request.urlopen(AGENT_URL, timeout=3) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode('utf-8'))
                        if data.get("status") == "healthy":
                            recovered = True
                            print(f"[L3 Sim] ai-agent recovered successfully to 200 OK after touch!")
                            break
            except Exception:
                pass
                
        # 6. Flask autoreloaderのログ (ロールバック後＋touch後)
        agent_logs_post = run_cmd("docker logs kanon-test-agent-core").stdout
        evidence.append("\n--- 6. Agent Logs (Post-Touch) ---")
        evidence.append(agent_logs_post)
        evidence.append("")
        
        is_touch_b_200 = recovered
        evidence.append(f"Verification [B] (Should be 200 healthy): {'PASSED' if is_touch_b_200 else 'FAILED'}")
        
        # 最終判定
        success = is_touch_a_500 and is_touch_b_200
        evidence.append(f"\nHypothesis Verification Result: {'SUCCESS' if success else 'FAILED'}")
        evidence.append("==========================================")
        
        # 証拠ファイル保存
        evidence_text = "\n".join(evidence)
        with open(EVIDENCE_FILE, "w") as f:
            f.write(evidence_text)
        print(f"[L3 Sim] Evidence file written to {EVIDENCE_FILE}")
        
        # アサーション失敗時はアノテーションに埋め込むため例外
        if not success:
            raise AssertionError(f"L3 Simulation validation failed. A/B test failure.\n{evidence_text[:1000]}")
            
        print("[L3 Sim] Simulation completed SUCCESSFULLY!")
        return True
        
    finally:
        # クリーンアップ
        print("[L3 Sim] Cleaning up test containers...")
        run_cmd(f"docker compose -f {COMPOSE_FILE} down -v")

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
