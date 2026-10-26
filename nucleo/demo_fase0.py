"""Demo da FROTA INTERNA NOVAIS (Fase 0 do PLANO-TIMES-AGENTES-NOVAIS).

Materializa os 5 agentes (fila, ponte, turno, ciclo, prefeito) de
nucleo/company/fleet/, roda uma rodada do dia em SHADOW com o painel do
Prefeito (10 números com fonte) e por fim roda a eval-suite de cada um.

Roda:  python -m nucleo.demo_fase0

Offline por padrão (FakeLLM — custo zero, determinístico). Nada é entregue nem
cobrado: toda a frota nasce e opera em SHADOW (C4) até passar dos gates.
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
FLEET_DIR = os.path.join(ROOT, "company", "fleet")
BRAIN_DIR = os.path.join(ROOT, ".brain-fase0")

FLEET = ["fila", "ponte", "turno", "ciclo", "prefeito"]

# Um dia plausível na Novais (dados de exemplo; em produção vêm das fontes vivas)
DIA = {
    "fila": {
        "task": {
            "now": "2026-10-26T09:00",
            "inbound": [
                {"id": "w1", "channel": "whatsapp", "subject": "quer site 48h",
                 "arrived_at": "2026-10-26T08:20", "sla_min": 15, "status": "waiting"},
                {"id": "w2", "channel": "formulario", "subject": "diagnostico relampago",
                 "arrived_at": "2026-10-26T08:52", "sla_min": 15, "status": "waiting"},
                {"id": "w3", "channel": "instagram", "subject": "duvida curso",
                 "arrived_at": "2026-10-26T08:30", "sla_min": 15, "status": "answered"},
            ],
        }
    },
    "ponte": {
        "task": {
            "channels": [
                {"name": "bot-whatsapp", "status_code": 200, "latency_ms": 850},
                {"name": "form-site", "status_code": 200, "latency_ms": 2400},
                {"name": "webhook-canal", "status_code": 200, "latency_ms": 300},
            ]
        }
    },
    "turno": {
        "task": {
            "projects": [
                {"name": "novais-digital", "deploy_status": "READY", "repo_ok": True},
                {"name": "geraboleto", "deploy_status": "READY", "repo_ok": True},
                {"name": "claria-reforma", "deploy_status": "READY", "repo_ok": True},
                {"name": "bras-ai", "deploy_status": "READY", "repo_ok": True},
                {"name": "site-cliente-x", "deploy_status": "ERROR", "repo_ok": True},
                {"name": "espelho-antigo", "deploy_status": "READY", "repo_ok": False},
            ]
        }
    },
    "ciclo": {
        "task": {
            "subscriptions": [
                {"client": "petshop-saudepet", "sku": "site-48h",
                 "amount_monthly": 67, "status": "active"},
                {"client": "alfaiataria-ai", "sku": "site-48h",
                 "amount_monthly": 67, "status": "overdue", "cycles_overdue": 1},
                {"client": "hg-autos", "sku": "atendente-whatsapp",
                 "amount_monthly": 997, "status": "active"},
            ]
        }
    },
}


def _invoke(agent, task, ledger):
    rid = "f0-" + uuid.uuid4().hex[:8]
    state = {"task": task, "mode": "SHADOW", "ledger": ledger,
             "run_id": rid, "verbose": False}
    return agent.invoke(state, config={"configurable": {"thread_id": rid}}).get("output") or {}


def main():
    brain = Brain(os.path.join(BRAIN_DIR, "events"))
    store = FileStore(os.path.join(BRAIN_DIR, "store"))
    llm = get_llm("worker")
    cp = MemorySaver()

    built = {}
    for aid in FLEET:
        spec_dir = os.path.join(FLEET_DIR, aid)
        spec, agent, gate = build_from_spec(spec_dir, llm, brain, store, cp)
        if not gate["ok"]:
            print(f"FAIL gate da fábrica em {aid}: {gate['problems']}")
            return 1
        built[aid] = (spec, agent)
        print(f"  [fabrica] {aid:<10} gate C1-C4 OK | modo={spec['mode']} "
              f"| alvo={spec['target_mode']} | guilda={spec['guild']}")

    print("\nRodada do dia (SHADOW — nada entregue, nada cobrado):\n")
    outs = {}
    for aid in FLEET[:-1]:  # prefeito roda por último, consumindo os outs
        spec, agent = built[aid]
        out = _invoke(agent, DIA[aid]["task"], spec.get("ledger"))
        outs[aid] = out
        print(f"  [{aid}]")
        for k in ("pending_count", "overdue_count", "oldest_wait_min",
                  "green_count", "degraded_count", "down_count",
                  "total_projects", "error_count", "orphan_count", "health_pct",
                  "mrr", "overdue_total"):
            if k in out:
                print(f"    {k}: {out[k]}")
        for a in (out.get("recommended_actions") or [])[:3]:
            print(f"    acao: {a}")
        print()

    # Painel do Prefeito (08h): agrega a frota + funil do checklist da segunda
    painel_task = {
        "fila_out": {k: outs["fila"].get(k) for k in ("pending_count", "overdue_count")},
        "ponte_out": {k: outs["ponte"].get(k) for k in
                      ("green_count", "degraded_count", "down_count", "total")},
        "turno_out": {k: outs["turno"].get(k) for k in
                      ("total_projects", "green_count", "error_count",
                       "orphan_count", "health_pct")},
        "ciclo_out": {k: outs["ciclo"].get(k) for k in
                      ("mrr", "paying_count", "overdue_total", "overdue_count")},
        "funnel": {
            "touches": {"value": 50, "source": "checklist-segunda (contagem no bloco)"},
            "conversations": {"value": 10, "source": "checklist-segunda (contagem no bloco)"},
            "diagnoses": {"value": 3, "source": "checklist-segunda (agenda)"},
            "sites_live": {"value": 4, "source": "anexo-b / inventario"},
        },
        "api_cost_month_brl": {"value": 310.0, "source": "g10-token-cost"},
    }
    spec, agent = built["prefeito"]
    panel = _invoke(agent, painel_task, spec.get("ledger"))
    print("  [prefeito] Painel 08h — 10 números com fonte:")
    for m in panel.get("metrics", []):
        mark = "ok " if m["source"] else "SEM FONTE"
        print(f"    {mark} | {m['label']}: {m['value']}  (fonte: {m['source']})")
    print(f"\n    semaforo: {panel.get('semaforo').upper()} | "
          f"all_sourced: {panel.get('all_sourced')}")
    for a in (panel.get("top_alerts") or [])[:5]:
        print(f"    alerta: {a}")

    # Eval-suite de cada agente (C4) — pass-rate tem que ser 100% na Fase 0
    print("\nEval-suite (C4):")
    all_ok = True
    for aid in FLEET:
        rep = run_evals(os.path.join(FLEET_DIR, aid), llm, brain, store, cp)
        status = "PASS" if rep["passed"] == rep["total"] else "FAIL"
        all_ok = all_ok and rep["passed"] == rep["total"]
        print(f"  {aid:<10} {rep['passed']}/{rep['total']}  {status}")
        for r in rep["results"]:
            if not r["passed"]:
                print(f"    - {r['id']}: {r['desc']}")

    if not all_ok:
        print("\nFAIL — eval-suite da Fase 0 reprovada.")
        return 1
    print("\nOK — Fase 0 aplicada: frota interna Novais materializada, rodada SHADOW "
          "com painel do Prefeito e eval-suite 100%.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
