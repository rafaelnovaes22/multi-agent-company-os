"""Demo do gate ASSISTED — human-in-the-loop real via interrupt() do LangGraph.

Roda:  python -m nucleo.demo_assisted

Mostra o g8-lead-qualifier em modo ASSISTED: ao chegar no gate, o grafo PAUSA
(interrupt) e pede aprovação do DRI. Resumimos com Command(resume=...) em dois
cenários — APROVAR (entrega) e REJEITAR (descarta). É o controle humano dos C4.
"""
from __future__ import annotations
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langgraph.checkpoint.memory import MemorySaver  # noqa: E402
from langgraph.types import Command  # noqa: E402

from nucleo.kernel.brain import Brain, FileStore  # noqa: E402
from nucleo.kernel.providers.llm import get_llm  # noqa: E402
from nucleo.factory.factory import build_from_spec  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
BRAIN_DIR = os.path.join(ROOT, ".brain")
SPEC_DIR = os.path.join(ROOT, "guilds", "g08_vendas", "g8-lead-qualifier")


def run_assisted(agent, spec, lead, approve):
    rid = "run-" + uuid.uuid4().hex[:8]
    cfg = {"configurable": {"thread_id": rid}}
    state = {
        "task": {"agent_id": spec["id"], "guild": spec["guild"],
                 "statement": "Qualificar lead", "lead": lead},
        "mode": "ASSISTED", "ledger": spec.get("ledger"), "run_id": rid, "verbose": True,
    }
    print(f"\n=== {lead['id']} | modo=ASSISTED | decisão do DRI = {'APROVAR' if approve else 'REJEITAR'} ===")
    res = agent.invoke(state, config=cfg)

    intr = res.get("__interrupt__")
    if intr:
        payload = intr[0].value
        prop = payload.get("proposed_output") or {}
        print(f"  PAUSA (interrupt): aprovação humana necessária p/ {payload.get('agent')} "
              f"-> proposta decision={prop.get('decision')} score={prop.get('score')}")
        res = agent.invoke(Command(resume={"approved": approve}), config=cfg)

    out = res.get("output")
    print(f"  -> resultado: output {'ENTREGUE' if out else 'DESCARTADO'} "
          f"(delivered={(out or {}).get('delivered')})")


def main():
    brain = Brain(os.path.join(BRAIN_DIR, "events"))
    store = FileStore(os.path.join(BRAIN_DIR, "store"))
    llm = get_llm("worker")
    spec, agent, _ = build_from_spec(SPEC_DIR, llm, brain, store, MemorySaver())
    print(f"LLM provider: {llm.name} | agente: {spec['id']} em ASSISTED")

    lead = {"id": "L-700", "company": "Decisao Humana", "revenue_brl_year": 2_500_000,
            "founder_led": True, "sells_well": True, "lacks_process": True, "firefighter": True}

    run_assisted(agent, spec, lead, approve=True)    # DRI aprova -> entrega
    run_assisted(agent, spec, lead, approve=False)   # DRI rejeita -> descarta

    print("\nOK - human-in-the-loop via interrupt(): o agente PROPÕE, o DRI decide. "
          "É assim que um agente sai de SHADOW e ganha autonomia gradual (C4).")


if __name__ == "__main__":
    main()
