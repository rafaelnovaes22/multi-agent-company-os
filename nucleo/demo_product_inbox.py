"""Demo do PRODUTO — agente inbox-triage multi-tenant.

Roda:  python -m nucleo.demo_product_inbox

Dois clientes de segmentos diferentes, MESMO agente: cada caixa de entrada é
triada com o contexto do tenant. Depois roda a eval-suite.
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
from nucleo.quality.eval_harness import run_evals  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
BRAIN = os.path.join(ROOT, ".brain-product")
SPEC = os.path.join(ROOT, "product", "inbox-triage")

TENANTS = {
    "novais-digital-limpeza": {"name": "Novais Digital Limpeza", "segment": "serviços de limpeza B2B", "currency": "BRL"},
    "bella-padaria": {"name": "Bella Padaria", "segment": "padaria / varejo alimentício", "currency": "BRL"},
}
INBOX = {
    "novais-digital-limpeza": [
        {"id": 1, "from": "Cond. Atlas", "text": "Quero um orçamento para limpeza mensal"},
        {"id": 2, "from": "Financeiro Y", "text": "Boleto da última nota está em atraso"},
        {"id": 3, "from": "Cliente X", "text": "URGENTE: faltou equipe hoje, serviço parado"},
        {"id": 4, "from": "Fornecedor", "text": "Quando chega o pedido do fornecedor de material?"},
    ],
    "bella-padaria": [
        {"id": 1, "from": "Mercado A", "text": "Preciso de uma proposta de fornecimento de pães"},
        {"id": 2, "from": "Cliente", "text": "O pedido veio com problema, quero reembolso"},
        {"id": 3, "from": "Contador", "text": "Manda a nota fiscal de ontem"},
    ],
}


def run_tenant(agent, spec, tid):
    rid = "run-" + uuid.uuid4().hex[:8]
    state = {"task": {"agent_id": spec["id"], "guild": spec["guild"], "tenant_id": tid,
                      "statement": "Triagem da caixa de entrada", "inbox": {"messages": INBOX[tid]}},
             "mode": "SHADOW", "ledger": spec.get("ledger"), "run_id": rid, "verbose": True}
    print(f"\n=== {TENANTS[tid]['name']} ({TENANTS[tid]['segment']}) ===")
    o = agent.invoke(state, config={"configurable": {"thread_id": rid}}).get("output") or {}
    print(f"  {o.get('total')} mensagens | urgentes: {o.get('urgent_count')} | por categoria: {o.get('counts_by_category')}")
    for x in o.get("triaged", []):
        u = " [URGENTE]" if x["urgency"] == "alta" else ""
        print(f"     #{x['id']} {x['category']:<11} -> {x['route']}{u}")


def main():
    brain = Brain(os.path.join(BRAIN, "events"))
    store = FileStore(os.path.join(BRAIN, "store"))
    llm = get_llm("worker")
    cp = MemorySaver()
    for tid, prof in TENANTS.items():
        store.put(("tenant", tid), "profile", prof)

    spec, agent, gate = build_from_spec(SPEC, llm, brain, store, cp)
    print(f"Produto: '{spec['id']}' (fleet={spec.get('fleet')}, multi_tenant={spec.get('multi_tenant')}) | gate ok={gate['ok']}")

    run_tenant(agent, spec, "novais-digital-limpeza")
    run_tenant(agent, spec, "bella-padaria")

    print("\n=== eval-harness (C4) do inbox-triage ===")
    rep = run_evals(SPEC, llm, brain, store, cp)
    print(f"  {rep['id']}: {rep['passed']}/{rep['total']} ({rep['rate']*100:.0f}%)")
    print("\nOK - 2o agente de produto (inbox-triage) vivo, multi-tenant, agnóstico de segmento.")


if __name__ == "__main__":
    main()
