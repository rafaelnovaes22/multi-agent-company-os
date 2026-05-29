"""Demo do Supervisor-raiz (CEO-OS) — roteia intenção -> guilda/funil (YC#5).

Roda:  python -m nucleo.demo_root

O root classifica a intenção em linguagem natural e despacha para a guilda certa:
receita -> funil G08xG02; diagnóstico -> g2-diagnose; governança -> g13-po-guardian;
mercado -> g1-market-intel. Sem middleware humano: o "gerente" é um agente.
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
from nucleo.kernel.supervisor import build_revenue_funnel, build_root_supervisor  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
BRAIN = os.path.join(ROOT, ".brain-root")
G = os.path.join(ROOT, "guilds")


def _task(spec, **kw):
    return {"task": {"agent_id": spec["id"], "guild": spec["guild"], "statement": "root", **kw},
            "mode": "SHADOW", "ledger": spec.get("ledger"), "run_id": "r-" + uuid.uuid4().hex[:6], "verbose": False}


def main():
    brain = Brain(os.path.join(BRAIN, "events"))
    store = FileStore(os.path.join(BRAIN, "store"))
    llm = get_llm("worker")
    cp = MemorySaver()

    sq, qual, _ = build_from_spec(os.path.join(G, "g08_vendas", "g8-lead-qualifier"), llm, brain, store, cp)
    so, outb, _ = build_from_spec(os.path.join(G, "g08_vendas", "g8-outbound-sdr"), llm, brain, store, cp)
    sd, diag, _ = build_from_spec(os.path.join(G, "g02_produto", "g2-diagnose"), llm, brain, store, cp)
    sp, pog, _ = build_from_spec(os.path.join(G, "g13_governanca", "g13-po-guardian"), llm, brain, store, cp)
    sm, mkt, _ = build_from_spec(os.path.join(G, "g01_estrategia", "g1-market-intel"), llm, brain, store, cp)
    funnel = build_revenue_funnel(qual, diag, outb, sq, sd, so, cp)

    def r_revenue(p):
        out = funnel.invoke({"entity": p, "mode": "SHADOW"}, config={"configurable": {"thread_id": "f-" + uuid.uuid4().hex[:6]}})
        q = out.get("qualification") or {}
        return {"qualify": q.get("decision"), "outreach": "sim" if out.get("outreach") else "não"}

    def r_diagnose(p):
        o = diag.invoke(_task(sd, client=p), config={"configurable": {"thread_id": _task(sd)["run_id"]}}).get("output") or {}
        return {"recommendation": o.get("recommendation"), "baseline": (o.get("baseline") or {}).get("baseline_cost_brl_month")}

    def r_governance(p):
        o = pog.invoke(_task(sp, target_spec=p), config={"configurable": {"thread_id": _task(sp)["run_id"]}}).get("output") or {}
        return {"outcome_valid": (o.get("verdict") or {}).get("valid")}

    def r_market(p):
        o = mkt.invoke(_task(sm, candidate=p), config={"configurable": {"thread_id": _task(sm)["run_id"]}}).get("output") or {}
        return {"passes_hard_filters": o.get("passes_hard_filters"), "icp_pool": o.get("icp_pool_estimate")}

    root = build_root_supervisor({"revenue": r_revenue, "diagnose": r_diagnose,
                                  "governance": r_governance, "market": r_market}, cp)

    pedidos = [
        ("Qualifica e prospecta este lead", {"id": "L-9", "company": "Z", "revenue_brl_year": 2_500_000, "founder_led": True, "sells_well": True, "lacks_process": True, "firefighter": True, "monthly_volume": 100, "hours_per_unit": 0.5, "hourly_cost_brl": 60, "process": "ordens de serviço"}),
        ("Diagnostica a operação deste cliente", {"id": "C-9", "revenue_brl_year": 2_000_000, "founder_led": True, "lacks_process": True, "monthly_volume": 150, "hours_per_unit": 0.4, "hourly_cost_brl": 55, "process": "agendamento de equipes"}),
        ("Valida a cláusula de outcome desta spec", {"id": "sku-x", "outcome_clause": {"statement": "Faz X", "positive_examples": ["a", "b", "c"], "negative_examples": ["x", "y", "z"], "delivered_event": "x.done==true"}}),
        ("Levanta inteligência de mercado deste vertical", {"vertical": "Exemplo", "est_companies_brazil": 60000, "founder_led_share": 0.6, "process_pain_evidence": 4, "tier2_sources": ["JUCESP"], "regulatory_risk": 1}),
        ("Faz o café", {}),
    ]
    for intent, payload in pedidos:
        out = root.invoke({"intent": intent, "payload": payload, "verbose": True},
                          config={"configurable": {"thread_id": "root-" + uuid.uuid4().hex[:6]}})
        print(f"      resultado: {out.get('result')}\n")

    print("OK - supervisor-raiz roteia intenção -> guilda (YC#5: sem middleware humano).")


if __name__ == "__main__":
    main()
