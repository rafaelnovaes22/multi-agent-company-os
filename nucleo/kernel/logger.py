"""logger — logging estruturado JSON para NÚCLEO (clean-code: JSON com campos nomeados).

Uso:
    from .logger import get_logger
    log = get_logger(__name__)
    log.info("agent_materialized", agent_id=spec["id"], guild=spec["guild"])

Fora de produção, formata como JSON por linha (parseável com jq).
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

_HANDLER = None


def get_logger(name: str) -> logging.Logger:
    global _HANDLER
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    if _HANDLER is None:
        _HANDLER = logging.StreamHandler(sys.stdout)
        _HANDLER.setFormatter(_JsonFormatter())
    logger.addHandler(_HANDLER)
    logger.propagate = False
    # permite log.info("event", key=val) → extra
    orig_log = logger._log

    def _patched(self, level, msg, args, exc_info=None, extra=None, stack_info=False, stacklevel=1, **kwargs):  # type: ignore
        if kwargs:
            extra = {**(extra or {}), **kwargs}
        return orig_log(level, msg, args, exc_info, extra, stack_info, stacklevel)

    logger._log = _patched.__get__(logger, logging.Logger)  # type: ignore
    return logger


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "level": record.levelname.lower(),
            "logger": record.name,
            "event": record.getMessage(),
        }
        # campos extras via extra={}
        for k, v in record.__dict__.items():
            if k not in (
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "taskName",
                "processName",
                "process",
                "message",
            ):
                payload[k] = v
        # mescla dicionário passado como msg
        if isinstance(record.msg, dict):
            payload.update(record.msg)
            payload["event"] = payload.get("event", "log")
        return json.dumps(payload, ensure_ascii=False)
