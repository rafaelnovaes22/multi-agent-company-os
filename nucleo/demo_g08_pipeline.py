"""Demo do supervisor da G08 — encadeia lead-qualifier -> (se qualified) outbound-sdr.

Roda:  python -m nucleo.demo_g08_pipeline

Mostra a hierarquia: um supervisor de guilda (agente) roteia o trabalho entre
workers. Lead qualificado segue para o outbound; lead desqualificado para no
qualificador. É o padrão que escala para as 14 guildas / 169 agentes.
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
from nucleo.kernel.supervisor import build_g08_supervisor  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
BRAIN_DIR = os.path.join(ROOT, ".brain")
Q_SPEC = os.path.join(ROOT, "guilds", "g08_vendas", "g8-lead-qualifier")
O_SPEC = os.path.join(ROOT, "guilds", "g08_vendas", "g8-outbound-sdr")


def run_pipeline(sup, lead):
    rid = "sup-" + uuid.uuid4().hex[:8]
    print(f"\n=== Pipeline G08 | {lead['id']} ({lead.get('company')}) ===")
    final = sup.invoke(
        {"lead": lead, "mode": "SHADOW", "verbose": True},
        config={"configurable": {"thread_id": rid}},
    )
    q = final.get("qualification") or {}
    o = final.get("outreach")
    print(
        f"  RESUMO: qualificação={q.get('decision')} (score {q.get('score')}); "
        f"outreach={'gerado (' + str(len(o.get('sequence', []))) + ' toques)' if o else 'não disparado'}"
    )


def main():
    brain = Brain(os.path.join(BRAIN_DIR, "events"))
    store = FileStore(os.path.join(BRAIN_DIR, "store"))
    llm = get_llm("worker")
    cp = MemorySaver()

    spec_q, qualifier, _ = build_from_spec(Q_SPEC, llm, brain, store, cp)
    spec_o, outbound, _ = build_from_spec(O_SPEC, llm, brain, store, cp)
    sup = build_g08_supervisor(qualifier, outbound, spec_q, spec_o, cp)
    print(f"Supervisor G08 montado: {spec_q['id']} -> (se qualified) -> {spec_o['id']}")

    # Lead qualificado: qualifica e segue para outbound.
    run_pipeline(
        sup,
        {
            "id": "L-201",
            "company": "Caos Ltda",
            "revenue_brl_year": 2_500_000,
            "founder_led": True,
            "sells_well": True,
            "lacks_process": True,
            "firefighter": True,
        },
    )
    # Lead desqualificado: para no qualificador.
    run_pipeline(
        sup,
        {
            "id": "L-202",
            "company": "Pequena Demais",
            "revenue_brl_year": 300_000,
            "founder_led": True,
        },
    )

    print(
        "\nOK - supervisor de guilda roteando workers (sem middleware humano, YC#5). "
        "Mesmo padrão escala para as 14 guildas."
    )


if __name__ == "__main__":
    main()
