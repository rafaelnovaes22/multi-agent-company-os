"""AgentShield — scaneia as specs/configs de TODA a frota em busca de riscos
(secrets, PII, guardians ausentes, eval ausente, C2/C3/C7/C8). Padrão ECC.

Mercado-agnóstico: valida a higiene dos agentes independentemente do vertical.
Severidades: high (bloqueia promoção), med (corrigir), low (informativo/Sprint 0).
"""

from __future__ import annotations

import glob
import json
import os
import re

import yaml

from ..kernel.guardians import validate_outcome_clause

SECRET_PATTERNS = [
    (r"sk-[A-Za-z0-9]{16,}", "chave estilo OpenAI"),
    (r"AKIA[0-9A-Z]{16}", "AWS access key"),
    (
        r"(?i)(api[_-]?key|secret|password|senha|token)\s*[:=]\s*['\"][^'\"]{8,}",
        "credencial inline",
    ),
]
EMAIL = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
CPF = r"\d{3}\.\d{3}\.\d{3}-\d{2}"
VENDOR_SDKS = ("openai", "anthropic", "stripe", "twilio", "whatsapp-web")


def _read(p):
    return open(p, encoding="utf-8").read() if os.path.exists(p) else ""


def scan_agent(spec_dir):
    spec = yaml.safe_load(_read(os.path.join(spec_dir, "spec.yaml"))) or {}
    aid = spec.get("id", os.path.basename(spec_dir))
    blob = " ".join(
        [_read(os.path.join(spec_dir, f)) for f in ("spec.yaml", "soul.md", "memory.md")]
    )
    f = []

    v = validate_outcome_clause(spec)
    if not v["valid"]:
        f.append(("high", "C2", f"outcome_clause inválida: {v['missing']}"))
    if spec.get("ledger") == "billable" and not (spec.get("economics") or {}).get("max_ratio"):
        f.append(("high", "C3", "billable sem economics.max_ratio"))
    if not spec.get("guardians"):
        f.append(("med", "GUARDIANS", "sem guardians declarados"))

    cases_p = os.path.join(spec_dir, "evals", "cases.json")
    n = len(json.load(open(cases_p, encoding="utf-8"))) if os.path.exists(cases_p) else 0
    if n == 0:
        f.append(("high", "C4", "sem eval-suite"))
    elif n < 30:
        f.append(("low", "C4", f"eval-suite com {n} casos (<30; aceitável só em Sprint 0)"))

    for pat, lbl in SECRET_PATTERNS:
        if re.search(pat, blob):
            f.append(("high", "SECRETS", f"possível {lbl}"))
    if re.search(CPF, blob):
        f.append(("high", "PII", "CPF presente em soul/memory"))
    emails = [e for e in re.findall(EMAIL, blob) if not e.endswith("example.com")]
    if emails:
        f.append(("med", "PII", f"e-mail real em soul/memory: {emails[:1]}"))

    tools = " ".join(spec.get("tools", []) or []).lower()
    for sdk in VENDOR_SDKS:
        if sdk in tools:
            f.append(("med", "C7", f"SDK de fornecedor citado em tools: {sdk} (use abstração)"))

    return aid, f


def scan_fleet(guilds_root):
    return [
        scan_agent(os.path.dirname(p))
        for p in sorted(glob.glob(os.path.join(guilds_root, "**", "spec.yaml"), recursive=True))
    ]


def scan_c8(code_root):
    """C8 — procura hardcode por tenant no código de produção."""
    pat = re.compile(r"if\s+tenant\w*\s*==|switch\s*\(\s*tenant|clients/\{[^}]*\}")
    hits = []
    for p in glob.glob(os.path.join(code_root, "**", "*.py"), recursive=True):
        if pat.search(_read(p)):
            hits.append(os.path.relpath(p, code_root))
    return hits
