import time
from unittest.mock import AsyncMock, MagicMock

import pytest
from prometheus_client import CollectorRegistry, generate_latest

from aiogram_metrics.middleware import MetricsMiddleware, _extract_command


def make_mock_update(
    update_type: str = 'message',
    lag_seconds: float = 0.05,
    text: str | None = None,
    user_id: int = 1,
):
    update = MagicMock()
    update.update_id = 1
    update.model_fields_set = {update_type, 'update_id'}

    msg = MagicMock()
    msg.date = MagicMock()
    msg.date.timestamp.return_value = time.time() - lag_seconds
    msg.text = text
    msg.from_user.id = user_id

    update.message = msg if update_type == 'message' else None
    update.callback_query = None
    return update


@pytest.mark.asyncio
async def test_middleware_increments_counter():
    registry = CollectorRegistry()
    middleware = MetricsMiddleware(bot_name='testbot', registry=registry)
    handler = AsyncMock(return_value=None)
    update = make_mock_update()

    await middleware(handler, update, {})

    output = generate_latest(registry).decode()
    assert 'tg_updates_total{bot="testbot",update_type="message"} 1.0' in output
    handler.assert_awaited_once()


@pytest.mark.asyncio
async def test_middleware_records_handler_duration():
    registry = CollectorRegistry()
    middleware = MetricsMiddleware(bot_name='testbot', registry=registry)
    handler = AsyncMock(return_value=None)
    update = make_mock_update()

    await middleware(handler, update, {})

    output = generate_latest(registry).decode()
    assert 'tg_handler_duration_seconds' in output
    assert 'bot="testbot"' in output


@pytest.mark.asyncio
async def test_middleware_records_long_polling_lag():
    registry = CollectorRegistry()
    middleware = MetricsMiddleware(bot_name='testbot', registry=registry)
    handler = AsyncMock(return_value=None)
    update = make_mock_update(lag_seconds=0.1)

    await middleware(handler, update, {})

    output = generate_latest(registry).decode()
    assert 'tg_long_polling_lag_seconds' in output


@pytest.mark.asyncio
async def test_middleware_counts_errors():
    registry = CollectorRegistry()
    middleware = MetricsMiddleware(bot_name='testbot', registry=registry)

    async def failing_handler(event, data):
        raise ValueError('boom')

    update = make_mock_update()

    with pytest.raises(ValueError):
        await middleware(failing_handler, update, {})

    output = generate_latest(registry).decode()
    assert 'tg_errors_total{bot="testbot",error_type="ValueError",update_type="message"} 1.0' in output


@pytest.mark.parametrize(
    'text,expected',
    [
        ('/start', 'start'),
        ('/start@MyCoolBot', 'start'),
        ('/ban@MyCoolBot 12345 spam', 'ban'),
        ('/help some args', 'help'),
        ('hello world', None),
        ('', None),
        (None, None),
        ('/', None),
    ],
)
def test_extract_command(text, expected):
    assert _extract_command(text) == expected


@pytest.mark.asyncio
async def test_middleware_counts_commands():
    registry = CollectorRegistry()
    middleware = MetricsMiddleware(bot_name='testbot', registry=registry)
    handler = AsyncMock(return_value=None)
    update = make_mock_update(text='/start@MyCoolBot deep-link')

    await middleware(handler, update, {})

    output = generate_latest(registry).decode()
    assert 'tg_commands_total{bot="testbot",command="start"} 1.0' in output


@pytest.mark.asyncio
async def test_middleware_ignores_non_command_messages():
    registry = CollectorRegistry()
    middleware = MetricsMiddleware(bot_name='testbot', registry=registry)
    handler = AsyncMock(return_value=None)
    update = make_mock_update(text='just a plain message')

    await middleware(handler, update, {})

    output = generate_latest(registry).decode()
    assert 'tg_commands_total{' not in output


@pytest.mark.asyncio
async def test_middleware_tracks_active_users():
    registry = CollectorRegistry()
    middleware = MetricsMiddleware(bot_name='testbot', registry=registry)
    handler = AsyncMock(return_value=None)

    await middleware(handler, make_mock_update(user_id=1), {})
    await middleware(handler, make_mock_update(user_id=2), {})
    await middleware(handler, make_mock_update(user_id=1), {})  # repeat, deduped

    output = generate_latest(registry).decode()
    assert 'tg_active_users_daily{bot="testbot"} 2.0' in output
    assert 'tg_active_users_monthly{bot="testbot"} 2.0' in output


@pytest.mark.asyncio
async def test_middleware_active_users_resets_on_new_day():
    registry = CollectorRegistry()
    middleware = MetricsMiddleware(bot_name='testbot', registry=registry)
    handler = AsyncMock(return_value=None)

    await middleware(handler, make_mock_update(user_id=1), {})
    await middleware(handler, make_mock_update(user_id=2), {})

    middleware._daily_key = '1970-01-01'
    await middleware(handler, make_mock_update(user_id=3), {})

    output = generate_latest(registry).decode()
    assert 'tg_active_users_daily{bot="testbot"} 1.0' in output
    assert 'tg_active_users_monthly{bot="testbot"} 3.0' in output
