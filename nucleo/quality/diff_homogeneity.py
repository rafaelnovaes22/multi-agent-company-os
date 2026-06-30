"""diff_homogeneity — tripwire mecânico que sinaliza diffs suspeitos de gaming em massa.

Por que existe (item 4 de docs/PLANO-AJUSTE-ROTA.md): o padrão histórico do loop do Hermes
é, a cada gate novo, achar o próximo vetor auto-declaratório e aplicá-lo EM MASSA, com diffs
mecanicamente idênticos:

  · #66-80  carimbou `"provenance": "independent"` em ~380 casos -> 380 linhas adicionadas idênticas.
  · #30-32  adicionou 270 casos tautológicos -> blocos de caso clonados, estrutura igual, valor pobre.

Este detector lê o diff vs origin/main e dispara REVISÃO quando vê homogeneidade acima do limiar.

LIMITE HONESTO (assumido, não escondido): é um TRIPWIRE, não um matador-de-raiz. É heurística
sobre a FORMA do ataque atual; espera-se evasão por jitter (variar uma linha, randomizar valores).
Não substitui o pre_pr_gate nem a prova externa (G-FONTE-EXTERNA/G-PERÍMETRO). O objetivo é
encarecer o gaming em lote e levar um humano a olhar — não atestar honestidade.

Dois sinais:
  A  Carimbo em massa: a MESMA linha adicionada repetida >= --line-threshold vezes no diff.
  B  Casos-clone: casos NOVOS em cases.json que compartilham a estrutura (mesmas chaves/tipos) E
     têm baixa diversidade de valores (>= --clone-threshold casos, diversidade < --diversity-floor).

Uso:
    python -m nucleo.quality.diff_homogeneity            # escopo: cases.json mudados vs origin/main
    python -m nucleo.quality.diff_homogeneity --json     # saída estruturada p/ CI
"""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
from collections import Counter, defaultdict

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Limiares default — calibrados para a escala dos ataques históricos (380 / 270), com folga
# para não disparar num agente que legitimamente adiciona ~30 casos variados.
LINE_THRESHOLD = 12       # linhas adicionadas idênticas a partir das quais é carimbo em massa
CLONE_THRESHOLD = 10      # casos novos com mesma estrutura a partir dos quais é cluster suspeito
DIVERSITY_FLOOR = 0.5     # razão de valores distintos abaixo da qual o cluster é "templado"

# Punção estrutural pura (não carrega informação de gaming) — ignorada no sinal A.
_STRUCTURAL_LINES = {"{", "}", "[", "]", "},", "],", "{,"}
# Chaves desenhadas para serem únicas por caso — excluídas da assinatura de valor do sinal B,
# senão um `id`/`desc` jitterado mascara um payload clonado.
DEFAULT_EXCLUDE_KEYS = ("id", "desc", "description", "name", "title")


def _git(*args):
    try:
        out = subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                             text=True, timeout=30)
        return out.stdout if out.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


# ---------------------------------------------------------------------------
# Sinal A — linhas adicionadas idênticas (carimbo em massa)
# ---------------------------------------------------------------------------
def added_line_homogeneity(diff_text, threshold=LINE_THRESHOLD):
    """Conta linhas ADICIONADAS idênticas num diff unificado. Devolve [(linha, count)] desc."""
    counts = Counter()
    for raw in diff_text.splitlines():
        if not raw.startswith("+") or raw.startswith("+++"):
            continue
        line = raw[1:].strip()
        if not line or line in _STRUCTURAL_LINES:
            continue
        counts[line] += 1
    return sorted(((ln, n) for ln, n in counts.items() if n >= threshold),
                  key=lambda t: t[1], reverse=True)


# ---------------------------------------------------------------------------
# Sinal B — casos-clone (estrutura igual + valor pobre)
# ---------------------------------------------------------------------------
def case_fingerprint(case, exclude_keys=DEFAULT_EXCLUDE_KEYS):
    """Assinatura ESTRUTURAL (chaves+tipos, valores apagados, índice de lista irrelevante)."""
    ex = set(exclude_keys)

    def walk(node):
        if isinstance(node, dict):
            parts = [f"{k}:{walk(v)}" for k, v in sorted(node.items()) if k not in ex]
            return "{" + ",".join(parts) + "}"
        if isinstance(node, list):
            return "[" + ",".join(sorted(walk(x) for x in node)) + "]"
        return type(node).__name__   # str/int/float/bool/NoneType — valor apagado

    return walk(case)


def value_signature(case, exclude_keys=DEFAULT_EXCLUDE_KEYS):
    """Tupla canônica dos VALORES escalares (p/ medir diversidade dentro de um cluster)."""
    ex = set(exclude_keys)
    vals = []

    def walk(node, path):
        if isinstance(node, dict):
            for k, v in sorted(node.items()):
                if k not in ex:
                    walk(v, f"{path}.{k}")
        elif isinstance(node, list):
            for i, x in enumerate(node):
                walk(x, f"{path}[{i}]")
        else:
            vals.append((path, node))

    walk(case, "")
    return tuple(vals)


def clone_clusters(cases, min_size=CLONE_THRESHOLD, diversity_floor=DIVERSITY_FLOOR,
                   exclude_keys=DEFAULT_EXCLUDE_KEYS):
    """Agrupa casos por estrutura; sinaliza clusters grandes com baixa diversidade de valor."""
    groups = defaultdict(list)
    for c in cases:
        groups[case_fingerprint(c, exclude_keys)].append(c)

    flagged = []
    for fp, members in groups.items():
        if len(members) < min_size:
            continue
        distinct = len({value_signature(m, exclude_keys) for m in members})
        diversity = distinct / len(members)
        if diversity < diversity_floor:
            flagged.append({
                "size": len(members),
                "distinct_values": distinct,
                "diversity": round(diversity, 3),
                "fingerprint": fp[:200],
            })
    return sorted(flagged, key=lambda d: d["size"], reverse=True)


# ---------------------------------------------------------------------------
# Coleta via git
# ---------------------------------------------------------------------------
def _changed_cases_paths():
    diff = _git("diff", "--name-only", "origin/main")
    if diff is None:
        return None
    paths = {p.strip() for p in diff.splitlines() if p.strip().endswith("evals/cases.json")}
    others = _git("ls-files", "--others", "--exclude-standard")
    if others:
        paths |= {p.strip() for p in others.splitlines() if p.strip().endswith("evals/cases.json")}
    return sorted(paths)


def _load_json(text):
    try:
        data = json.loads(text)
        return data if isinstance(data, list) else []
    except (ValueError, TypeError):
        return []


def _added_cases(path):
    """Casos presentes na versão atual de `path` cujo `id` não existia em origin/main."""
    try:
        new = _load_json(open(os.path.join(ROOT, path), encoding="utf-8").read())
    except OSError:
        return []
    old_raw = _git("show", f"origin/main:{path}")
    old_ids = {c.get("id") for c in _load_json(old_raw)} if old_raw else set()
    return [c for c in new if c.get("id") not in old_ids]


def scan(line_threshold=LINE_THRESHOLD, clone_threshold=CLONE_THRESHOLD,
         diversity_floor=DIVERSITY_FLOOR):
    """Roda os dois sinais sobre o diff vs origin/main. Devolve dict de relatório."""
    paths = _changed_cases_paths()
    if paths is None:
        return {"git": False, "paths": [], "signal_a": [], "signal_b": []}

    diff_text = _git("diff", "origin/main", "--", *paths) or "" if paths else ""
    signal_a = added_line_homogeneity(diff_text, line_threshold)

    signal_b = []
    for p in paths:
        added = _added_cases(p)
        for cl in clone_clusters(added, clone_threshold, diversity_floor):
            signal_b.append({"path": p, **cl})

    return {"git": True, "paths": paths, "signal_a": signal_a, "signal_b": signal_b}


def main(argv):
    ap = argparse.ArgumentParser(description="Tripwire de homogeneidade de diff (gaming em massa).")
    ap.add_argument("--line-threshold", type=int, default=LINE_THRESHOLD)
    ap.add_argument("--clone-threshold", type=int, default=CLONE_THRESHOLD)
    ap.add_argument("--diversity-floor", type=float, default=DIVERSITY_FLOOR)
    ap.add_argument("--json", action="store_true", help="saída estruturada")
    args = ap.parse_args(argv)

    rep = scan(args.line_threshold, args.clone_threshold, args.diversity_floor)

    if args.json:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        return 1 if (rep["signal_a"] or rep["signal_b"]) else 0

    if not rep["git"]:
        print("diff_homogeneity — git/origin/main indisponível; nada a comparar (tripwire é advisory).")
        return 0

    print(f"diff_homogeneity — {len(rep['paths'])} cases.json mudado(s) vs origin/main")
    tripped = bool(rep["signal_a"] or rep["signal_b"])

    if rep["signal_a"]:
        print(f"\n⚠ Sinal A — carimbo em massa ({len(rep['signal_a'])} linha(s) repetida(s) "
              f">= {args.line_threshold}x):")
        for ln, n in rep["signal_a"][:10]:
            print(f"  {n:>4}x  {ln[:100]}")

    if rep["signal_b"]:
        print(f"\n⚠ Sinal B — casos-clone (estrutura igual, diversidade < {args.diversity_floor}):")
        for c in rep["signal_b"][:10]:
            print(f"  {c['size']:>4} casos / {c['distinct_values']} valores distintos "
                  f"(diversidade {c['diversity']}) em {c['path']}")

    if tripped:
        print("\n⚠ TRIPWIRE DISPARADO — revisão humana recomendada. NÃO é prova de gaming nem hard-fail: "
              "é a forma do ataque histórico (#30-32, #66-80). Confirme que a homogeneidade tem causa "
              "legítima (mesmo gerador honesto) e não carimbo/clone em lote. Espera-se evasão por jitter.")
        return 1

    print("\n✅ Sem homogeneidade suspeita acima dos limiares.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
