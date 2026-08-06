"""Demo do FUNIL DE RECEITA — orquestração cross-guild (G08 x G02).

Roda:  python -m nucleo.demo_funnel

Encadeia: g8-lead-qualifier -> (qualified) -> g2-diagnose -> (go) -> g8-outbound-sdr.
Cada etapa tem um gate; o lead que reprova para ali. É o caminho da receita ponta
a ponta, ainda em SHADOW (nada entregue/cobrado).
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
from nucleo.kernel.supervisor import build_revenue_funnel  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
BRAIN_DIR = os.path.join(ROOT, ".brain")
Q_SPEC = os.path.join(ROOT, "guilds", "g08_vendas", "g8-lead-qualifier")
D_SPEC = os.path.join(ROOT, "guilds", "g02_produto", "g2-diagnose")
O_SPEC = os.path.join(ROOT, "guilds", "g08_vendas", "g8-outbound-sdr")


def run_funnel(funnel, entity):
    rid = "fn-" + uuid.uuid4().hex[:8]
    print(f"\n=== Funil | {entity['id']} ({entity.get('company')}) ===")
    final = funnel.invoke(
        {"entity": entity, "mode": "SHADOW", "verbose": True},
        config={"configurable": {"thread_id": rid}},
    )
    q = final.get("qualification") or {}
    d = final.get("diagnostic") or {}
    o = final.get("outreach")
    onde = (
        "outreach disparado"
        if o
        else (
            "parou no diagnóstico" if q.get("decision") == "qualified" else "parou na qualificação"
        )
    )
    print(
        f"  RESUMO: qualify={q.get('decision')} | diagnose={d.get('recommendation', '—')} | "
        f"prospect={'sim' if o else 'não'} -> {onde}"
    )


def main():
    brain = Brain(os.path.join(BRAIN_DIR, "events"))
    store = FileStore(os.path.join(BRAIN_DIR, "store"))
    llm = get_llm("worker")
    cp = MemorySaver()

    spec_q, qualifier, _ = build_from_spec(Q_SPEC, llm, brain, store, cp)
    spec_d, diagnoser, _ = build_from_spec(D_SPEC, llm, brain, store, cp)
    spec_o, outbound, _ = build_from_spec(O_SPEC, llm, brain, store, cp)
    funnel = build_revenue_funnel(qualifier, diagnoser, outbound, spec_q, spec_d, spec_o, cp)
    print(
        "Funil montado: g8-lead-qualifier -> (qualified) -> g2-diagnose -> (go) -> g8-outbound-sdr"
    )

    entities = [
        # qualifica + diagnóstico go -> percorre o funil inteiro
        {
            "id": "E-001",
            "company": "Caos Servicos",
            "revenue_brl_year": 2_500_000,
            "founder_led": True,
            "sells_well": True,
            "lacks_process": True,
            "firefighter": True,
            "monthly_volume": 200,
            "hours_per_unit": 0.5,
            "hourly_cost_brl": 60,
            "process": "triagem de pedidos",
        },
        # fora do ICP -> para na qualificação
        {
            "id": "E-002",
            "company": "Pequena Demais",
            "revenue_brl_year": 300_000,
            "founder_led": True,
        },
        # qualifica, mas sem baseline -> para no diagnóstico (no-go)
        {
            "id": "E-003",
            "company": "Fit Sem Volume",
            "revenue_brl_year": 2_000_000,
            "founder_led": True,
            "lacks_process": True,
        },
    ]
    for e in entities:
        run_funnel(funnel, e)

    print(
        "\nOK - funil de receita cross-guild com gate em cada etapa (qualify -> diagnose -> prospect), "
        "em SHADOW. É o mesmo padrão do supervisor-raiz roteando as 14 guildas."
    )


if __name__ == "__main__":
    main()
