"""Self-harness wrapper — MULTI-TENANT (o NÚCLEO é o produto vendido a clientes).

Cada cliente é um TENANT. O contexto (perfil da empresa do cliente) e a MEMÓRIA do
agente são namespaced por tenant: o agente aprende a empresa DAQUELE cliente, sem
vazar entre clientes (C5/C8). Agentes internos (sem tenant_id) usam o namespace global.

- load_context: carrega SOUL + MEMORY (por tenant) + instincts + perfil do tenant.
- emit_artifact: registra o artefato no Brain (com tenant_id) — C6/YC#3.
- snapshot: grava o snapshot (por tenant) p/ o learning loop.
"""

from __future__ import annotations

import datetime


def _ns(state, kind, aid):
    """Namespace por tenant quando há tenant_id; global p/ agentes internos."""
    tid = state["task"].get("tenant_id")
    if tid:
        return {
            "soul": ("tenant", tid, "agent", aid),
            "memory": ("tenant", tid, "agent", aid, "memory"),
            "snapshots": ("tenant", tid, "snapshots", aid),
        }[kind]
    return {
        "soul": ("agent", aid),
        "memory": ("agent", aid, "memory"),
        "snapshots": ("snapshots", aid),
    }[kind]


def load_context(state, *, store, spec):
    aid = spec["id"]
    tid = state["task"].get("tenant_id")
    q = state["task"].get("statement", "")
    soul = store.get(_ns(state, "soul", aid), "soul") or {}
    memory = store.search(_ns(state, "memory", aid), q, 12)
    instincts = store.search(("instincts", aid), "", 8)
    profile = (store.get(("tenant", tid), "profile") if tid else None) or {}
    if state.get("verbose"):
        scope = f"tenant={tid}" if tid else "interno"
        print(
            f"  -> load_context [{scope}]: soul={'sim' if soul else 'nao'} "
            f"memory={len(memory)} perfil={'sim' if profile else 'nao'}"
        )
    return {
        "context": {
            "soul": soul,
            "memory": memory,
            "instincts": instincts,
            "tenant_profile": profile,
        },
        "scratchpad": [],
        "citations": [],
        "cost_tokens": 0,
    }


def emit_artifact(state, *, brain, spec):
    out = state.get("output") or {}
    ev = brain.emit_event(
        {
            "actor": spec["id"],
            "guild": spec.get("guild"),
            "tenant_id": state["task"].get("tenant_id"),
            "action": "run_completed",
            "run_id": state.get("run_id"),
            "mode": state.get("mode"),
            "ledger": state.get("ledger"),
            "delivered": out.get("delivered", False),
            "billing_amount": out.get("billing_amount", 0),
            "output": out,
            "citations": state.get("citations", []),
            "cost_tokens": state.get("cost_tokens", 0),
        }
    )
    if state.get("verbose"):
        print(
            f"  -> emit_artifact: '{ev['action']}' (tenant={ev['tenant_id']}, delivered={ev['delivered']})"
        )
    return {}


def snapshot(state, *, store, spec):
    aid = spec["id"]
    snap = {
        "run_id": state.get("run_id"),
        "tenant_id": state["task"].get("tenant_id"),
        "task": state.get("task"),
        "output": state.get("output"),
        "mode": state.get("mode"),
        "cost_tokens": state.get("cost_tokens", 0),
        "scratchpad": state.get("scratchpad", []),
        "processed": False,
        "ts": datetime.datetime.now().isoformat(timespec="seconds"),
    }
    store.put(_ns(state, "snapshots", aid), state.get("run_id", "run"), snap)
    if state.get("verbose"):
        print(f"  -> snapshot: gravado (tenant={snap['tenant_id']}, run={state.get('run_id')})")
    return {}
