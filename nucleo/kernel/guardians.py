"""Guardians — validadores de runtime da Constituição (C1–C8).

Sprint 0 inclui:
- `validate_outcome_clause` (C2): a verificação que o g13-po-guardian executa.
- `run_guardians`: o passo de self-critique (closed loop YC#2) antes da entrega.
"""
from __future__ import annotations


def validate_outcome_clause(target_spec: dict) -> dict:
    """C2 — a cláusula de outcome precisa de: statement + >=3 positivos + >=3 negativos + delivered_event."""
    oc = (target_spec or {}).get("outcome_clause", {}) or {}
    missing = []
    if not oc.get("statement"):
        missing.append("statement")
    if len(oc.get("positive_examples", []) or []) < 3:
        missing.append(">=3 positive_examples")
    if len(oc.get("negative_examples", []) or []) < 3:
        missing.append(">=3 negative_examples")
    if not oc.get("delivered_event"):
        missing.append("delivered_event")
    return {
        "valid": not missing,
        "missing": missing,
        "checked_spec": (target_spec or {}).get("id", "?"),
    }


def run_guardians(guardians: list, state: dict) -> dict:
    """Self-critique mínimo: cada agente é criticado antes de 'entregar' (C2/C6)."""
    out = state.get("output") or {}
    notes = []
    if "rationale" not in out:
        notes.append("output sem rationale")
    if not state.get("citations"):
        notes.append("sem citações (C6 — toda saída cita fonte do Brain)")
    return {"guardians": guardians or [], "ok": not notes, "notes": notes}
