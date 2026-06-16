<h1 align="center">aiogram3-metrics</h1>
<p align="center">
<b>Prometheus metrics for aiogram 3.x bots</b>
</p>

<p align="center">
<img src="https://img.shields.io/badge/made%20by-Phasalo-000FFF">
<img src="https://img.shields.io/badge/version-0.1.0-0000FF">
</p>

<p align="center">
    <a href="README.md">Русский</a> | English
</p>

## Quick start

### Installation

```bash
pip install aiogram3-metrics
```

### Usage

```python
from aiogram_metrics import MetricsMiddleware, InstrumentedAiohttpSession, start_metrics_server

# /metrics HTTP endpoint
start_metrics_server(port=9101)

# Instrumented session (API call latency and counts)
session = InstrumentedAiohttpSession(bot_name="mybot")
bot = Bot(token=TOKEN, session=session)

# Middleware (update counts, handler latency, errors)
dp.update.outer_middleware(MetricsMiddleware(bot_name="mybot"))
```

## Metrics

### MetricsMiddleware

| Metric | Type | Labels |
|---|---|---|
| `tg_updates_total` | Counter | bot, update_type |
| `tg_handler_duration_seconds` | Histogram | bot, update_type |
| `tg_long_polling_lag_seconds` | Histogram | bot |
| `tg_errors_total` | Counter | bot, update_type, error_type |

### InstrumentedAiohttpSession

| Metric | Type | Labels |
|---|---|---|
| `tg_api_call_duration_seconds` | Histogram | bot, method |
| `tg_api_calls_total` | Counter | bot, method, status |

## Testing

```bash
pytest tests/ -v
```

<br>
<p align="center">
<b>Phasalo</b><br>
2026
</p>
