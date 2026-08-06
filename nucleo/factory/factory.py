"""A Fábrica (L3) — software factory com governança (YC#4).

Lê uma spec (+ eval-cases), roda o gate de fábrica (C1/C2/C3/C4) e materializa
o agente via o template universal. "Implementar cada agente" = escrever a spec;
a Fábrica gera o resto. Ver 02-ARQUITETURA.md §5.
"""

from __future__ import annotations

import json
import os

import yaml

from ..kernel.agent_template import build_agent


class FactoryGateError(Exception):
    pass


def load_spec(spec_dir: str) -> dict:
    with open(os.path.join(spec_dir, "spec.yaml"), encoding="utf-8") as f:
        spec = yaml.safe_load(f)
    spec["eval_count"] = _count_evals(spec_dir)
    spec["_spec_dir"] = spec_dir
    return spec


def _count_evals(spec_dir: str) -> int:
    p = os.path.join(spec_dir, "evals", "cases.json")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return len(json.load(f))
    return 0


def factory_gate(spec: dict, *, strict: bool = False) -> dict:
    """Gate de fábrica ANTES de materializar (C1/C2/C3/C4)."""
    problems, warnings = [], []
    oc = spec.get("outcome_clause", {}) or {}

    # C2 — cláusula de outcome
    if not oc.get("statement"):
        problems.append("C2: outcome_clause.statement ausente")
    if len(oc.get("positive_examples", []) or []) < 3:
        problems.append("C2: <3 positive_examples")
    if len(oc.get("negative_examples", []) or []) < 3:
        problems.append("C2: <3 negative_examples")
    if not oc.get("delivered_event"):
        problems.append("C2: delivered_event ausente")

    # C3 — billable precisa de economics
    if spec.get("ledger") == "billable" and not spec.get("economics"):
        problems.append("C3: ledger=billable sem economics")

    # C4 — eval-suite (produção exige >=30; Sprint 0 apenas avisa)
    if spec.get("eval_count", 0) < 30:
        warnings.append(
            f"C4: eval-suite com {spec.get('eval_count', 0)} casos (<30) — ok p/ Sprint 0"
        )

    if problems and strict:
        raise FactoryGateError("; ".join(problems))
    return {"ok": not problems, "problems": problems, "warnings": warnings}


def build_from_spec(spec_dir: str, llm, brain, store, checkpointer, *, strict: bool = False):
    """Carrega a spec, valida no gate e devolve (spec, agente_compilado, resultado_do_gate)."""
    spec = load_spec(spec_dir)
    gate = factory_gate(spec, strict=strict)
    agent = build_agent(spec, llm, brain, store, checkpointer)
    return spec, agent, gate
