import time
import urllib.request

from aiogram_metrics.server import start_metrics_server


def test_metrics_server_responds():
    port = 19101
    start_metrics_server(port=port)
    time.sleep(0.3)

    response = urllib.request.urlopen(f"http://localhost:{port}/metrics")
    assert response.status == 200
    body = response.read().decode()
    assert "python_info" in body
