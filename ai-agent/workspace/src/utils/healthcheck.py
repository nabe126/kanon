import os
import shutil
import time
from typing import Dict, Any

def get_system_metrics() -> Dict[str, Any]:
    """CPU負荷、メモリ使用状況、ディスク空き容量を含むシステムメトリクスを取得します (Task-003)"""
    metrics = {
        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S%z'),
        "status": "healthy",
        "cpu": {},
        "memory": {},
        "disk": {}
    }
    
    # 1. CPU使用率（Linux /proc/loadavg のパース。ない場合は簡易的な擬似値）
    try:
        if os.path.exists("/proc/loadavg"):
            with open("/proc/loadavg", "r") as f:
                load = f.read().split()
                metrics["cpu"]["load_1m"] = float(load[0])
                metrics["cpu"]["load_5m"] = float(load[1])
                metrics["cpu"]["load_15m"] = float(load[2])
        else:
            # 非Linux環境（Macでのローカル稼働等）のダミーフォールバック
            metrics["cpu"]["load_1m"] = 0.0
            metrics["cpu"]["load_5m"] = 0.0
            metrics["cpu"]["load_15m"] = 0.0
    except Exception as e:
        metrics["cpu"]["error"] = f"Failed to parse loadavg: {e}"
        metrics["status"] = "warning"

    # 2. メモリ状況（Linux /proc/meminfo のパース）
    try:
        if os.path.exists("/proc/meminfo"):
            mem_info = {}
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2:
                        key = parts[0].replace(":", "")
                        val = int(parts[1])
                        mem_info[key] = val
            
            total = mem_info.get("MemTotal", 0)
            free = mem_info.get("MemFree", 0)
            buffers = mem_info.get("Buffers", 0)
            cached = mem_info.get("Cached", 0)
            
            # 実質的な使用中メモリ = Total - (Free + Buffers + Cached)
            used = total - free - buffers - cached
            metrics["memory"]["total_mb"] = total // 1024
            metrics["memory"]["free_mb"] = free // 1024
            metrics["memory"]["used_mb"] = used // 1024
            metrics["memory"]["percent"] = round((used / total) * 100, 2) if total > 0 else 0.0
        else:
            # 非Linux環境でのモック
            metrics["memory"]["total_mb"] = 8192
            metrics["memory"]["free_mb"] = 4096
            metrics["memory"]["used_mb"] = 4096
            metrics["memory"]["percent"] = 50.0
    except Exception as e:
        metrics["memory"]["error"] = f"Failed to parse meminfo: {e}"
        metrics["status"] = "warning"

    # 3. ディスク状況（shutil.disk_usageを使用）
    try:
        # /workspaceマウント領域、存在しなければカレントチェック
        path_to_check = "/workspace" if os.path.exists("/workspace") else "."
        usage = shutil.disk_usage(path_to_check)
        metrics["disk"]["total_gb"] = round(usage.total / (1024**3), 2)
        metrics["disk"]["used_gb"] = round(usage.used / (1024**3), 2)
        metrics["disk"]["free_gb"] = round(usage.free / (1024**3), 2)
        metrics["disk"]["percent"] = round((usage.used / usage.total) * 100, 2) if usage.total > 0 else 0.0
    except Exception as e:
        metrics["disk"]["error"] = f"Failed to read disk usage: {e}"
        metrics["status"] = "warning"

    # 4. 閾値に基づくステータス判定
    # statusの優先順位: unhealthy > warning > healthy
    status_candidate = "healthy"
    
    # CPU 閾値評価
    cores = os.cpu_count() or 4
    cpu_load = metrics["cpu"].get("load_1m", 0.0)
    if cpu_load >= cores * 3.0:
        status_candidate = "unhealthy"
    elif cpu_load >= cores * 1.5:
        status_candidate = "warning"
            
    # メモリ 閾値評価
    mem_percent = metrics["memory"].get("percent", 0.0)
    if mem_percent >= 95.0:
        status_candidate = "unhealthy"
    elif mem_percent >= 90.0:
        if status_candidate != "unhealthy":
            status_candidate = "warning"
            
    # ディスク 閾値評価
    disk_percent = metrics["disk"].get("percent", 0.0)
    if disk_percent >= 95.0:
        status_candidate = "unhealthy"
    elif disk_percent >= 90.0:
        if status_candidate != "unhealthy":
            status_candidate = "warning"
            
    # 収集時の例外判定とのマージ
    if metrics["status"] == "warning" and status_candidate == "unhealthy":
        metrics["status"] = "unhealthy"
    elif metrics["status"] == "healthy":
        metrics["status"] = status_candidate

    return metrics
