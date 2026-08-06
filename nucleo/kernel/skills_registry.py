"""skills_registry — registro e helpers base para handlers (SRP: só registro)."""
from __future__ import annotations

from typing import Any, Callable

_HANDLERS: dict[str, Callable[..., Any]] = {}


def register(name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def deco(fn: Callable[..., Any]) -> Callable[..., Any]:
        _HANDLERS[name] = fn
        return fn
    return deco


def get_handler(name: str) -> Callable[..., Any]:
    return _HANDLERS.get(name) or _HANDLERS["outcome_clause_validator"]


def _tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _spec_citations(state: dict[str, Any], spec: dict[str, Any]) -> list[str]:
    """Deriva citations da spec (C6): consumes_l0 + tools + delivered_event + tenant."""
    cites = []
    for ref in (spec.get("consumes_l0") or []):
        cites.append("l0:" + str(ref))
    for tool in (spec.get("tools") or []):
        cites.append("tool:" + str(tool))
    dev = (spec.get("outcome_clause") or {}).get("delivered_event")
    if dev:
        cites.append("delivered_event:" + str(dev))
    tid = state.get("task", {}).get("tenant_id")
    if tid:
        cites.append("tenant:" + str(tid))
    return cites or ["spec:" + str(spec.get("id", "?"))]
