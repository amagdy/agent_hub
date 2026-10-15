import logging
import os
import sys

import structlog


def _filter_private_fields(logger, log_method, event_dict):
    filter_keywords = ["password", "secret"]
    for key in list(event_dict.keys()):
        if any(keyword in key.lower() for keyword in filter_keywords):
            del event_dict[key]
    return event_dict

def _resolve_level():
    # Fetch LOG_LEVEL (default INFO); fall back to INFO on an invalid value
    raw_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, raw_level, logging.INFO)
    return level if isinstance(level, int) else logging.INFO


structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        _filter_private_fields,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(_resolve_level()),
    logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
    cache_logger_on_first_use=False,
)

logger = structlog.get_logger("app")
