"""Gate C4 — onde o modo do agente decide se ele ENTREGA / COBRA.

- SHADOW: roda mas NUNCA entrega/cobra (output marcado delivered=False, billing=0).
- PILOT / AUTONOMOUS: entrega direto.
- ASSISTED: pausa e pede aprovação humana via `interrupt()` (human-in-the-loop do DRI).

É o mecanismo de "evoluir ganhando autonomia": o agente só sai de SHADOW por gate.

Kill-switch de frota (resiliência operacional, NIST "sobreviver ao inevitável"):
quando ativo — flag no store (`("fleet",), "kill_switch"`, via governance/promote)
ou env FLEET_KILL_SWITCH — TODO agente se comporta como SHADOW, independente do
modo promovido: sem entrega, sem cobrança, sem pausa de aprovação. Contenção da
frota inteira em 1 comando, sem deploy e sem mexer nos modos persistidos.
"""
from __future__ import annotations
import os

from langgraph.types import interrupt

KILL_SWITCH_NS = ("fleet",)
KILL_SWITCH_KEY = "kill_switch"
KILL_SWITCH_ENV = "FLEET_KILL_SWITCH"


def kill_switch_on(store=None) -> bool:
    if os.environ.get(KILL_SWITCH_ENV, "").strip().lower() in ("1", "true", "on"):
        return True
    if store is None:
        return False
    flag = store.get(KILL_SWITCH_NS, KILL_SWITCH_KEY)
    return bool(flag.get("on")) if isinstance(flag, dict) else bool(flag)


def gate(state: dict, *, spec: dict, store=None) -> dict:
    mode = state.get("mode", "SHADOW")
    out = dict(state.get("output") or {})

    if kill_switch_on(store):
        out.update(delivered=False, billing_amount=0, fleet_kill_switch=True)
        if state.get("verbose"):
            print("  -> gate[KILL-SWITCH]: frota contida — sem entrega/cobranca (forca SHADOW)")
        return {"output": out, "_gate": "proceed"}

    if mode == "SHADOW":
        out.update(delivered=False, billing_amount=0)
        if state.get("verbose"):
            print("  -> gate[SHADOW]: output NAO entregue, billing=0 (mede concordancia)")
        return {"output": out, "_gate": "proceed"}

    # C3 runtime enforcement: deterministic billable handlers expose c3_ok/status.
    # Never mark delivered=True when unit economics breach max_ratio.
    c3_blocked = out.get("c3_ok") is False or out.get("status") == "blocked"

    if mode in ("PILOT", "AUTONOMOUS"):
        if c3_blocked:
            out.update(delivered=False, billing_amount=0)
            if state.get("verbose"):
                print(f"  -> gate[{mode}]: bloqueado por C3 (sem entrega/cobranca)")
            return {"output": out, "_gate": "proceed"}
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
        if c3_blocked:
            out.update(delivered=False, billing_amount=0)
            return {"output": out, "_gate": "proceed"}
        out.update(delivered=True)
        return {"output": out, "_gate": "proceed"}

    return {"output": out, "_gate": "proceed"}
