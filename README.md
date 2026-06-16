<h1 align="center">aiogram-metrics</h1>
<p align="center">
<b>Prometheus метрики для aiogram 3.x ботов</b>
</p>

<p align="center">
<img src="https://img.shields.io/badge/made%20by-Phasalo-000FFF">
<img src="https://img.shields.io/badge/version-0.1.0-0000FF">
</p>

<p align="center">
    Русский | <a href="README-en.md">English</a>
</p>

## Быстрый старт

### Установка

```bash
pip install aiogram-metrics
```

### Использование

```python
from aiogram_metrics import MetricsMiddleware, InstrumentedAiohttpSession, start_metrics_server

# /metrics HTTP endpoint
start_metrics_server(port=9101)

# Инструментация сессии (latency и счётчик API вызовов)
session = InstrumentedAiohttpSession(bot_name="mybot")
bot = Bot(token=TOKEN, session=session)

# Middleware (счётчик апдейтов, latency хендлеров, ошибки)
dp.update.outer_middleware(MetricsMiddleware(bot_name="mybot"))
```

## Метрики

### MetricsMiddleware

| Метрика | Тип | Labels |
|---|---|---|
| `tg_updates_total` | Counter | bot, update_type |
| `tg_handler_duration_seconds` | Histogram | bot, update_type |
| `tg_long_polling_lag_seconds` | Histogram | bot |
| `tg_errors_total` | Counter | bot, update_type, error_type |

### InstrumentedAiohttpSession

| Метрика | Тип | Labels |
|---|---|---|
| `tg_api_call_duration_seconds` | Histogram | bot, method |
| `tg_api_calls_total` | Counter | bot, method, status |

## Тестирование

```bash
pytest tests/ -v
```

<br>
<p align="center">
<b>Phasalo</b><br>
<i>Делаем красиво!</i><br><br>
2026
</p>
