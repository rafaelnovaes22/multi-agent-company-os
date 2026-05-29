"""Demo do /promote (C4) — um agente evolui de modo passando pelos gates.

Roda:  python -m nucleo.demo_promote

Promove o g8-lead-qualifier SHADOW->PILOT->ASSISTED->AUTONOMOUS. Mostra:
- gates passando (incl. eval-harness como Gate 4);
- ANTI-SELF-APPROVAL: tentativa com mesmo aprovador em po e promotion_officer é BLOQUEADA (G5);
- promoção final só com aprovadores distintos + CI/CD + security guardian.
"""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langgraph.checkpoint.memory import MemorySaver  # noqa: E402

from nucleo.kernel.brain import Brain, FileStore  # noqa: E402
from nucleo.kernel.providers.llm import get_llm  # noqa: E402
from nucleo.governance.promote import promote, current_mode  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
GOV_DIR = os.path.join(ROOT, ".brain-gov")
EVAL_DIR = os.path.join(ROOT, ".brain-eval")
SPEC = os.path.join(ROOT, "guilds", "g08_vendas", "g8-lead-qualifier")


def show(title, res):
    print(f"\n>>> {title}: {res['from']} -> {res['to']}  =>  {'PROMOVIDO' if res['ok'] else 'BLOQUEADO'}")
    for c in res.get("gates", []):
        print(f"      [{ 'OK ' if c['ok'] else 'X  '}] {c['gate']}: {c['evidence']}")


def main():
    gov_brain = Brain(os.path.join(GOV_DIR, "events"))
    gov_store = FileStore(os.path.join(GOV_DIR, "store"))
    # deps do Gate 4 (eval-harness) — Brain/store separados p/ não poluir
    deps = {"llm": get_llm("worker"),
            "brain": Brain(os.path.join(EVAL_DIR, "events")),
            "store": FileStore(os.path.join(EVAL_DIR, "store")),
            "checkpointer": MemorySaver()}

    aid = "g8-lead-qualifier"
    print(f"Modo inicial de {aid}: {current_mode(gov_store, aid)}")

    show("SHADOW->PILOT (aprovadores distintos)",
         promote(SPEC, "PILOT", {"approver_po": "alice", "approver_promotion_officer": "bob"}, deps, gov_brain, gov_store))

    show("PILOT->ASSISTED (com SLA assinado)",
         promote(SPEC, "ASSISTED", {"sla": "lead.qualified<=5min;>=85% fit", "approver_po": "alice", "approver_promotion_officer": "bob"}, deps, gov_brain, gov_store))

    show("ASSISTED->AUTONOMOUS (MESMO aprovador -> deve bloquear no G5)",
         promote(SPEC, "AUTONOMOUS", {"sla": "ok", "approver_po": "alice", "approver_promotion_officer": "alice", "cicd_active": True, "approver_security": "carol"}, deps, gov_brain, gov_store))

    show("ASSISTED->AUTONOMOUS (aprovadores distintos + CI/CD + security)",
         promote(SPEC, "AUTONOMOUS", {"sla": "ok", "approver_po": "alice", "approver_promotion_officer": "bob", "cicd_active": True, "approver_security": "carol"}, deps, gov_brain, gov_store))

    print(f"\nModo final de {aid}: {current_mode(gov_store, aid)}")
    log = gov_store.get(("promotions", aid), "log") or []
    print("Log de promoções (append-only):", " | ".join(f"{e['from']}->{e['to']}" for e in log))
    print("\nOK - C4 operacional: agente só ganha autonomia passando pelos gates; auto-aprovação bloqueada.")


if __name__ == "__main__":
    main()
