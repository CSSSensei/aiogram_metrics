from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.client.session.aiohttp import AiohttpSession
from prometheus_client import CollectorRegistry, generate_latest

from aiogram_metrics.session import InstrumentedAiohttpSession


@pytest.mark.asyncio
async def test_session_records_api_call_duration():
    registry = CollectorRegistry()
    session = InstrumentedAiohttpSession(bot_name="testbot", registry=registry)

    mock_method = MagicMock()
    mock_method.__class__.__name__ = "SendMessage"

    with patch.object(AiohttpSession, "make_request", new_callable=AsyncMock) as mock_super:
        mock_super.return_value = MagicMock()
        await session.make_request(MagicMock(), mock_method)

    output = generate_latest(registry).decode()
    assert "tg_api_call_duration_seconds" in output
    assert 'method="SendMessage"' in output
    assert 'bot="testbot"' in output


@pytest.mark.asyncio
async def test_session_counts_api_calls_success():
    registry = CollectorRegistry()
    session = InstrumentedAiohttpSession(bot_name="testbot", registry=registry)

    mock_method = MagicMock()
    mock_method.__class__.__name__ = "GetUpdates"

    with patch.object(AiohttpSession, "make_request", new_callable=AsyncMock) as mock_super:
        mock_super.return_value = MagicMock()
        await session.make_request(MagicMock(), mock_method)

    output = generate_latest(registry).decode()
    assert 'tg_api_calls_total{bot="testbot",method="GetUpdates",status="success"} 1.0' in output


@pytest.mark.asyncio
async def test_session_counts_api_calls_error():
    registry = CollectorRegistry()
    session = InstrumentedAiohttpSession(bot_name="testbot", registry=registry)

    mock_method = MagicMock()
    mock_method.__class__.__name__ = "SendMessage"

    with patch.object(AiohttpSession, "make_request", new_callable=AsyncMock) as mock_super:
        mock_super.side_effect = RuntimeError("network error")
        with pytest.raises(RuntimeError):
            await session.make_request(MagicMock(), mock_method)

    output = generate_latest(registry).decode()
    assert 'status="error"' in output
