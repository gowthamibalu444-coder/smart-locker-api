"""
Custom JSON formatter for structured logging.
Outputs log records as JSON strings suitable for Logstash ingestion.
"""
import json
import logging
import traceback
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    """
    Formats log records as JSON for Logstash/Kibana consumption.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Attach extra contextual data if present
        for key in ("user_id", "action", "locker_id", "reservation_id", "ip"):
            if hasattr(record, key):
                log_entry[key] = getattr(record, key)

        # Attach exception info if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info),
            }

        return json.dumps(log_entry)
