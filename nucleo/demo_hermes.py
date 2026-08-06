"""Demo do Hermes Learning Loop — fecha o ciclo "evoluir aprendendo".

Pré-requisito: rode antes `python -m nucleo.demo` e `python -m nucleo.demo_g8`
(eles geram os snapshots que o Hermes vai processar).

Roda:  python -m nucleo.demo_hermes

Mostra: memória ANTES -> roda o Hermes (extrai fatos dos snapshots) -> memória
DEPOIS -> re-executa o g8-lead-qualifier para provar que ele agora CARREGA os
fatos aprendidos (load_context: memory>0). Loop fechado.
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
from nucleo.learning.hermes import run_hermes  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
BRAIN_DIR = os.path.join(ROOT, ".brain")
G8_SPEC = os.path.join(ROOT, "guilds", "g08_vendas", "g8-lead-qualifier")


def mem_counts(store):
    return {
        aid: len(store.search(("agent", aid, "memory"))) for aid in store.subdirs(("snapshots",))
    }


def main():
    brain = Brain(os.path.join(BRAIN_DIR, "events"))
    store = FileStore(os.path.join(BRAIN_DIR, "store"))

    if not store.subdirs(("snapshots",)):
        print("Sem snapshots. Rode antes: python -m nucleo.demo  e  python -m nucleo.demo_g8")
        return

    print("Memória ANTES:", mem_counts(store))

    print("\n=== Hermes Learning Loop (lê snapshots -> extrai instincts -> propõe memória) ===")
    summary = run_hermes(store, brain, verbose=True)
    print(
        f"\nResumo: {summary['processed_snapshots']} snapshots processados, "
        f"{summary['total_proposed']} fato(s) de memória propostos."
    )
    print("Memória DEPOIS:", mem_counts(store))

    # Fecha o loop: na próxima execução o agente já carrega o que aprendeu.
    print("\n=== Loop fechado: re-execução do g8-lead-qualifier ===")
    llm = get_llm("worker")
    spec, agent, _ = build_from_spec(G8_SPEC, llm, brain, store, MemorySaver())
    rid = "run-" + uuid.uuid4().hex[:8]
    state = {
        "task": {
            "agent_id": spec["id"],
            "guild": spec["guild"],
            "statement": "Qualificar lead contra o ICP",
            "lead": {
                "id": "L-009",
                "company": "Novo Lead",
                "revenue_brl_year": 2_000_000,
                "founder_led": True,
                "lacks_process": True,
            },
        },
        "mode": "SHADOW",
        "ledger": "billable",
        "run_id": rid,
        "verbose": True,
    }
    agent.invoke(state, config={"configurable": {"thread_id": rid}})
    print(
        "\nOK - o agente carrega os fatos aprendidos (memory>0 acima). "
        "Snapshot -> Hermes -> memória -> próxima run: evoluir aprendendo (closed loop)."
    )


if __name__ == "__main__":
    main()
