"""Demo do eval-harness — roda a eval-suite de TODOS os agentes da frota e reporta pass-rate.

Roda:  python -m nucleo.demo_eval

É o C4/"software factory" em ação: cada agente é verificado contra seus casos com
gabarito conhecido. Em produção, o Gate 4 da promoção exige pass-rate >= threshold.
Usa um Brain de eval separado (.brain-eval) para não poluir o Company Brain.
"""

from __future__ import annotations

import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langgraph.checkpoint.memory import MemorySaver  # noqa: E402

from nucleo.kernel.brain import Brain, FileStore  # noqa: E402
from nucleo.kernel.providers.llm import get_llm  # noqa: E402
from nucleo.quality.eval_harness import run_evals  # noqa: E402
from nucleo.quality.rate_floor import (  # noqa: E402
    FLOOR_FILENAME,
    FLOOR_PATH,
    build_floor,
    check_floor,
    load_floor,
    write_floor,
)

ROOT = os.path.dirname(os.path.abspath(__file__))
EVAL_DIR = os.path.join(ROOT, ".brain-eval")


def main(argv=None):
    update_floor = "--update-floor" in (argv or [])
    brain = Brain(os.path.join(EVAL_DIR, "events"))
    store = FileStore(os.path.join(EVAL_DIR, "store"))
    llm = get_llm("worker")
    cp = MemorySaver()

    spec_dirs = sorted(
        os.path.dirname(p)
        for p in glob.glob(os.path.join(ROOT, "guilds", "**", "spec.yaml"), recursive=True)
    )
    print(f"eval-harness | {len(spec_dirs)} agentes | LLM={llm.name}\n")
    print(f"{'Agente':<24}{'handler':<22}{'pass':>6}{'/tot':>5}{'rate':>7}")
    print("-" * 64)

    reports = []
    for sd in spec_dirs:
        rep = run_evals(sd, llm, brain, store, cp)
        reports.append(rep)
        rate = f"{rep['rate']*100:.0f}%"
        warn = "" if rep["grader_found"] else "  (sem grader!)"
        print(
            f"{rep['id']:<24}{rep['act_handler']:<22}{rep['passed']:>6}{rep['total']:>5}{rate:>7}{warn}"
        )

    tot = sum(r["total"] for r in reports)
    pas = sum(r["passed"] for r in reports)
    print("-" * 64)
    print(f"{'TOTAL':<46}{pas:>6}{tot:>5}{(pas/tot*100 if tot else 0):>6.0f}%")

    # detalhe das falhas (se houver)
    fails = [
        (r["id"], c["id"], c["desc"]) for r in reports for c in r["results"] if not c["passed"]
    ]
    if fails:
        print("\nFalhas:")
        for aid, cid, desc in fails:
            print(f"  - {aid} / {cid}: {desc}")
    else:
        print("\nOK - toda a eval-suite da frota passou (gabarito conhecido). Gate 4 verde.")

    # Piso de pass-rate (ratchet executável): o run reprova (exit 1) abaixo do piso
    # congelado — fecha a classe "0% executável mas verde-estrutural" (lote G01–G03).
    if update_floor:
        write_floor(FLOOR_PATH, build_floor(reports))
        print(f"\nPiso de pass-rate atualizado em {FLOOR_FILENAME} ({len(reports)} agentes).")
        return 0
    floor = load_floor()
    if floor is None:
        print(
            f"\nPISO AUSENTE ({FLOOR_FILENAME} não encontrado/ilegível) — "
            "rode com --update-floor após revisar."
        )
        return 1
    ok, violations = check_floor(reports, floor)
    if not ok:
        print(f"\nPISO DE PASS-RATE VIOLADO ({len(violations)}):")
        for v in violations:
            print(f"  - {v}")
        print("Suba o piso só após melhora genuína: python -m nucleo.demo_eval --update-floor.")
        return 1
    print(f"\nPiso de pass-rate OK: {len(reports)} agentes no/acima do piso; TOTAL {pas}/{tot}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
