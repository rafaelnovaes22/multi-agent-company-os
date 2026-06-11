"""forge_check — o gate de QUALIDADE da Fábrica, versionado no repo (definition-of-done).

Por que existe: o checker antigo (externo, /tmp) só validava C2/C3/C4 *estrutural* — era
cego ao que de fato quebrou a frota: agentes "eco" genéricos que não executam a capacidade
que prometem, eval theater (casos que só testam o contrato), C3 declarado mas não enforçado,
e perda de target_mode/KPIs/guardians. Aqui esses eixos viram gate.

Modelo RATCHET (catraca): o estado atual imperfeito é congelado em `forge_baseline.json`
(grandfathered). Regras duras reprovam SEMPRE. Regras de catraca reprovam apenas
violações NOVAS (fora do baseline) — então o main segue verde, mas nenhum agente novo/alterado
pode regredir: tem de nascer com handler real, casos de domínio, target_mode etc. O baseline
só encolhe (burn-down). Atualize-o intencionalmente com `--update-baseline`.

Uso:
    python -m nucleo.quality.forge_check                 # gate (exit 1 se houver violação nova)
    python -m nucleo.quality.forge_check --update-baseline   # recongela o baseline (uso raro, deliberado)
"""
from __future__ import annotations
import glob
import json
import os
import re
import sys

import yaml

# Portabilidade: no Windows o stdout default é cp1252 e quebra ao imprimir os
# emojis/acentos do relatório (UnicodeEncodeError). Força UTF-8 com fallback.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GUILDS = os.path.join(ROOT, "nucleo", "guilds")
PRODUCT = os.path.join(ROOT, "nucleo", "product")
BASELINE_PATH = os.path.join(ROOT, "nucleo", "quality", "forge_baseline.json")

GENERIC = {"spec_driven", "guardian_check", "supervisor_route"}
CONTRACT_KEYS = {"agent_id", "handler_kind", "artifact_type", "status", "risk",
                 "requires_human_review", "routed_to", "capabilities_any", "capabilities"}
MIN_CASES = 30

# Descrições de caso "de harness" (geradas em massa por script, não autoradas a partir
# da INTENÇÃO de um cenário). Quando TODOS os casos de um agente compartilham uma dessas
# descrições-template, é forte sinal de que o `expected` é replay do próprio handler
# (eval theater) e não um gabarito independente. Ver os PRs #30/#31/#32 ("...domain eval").
# NÃO casa descrições de domínio reais nem casos numerados-mas-distintos (protegido por
# DISTINCT_DESC_MAX abaixo, ex.: "burn scenario 1..30" tem 30 desc distintos).
_TEMPLATE_DESC = re.compile(
    r"\b(domain eval|varied|smoke test|placeholder|scenario\s*\d+|cen[áa]rio\s*\d+|"
    r"test\s*case\s*\d+|caso\s*\d+|dummy|exemplo\s*\d+)\b", re.I)
TEMPLATE_DESC_FRAC = 0.9   # ≥90% dos casos com desc-template
DISTINCT_DESC_MAX = 2      # e ≤2 descrições distintas no total


def _load(spec_path):
    with open(spec_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _is_billable(spec):
    econ = spec.get("economics") or {}
    return spec.get("ledger") == "billable" or econ.get("ledger") == "billable"


def collect():
    """Varre a frota e devolve (specs_index, dimensões de violação como conjuntos de ids)."""
    hard = {"c2_incompleto": set(), "c3_sem_max_ratio": set(), "expected_proibido": set(),
            "sem_cases": set(), "ids_duplicados": set(),
            "sem_tools": set()}                  # spec sem tools: declaradas (least-privilege)
    ratchet = {"handler_generico": set(),      # agente com handler de eco (capability gap)
               "eval_theater": set(),           # handler determinístico mas casos só de contrato
               "c3_nao_enforcado": set(),        # billable + handler genérico (declara mas não checa)
               "sem_target_mode": set(),         # perdeu o modo-alvo do catálogo
               "abaixo_min_casos": set(),        # < MIN_CASES casos
               "tools_nao_enforcadas": set()}    # toolbox em observe (sem tools_enforce: true)
    index = {}

    paths = glob.glob(os.path.join(GUILDS, "**", "spec.yaml"), recursive=True) + \
            glob.glob(os.path.join(PRODUCT, "**", "spec.yaml"), recursive=True)
    for sp in paths:
        spec = _load(sp)
        aid = spec.get("id") or os.path.basename(os.path.dirname(sp))
        handler = spec.get("act_handler", "")
        index[aid] = handler
        generic = handler in GENERIC

        # --- C2 (dura) ---
        oc = spec.get("outcome_clause") or {}
        if not (oc.get("statement") and len(oc.get("positive_examples") or []) >= 3
                and len(oc.get("negative_examples") or []) >= 3 and oc.get("delivered_event")):
            hard["c2_incompleto"].add(aid)

        # --- C3 (dura): billable precisa de economics.max_ratio ---
        if _is_billable(spec) and (spec.get("economics") or {}).get("max_ratio") is None:
            hard["c3_sem_max_ratio"].add(aid)

        # --- C3 enforcement (catraca): billable com handler genérico não checa C3 em runtime ---
        if _is_billable(spec) and generic:
            ratchet["c3_nao_enforcado"].add(aid)

        # --- capability gap (catraca): handler de eco genérico ---
        if generic:
            ratchet["handler_generico"].add(aid)

        # --- target_mode (catraca): catálogo define modo-alvo de promoção ---
        if not spec.get("target_mode"):
            ratchet["sem_target_mode"].add(aid)

        # --- least-privilege (dura): toda spec declara as tools que o handler usa ---
        if not spec.get("tools"):
            hard["sem_tools"].add(aid)

        # --- least-privilege (catraca): toolbox em observe — agente novo nasce com
        #     tools_enforce: true (violação vira ToolDenied, não só telemetria) ---
        if not spec.get("tools_enforce"):
            ratchet["tools_nao_enforcadas"].add(aid)

        # --- cases ---
        cases_path = os.path.join(os.path.dirname(sp), "evals", "cases.json")
        if not os.path.exists(cases_path):
            hard["sem_cases"].add(aid)
            continue
        cases = json.load(open(cases_path, encoding="utf-8"))
        ids = [c.get("id") for c in cases]
        if len(set(ids)) != len(ids):
            hard["ids_duplicados"].add(aid)
        if len(cases) < MIN_CASES:
            ratchet["abaixo_min_casos"].add(aid)
        for c in cases:
            exp = c.get("expected", {}) or {}
            if any(k in exp for k in ("delivered", "billing_amount")):
                hard["expected_proibido"].add(aid)
        # eval theater (catraca): handler determinístico cujos casos não provam capacidade.
        # Dois sinais: (a) o `expected` não exerce NENHUMA chave de domínio (só contrato), ou
        # (b) os casos foram gerados em massa com descrições-template homogêneas — proxy de
        # `expected` = replay do handler, não gabarito autorado da intenção do cenário.
        if not generic:
            domain_keys = set()
            descs = []
            for c in cases:
                domain_keys |= {k for k in (c.get("expected", {}) or {}) if k not in CONTRACT_KEYS}
                descs.append((c.get("desc") or "").strip())
            distinct = len(set(descs))
            template_frac = (sum(1 for d in descs if _TEMPLATE_DESC.search(d)) / len(descs)
                             if descs else 0.0)
            templated = distinct <= DISTINCT_DESC_MAX and template_frac >= TEMPLATE_DESC_FRAC
            if not domain_keys or templated:
                ratchet["eval_theater"].add(aid)

    return index, hard, ratchet


def main(argv):
    update = "--update-baseline" in argv
    index, hard, ratchet = collect()

    if update:
        json.dump({k: sorted(v) for k, v in ratchet.items()},
                  open(BASELINE_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"forge_baseline.json atualizado ({sum(len(v) for v in ratchet.values())} itens grandfathered).")
        return 0

    baseline = {}
    if os.path.exists(BASELINE_PATH):
        baseline = {k: set(v) for k, v in json.load(open(BASELINE_PATH, encoding="utf-8")).items()}

    failures = []
    # Regras duras: qualquer violação reprova.
    for name, ids in hard.items():
        if ids:
            failures.append((f"DURA: {name}", sorted(ids)))
    # Regras de catraca: só violações NOVAS (fora do baseline) reprovam.
    for name, ids in ratchet.items():
        base = baseline.get(name, set())
        new = ids - base
        fixed = base - ids
        if new:
            failures.append((f"CATRACA(nova): {name}", sorted(new)))
        if fixed:
            print(f"  burn-down: {name} reduziu em {len(fixed)} -> rode --update-baseline p/ travar o ganho: {sorted(fixed)[:8]}")

    total_agents = len(index)
    print(f"\nforge_check — {total_agents} agentes varridos.")
    print("Resumo de catraca (atual / baseline):")
    for name in ratchet:
        print(f"  {name:22s} {len(ratchet[name]):3d} / {len(baseline.get(name, set())):3d}")

    if failures:
        print("\n❌ FORGE CHECK REPROVADO — violações novas (fora do baseline):")
        for label, ids in failures:
            print(f"  [{label}] {len(ids)}: {ids[:12]}{' ...' if len(ids) > 12 else ''}")
        print("\nCorrija (handler real / casos de domínio / target_mode / C2-C3) ou, se for intencional,")
        print("rode `python -m nucleo.quality.forge_check --update-baseline` e justifique no PR.")
        return 1

    print("\n✅ FORGE CHECK OK — sem violações novas; doutrina C2/C3/C4 + qualidade preservadas.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
