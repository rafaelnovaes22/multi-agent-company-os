"""Validate public demo input before invoking the company graph."""

from __future__ import annotations

from typing import Any

MAX_BODY_BYTES = 16_384
MAX_TEXT_LENGTH = 2_000
BOOLEAN_CONTEXT_FIELDS = (
    "founder_led",
    "sells_well",
    "lacks_process",
    "firefighter",
    "high_personnel_cost",
    "large_team",
    "public_sector",
)


def validate_intent_request(request: Any) -> tuple[str, dict[str, Any]]:
    if not isinstance(request, dict):
        raise ValueError("Corpo recebido deve ser um objeto JSON.")
    intent = request.get("intent")
    if not isinstance(intent, str) or not 1 <= len(intent.strip()) <= MAX_TEXT_LENGTH:
        raise ValueError("intent deve conter de 1 a 2000 caracteres.")
    context = request.get("context", {})
    if not isinstance(context, dict):
        raise ValueError("context deve ser um objeto JSON.")
    validate_context(context)
    return intent.strip(), context


def validate_context(context: dict[str, Any]) -> None:
    for field in ("company", "segment", "pain"):
        value = context.get(field, "")
        if not isinstance(value, str) or len(value) > MAX_TEXT_LENGTH:
            raise ValueError(f"{field} deve ser texto de até 2000 caracteres.")
    revenue = context.get("revenue_brl_year", 0)
    if isinstance(revenue, bool) or not isinstance(revenue, (int, float)):
        raise ValueError("revenue_brl_year deve ser um número não negativo.")
    if not 0 <= revenue <= 1e15:
        raise ValueError("revenue_brl_year deve estar entre zero e 10^15.")
    for field in BOOLEAN_CONTEXT_FIELDS:
        if field in context and not isinstance(context[field], bool):
            raise ValueError(f"{field} deve ser booleano.")
