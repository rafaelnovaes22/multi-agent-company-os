"""Relatório de EXECUÇÃO do piloto verificável (VERIFY-IN-EVAL F2).

Roda os eval-cases de um agente `spec_executor` pelo caminho real (handler → verify_code →
ExecutionProvider corrente) e reporta os DOIS números da tese:

  static_pass_rate  — fração de artefatos que passam o oráculo ESTÁTICO (F0 move, de 0).
  delivered_rate    — fração com delivered_ok=True (SÓ a execução real move; 0 sob InertExecutor).
  delivered_eligible_rate — entrega sobre os casos ELEGÍVEIS (expected.exec_delivered=True, a
      intenção de design SOB EXECUÇÃO REAL declarada no eval-case). É o número do SLA G7
      (>=95%): a suíte é discriminante (negativos-por-design NÃO entram no denominador;
      entregar num negativo é falso-positivo grave, contado em false_positive_delivery_count
      e HARD-FAIL no gate).

Valor central da F2: os artefatos "plausível-mas-logicamente-errado" passam o ESTÁTICO e
FALHAM a EXECUÇÃO — delivered_ok=False. É o que o F0 não consegue pegar e só o runner pega.

Uso (nightly, runner Linux+Docker):
    EXEC_PROVIDER=docker EXEC_IMAGE=nucleo-exec:latest python -m nucleo.quality.exec_report \
        nucleo/guilds/g03_engenharia/g3-build-error-resolver
Sem EXEC_PROVIDER (offline) reporta delivered_rate=0 — honesto, não executou.
"""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
import uuid

from langgraph.checkpoint.memory import MemorySaver

from ..factory.factory import load_spec, build_from_spec
from ..kernel.brain import Brain, FileStore
from ..kernel.providers.llm import get_llm
from ..kernel.execution import get_executor

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def _git_commit() -> str:
    try:
        r = subprocess.run(["git", "rev-parse", "--short=12", "HEAD"], capture_output=True,
                           text=True, timeout=5)
        if r.returncode == 0:
            return r.stdout.strip()
    except Exception:  # noqa: BLE001 — metadado opcional
        pass
    return "unknown"


def run(spec_dir: str) -> dict:
    import json
    spec = load_spec(spec_dir)
    llm = get_llm("worker")
    brain = Brain(os.path.join("c:\\tmp", ".brain-exec", "events"))
    store = FileStore(os.path.join("c:\\tmp", ".brain-exec", "store"))
    _, agent, _ = build_from_spec(spec_dir, llm, brain, store, MemorySaver())
    cases = json.load(open(os.path.join(spec_dir, "evals", "cases.json"), encoding="utf-8"))

    rows = []
    for c in cases:
        payload = {k: v for k, v in c.items() if k not in ("id", "desc", "expected")}
        rid = "ex-" + uuid.uuid4().hex[:8]
        state = {"task": {"agent_id": spec["id"], "guild": spec["guild"], "statement": "exec", **payload},
                 "mode": "SHADOW", "ledger": spec.get("ledger"), "run_id": rid, "verbose": False}
        out = agent.invoke(state, config={"configurable": {"thread_id": rid}}).get("output") or {}
        oracle = c.get("oracle") or {}
        exp = c.get("expected") or {}
        rows.append({"id": c.get("id"), "desc": c.get("desc"),
                     "static_ok": bool(out.get("static_ok")),
                     "expected_static_ok": exp.get("static_ok"),
                     "expected_exec_delivered": exp.get("exec_delivered"),
                     "delivered_ok": bool(out.get("delivered_ok")),
                     "tests_pass": out.get("tests_pass"), "first_fail": out.get("first_fail"),
                     "runtime": oracle.get("runtime") or "python",
                     "test_cmd": oracle.get("test_cmd") or "pytest -q",
                     "heldout_files": sorted((oracle.get("heldout_files") or {}).keys())})

    n = len(rows)
    static_pass = sum(1 for r in rows if r["static_ok"])
    delivered = sum(1 for r in rows if r["delivered_ok"])
    # o discriminante da F2: passou o estático MAS não entregou (execução reprovou)
    caught_by_exec = [r for r in rows if r["static_ok"] and not r["delivered_ok"]]
    return {"id": spec["id"], "spec_dir": spec_dir, "commit": _git_commit(),
            "n": n, "static_pass": static_pass, "delivered": delivered,
            "caught_by_exec": caught_by_exec, "rows": rows}


def run_generative(spec_dir: str, llm=None, executor=None) -> dict:
    """Variante GERADORA (épico red→green, plano §4.7): roda SÓ os casos elegíveis
    (expected.exec_delivered=True) SEM o artifact baked — o agente gera com LLM real,
    itera contra o executor nos testes visíveis e o held-out decide `delivered` na
    verificação final. O número resultante mede o AGENTE, não as fixtures; é publicado
    separado do replay e nunca somado a ele."""
    from ..kernel.generate import generate_red_green
    from ..kernel.verification import verify_code
    spec = load_spec(spec_dir)
    llm = llm if llm is not None else get_llm("worker")
    executor = executor if executor is not None else get_executor()
    cases = json.load(open(os.path.join(spec_dir, "evals", "cases.json"), encoding="utf-8"))
    eligible = [c for c in cases if (c.get("expected") or {}).get("exec_delivered") is True]

    rows = []
    for c in eligible:
        seed = c.get("seed") or {}
        oracle = c.get("oracle") or {}
        request = c.get("request") or c.get("desc") or ""
        gen = generate_red_green(request, seed, oracle, llm, executor)
        v = verify_code(gen["artifact"], seed, oracle, executor=executor)
        rows.append({"id": c.get("id"), "desc": c.get("desc"),
                     "static_ok": bool(v.get("static_ok")),
                     # generativo: o estático observado não é asserção do caso (o agente
                     # pode falhar honestamente) — não entra no oracle_correct.
                     "expected_static_ok": None,
                     "expected_exec_delivered": True,
                     "delivered_ok": bool(v.get("delivered_ok")),
                     "tests_pass": v.get("tests_pass"), "first_fail": v.get("first_fail"),
                     "attempts": gen["attempts"], "loop_green": gen["loop_green"],
                     "runtime": oracle.get("runtime") or "python",
                     "test_cmd": oracle.get("test_cmd") or "pytest -q",
                     "heldout_files": sorted((oracle.get("heldout_files") or {}).keys())})

    n = len(rows)
    static_pass = sum(1 for r in rows if r["static_ok"])
    delivered = sum(1 for r in rows if r["delivered_ok"])
    caught_by_exec = [r for r in rows if r["static_ok"] and not r["delivered_ok"]]
    return {"id": spec["id"], "spec_dir": spec_dir, "commit": _git_commit(),
            "generative": True, "llm": getattr(llm, "name", "unknown"),
            "n": n, "static_pass": static_pass, "delivered": delivered,
            "caught_by_exec": caught_by_exec, "rows": rows}


def _rate(passed: int, total: int) -> dict:
    percent = round((100 * passed / total), 2) if total else 0.0
    return {"passed": passed, "total": total, "percent": percent}


def _row_credit(row: dict) -> str:
    if not row.get("static_ok"):
        return "not_static_ok"
    if row.get("delivered_ok") is True and row.get("tests_pass") is True:
        return "credited"
    if row.get("tests_pass") is False:
        return "blocked_by_execution_failure"
    return "unverified"


def summarize(rep: dict, *, executor_name: str, executor_available: bool) -> dict:
    """Contrato machine-readable do nightly VERIFY-IN-EVAL.

    Mantém os números centrais da tese (static vs delivered) e explicita o gap operacional:
    casos que passaram no estático mas ainda não viraram entrega validada por execução real.
    """
    total = int(rep.get("n") or 0)
    static_pass = int(rep.get("static_pass") or 0)
    delivered = int(rep.get("delivered") or 0)
    caught = list(rep.get("caught_by_exec") or [])
    static_without_delivery = max(static_pass - delivered, 0)
    rows = []
    for row in rep.get("rows") or []:
        item = dict(row)
        item["execution_credit"] = _row_credit(item)
        # oracle_correct: o estático OBSERVADO bate o `expected.static_ok` do caso.
        # É o discriminante honesto da suíte (positivos passam, negativos/adversariais
        # são barrados). None quando o caso não declara expected.static_ok.
        exp_static = item.get("expected_static_ok")
        item["oracle_correct"] = (bool(item.get("static_ok")) == exp_static) if isinstance(exp_static, bool) else None
        rows.append(item)
    oracle_evaluated_count = sum(1 for r in rows if r.get("oracle_correct") is not None)
    oracle_correct_count = sum(1 for r in rows if r.get("oracle_correct") is True)
    # A suíte é DISCRIMINANTE: só os casos com `expected.exec_delivered=True` (intenção de
    # design SOB EXECUÇÃO REAL, declarada pelo humano no eval-case; não confundir com
    # `expected.delivered_ok`, que é o sinal offline do grader G4) contam no denominador do
    # SLA de entrega. Negativos-por-design (adversarial/plausível-mas-errado) medem o
    # FAIL-SAFE, não a entrega: um deles entregar é falso-positivo grave (resposta errada
    # silenciosa).
    eligible = [r for r in rows if r.get("expected_exec_delivered") is True]
    delivered_eligible = sum(1 for r in eligible if r.get("delivered_ok"))
    false_positive_deliveries = [
        r for r in rows if r.get("expected_exec_delivered") is False and r.get("delivered_ok")
    ]
    executed_count = sum(1 for r in rows if isinstance(r.get("tests_pass"), bool))
    tests_passed_count = sum(1 for r in rows if r.get("tests_pass") is True)
    tests_failed_count = sum(1 for r in rows if r.get("tests_pass") is False)
    if not executor_available:
        reason = "executor_unavailable"
    elif delivered > 0:
        reason = "execution_validated"
    elif static_without_delivery > 0:
        reason = "no_delivery_credited"
    else:
        reason = "no_static_candidates"
    return {
        "agent_id": rep.get("id"),
        "spec_dir": rep.get("spec_dir"),
        "commit": rep.get("commit"),
        "executor": {"name": executor_name, "available": bool(executor_available)},
        "total": total,
        "static_pass_rate": _rate(static_pass, total),
        "delivered_rate": _rate(delivered, total),
        # SLA de entrega (G7): entrega sobre os casos ELEGÍVEIS (expected.exec_delivered=True).
        "delivered_eligible_rate": _rate(delivered_eligible, len(eligible)),
        "false_positive_delivery_count": len(false_positive_deliveries),
        "false_positive_deliveries": [
            {"id": r.get("id"), "desc": r.get("desc")} for r in false_positive_deliveries
        ],
        "executed_count": executed_count,
        "tests_passed_count": tests_passed_count,
        "tests_failed_count": tests_failed_count,
        "oracle_evaluated_count": oracle_evaluated_count,
        "oracle_correct_count": oracle_correct_count,
        "static_without_delivery_count": static_without_delivery,
        "static_sem_delivery": static_without_delivery,
        "execution_credit": {
            "can_credit_delivery": bool(executor_available and delivered > 0),
            "credited_deliveries": delivered,
            "blocked_static_without_delivery": static_without_delivery,
            "reason": reason,
        },
        "caught_by_exec_count": len(caught),
        "caught_by_exec": [
            {"id": r.get("id"), "desc": r.get("desc"), "tests_pass": r.get("tests_pass"),
             "first_fail": r.get("first_fail")}
            for r in caught
        ],
        "rows": rows,
    }


def mark_audit_only(summary: dict, reason: str) -> dict:
    """Marca um relatório como artifact de auditoria, sem crédito de entrega.

    Usado para naturezas recém-instrumentadas ou estáticas que devem ser publicadas no
    nightly, mas ainda não fazem parte do gate estrito de crédito real.
    """
    audited = dict(summary)
    audited["rows"] = [dict(row) for row in summary.get("rows") or []]
    audited["audit_only"] = True
    audited["audit_reason"] = reason
    audited["execution_credit"] = dict(summary.get("execution_credit") or {})
    audited["execution_credit"].update({
        "can_credit_delivery": False,
        "credited_deliveries": 0,
        "reason": f"audit_only:{reason}",
    })
    for row in audited["rows"]:
        row["execution_credit"] = "audit_only"
    return audited


def render_text(summary: dict) -> str:
    """Renderiza o relatório humano; o JSON vem de `summarize`."""
    static_rate = summary["static_pass_rate"]
    delivered_rate = summary["delivered_rate"]
    total = summary["total"]
    mode = "GENERATIVO (red→green)" if summary.get("generative") else "replay de fixtures"
    lines = [
        f"exec_report — {summary['agent_id']}  | modo={mode} | executor={summary['executor']['name']} "
        f"available={summary['executor']['available']}"
        + (f" | llm={summary['llm']}" if summary.get("generative") else ""),
        "",
        f"  static_pass_rate = {static_rate['passed']}/{total}  ({static_rate['percent']:.0f}%)  ← F0 move",
        f"  delivered_rate   = {delivered_rate['passed']}/{total}  ({delivered_rate['percent']:.0f}%)  ← só execução real move",
        f"  delivered_eligible_rate = {summary['delivered_eligible_rate']['passed']}"
        f"/{summary['delivered_eligible_rate']['total']}  "
        f"({summary['delivered_eligible_rate']['percent']:.0f}%)  ← SLA G7 (só casos expected.exec_delivered=True)",
        f"  false_positive_deliveries = {summary['false_positive_delivery_count']}  ← fail-safe (tem de ser 0)",
        f"  executed_count   = {summary['executed_count']}/{total}",
        f"  tests_passed     = {summary['tests_passed_count']}/{total}",
        f"  static_sem_delivery = {summary['static_without_delivery_count']}/{total}  ← gap a maturar",
        f"  execution_credit = {summary['execution_credit']['credited_deliveries']}/{total} "
        f"({summary['execution_credit']['reason']})",
    ]
    if not summary["executor"]["available"]:
        lines.append("\n  (executor inerte/indisponível — delivered_rate=0 é honesto: não executou)")
    else:
        lines.append(
            f"\n  {summary['caught_by_exec_count']} artefato(s) passaram o ESTÁTICO mas a EXECUÇÃO reprovou "
            "(o que só a F2 pega):"
        )
        for row in summary["caught_by_exec"]:
            desc = (row.get("desc") or "")[:70]
            lines.append(f"    - {row.get('id')}: {desc}")
    return "\n".join(lines)


def _parse(argv):
    parser = argparse.ArgumentParser(description="Relatório VERIFY-IN-EVAL: estático vs execução real.")
    parser.add_argument("spec_dir", nargs="?", default="nucleo/guilds/g03_engenharia/g3-build-error-resolver")
    parser.add_argument("--json", action="store_true", help="emite somente JSON machine-readable")
    parser.add_argument("--json-output", help="também grava o resumo JSON neste caminho")
    parser.add_argument("--audit-only", action="store_true",
                        help="publica o relatório como auditoria sem crédito de entrega")
    parser.add_argument("--audit-reason", default="not_in_strict_execution_gate",
                        help="motivo usado quando --audit-only bloqueia crédito")
    parser.add_argument("--generative", action="store_true",
                        help="modo GERADOR (red→green): o agente gera o artefato com LLM real "
                             "nos casos elegíveis; mede o agente, não as fixtures")
    parser.add_argument("--require-real-llm", action="store_true",
                        help="falha se o provider for FakeLLMProvider (evita publicar um "
                             "'0%% generativo' medido com LLM fake — sinal falso)")
    return parser.parse_args(argv)


def main(argv):
    args = _parse(argv)
    ex = get_executor()
    available = ex.available
    if args.generative:
        llm = get_llm("worker")
        if args.require_real_llm:
            from ..kernel.providers.llm import FakeLLMProvider
            if isinstance(llm, FakeLLMProvider):
                print("exec_report --generative: LLM_PROVIDER ausente/fake — geração exige LLM "
                      "real (--require-real-llm). Nada foi medido.", file=sys.stderr)
                return 2
        rep = run_generative(args.spec_dir, llm=llm, executor=ex)
    else:
        rep = run(args.spec_dir)
    summary = summarize(rep, executor_name=ex.name, executor_available=available)
    if rep.get("generative"):
        summary["generative"] = True
        summary["llm"] = rep.get("llm")
    if args.audit_only:
        summary = mark_audit_only(summary, args.audit_reason)
    json_text = json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True)
    if args.json_output:
        with open(args.json_output, "w", encoding="utf-8") as f:
            f.write(json_text + "\n")
    if args.json:
        print(json_text)
    else:
        print(render_text(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
