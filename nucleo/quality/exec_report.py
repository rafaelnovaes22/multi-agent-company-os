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


def main(argv):
    spec_dir = argv[0] if argv else "nucleo/guilds/g03_engenharia/g3-build-error-resolver"
    ex = get_executor()
    rep = run(spec_dir)
    n = rep["n"]
    print(f"exec_report — {rep['id']}  | executor={ex.name} available={ex.available}\n")
    print(f"  static_pass_rate = {rep['static_pass']}/{n}  ({100*rep['static_pass']/n:.0f}%)  ← F0 move")
    print(f"  delivered_rate   = {rep['delivered']}/{n}  ({100*rep['delivered']/n:.0f}%)  ← só execução real move")
    if not ex.available:
        print("\n  (executor inerte/indisponível — delivered_rate=0 é honesto: não executou)")
    else:
        print(f"\n  {len(rep['caught_by_exec'])} artefato(s) passaram o ESTÁTICO mas a EXECUÇÃO reprovou "
              f"(o que só a F2 pega):")
        for r in rep["caught_by_exec"]:
            print(f"    - {r['id']}: {r['desc'][:70]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
