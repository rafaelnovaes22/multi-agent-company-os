"""Demo da Sprint 0 — prova o loop end-to-end em SHADOW.

Roda:  python -m nucleo.demo     (a partir da pasta Multi-Agentes)
       python nucleo/demo.py

O que demonstra:
- A Fábrica materializa o g13-po-guardian a partir da spec.yaml (gate de fábrica C1/C2/C4).
- O agente roda o grafo LangGraph: load_context -> act -> self_critique -> gate -> emit_artifact -> snapshot.
- Em SHADOW o output NÃO é entregue/cobrado (delivered=False), mas é medido e registrado.
- Toda ação vira artefato no Company Brain (event store) e snapshot p/ o learning loop.
"""
from __future__ import annotations
import os
import sys
import uuid

# garante que 'nucleo' é importável ao rodar como script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langgraph.checkpoint.memory import MemorySaver  # noqa: E402

from nucleo.kernel.brain import Brain, FileStore  # noqa: E402
from nucleo.kernel.providers.llm import get_llm  # noqa: E402
from nucleo.factory.factory import build_from_spec  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
BRAIN_DIR = os.path.join(ROOT, ".brain")
SPEC_DIR = os.path.join(ROOT, "guilds", "g13_governanca", "g13-po-guardian")


def bootstrap_soul_memory(store, aid):
    """Self-harness: semeia SOUL + MEMORY na 1a vez (depois o learning loop mantém)."""
    if not store.get(("agent", aid), "soul"):
        store.put(("agent", aid), "soul", {
            "role": "PO Guardian - defensor do contrato comercial (C1/C2)",
            "principles": ["outcome-first", "bloquear cláusula vaga"],
            "avoid": ["aprovar outcome ambíguo sob pressão"],
        })
    if not store.search(("agent", aid, "memory")):
        store.put(("agent", aid, "memory"), "seed-1",
                  "§ [confidence:local] [2026-05-29] [run:seed] Cláusula sem delivered_event é a falha mais comum.")


def run_once(spec, agent, mode, target_spec):
    run_id = "run-" + uuid.uuid4().hex[:8]
    state = {
        "task": {
            "agent_id": spec["id"], "guild": spec["guild"],
            "statement": "Validar a cláusula de outcome da spec alvo",
            "target_spec": target_spec,
        },
        "mode": mode, "ledger": spec.get("ledger", "operating"),
        "run_id": run_id, "verbose": True,
    }
    print(f"\n=== RUN {run_id} | modo={mode} | alvo={target_spec.get('id')} ===")
    final = agent.invoke(state, config={"configurable": {"thread_id": run_id}})
    out = final.get("output") or {}
    v = out.get("verdict", {})
    print(f"  RESULTADO: valid={v.get('valid')} missing={v.get('missing')} "
          f"delivered={out.get('delivered')} custo_tokens={final.get('cost_tokens')}")
    return final


def main():
    brain = Brain(os.path.join(BRAIN_DIR, "events"))
    store = FileStore(os.path.join(BRAIN_DIR, "store"))
    llm = get_llm("guardian")
    checkpointer = MemorySaver()

    print(f"LLM provider: {llm.name}  (defina ANTHROPIC_API_KEY p/ LLM real)")
    spec, agent, gate = build_from_spec(SPEC_DIR, llm, brain, store, checkpointer)
    bootstrap_soul_memory(store, spec["id"])
    print(f"Fabrica: agente '{spec['id']}' materializado. "
          f"Gate de fabrica -> ok={gate['ok']} problems={gate['problems']} warnings={gate['warnings']}")

    spec_boa = {"id": "sku-exemplo-bom", "outcome_clause": {
        "statement": "Qualifica lead em <=2min com 95% de acuracia",
        "positive_examples": ["a", "b", "c"], "negative_examples": ["x", "y", "z"],
        "delivered_event": "lead.qualified == true"}}
    spec_ruim = {"id": "sku-exemplo-ruim", "outcome_clause": {
        "statement": "", "positive_examples": ["a"],
        "negative_examples": [], "delivered_event": ""}}

    run_once(spec, agent, "SHADOW", spec_boa)
    run_once(spec, agent, "SHADOW", spec_ruim)

    print("\n=== Company Brain (event store) ===")
    for ev in brain.events():
        print(f"  [{ev['ts']}] {ev['actor']} {ev['action']} "
              f"delivered={ev['delivered']} billing={ev['billing_amount']} "
              f"custo={ev['cost_tokens']} run={ev['run_id']}")

    print(f"\nEvent store : {brain.events_path}")
    print(f"Snapshots   : {os.path.join(BRAIN_DIR, 'store', 'snapshots', spec['id'])}")
    print("\nOK - loop end-to-end provado em SHADOW "
          "(load_context -> act -> self_critique -> gate -> emit_artifact -> snapshot).")
    print("Proximo: promover via gate (PILOT/ASSISTED) e plugar mais guildas na Fabrica.")


if __name__ == "__main__":
    main()
