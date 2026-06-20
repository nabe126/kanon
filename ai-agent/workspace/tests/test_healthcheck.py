from unittest.mock import patch, mock_open
import os
from src.utils.healthcheck import get_system_metrics

def test_get_system_metrics_structure() -> None:
    """ヘルスチェックメトリクスの辞書構造とキーの存在を検証します。"""
    metrics = get_system_metrics()
    assert isinstance(metrics, dict)
    assert "timestamp" in metrics
    assert "status" in metrics
    assert "cpu" in metrics
    assert "memory" in metrics
    assert "disk" in metrics
    
    assert metrics["status"] in ["healthy", "warning", "unhealthy"]

def test_get_system_metrics_values() -> None:
    """ディスク、メモリなどのメトリクスの数値範囲を検証します。"""
    metrics = get_system_metrics()
    
    # 正常にディスク容量が取得できているか (0より大きいこと)
    assert metrics["disk"]["total_gb"] > 0
    assert metrics["disk"]["free_gb"] >= 0
    assert 0.0 <= metrics["disk"]["percent"] <= 100.0
    
    # メモリメトリクスの確認 (エラー時は-1が設定される)
    if "error" not in metrics["memory"]:
        assert metrics["memory"]["total_mb"] > 0
        assert metrics["memory"]["free_mb"] >= 0
        assert 0.0 <= metrics["memory"]["percent"] <= 100.0

def test_healthcheck_thresholds() -> None:
    """リソース閾値判定のステータス評価テスト"""
    
    # 1. CPU高負荷時の評価 (cores * 3.0 以上で unhealthy)
    with patch("os.cpu_count", return_value=4):
        # /proc/loadavg をモックしてロード 13.0 (4*3.0 = 12.0 なので unhealthy) を返すようにする
        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data="13.0 10.0 5.0 1/100 12345")):
                metrics = get_system_metrics()
                assert metrics["status"] == "unhealthy"

        # load 7.0 (cores*1.5 = 6.0 より大きく cores*3.0 = 12.0 より小さいので warning)
        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data="7.0 5.0 3.0 1/100 12345")):
                metrics = get_system_metrics()
                assert metrics["status"] == "warning"

    # 2. メモリ高負荷時の評価 (95% 以上で unhealthy)
    # used = (10000 - 200 - 100 - 100) = 9600 / 10000 = 96%
    meminfo_unhealthy = """MemTotal: 10240000 kB
MemFree: 204800 kB
Buffers: 102400 kB
Cached: 102400 kB
"""
    with patch("os.path.exists", lambda path: path == "/proc/meminfo"):
        with patch("builtins.open", mock_open(read_data=meminfo_unhealthy)):
            metrics = get_system_metrics()
            assert metrics["status"] == "unhealthy"

    # used = (10000 - 700 - 100 - 100) = 9100 / 10000 = 91% (warning)
    meminfo_warning = """MemTotal: 10240000 kB
MemFree: 716800 kB
Buffers: 102400 kB
Cached: 102400 kB
"""
    with patch("os.path.exists", lambda path: path == "/proc/meminfo"):
        with patch("builtins.open", mock_open(read_data=meminfo_warning)):
            metrics = get_system_metrics()
            assert metrics["status"] == "warning"
