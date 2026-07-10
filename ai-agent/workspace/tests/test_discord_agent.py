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

from unittest.mock import MagicMock
from src.discord_agent import generate_agent_reply

@pytest.mark.anyio
async def test_generate_agent_reply_success() -> None:
    """generate_agent_reply がモックされたクライアントから正常に応答を返すことのテスト"""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Hello, this is a mock reply."
    mock_response.function_calls = None
    mock_client.models.generate_content.return_value = mock_response

    contents = [{"role": "user", "content": "hello"}]
    reply = await generate_agent_reply(contents, genai_client=mock_client)

    assert reply == "Hello, this is a mock reply."
    assert mock_client.models.generate_content.call_count == 1
    call_kwargs = mock_client.models.generate_content.call_args[1]
    assert call_kwargs["model"] == 'gemini-3.1-flash-lite'

@pytest.mark.anyio
async def test_generate_agent_reply_missing_key() -> None:
    """APIキーもクライアントも指定されていない場合、エラーメッセージを返すことのテスト"""
    contents = [{"role": "user", "content": "hello"}]
    reply = await generate_agent_reply(contents, api_key=None, genai_client=None)
    assert "エラー: GEMINI_API_KEY" in reply

from google.genai.errors import ServerError
import tenacity

@pytest.mark.anyio
async def test_generate_agent_reply_retry_success(monkeypatch) -> None:
    """一過性のエラー（ServerError）が起きた後、リトライして最終的に成功することのテスト"""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Success after retry."
    mock_response.function_calls = None
    
    err = ServerError(503, {"error": {"message": "Service Unavailable", "status": "UNAVAILABLE"}})
    mock_client.models.generate_content.side_effect = [err, mock_response]

    contents = [{"role": "user", "content": "hello"}]
    monkeypatch.setattr(generate_agent_reply.retry, "wait", tenacity.wait_none())

    reply = await generate_agent_reply(contents, genai_client=mock_client)
    assert reply == "Success after retry."
    assert mock_client.models.generate_content.call_count == 2

@pytest.mark.anyio
async def test_generate_agent_reply_retry_failure(monkeypatch) -> None:
    """一過性エラーが5回連続して発生した場合、最終的に例外が送出されることのテスト"""
    mock_client = MagicMock()
    err = ServerError(503, {"error": {"message": "Service Unavailable", "status": "UNAVAILABLE"}})
    mock_client.models.generate_content.side_effect = [err] * 6

    contents = [{"role": "user", "content": "hello"}]
    monkeypatch.setattr(generate_agent_reply.retry, "wait", tenacity.wait_none())

    with pytest.raises(ServerError):
        await generate_agent_reply(contents, genai_client=mock_client)
    
    assert mock_client.models.generate_content.call_count == 5

def test_agent_tools_blacklist() -> None:
    """agent_tools のセキュリティブラックリストが正しくアクセスを拒否することのテスト"""
    from src.utils.agent_tools import _is_blocked_path, read_file, list_dir
    
    # 判定関数のテスト
    assert _is_blocked_path("/workspace/ai-agent/secrets/.env") is True
    assert _is_blocked_path("/workspace/controller/monitor.py") is True
    assert _is_blocked_path("/workspace/.git/config") is True
    assert _is_blocked_path("/workspace/ai-agent/workspace/src/discord_agent.py") is False
    
    # ツール呼び出し時のブロックテスト
    res_read = read_file("/workspace/ai-agent/secrets/.env")
    assert "restricted for security" in res_read
    
    res_list = list_dir("/workspace/controller")
    assert "restricted for security" in res_list
