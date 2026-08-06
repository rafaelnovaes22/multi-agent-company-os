"""Demo da FROTA INTEIRA — materializa todos os agentes descobertos, monta os
supervisores de guilda + o CEO-OS, imprime o mapa da empresa e roteia intenções
em linguagem natural ponta a ponta (CEO-OS -> supervisor de guilda -> worker).

Roda:  python -m nucleo.demo_company

É a prova do reframe "fleet único": o cliente compra a empresa-OS inteira e fala
com ela por intenção. Tudo em SHADOW (nada entregue/cobrado), offline (FakeLLM).
"""

from __future__ import annotations

import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langgraph.checkpoint.memory import MemorySaver  # noqa: E402

from nucleo.kernel.brain import Brain, FileStore  # noqa: E402
from nucleo.kernel.providers.llm import get_llm  # noqa: E402
from nucleo.kernel.registry import build_company  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
CO_DIR = os.path.join(ROOT, ".brain-company")


def main():
    brain = Brain(os.path.join(CO_DIR, "events"))
    store = FileStore(os.path.join(CO_DIR, "store"))
    llm = get_llm("root")
    cp = MemorySaver()

    root_graph, guild_sups, fleet = build_company(ROOT, llm, brain, store, cp)
    n_agents = sum(len(ws) for ws in fleet.values())
    print(f"NÚCLEO — empresa-OS | {n_agents} agentes em {len(fleet)} guildas | LLM={llm.name}\n")
    for gk in sorted(fleet):
        ids = ", ".join(spec["id"] for spec, _ in fleet[gk])
        print(f"  {gk}: {len(fleet[gk]):>2} agentes — {ids}")

    print("\nRoteando intenções pelo CEO-OS:")
    intents = [
        "Quero qualificar este lead e ver se vale prospectar",
        "Valide a cláusula de outcome desta spec",
        "Levante inteligência de mercado para um vertical",
    ]
    for it in intents:
        out = root_graph.invoke(
            {"intent": it, "payload": {}, "verbose": True},
            config={"configurable": {"thread_id": "co-" + uuid.uuid4().hex[:6]}},
        )
        res = out.get("result", {})
        ran = list((res.get("results") or {}).keys())
        print(f"    => guilda {res.get('guild')} | worker(s): {ran or '—'}\n")

    print("OK - frota materializada e roteável pelo CEO-OS (SHADOW, offline).")


if __name__ == "__main__":
    main()
