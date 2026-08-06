"""Onboarding de tenant — operacionaliza a venda.

Fluxo: registra o cliente (config do tenant, C8) -> roda o g2-diagnose (venda) ->
ativa, em SHADOW, os agentes de produto recomendados (live) na conta do cliente ->
agrega os sinais e roda o painel-dono. Multi-tenant, agnóstico de segmento.
"""

from __future__ import annotations

import os
import uuid

from ..factory.factory import build_from_spec

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../nucleo
PRODUCT_DIR = os.path.join(ROOT, "product")
DIAG_DIR = os.path.join(ROOT, "guilds", "g02_produto", "g2-diagnose")
PAYLOAD_KEY = {
    "fin-caixa": "finance",
    "inbox-triage": "inbox",
    "ops-followup": "ops",
    "atendimento": "atendimento",
}


def _invoke(agent, task, ledger):
    rid = "ob-" + uuid.uuid4().hex[:8]
    st = {"task": task, "mode": "SHADOW", "ledger": ledger, "run_id": rid, "verbose": False}
    return agent.invoke(st, config={"configurable": {"thread_id": rid}}).get("output") or {}


def onboard(tenant_id, profile, client_signals, data, llm, brain, store, cp):
    store.put(("tenant", tenant_id), "profile", profile)  # config do tenant (C8)

    dspec, dagent, _ = build_from_spec(DIAG_DIR, llm, brain, store, cp)
    diag = _invoke(
        dagent,
        {
            "agent_id": dspec["id"],
            "guild": dspec["guild"],
            "tenant_id": tenant_id,
            "statement": "diagnostico",
            "client": client_signals,
        },
        dspec.get("ledger"),
    )
    recs = diag.get("recommended_agents", [])
    live = [r for r in sorted(recs, key=lambda r: r["prioridade"]) if r["status"] == "live"]

    metrics, results = {}, {}
    for r in live:
        aid = r["id"]
        spec, agent, _ = build_from_spec(os.path.join(PRODUCT_DIR, aid), llm, brain, store, cp)
        task = {
            "agent_id": aid,
            "guild": spec["guild"],
            "tenant_id": tenant_id,
            "statement": "onboarding",
        }
        if aid == "painel-dono":
            task["metrics"] = metrics  # agrega os sinais do fleet
        else:
            k = PAYLOAD_KEY.get(aid)
            if k and aid in data:
                task[k] = data[aid]
        out = _invoke(agent, task, spec.get("ledger"))
        results[aid] = out
        if aid == "fin-caixa":
            metrics.update(
                cash_position=out.get("cash_position"),
                projected_cash=out.get("projected_cash"),
                total_overdue=out.get("total_overdue"),
                margin_pct=out.get("margin_pct"),
            )
        elif aid == "inbox-triage":
            metrics["urgent_msgs"] = out.get("urgent_count")
        elif aid == "ops-followup":
            metrics["stalled_tasks"] = out.get("stalled_count")
        elif aid == "atendimento":
            metrics["pending_replies"] = out.get("reply_queue_count")

    return {
        "tenant": tenant_id,
        "diagnosis": {"recommendation": diag.get("recommendation"), "recommended": recs},
        "activated": list(results.keys()),
        "results": results,
        "metrics": metrics,
    }
