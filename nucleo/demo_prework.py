"""Demo do PRÉ-WORK do workshop (dogfooding) — agora com FIRMOGRAPHICS REAIS de SP.

Roda:  python -m nucleo.demo_prework

Para cada vertical candidato: g1-market-intel aplica os hard-filters (F1/F2/F4);
se passar, g1-opportunity-sizer estima o tamanho. Ranqueia por ICP-pool (densidade).

DADOS:
- ICP-pool = nº de empresas em SP na faixa 5–49 empregados (proxy de porte do ICP
  R$1–20M "vende bem, tem equipe"). FONTE REAL: IBGE/CEMPRE tabela 7528, UF=SP, 2023.
- pain = 4/5 (dor de processo confirmada e TRANSVERSAL — pesquisa SP rodada 1).
- regulatory_risk e tier2 vêm da pesquisa (advocacia: cold outreach vedado pela OAB
  -> tier2 vazio -> reprovado em F4; saúde: CFM -> risco 4).
- avg_ticket_brl_year = ASSUNÇÃO ilustrativa (R$12k) — WTP real foi REFUTADO na pesquisa.
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

ROOT = os.path.dirname(os.path.abspath(__file__))
BRAIN_DIR = os.path.join(ROOT, ".brain")
MI_SPEC = os.path.join(ROOT, "guilds", "g01_estrategia", "g1-market-intel")
OS_SPEC = os.path.join(ROOT, "guilds", "g01_estrategia", "g1-opportunity-sizer")

# pool = empresas SP 5–49 empregados (IBGE/CEMPRE 7528, 2023). founder_led_share=1.0 (pool já é proxy do ICP).
TICKET = 12_000  # ASSUNÇÃO ilustrativa (WTP real sem fonte confiável)
def cand(v, pool, tier2, reg, cnae):
    return {"vertical": v, "est_companies_brazil": pool, "founder_led_share": 1.0,
            "process_pain_evidence": 4, "tier2_sources": tier2, "regulatory_risk": reg,
            "reachable_share": 0.3, "conversion": 0.05, "avg_ticket_brl_year": TICKET, "cnae": cnae}

CANDIDATOS = [
    cand("Varejo (47, e-comm subset)", 103_510, ["JUCESP", "ABComm"], 1, "47*"),
    cand("Indústria leve (C, ampla)", 49_872, ["JUCESP", "sindicatos"], 1, "C*"),
    cand("Prestadores B2B (limpeza+admin)", 33_415, ["JUCESP"], 1, "81+82"),
    cand("Food service", 31_998, ["JUCESP", "ABRASEL"], 1, "56"),
    cand("Construção/reforma", 20_631, ["JUCESP"], 2, "41+43"),
    cand("Distribuição/atacado", 19_633, ["JUCESP"], 1, "46"),
    cand("Clínicas/saúde", 15_838, ["JUCESP", "CRM-SP"], 4, "86"),
    cand("Educação", 14_272, ["JUCESP"], 2, "85"),
    cand("Contabilidade", 7_409, ["JUCESP", "CRC-SP"], 1, "69.2"),
    cand("Software houses/TI", 4_322, ["JUCESP", "ABES"], 1, "62"),
    cand("Arquitetura/engenharia", 3_681, ["JUCESP", "CREA/CAU"], 2, "71"),
    cand("Advocacia", 2_717, [], 5, "69.1"),          # tier2 vazio: OAB veda cold outreach -> F4 falha
    cand("Agências de marketing", 2_057, ["JUCESP"], 1, "73"),
]


def _run(agent, spec, candidate):
    rid = "pw-" + uuid.uuid4().hex[:8]
    st = {"task": {"agent_id": spec["id"], "guild": spec["guild"], "statement": "Pré-work", "candidate": candidate},
          "mode": "SHADOW", "ledger": spec.get("ledger"), "run_id": rid, "verbose": False}
    return agent.invoke(st, config={"configurable": {"thread_id": rid}}).get("output") or {}


def main():
    brain = Brain(os.path.join(BRAIN_DIR, "events"))
    store = FileStore(os.path.join(BRAIN_DIR, "store"))
    llm = get_llm("worker")
    cp = MemorySaver()
    spec_mi, market_intel, _ = build_from_spec(MI_SPEC, llm, brain, store, cp)
    spec_os, sizer, _ = build_from_spec(OS_SPEC, llm, brain, store, cp)
    print(f"Pré-work (dogfooding) | {spec_mi['id']} + {spec_os['id']} | LLM={llm.name}")
    print("Firmographics REAIS: IBGE/CEMPRE tab.7528, SP, 2023, faixa 5-49 empregados (proxy do ICP).")
    print("Ticket = ASSUNCAO ilustrativa (R$12k/ano) — WTP real sem fonte confiavel.\n")

    rows = []
    for c in CANDIDATOS:
        intel = _run(market_intel, spec_mi, c)
        som = None
        if intel.get("passes_hard_filters"):
            som = _run(sizer, spec_os, {**c, "icp_pool_estimate": intel.get("icp_pool_estimate")}).get("som_brl")
        rows.append((c["vertical"], c["cnae"], intel.get("icp_pool_estimate"),
                     c["regulatory_risk"], intel.get("passes_hard_filters"), som))

    rows.sort(key=lambda r: -(r[2] or 0))
    print(f"{'Vertical':<33}{'CNAE':>7}{'ICP(5-49)':>11}{'reg':>4}{'F1/2/4':>8}")
    print("-" * 64)
    for v, cnae, pool, reg, passa, som in rows:
        flag = "OK" if passa else "CORTE"
        print(f"{v:<33}{cnae:>7}{pool:>11,}{reg:>4}{flag:>8}")
    aprov = [r for r in rows if r[4]]
    print(f"\nPassaram hard-filters (F1/F2/F4): {len(aprov)}/{len(rows)}")
    print("Cortados:", ", ".join(f"{r[0]} ({'OAB veda outreach' if r[1]=='69.1' else 'sem Tier2'})" for r in rows if not r[4]) or "nenhum")
    print("\nTop densidade (ICP-proxy) + regulatório favorável (reg<=2):")
    for v, cnae, pool, reg, passa, som in [r for r in rows if r[4] and r[3] <= 2][:6]:
        print(f"   - {v} (CNAE {cnae}): {pool:,} empresas 5-49")
    print("\nNOTA: densidade é REAL; ticket/WTP e fit-agêntico ainda vão à matriz do workshop.")
    print("Varejo(47) e Indústria(C) são supersets amplos — e-commerce/'leve' não isolados no nível de divisão.")


if __name__ == "__main__":
    main()
