"""eval-harness — roda a eval-suite (evals/cases.json) de QUALQUER agente e mede pass-rate.

Torna o C4 (eval suite) real e é o motor do Gate 4 da promoção (um agente só sobe de
modo se passar aqui). Mercado-agnóstico: o caso traz o payload da task + 'expected';
o grader por act_handler decide pass/fail. Ver 02-ARQUITETURA §3 (YC#4 software factory).
"""
from __future__ import annotations
import json
import os
import uuid

from ..factory.factory import load_spec, build_from_spec
from .graders import get_grader, generic_contract_grader


def run_evals(spec_dir, llm, brain, store, checkpointer) -> dict:
    spec = load_spec(spec_dir)
    _, agent, _ = build_from_spec(spec_dir, llm, brain, store, checkpointer)
    handler = spec.get("act_handler", "outcome_clause_validator")
    # Grader específico prevalece; senão cai no genérico de contrato (valida `expected`
    # de domínio contra o top-level do output). Assim os handlers determinísticos por
    # guilda (rice_score, churn_risk_score, ...) são avaliados sem precisar de 1 grader
    # nominal cada — o genérico checa presença+compatibilidade (tolerância 1%).
    specific = get_grader(handler)
    grader = specific or generic_contract_grader

    cases_path = os.path.join(spec_dir, "evals", "cases.json")
    cases = json.load(open(cases_path, encoding="utf-8")) if os.path.exists(cases_path) else []

    results = []
    for c in cases:
        payload = {k: v for k, v in c.items() if k not in ("id", "desc", "expected")}
        rid = "ev-" + uuid.uuid4().hex[:8]
        state = {
            "task": {"agent_id": spec["id"], "guild": spec["guild"], "statement": "eval-case", **payload},
            "mode": "SHADOW", "ledger": spec.get("ledger"), "run_id": rid, "verbose": False,
        }
        out = agent.invoke(state, config={"configurable": {"thread_id": rid}}).get("output")
        passed = bool(grader and grader(out, c.get("expected", {})))
        results.append({"id": c.get("id"), "desc": c.get("desc"), "passed": passed})

    npass = sum(1 for r in results if r["passed"])
    n = len(cases)
    return {
        "id": spec["id"], "act_handler": handler, "total": n, "passed": npass,
        "rate": (npass / n if n else 0.0),
        "grader_found": True,                       # sempre há grader (genérico de contrato)
        "grader_specific": specific is not None,    # distingue específico vs fallback genérico
        "results": results,
    }
