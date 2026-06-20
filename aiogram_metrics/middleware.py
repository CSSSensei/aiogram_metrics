import time
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Update
from prometheus_client import REGISTRY, CollectorRegistry, Counter, Gauge, Histogram

BUCKETS = [0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]


def _extract_command(text: str | None) -> str | None:
    if not text or not text.startswith('/'):
        return None
    token = text.split(maxsplit=1)[0]
    command = token[1:].split('@', 1)[0]
    return command or None


def _build_metrics(registry: CollectorRegistry):
    return (
        Counter(
            'tg_updates_total',
            'Total Telegram updates processed',
            ['bot', 'update_type'],
            registry=registry,
        ),
        Histogram(
            'tg_handler_duration_seconds',
            'Handler processing duration in seconds',
            ['bot', 'update_type'],
            buckets=BUCKETS,
            registry=registry,
        ),
        Histogram(
            'tg_long_polling_lag_seconds',
            'Seconds between update creation and processing start',
            ['bot'],
            buckets=BUCKETS,
            registry=registry,
        ),
        Counter(
            'tg_errors_total',
            'Total handler errors',
            ['bot', 'update_type', 'error_type'],
            registry=registry,
        ),
        Counter(
            'tg_commands_total',
            'Total bot commands received',
            ['bot', 'command'],
            registry=registry,
        ),
        Gauge(
            'tg_active_users_daily',
            'Distinct users seen in the current UTC day (resets on restart)',
            ['bot'],
            registry=registry,
        ),
        Gauge(
            'tg_active_users_monthly',
            'Distinct users seen in the current UTC month (resets on restart)',
            ['bot'],
            registry=registry,
        ),
    )


class MetricsMiddleware(BaseMiddleware):
    def __init__(self, bot_name: str, registry: CollectorRegistry = REGISTRY) -> None:
        self._bot_name = bot_name
        (
            self._updates,
            self._duration,
            self._lag,
            self._errors,
            self._commands,
            self._active_daily,
            self._active_monthly,
        ) = _build_metrics(registry)

        self._daily_key: str | None = None
        self._daily_users: set[int] = set()
        self._monthly_key: str | None = None
        self._monthly_users: set[int] = set()

    def _track_active_user(self, user_id: int, now: datetime) -> None:
        day_key = now.strftime('%Y-%m-%d')
        month_key = now.strftime('%Y-%m')

        if day_key != self._daily_key:
            self._daily_key = day_key
            self._daily_users = set()
        if month_key != self._monthly_key:
            self._monthly_key = month_key
            self._monthly_users = set()

        self._daily_users.add(user_id)
        self._monthly_users.add(user_id)
        self._active_daily.labels(bot=self._bot_name).set(len(self._daily_users))
        self._active_monthly.labels(bot=self._bot_name).set(len(self._monthly_users))

    async def __call__(
        self,
        handler: Callable[[Update, dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: dict[str, Any],
    ) -> Any:
        update_type = next(iter(event.model_fields_set - {'update_id'}), 'unknown')

        event_date = None
        if event.message is not None:
            event_date = event.message.date
        elif event.callback_query is not None and event.callback_query.message is not None:
            event_date = event.callback_query.message.date

        if event_date is not None:
            lag = time.time() - event_date.timestamp()
            if 0 <= lag < 3600:
                self._lag.labels(bot=self._bot_name).observe(lag)

        event_obj = getattr(event, update_type, None)
        user = getattr(event_obj, 'from_user', None)
        if user is not None:
            self._track_active_user(user.id, datetime.now(timezone.utc))

        if event.message is not None:
            command = _extract_command(event.message.text)
            if command is not None:
                self._commands.labels(bot=self._bot_name, command=command).inc()

        self._updates.labels(bot=self._bot_name, update_type=update_type).inc()
        start = time.monotonic()
        try:
            return await handler(event, data)
        except Exception as exc:
            self._errors.labels(
                bot=self._bot_name,
                update_type=update_type,
                error_type=type(exc).__name__,
            ).inc()
            raise
        finally:
            self._duration.labels(bot=self._bot_name, update_type=update_type).observe(time.monotonic() - start)
