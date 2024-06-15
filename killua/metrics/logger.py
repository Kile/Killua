from logging import StreamHandler
from prometheus_client import Counter

LOGGING_COUNTER = Counter("logging", "Log entries", ["logger", "level"])


class PrometheusLoggingHandler(StreamHandler):
    """
    A logging handler that adds logging metrics to prometheus
    """

    def emit(self, record):
        LOGGING_COUNTER.labels(record.name, record.levelname).inc()
        super().emit(record)