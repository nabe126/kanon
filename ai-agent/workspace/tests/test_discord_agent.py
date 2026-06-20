import os
import pytest
import asyncio
from src.discord_agent import app, run_mock_loop

def test_flask_healthz() -> None:
    """Flask healthz エンドポイントのテスト"""
    client = app.test_client()
    response = client.get('/healthz')
    assert response.status_code == 200
    data = response.get_json()
    assert "status" in data
    assert "agent_status" in data
    assert data["status"] in ["healthy", "warning", "unhealthy"]

def test_flask_healthz_fail_disabled(monkeypatch) -> None:
    """テストハーネスが無効（デフォルト）の状態で /healthz/fail を叩くと 403 になること"""
    monkeypatch.setenv("KANON_TEST_TRIGGER", "false")
    client = app.test_client()
    response = client.get('/healthz/fail')
    assert response.status_code == 403
    
    # healthz 自体は healthy のままであること
    response_hz = client.get('/healthz')
    assert response_hz.status_code == 200

def test_flask_healthz_fail_enabled(monkeypatch) -> None:
    """テストハーネスを有効にして /healthz/fail を叩くと 500 unhealthy がトリガーされること"""
    monkeypatch.setenv("KANON_TEST_TRIGGER", "true")
    client = app.test_client()
    
    # 疑似障害のトリガー
    response_fail = client.get('/healthz/fail')
    assert response_fail.status_code == 200
    
    # /healthz が 500 unhealthy を返すようになったか確認
    response_hz = client.get('/healthz')
    assert response_hz.status_code == 500
    data = response_hz.get_json()
    assert data["status"] == "unhealthy"
    assert "Simulated failure" in data["agent_status"]

@pytest.mark.anyio
async def test_run_mock_loop() -> None:
    """モック Discord ループのキャンセルハンドリングテスト"""
    task = asyncio.create_task(run_mock_loop())
    await asyncio.sleep(0.1)
    task.cancel()
    
    try:
        await task
    except asyncio.CancelledError:
        pass  # 正常にキャンセルされればパス
