"""Relatório de EXECUÇÃO do piloto verificável (VERIFY-IN-EVAL F2).

Roda os eval-cases de um agente `spec_executor` pelo caminho real (handler → verify_code →
ExecutionProvider corrente) e reporta os DOIS números da tese:

  static_pass_rate  — fração de artefatos que passam o oráculo ESTÁTICO (F0 move, de 0).
  delivered_rate    — fração com delivered_ok=True (SÓ a execução real move; 0 sob InertExecutor).

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


def run(spec_dir: str) -> dict:
    import glob
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
        rows.append({"id": c.get("id"), "desc": c.get("desc"),
                     "static_ok": bool(out.get("static_ok")),
                     "delivered_ok": bool(out.get("delivered_ok")),
                     "tests_pass": out.get("tests_pass"), "first_fail": out.get("first_fail")})

    n = len(rows)
    static_pass = sum(1 for r in rows if r["static_ok"])
    delivered = sum(1 for r in rows if r["delivered_ok"])
    # o discriminante da F2: passou o estático MAS não entregou (execução reprovou)
    caught_by_exec = [r for r in rows if r["static_ok"] and not r["delivered_ok"]]
    return {"id": spec["id"], "n": n, "static_pass": static_pass, "delivered": delivered,
            "caught_by_exec": caught_by_exec, "rows": rows}


def _rate(passed: int, total: int) -> dict:
    percent = round((100 * passed / total), 2) if total else 0.0
    return {"passed": passed, "total": total, "percent": percent}


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
    return {
        "agent_id": rep.get("id"),
        "executor": {"name": executor_name, "available": bool(executor_available)},
        "total": total,
        "static_pass_rate": _rate(static_pass, total),
        "delivered_rate": _rate(delivered, total),
        "static_without_delivery_count": static_without_delivery,
        "caught_by_exec_count": len(caught),
        "caught_by_exec": [
            {"id": r.get("id"), "desc": r.get("desc"), "tests_pass": r.get("tests_pass"),
             "first_fail": r.get("first_fail")}
            for r in caught
        ],
        "rows": rep.get("rows") or [],
    }


def render_text(summary: dict) -> str:
    """Renderiza o relatório humano; o JSON vem de `summarize`."""
    static_rate = summary["static_pass_rate"]
    delivered_rate = summary["delivered_rate"]
    total = summary["total"]
    lines = [
        f"exec_report — {summary['agent_id']}  | executor={summary['executor']['name']} "
        f"available={summary['executor']['available']}",
        "",
        f"  static_pass_rate = {static_rate['passed']}/{total}  ({static_rate['percent']:.0f}%)  ← F0 move",
        f"  delivered_rate   = {delivered_rate['passed']}/{total}  ({delivered_rate['percent']:.0f}%)  ← só execução real move",
        f"  static_sem_delivery = {summary['static_without_delivery_count']}/{total}  ← gap a maturar",
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
    return parser.parse_args(argv)


def main(argv):
    args = _parse(argv)
    ex = get_executor()
    available = ex.available
    rep = run(args.spec_dir)
    summary = summarize(rep, executor_name=ex.name, executor_available=available)
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
