"""Gate C4 — onde o modo do agente decide se ele ENTREGA / COBRA.

- SHADOW: roda mas NUNCA entrega/cobra (output marcado delivered=False, billing=0).
- PILOT / AUTONOMOUS: entrega direto.
- ASSISTED: pausa e pede aprovação humana via `interrupt()` (human-in-the-loop do DRI).

É o mecanismo de "evoluir ganhando autonomia": o agente só sai de SHADOW por gate.
"""
from __future__ import annotations
from langgraph.types import interrupt


def gate(state: dict, *, spec: dict) -> dict:
    mode = state.get("mode", "SHADOW")
    out = dict(state.get("output") or {})

    if mode == "SHADOW":
        out.update(delivered=False, billing_amount=0)
        if state.get("verbose"):
            print("  -> gate[SHADOW]: output NAO entregue, billing=0 (mede concordancia)")
        return {"output": out, "_gate": "proceed"}

    if mode in ("PILOT", "AUTONOMOUS"):
        out.update(delivered=True)
        if state.get("verbose"):
            print(f"  -> gate[{mode}]: entrega direta")
        return {"output": out, "_gate": "proceed"}

    if mode == "ASSISTED":
        decision = interrupt({
            "type": "approval_required",
            "agent": spec["id"],
            "proposed_output": out,
            "cost_tokens": state.get("cost_tokens", 0),
        })
        if not decision or not decision.get("approved"):
            return {"output": None, "_gate": "halt"}
        out.update(delivered=True)
        return {"output": out, "_gate": "proceed"}

    return {"output": out, "_gate": "proceed"}
