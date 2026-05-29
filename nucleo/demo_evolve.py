"""Demo do /evolve — instinct de UM agente vira SKILL de TODA a empresa.

Pré-requisito: rode antes `python -m nucleo.demo_hermes` (popula a memória).

Roda:  python -m nucleo.demo_evolve

Agrupa os fatos de memória de todos os agentes por tópico e promove os tópicos
com suporte suficiente a skills compartilhadas em nucleo/company/skills/.
"""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nucleo.kernel.brain import Brain, FileStore  # noqa: E402
from nucleo.learning.evolve import run_evolve  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
BRAIN_DIR = os.path.join(ROOT, ".brain")


def main():
    brain = Brain(os.path.join(BRAIN_DIR, "events"))
    store = FileStore(os.path.join(BRAIN_DIR, "store"))

    print("=== /evolve (instincts recorrentes -> skills compartilhadas) ===")
    res = run_evolve(store, brain, min_support=2, verbose=True)

    print(f"\nCorpus analisado: {res['corpus_size']} fatos. "
          f"Skills promovidas: {len(res['promoted'])}.")
    skills_dir = os.path.join(ROOT, "company", "skills")
    if os.path.isdir(skills_dir):
        print("Skills em nucleo/company/skills/:")
        for fn in sorted(os.listdir(skills_dir)):
            print(f"  - {fn}")
    print("\nOK - o aprendizado individual virou capacidade da frota (a empresa fica mais inteligente).")


if __name__ == "__main__":
    main()
