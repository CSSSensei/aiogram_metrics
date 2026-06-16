import time
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Update
from prometheus_client import REGISTRY, CollectorRegistry, Counter, Histogram

BUCKETS = [0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]


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
    )


class MetricsMiddleware(BaseMiddleware):
    def __init__(self, bot_name: str, registry: CollectorRegistry = REGISTRY) -> None:
        self._bot_name = bot_name
        self._updates, self._duration, self._lag, self._errors = _build_metrics(registry)

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
            self._duration.labels(bot=self._bot_name, update_type=update_type).observe(
                time.monotonic() - start
            )
