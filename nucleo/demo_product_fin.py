"""Demo do PRODUTO — agente fin-caixa multi-tenant.

Roda:  python -m nucleo.demo_product_fin

Prova o coração do produto: DOIS clientes de SEGMENTOS DIFERENTES (limpeza B2B e
padaria) usam o MESMO agente fin-caixa, cada um com seu contexto/memória (tenant),
recebendo respostas específicas da empresa dele — em SHADOW. Depois roda a eval-suite.
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
from nucleo.quality.eval_harness import run_evals  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
BRAIN = os.path.join(ROOT, ".brain-product")
SPEC = os.path.join(ROOT, "product", "fin-caixa")

TENANTS = {
    "novais-digital-limpeza": {
        "name": "Novais Digital Limpeza",
        "segment": "serviços de limpeza B2B",
        "currency": "BRL",
    },
    "bella-padaria": {
        "name": "Bella Padaria",
        "segment": "padaria / varejo alimentício",
        "currency": "BRL",
    },
}
FINANCE = {
    "novais-digital-limpeza": {
        "today": "2026-05-29",
        "balance": 18000,
        "receivables": [
            {"customer": "Cond. Atlas", "amount": 6000, "due_date": "2026-05-20", "status": "open"},
            {"customer": "Empresa Y", "amount": 3000, "due_date": "2026-06-10", "status": "open"},
        ],
        "payables": [{"supplier": "Insumos Z", "amount": 9000, "due_date": "2026-06-02"}],
        "revenue_month": 60000,
        "cost_month": 52000,
    },
    "bella-padaria": {
        "today": "2026-05-29",
        "balance": 4000,
        "receivables": [
            {"customer": "Mercado A", "amount": 2000, "due_date": "2026-05-15", "status": "open"}
        ],
        "payables": [{"supplier": "Farinha BR", "amount": 8000, "due_date": "2026-06-01"}],
        "revenue_month": 40000,
        "cost_month": 37000,
    },
}


def run_tenant(agent, spec, tid):
    rid = "run-" + uuid.uuid4().hex[:8]
    state = {
        "task": {
            "agent_id": spec["id"],
            "guild": spec["guild"],
            "tenant_id": tid,
            "statement": "Gestão de caixa",
            "finance": FINANCE[tid],
        },
        "mode": "SHADOW",
        "ledger": spec.get("ledger"),
        "run_id": rid,
        "verbose": True,
    }
    print(f"\n=== {TENANTS[tid]['name']} ({TENANTS[tid]['segment']}) | tenant={tid} ===")
    o = agent.invoke(state, config={"configurable": {"thread_id": rid}}).get("output") or {}
    print(
        f"  caixa atual: R$ {o.get('cash_position'):,} | projetado: R$ {o.get('projected_cash'):,} | "
        f"vencidos: R$ {o.get('total_overdue'):,} ({o.get('overdue_count')}) | margem: {o.get('margin_pct')}%"
    )
    print("  ações recomendadas:")
    for a in o.get("recommended_actions", []):
        print(f"     - {a}")
    if not o.get("recommended_actions"):
        print("     (nenhuma — caixa saudável)")


def main():
    brain = Brain(os.path.join(BRAIN, "events"))
    store = FileStore(os.path.join(BRAIN, "store"))
    llm = get_llm("worker")
    cp = MemorySaver()

    for tid, prof in TENANTS.items():
        store.put(("tenant", tid), "profile", prof)  # onboarding do cliente (config, C8)

    spec, agent, gate = build_from_spec(SPEC, llm, brain, store, cp)
    print(
        f"Produto: agente '{spec['id']}' (fleet={spec.get('fleet')}, multi_tenant={spec.get('multi_tenant')}) "
        f"| gate fábrica ok={gate['ok']}"
    )

    run_tenant(agent, spec, "novais-digital-limpeza")
    run_tenant(agent, spec, "bella-padaria")

    print("\n=== Isolamento multi-tenant ===")
    print("Tenants com dados no store:", store.subdirs(("tenant",)))
    print(
        "Snapshots Novais Digital:",
        store.subdirs(("tenant", "novais-digital-limpeza", "snapshots")),
    )
    print("Snapshots Bella:", store.subdirs(("tenant", "bella-padaria", "snapshots")))

    print("\n=== eval-harness (C4) do fin-caixa ===")
    rep = run_evals(SPEC, llm, brain, store, cp)
    print(f"  {rep['id']}: {rep['passed']}/{rep['total']} ({rep['rate']*100:.0f}%)")

    print(
        "\nOK - MESMO agente, DOIS segmentos diferentes, contexto/memória por tenant (C5/C8), "
        "em SHADOW. É o produto multi-tenant agnóstico de segmento."
    )


if __name__ == "__main__":
    main()
