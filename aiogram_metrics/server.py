import logging
import threading

from prometheus_client import start_http_server

logger = logging.getLogger(__name__)

_server_started = False
_lock = threading.Lock()


def start_metrics_server(port: int) -> None:
    global _server_started
    with _lock:
        if _server_started:
            logger.warning("metrics server already started, skipping")
            return
        start_http_server(port)
        _server_started = True
        logger.info("metrics server started on port %d", port)
