import time
from typing import Any

from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.exceptions import (
    TelegramAPIError,
    TelegramBadRequest,
    TelegramConflictError,
    TelegramEntityTooLarge,
    TelegramForbiddenError,
    TelegramNetworkError,
    TelegramNotFound,
    TelegramRetryAfter,
    TelegramServerError,
    TelegramUnauthorizedError,
)
from prometheus_client import REGISTRY, CollectorRegistry, Counter, Histogram

BUCKETS = [0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0]


def _classify_error(exc: BaseException) -> tuple[str, bool]:
    if isinstance(exc, TelegramRetryAfter):
        return 'retry_after', False
    if isinstance(exc, TelegramForbiddenError):
        return 'forbidden', 'block' in str(exc).lower()
    if isinstance(exc, TelegramBadRequest):
        return 'bad_request', False
    if isinstance(exc, TelegramNotFound):
        return 'not_found', False
    if isinstance(exc, TelegramConflictError):
        return 'conflict', False
    if isinstance(exc, TelegramUnauthorizedError):
        return 'unauthorized', False
    if isinstance(exc, TelegramEntityTooLarge):
        return 'entity_too_large', False
    if isinstance(exc, TelegramServerError):
        return 'server_error', False
    if isinstance(exc, TelegramNetworkError):
        return 'network', False
    if isinstance(exc, TelegramAPIError):
        return 'api_error', False
    return 'other', False


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
        Counter(
            'tg_api_errors_total',
            'Total Telegram API errors by type',
            ['bot', 'method', 'error_type'],
            registry=registry,
        ),
        Counter(
            'tg_bot_blocked_total',
            'Times the bot was blocked by a user (or kicked from a chat)',
            ['bot'],
            registry=registry,
        ),
    )


class InstrumentedAiohttpSession(AiohttpSession):
    def __init__(self, bot_name: str, registry: CollectorRegistry = REGISTRY, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._bot_name = bot_name
        self._api_duration, self._api_calls, self._api_errors, self._bot_blocked = _build_session_metrics(registry)

    async def make_request(self, bot: Any, method: Any, **kwargs: Any) -> Any:
        method_name = type(method).__name__
        start = time.monotonic()
        status = 'success'
        try:
            return await super().make_request(bot, method, **kwargs)
        except Exception as exc:
            status = 'error'
            error_type, is_blocked = _classify_error(exc)
            self._api_errors.labels(bot=self._bot_name, method=method_name, error_type=error_type).inc()
            if is_blocked:
                self._bot_blocked.labels(bot=self._bot_name).inc()
            raise
        finally:
            self._api_duration.labels(bot=self._bot_name, method=method_name).observe(time.monotonic() - start)
            self._api_calls.labels(bot=self._bot_name, method=method_name, status=status).inc()
