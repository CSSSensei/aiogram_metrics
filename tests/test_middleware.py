import time
from unittest.mock import AsyncMock, MagicMock

import pytest
from prometheus_client import CollectorRegistry, generate_latest

from aiogram_metrics.middleware import MetricsMiddleware


def make_mock_update(update_type: str = "message", lag_seconds: float = 0.05):
    update = MagicMock()
    update.update_id = 1
    update.model_fields_set = {update_type, "update_id"}

    msg = MagicMock()
    msg.date = MagicMock()
    msg.date.timestamp.return_value = time.time() - lag_seconds

    update.message = msg if update_type == "message" else None
    update.callback_query = None
    return update


@pytest.mark.asyncio
async def test_middleware_increments_counter():
    registry = CollectorRegistry()
    middleware = MetricsMiddleware(bot_name="testbot", registry=registry)
    handler = AsyncMock(return_value=None)
    update = make_mock_update()

    await middleware(handler, update, {})

    output = generate_latest(registry).decode()
    assert 'tg_updates_total{bot="testbot",update_type="message"} 1.0' in output
    handler.assert_awaited_once()


@pytest.mark.asyncio
async def test_middleware_records_handler_duration():
    registry = CollectorRegistry()
    middleware = MetricsMiddleware(bot_name="testbot", registry=registry)
    handler = AsyncMock(return_value=None)
    update = make_mock_update()

    await middleware(handler, update, {})

    output = generate_latest(registry).decode()
    assert "tg_handler_duration_seconds" in output
    assert 'bot="testbot"' in output


@pytest.mark.asyncio
async def test_middleware_records_long_polling_lag():
    registry = CollectorRegistry()
    middleware = MetricsMiddleware(bot_name="testbot", registry=registry)
    handler = AsyncMock(return_value=None)
    update = make_mock_update(lag_seconds=0.1)

    await middleware(handler, update, {})

    output = generate_latest(registry).decode()
    assert "tg_long_polling_lag_seconds" in output


@pytest.mark.asyncio
async def test_middleware_counts_errors():
    registry = CollectorRegistry()
    middleware = MetricsMiddleware(bot_name="testbot", registry=registry)

    async def failing_handler(event, data):
        raise ValueError("boom")

    update = make_mock_update()

    with pytest.raises(ValueError):
        await middleware(failing_handler, update, {})

    output = generate_latest(registry).decode()
    assert 'tg_errors_total{bot="testbot",error_type="ValueError",update_type="message"} 1.0' in output
