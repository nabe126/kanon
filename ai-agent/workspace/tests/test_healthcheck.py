from src.utils.healthcheck import get_system_metrics

def test_get_system_metrics_structure():
    """ヘルスチェックメトリクスの辞書構造とキーの存在を検証します。"""
    metrics = get_system_metrics()
    assert isinstance(metrics, dict)
    assert "timestamp" in metrics
    assert "status" in metrics
    assert "cpu" in metrics
    assert "memory" in metrics
    assert "disk" in metrics
    
    assert metrics["status"] in ["healthy", "warning", "critical"]

def test_get_system_metrics_values():
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
