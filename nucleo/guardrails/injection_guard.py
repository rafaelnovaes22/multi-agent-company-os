"""Camada 1 anti-injection da frota (stdlib-only, sem LLM).

3 camadas do NÚCLEO:
  1. injection_guard (este módulo): bloqueia 32 padrões no input da task, log JSON (C6).
  2. soul.md + outcome_clause da spec: restrições de persona/contrato (C2).
  3. guardians (self-critique) + gate C4: pós-filtro e decisão de entrega/cobrança.

Enforcement em runtime: `gate()` (nucleo/kernel/gates.py) chama `screen_task`
antes de qualquer entrega — task com injection cai em `delivered=False`,
`billing_amount=0`, `status="blocked"`. Nunca alega LLM: motivo determinístico
`injection:<ID>`.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone

PATTERNS: list[dict[str, str]] = [
    {"id": "INJ01", "name": "ignore-previous-instructions", "regex": r"ignor(e|a|e as) (as )?(instrucoes|instru[cç][oõ]es|previous instructions)"},
    {"id": "INJ02", "name": "system-prompt-leak", "regex": r"(mostre|revele|exiba|show).{0,30}(system prompt|prompt do sistema|instrucao do sistema)"},
    {"id": "INJ03", "name": "jailbreak-dan", "regex": r"\bDAN\b.{0,20}(mode|jailbreak)|jailbreak"},
    {"id": "INJ04", "name": "roleplay-evil", "regex": r"(aja como|act as|finja ser|pretend to be).{0,30}(hacker|vilao|sem limites|without limits)"},
    {"id": "INJ05", "name": "prompt-injection-pt", "regex": r"(esqueca|ignore).{0,20}(tudo|regras|guardrails)"},
    {"id": "INJ06", "name": "developer-mode", "regex": r"(modo desenvolvedor|developer mode|dev mode)"},
    {"id": "INJ07", "name": "base64-exfil", "regex": r"(codifique|encode).{0,20}base64"},
    {"id": "INJ08", "name": "translate-instruction", "regex": r"(traduza|translate).{0,20}(instrucoes|instructions)"},
    {"id": "INJ09", "name": "override-guardian", "regex": r"(desative|disable|bypass|contorne).{0,20}(guardian|filtro|filter|moderacao|gate)"},
    {"id": "INJ10", "name": "xss-script-tag", "regex": r"<\s*script[^>]*>"},
    {"id": "INJ11", "name": "xss-img-onerror", "regex": r"<\s*img[^>]*onerror"},
    {"id": "INJ12", "name": "xss-svg-onload", "regex": r"<\s*svg[^>]*onload"},
    {"id": "INJ13", "name": "xss-javascript-uri", "regex": r"javascript\s*:"},
    {"id": "INJ14", "name": "xss-event-handler", "regex": r"on(click|load|error|mouseover|focus)\s*="},
    {"id": "INJ15", "name": "sql-injection-union", "regex": r"union\s+select"},
    {"id": "INJ16", "name": "sql-injection-drop", "regex": r"drop\s+table"},
    {"id": "INJ17", "name": "sql-injection-or-1", "regex": r"or\s+1\s*=\s*1"},
    {"id": "INJ18", "name": "path-traversal", "regex": r"\.\./\.\./"},
    {"id": "INJ19", "name": "ssrf-localhost", "regex": r"(localhost|127\.0\.0\.1|169\.254\.169\.254)"},
    {"id": "INJ20", "name": "prompt-leak-delimiter", "regex": r"(###|```).{0,10}(system|instrucao)"},
    {"id": "INJ21", "name": "token-smuggling", "regex": r"(seu token|api[_-]?key|secret).{0,15}(e |is |:)"},
    {"id": "INJ22", "name": "phishing-redirect", "regex": r"(wa\.me|whatsapp).{0,20}(http|bit\.ly|tinyurl)"},
    {"id": "INJ23", "name": "instruction-in-image", "regex": r"(leia|read).{0,15}(qr ?code|imagem anexa).{0,15}(instrucao|instruction)"},
    {"id": "INJ24", "name": "multilang-bypass-en", "regex": r"from now on.{0,20}(you are|act as)"},
    {"id": "INJ25", "name": "multilang-bypass-es", "regex": r"(a partir de ahora|de ahora en adelante).{0,20}(eres|actua como)"},
    {"id": "INJ26", "name": "refund-scam", "regex": r"(reembolso|refund).{0,20}(cartao|pix|conta).{0,20}(envie|informe)"},
    {"id": "INJ27", "name": "pii-harvest-doc", "regex": r"(informe|digite|envie).{0,20}(cpf|rg|cnpj)"},
    {"id": "INJ28", "name": "pii-harvest-card", "regex": r"(numero do cartao|card number| CVV |cvv)"},
    {"id": "INJ29", "name": "chain-of-thought-leak", "regex": r"(mostre seu raciocinio|show your reasoning|chain.of.thought)"},
    {"id": "INJ30", "name": "tool-use-escalation", "regex": r"(execute|rode|run).{0,20}(comando|command|shell|rm -rf)"},
    {"id": "INJ31", "name": "persona-grandma", "regex": r"(vozinha|grandma).{0,25}(dormir|sleep).{0,25}(receita|napalm|windows key)"},
    {"id": "INJ32", "name": "indirect-order", "regex": r"(mensagem no whatsapp|forward).{0,20}(diz para|instructs to).{0,20}(transferir|pagar|pay)"},
]

_COMPILED: list[tuple[str, re.Pattern[str]]] = [(p["id"], re.compile(p["regex"], re.IGNORECASE)) for p in PATTERNS]


def scan_injection(text: str | None) -> dict[str, str | bool | None]:
    """Varre um texto; retorna {"blocked": bool, "pattern": id|None}."""
    for pid, rx in _COMPILED:
        if rx.search(text or ""):
            return {"blocked": True, "pattern": pid}
    return {"blocked": False, "pattern": None}


def _iter_strings(obj: object, depth: int = 0) -> list[str]:
    """Coleta strings de task dict (recursivo, 3 níveis — evita custo em payload grande)."""
    found: list[str] = []
    if isinstance(obj, str):
        return [obj]
    if depth >= 3 or not isinstance(obj, (dict, list)):
        return found
    items = obj.values() if isinstance(obj, dict) else obj
    for v in items:
        found.extend(_iter_strings(v, depth + 1))
    return found


def screen_task(task: dict | None) -> dict[str, str | bool | None]:
    """Camada 1 sobre a task inteira. Log JSON (C6) no primeiro match."""
    for text in _iter_strings(task or {}):
        hit = scan_injection(text)
        if hit["blocked"]:
            log = {"event": "injection_blocked", "pattern": hit["pattern"],
                   "input": (text or "")[:80], "ts": datetime.now(timezone.utc).isoformat()}
            print(json.dumps(log), file=sys.stderr)
            return hit
    return {"blocked": False, "pattern": None}
