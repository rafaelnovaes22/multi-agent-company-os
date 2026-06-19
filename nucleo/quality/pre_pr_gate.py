"""pre_pr_gate — self-check HARD-FAIL que o loop do Hermes roda ANTES de abrir um PR.

Por que existe (a lição do episódio #30/#31/#32): o Hermes fechou a catraca
`handler_generico` com evals tautológicos (o `expected` era replay do próprio handler)
e TODOS os gates verdes passaram. A regra "eval de domínio, não theater" existia só em
texto no AGENTS.md — e texto é gameável. Este gate transforma os pontos da avaliação do
Hermes em BLOQUEIO executável: o loop não abre PR se reprovar aqui.

Difere do forge_check: o forge_check é o ratchet da frota (congela débito no baseline).
Este gate NÃO grandfatheriza nada — é HARD-FAIL. Os pontos enforçados:

  P1  Fechar catraca não é prova de valor: todo handler determinístico precisa de PROVA
      INDEPENDENTE adequada à sua natureza —
        · natureza build/ops/browser (held-out-capaz)  -> critério held-out em `oracle`
          (heldout_files/structure/browser/bug_markers) que o agente nunca vê;
        · natureza cálculo/decisão                      -> ≥1 caso de proveniência
          `human`/`independent` (existe um valor de referência autorado de FORA do handler).
  P1b Proveniência obrigatória: TODO eval-case de handler determinístico declara
      `provenance` ∈ {catalog, human, independent}. Ausente ou replay/handler/derived = reprova.
  P2  Baseline só encolhe: se `forge_baseline.json` mudou no diff, o total não pode CRESCER
      e exige `nucleo/quality/BASELINE-CHANGE.md` justificando (auditoria do PR que "fecha métrica").

Limite honesto (idem #33): proveniência "autorado vs replay" NÃO é 100% decidível
estaticamente. Este gate eleva o custo do gaming e exige que fechar capacidade venha com
uma prova de fora — não é um oráculo de honestidade.

Uso:
    python -m nucleo.quality.pre_pr_gate            # escopo: só os agentes mudados vs origin/main
    python -m nucleo.quality.pre_pr_gate --fleet    # audita a frota inteira (backlog de retrofit)
"""
from __future__ import annotations
import glob
import json
import os
import subprocess
import sys

import yaml

from nucleo.quality.forge_check import GENERIC  # mesma definição de handler genérico

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GUILDS = os.path.join(ROOT, "nucleo", "guilds")
PRODUCT = os.path.join(ROOT, "nucleo", "product")
BASELINE_PATH = os.path.join(ROOT, "nucleo", "quality", "forge_baseline.json")
BASELINE_JUSTIFY = os.path.join(ROOT, "nucleo", "quality", "BASELINE-CHANGE.md")

PROVENANCE_OK = {"catalog", "human", "independent"}
PROVENANCE_INDEPENDENT = {"human", "independent"}   # prova autorada de fora do handler
HELDOUT_CRITERION_KEYS = ("heldout_files", "structure", "browser", "bug_markers")


def _git(*args):
    """Roda git; devolve stdout (str) ou None se git/branch indisponível."""
    try:
        out = subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                             text=True, timeout=30)
        return out.stdout if out.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def _changed_paths():
    """Arquivos mudados vs origin/main (working tree + staged + untracked). None se git falhar."""
    base = "origin/main"
    diff = _git("diff", "--name-only", base)
    if diff is None:
        return None
    paths = set(p for p in diff.splitlines() if p.strip())
    others = _git("ls-files", "--others", "--exclude-standard")
    if others:
        paths |= set(p for p in others.splitlines() if p.strip())
    return paths


def _agent_dir(spec_path):
    return os.path.dirname(spec_path)


def _is_held_out_capable(spec, cases):
    """build/ops/browser/structure: já tem oracle, ou é guilda de engenharia (G03)."""
    if any(c.get("oracle") for c in cases):
        return True
    return str(spec.get("guild", "")).upper().startswith("G03")


def _audit_agent(spec_path):
    """Devolve lista de violações (strings) do agente em spec_path. Vazia = ok."""
    spec = yaml.safe_load(open(spec_path, encoding="utf-8"))
    aid = spec.get("id") or os.path.basename(os.path.dirname(spec_path))
    handler = spec.get("act_handler", "")
    if handler in GENERIC:
        return []   # genérico (roteador/checador de contrato) não promete cálculo — fora do escopo

    cases_path = os.path.join(_agent_dir(spec_path), "evals", "cases.json")
    if not os.path.exists(cases_path):
        return [f"{aid}: handler determinístico sem evals/cases.json"]
    cases = json.load(open(cases_path, encoding="utf-8"))
    if not cases:
        return [f"{aid}: cases.json vazio"]

    viol = []

    # P1b — proveniência obrigatória em todo caso
    sem_prov = [c.get("id", "?") for c in cases if c.get("provenance") not in PROVENANCE_OK]
    if sem_prov:
        viol.append(f"{aid}: {len(sem_prov)} caso(s) sem `provenance` válido "
                    f"(use catalog|human|independent; replay/ausente é proibido) -> {sem_prov[:6]}")

    # P1 — prova independente adequada à natureza
    if _is_held_out_capable(spec, cases):
        has_heldout = any(
            isinstance(c.get("oracle"), dict) and any(c["oracle"].get(k) for k in HELDOUT_CRITERION_KEYS)
            for c in cases)
        if not has_heldout:
            viol.append(f"{aid}: natureza build/ops/browser exige critério held-out em "
                        f"`oracle` ({'/'.join(HELDOUT_CRITERION_KEYS)}) — nenhum caso o declara")
    else:
        has_independent = any(c.get("provenance") in PROVENANCE_INDEPENDENT for c in cases)
        if not has_independent:
            viol.append(f"{aid}: natureza cálculo/decisão exige ≥1 caso com proveniência "
                        f"human|independent (valor de referência autorado FORA do handler); "
                        f"todos os casos seriam replayáveis pelo próprio handler")
    return viol


def _audit_baseline(changed):
    """P2 — se o baseline mudou no diff, total não pode crescer e exige justificativa."""
    rel = os.path.relpath(BASELINE_PATH, ROOT).replace("\\", "/")
    if changed is None or rel not in {p.replace("\\", "/") for p in changed}:
        return []
    viol = []
    new = json.load(open(BASELINE_PATH, encoding="utf-8"))
    new_total = sum(len(v) for v in new.values())
    old_raw = _git("show", f"origin/main:{rel}")
    if old_raw is not None:
        old_total = sum(len(v) for v in json.loads(old_raw).values())
        if new_total > old_total:
            viol.append(f"forge_baseline.json CRESCEU ({old_total} -> {new_total}): o baseline só "
                        f"encolhe (burn-down). Regressão de qualidade escondida no baseline é proibida.")
    if not os.path.exists(BASELINE_JUSTIFY):
        viol.append("forge_baseline.json mudou sem nucleo/quality/BASELINE-CHANGE.md justificando "
                    "(toda alteração de baseline é PR que 'fecha métrica' e exige auditoria).")
    return viol


def main(argv):
    fleet = "--fleet" in argv
    all_specs = sorted(glob.glob(os.path.join(GUILDS, "**", "spec.yaml"), recursive=True) +
                       glob.glob(os.path.join(PRODUCT, "**", "spec.yaml"), recursive=True))

    changed = _changed_paths()
    if fleet:
        specs = all_specs
        scope = f"FROTA INTEIRA ({len(specs)} specs)"
    elif changed is None:
        specs = all_specs
        scope = "git indisponível -> auditando FROTA INTEIRA (fail-safe)"
    else:
        changed_norm = {p.replace("\\", "/") for p in changed}
        specs = [sp for sp in all_specs
                 if any(c.startswith(os.path.relpath(_agent_dir(sp), ROOT).replace("\\", "/"))
                        for c in changed_norm)]
        scope = f"agentes mudados vs origin/main ({len(specs)} agente(s))"

    print(f"pre_pr_gate — escopo: {scope}")

    violations = []
    for sp in specs:
        violations += _audit_agent(sp)
    violations += _audit_baseline(changed)

    if violations:
        print(f"\n❌ PRE-PR GATE REPROVADO — {len(violations)} violação(ões) (HARD-FAIL, sem grandfather):\n")
        for v in violations:
            print(f"  • {v}")
        print("\nNão abra PR. Para cada handler determinístico: dê proveniência aos casos "
              "(provenance) e prova independente da natureza (held-out em `oracle` p/ build/ops; "
              "≥1 caso human|independent p/ cálculo). Ver AGENTS.md §0/§3.")
        return 1

    print(f"\n✅ PRE-PR GATE OK — {len(specs)} agente(s) com proveniência + prova independente. "
          "Pode abrir PR (forge_check/CI continuam valendo).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
