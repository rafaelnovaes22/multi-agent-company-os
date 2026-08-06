"""Demo do g2-diagnose — o PRIMEIRO entregável cobrável (diagnóstico C1).

Roda:  python -m nucleo.demo_diagnose

A Fábrica materializa o g2-diagnose; ele diagnostica clientes sintéticos em
SHADOW: mede o baseline humano (R$), confirma fit com o ICP, propõe o outcome e
lista candidatos a SKU. É o que se VENDE antes de construir o produto (C1).
"""

from __future__ import annotations

import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langgraph.checkpoint.memory import MemorySaver  # noqa: E402

from nucleo.factory.factory import build_from_spec  # noqa: E402
from nucleo.kernel.brain import Brain, FileStore  # noqa: E402
from nucleo.kernel.providers.llm import get_llm  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
BRAIN_DIR = os.path.join(ROOT, ".brain")
SPEC_DIR = os.path.join(ROOT, "guilds", "g02_produto", "g2-diagnose")


def run_diag(spec, agent, client):
    rid = "run-" + uuid.uuid4().hex[:8]
    state = {
        "task": {
            "agent_id": spec["id"],
            "guild": spec["guild"],
            "statement": "Diagnosticar o cliente (C1)",
            "client": client,
        },
        "mode": "SHADOW",
        "ledger": spec.get("ledger"),
        "run_id": rid,
        "verbose": True,
    }
    print(f"\n=== Diagnóstico: {client.get('id')} ({client.get('company', '?')}) | modo=SHADOW ===")
    final = agent.invoke(state, config={"configurable": {"thread_id": rid}})
    d = final.get("output") or {}
    b = d.get("baseline", {})
    print(f"  problema   : {d.get('problem')}")
    print(
        f"  baseline   : {b.get('monthly_volume')} un/mês x {b.get('hours_per_unit')}h x R${b.get('hourly_cost_brl')} "
        f"= R${b.get('baseline_cost_brl_month')}/mês ({b.get('baseline_hours_month')}h)"
    )
    print(f"  outcome    : {d.get('proposed_outcome')}")
    print(f"  métrica    : {d.get('success_metric')}")
    print(
        f"  agentes a ativar: {[a['id'] + '(' + a['status'] + ')' for a in d.get('recommended_agents', [])]}"
    )
    print(f"  RECOMENDA  : {d.get('recommendation')} (fit ICP {d.get('fit_icp_score')})")


def main():
    brain = Brain(os.path.join(BRAIN_DIR, "events"))
    store = FileStore(os.path.join(BRAIN_DIR, "store"))
    llm = get_llm("worker")
    spec, agent, gate = build_from_spec(SPEC_DIR, llm, brain, store, MemorySaver())
    print(
        f"LLM: {llm.name} | Fábrica materializou '{spec['id']}' (billable). "
        f"Gate -> ok={gate['ok']} warnings={gate['warnings']}"
    )

    clientes = [
        {
            "id": "C-001",
            "company": "Caos Servicos",
            "revenue_brl_year": 2_500_000,
            "founder_led": True,
            "sells_well": True,
            "lacks_process": True,
            "firefighter": True,
            "monthly_volume": 200,
            "hours_per_unit": 0.5,
            "hourly_cost_brl": 60,
            "process": "triagem de pedidos de entrada",
            "pain": "triagem manual consome o dia do fundador",
        },
        {
            "id": "C-002",
            "company": "Pequena Demais",
            "revenue_brl_year": 300_000,
            "founder_led": True,
            "monthly_volume": 5,
            "hours_per_unit": 0.2,
            "hourly_cost_brl": 50,
        },
        {
            "id": "C-003",
            "company": "Fit Sem Volume",
            "revenue_brl_year": 2_000_000,
            "founder_led": True,
            "lacks_process": True,
        },
    ]
    for c in clientes:
        run_diag(spec, agent, c)

    print("\n=== Company Brain (diagnósticos) ===")
    for ev in brain.events():
        if ev.get("actor") == spec["id"]:
            o = ev.get("output") or {}
            print(
                f"  [{ev['ts']}] client={o.get('client_id')} rec={o.get('recommendation')} "
                f"baseline=R${(o.get('baseline') or {}).get('baseline_cost_brl_month')}/mês delivered={ev['delivered']}"
            )

    print(
        "\nOK - g2-diagnose entrega o 1º produto cobrável (diagnóstico C1) em SHADOW. "
        "Vende-se o diagnóstico, mede-se a dor real, e SÓ DEPOIS a Fábrica constrói o SKU."
    )


if __name__ == "__main__":
    main()
