import time
from typing import Any

from aiogram.client.session.aiohttp import AiohttpSession
from prometheus_client import REGISTRY, CollectorRegistry, Counter, Histogram

BUCKETS = [0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0]


def _build_session_metrics(registry: CollectorRegistry):
    return (
        Histogram(
            'tg_api_call_duration_seconds',
            'Telegram API call duration in seconds',
            ['bot', 'method'],
            buckets=BUCKETS,
            registry=registry,
        ),
        Counter(
            'tg_api_calls_total',
            'Total Telegram API calls',
            ['bot', 'method', 'status'],
            registry=registry,
        ),
    )


class InstrumentedAiohttpSession(AiohttpSession):
    def __init__(self, bot_name: str, registry: CollectorRegistry = REGISTRY, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._bot_name = bot_name
        self._api_duration, self._api_calls = _build_session_metrics(registry)

    async def make_request(self, bot: Any, method: Any, **kwargs: Any) -> Any:
        method_name = type(method).__name__
        start = time.monotonic()
        status = 'success'
        try:
            return await super().make_request(bot, method, **kwargs)
        except Exception:
            status = 'error'
            raise
        finally:
            self._api_duration.labels(bot=self._bot_name, method=method_name).observe(
                time.monotonic() - start
            )
            self._api_calls.labels(bot=self._bot_name, method=method_name, status=status).inc()
