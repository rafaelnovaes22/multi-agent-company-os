"""Demo do ONBOARDING — o fluxo que se mostra ao cliente/CEO.

Roda:  python -m nucleo.demo_onboarding

Um cliente novo (qualquer segmento) entra: diagnóstico -> ativa o fleet de produto
recomendado em SHADOW -> painel do dono. Depois, eval-harness de todo o fleet de produto.
"""
from __future__ import annotations
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langgraph.checkpoint.memory import MemorySaver  # noqa: E402

from nucleo.kernel.brain import Brain, FileStore  # noqa: E402
from nucleo.kernel.providers.llm import get_llm  # noqa: E402
from nucleo.product.onboarding import onboard  # noqa: E402
from nucleo.quality.eval_harness import run_evals  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
BRAIN = os.path.join(ROOT, ".brain-onboarding")

PROFILE = {"name": "Loja do Zé", "segment": "comércio local (qualquer segmento)", "currency": "BRL"}
SIGNALS = {"id": "loja-do-ze", "revenue_brl_year": 2_500_000, "founder_led": True, "sells_well": True,
           "lacks_process": True, "firefighter": True, "monthly_volume": 120, "hours_per_unit": 0.5,
           "hourly_cost_brl": 55, "process": "atendimento e entregas"}
DATA = {
    "fin-caixa": {"today": "2026-05-29", "balance": 9000,
                  "receivables": [{"customer": "Cliente A", "amount": 5000, "due_date": "2026-05-18", "status": "open"}],
                  "payables": [{"supplier": "Distribuidora", "amount": 16000, "due_date": "2026-06-03"}],
                  "revenue_month": 45000, "cost_month": 41000},
    "inbox-triage": {"messages": [{"id": 1, "text": "Quero um orçamento"},
                                  {"id": 2, "text": "Boleto em atraso, segue"},
                                  {"id": 3, "text": "URGENTE: pedido parado"}]},
    "ops-followup": {"today": "2026-05-29", "tasks": [
        {"title": "Entregar pedido 32", "status": "parado", "owner": "ze"},
        {"title": "Renovar alvará", "status": "open", "due_date": "2026-05-10", "owner": ""},
        {"title": "Pagar fornecedor", "status": "done", "owner": "ze"}]},
    "atendimento": {"requests": [{"customer": "A", "type": "orçamento", "waiting_hours": 30},
                                 {"customer": "B", "type": "dúvida", "waiting_hours": 10}]},
}


def main():
    brain = Brain(os.path.join(BRAIN, "events"))
    store = FileStore(os.path.join(BRAIN, "store"))
    llm = get_llm("worker")
    cp = MemorySaver()

    print(f"ONBOARDING — {PROFILE['name']} ({PROFILE['segment']})\n")
    res = onboard("loja-do-ze", PROFILE, SIGNALS, DATA, llm, brain, store, cp)

    d = res["diagnosis"]
    print(f"1) Diagnóstico (venda): recomendação = {d['recommendation']}")
    print("   agentes recomendados: " + ", ".join(f"{a['id']}({a['status']})" for a in d["recommended"]))
    print(f"\n2) Ativados em SHADOW na conta do cliente: {res['activated']}")
    r = res["results"]
    if "fin-caixa" in r:
        print(f"   - fin-caixa: caixa proj. R$ {r['fin-caixa'].get('projected_cash')}, vencidos R$ {r['fin-caixa'].get('total_overdue')}")
    if "inbox-triage" in r:
        print(f"   - inbox-triage: {r['inbox-triage'].get('total')} msgs, {r['inbox-triage'].get('urgent_count')} urgente(s)")
    if "ops-followup" in r:
        print(f"   - ops-followup: {r['ops-followup'].get('stalled_count')} paradas, {r['ops-followup'].get('no_owner_count')} sem dono")
    if "atendimento" in r:
        print(f"   - atendimento: fila {r['atendimento'].get('reply_queue_count')}, atrasadas {r['atendimento'].get('overdue_replies')}")
    if "painel-dono" in r:
        p = r["painel-dono"]
        print(f"\n3) Painel do dono: SEMÁFORO = {p.get('semaforo').upper()} | {p.get('resumo')}")
        for a in p.get("top_alerts", []):
            print(f"      ! {a}")

    print("\n=== eval-harness (C4) do fleet de produto ===")
    for sd in sorted(os.path.dirname(p) for p in glob.glob(os.path.join(ROOT, "product", "**", "spec.yaml"), recursive=True)):
        rep = run_evals(sd, llm, brain, store, cp)
        print(f"   {rep['id']:<16} {rep['passed']}/{rep['total']} ({rep['rate']*100:.0f}%)")

    print("\nOK - venda -> ativação do fleet em SHADOW -> painel do dono, multi-tenant e agnóstico de segmento.")


if __name__ == "__main__":
    main()
