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
