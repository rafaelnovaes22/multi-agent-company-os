"""Demo do g8-lead-qualifier — um agente de NEGÓCIO real qualificando leads
contra o ICP (company/icp.md), em SHADOW, sobre o mesmo kernel/Fábrica.

Roda:  python -m nucleo.demo_g8     (a partir da pasta Multi-Agentes)

Prova: a Fábrica materializa o g8-lead-qualifier a partir da spec.yaml; ele
carrega o ICP via load_icp() (C5), pontua cada lead pelos sinais do Tier 1,
decide trilha, e registra tudo no Company Brain — em SHADOW (delivered=False).
"""
from __future__ import annotations
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langgraph.checkpoint.memory import MemorySaver  # noqa: E402

from nucleo.kernel.brain import Brain, FileStore  # noqa: E402
from nucleo.kernel.providers.llm import get_llm  # noqa: E402
from nucleo.factory.factory import build_from_spec  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
BRAIN_DIR = os.path.join(ROOT, ".brain")
SPEC_DIR = os.path.join(ROOT, "guilds", "g08_vendas", "g8-lead-qualifier")


def bootstrap(store, aid):
    if not store.get(("agent", aid), "soul"):
        with open(os.path.join(SPEC_DIR, "soul.md"), encoding="utf-8") as f:
            store.put(("agent", aid), "soul", {"text": f.read()})


def run_lead(spec, agent, lead, mode="SHADOW"):
    run_id = "run-" + uuid.uuid4().hex[:8]
    state = {
        "task": {"agent_id": spec["id"], "guild": spec["guild"],
                 "statement": "Qualificar lead contra o ICP", "lead": lead},
        "mode": mode, "ledger": spec.get("ledger", "billable"),
        "run_id": run_id, "verbose": True,
    }
    print(f"\n=== {lead['id']} ({lead.get('company', '?')}) | R${lead.get('revenue_brl_year', 0):,} | modo={mode} ===")
    final = agent.invoke(state, config={"configurable": {"thread_id": run_id}})
    o = final.get("output") or {}
    print(f"  RESULTADO: {o.get('decision')} score={o.get('score')} trilha='{o.get('track')}' "
          f"delivered={o.get('delivered')}")
    print(f"  sinais ICP: {list((o.get('icp_fit_signals') or {}).keys())}")
    print(f"  citacoes: {final.get('citations')}")
    return final


def main():
    brain = Brain(os.path.join(BRAIN_DIR, "events"))
    store = FileStore(os.path.join(BRAIN_DIR, "store"))
    llm = get_llm("worker")
    checkpointer = MemorySaver()
    print(f"LLM provider: {llm.name}")

    spec, agent, gate = build_from_spec(SPEC_DIR, llm, brain, store, checkpointer)
    bootstrap(store, spec["id"])
    print(f"Fabrica: '{spec['id']}' materializado (act_handler={spec.get('act_handler')}). "
          f"Gate -> ok={gate['ok']} problems={gate['problems']} warnings={gate['warnings']}")

    leads = [
        {"id": "L-001", "company": "Novais Digital Servicos", "revenue_brl_year": 2_500_000,
         "founder_led": True, "sells_well": True, "lacks_process": True, "firefighter": True},
        {"id": "L-002", "company": "Nano Ideia", "revenue_brl_year": 400_000,
         "founder_led": True, "lacks_process": True},
        {"id": "L-003", "company": "Madura Corp", "revenue_brl_year": 3_000_000,
         "founder_led": False, "sells_well": True, "ops_mature": True},
        {"id": "L-004", "company": "Meio Termo", "revenue_brl_year": 1_800_000,
         "founder_led": True, "firefighter": True},
    ]
    for ld in leads:
        run_lead(spec, agent, ld)

    print("\n=== Company Brain (eventos do g8-lead-qualifier) ===")
    for ev in brain.events():
        if ev.get("actor") == spec["id"]:
            o = ev.get("output") or {}
            print(f"  [{ev['ts']}] lead={o.get('lead_id')} decision={o.get('decision')} "
                  f"score={o.get('score')} delivered={ev['delivered']} billing={ev['billing_amount']} run={ev['run_id']}")

    print("\nOK - g8-lead-qualifier qualificando leads em SHADOW, ancorado no ICP "
          "(company/icp.md via load_icp). Mesmo kernel/Fabrica do g13-po-guardian.")


if __name__ == "__main__":
    main()
