"""Estado universal do agente (C5/C6). Um único schema para TODOS os agentes —
worker e supervisor. Ver 04-IMPLEMENTACAO.md §2.1."""
from __future__ import annotations
from typing import Optional
from typing_extensions import TypedDict


class AgentState(TypedDict, total=False):
    task: dict                 # outcome solicitado (cláusula C2): agent_id, guild, statement, target_spec...
    context: dict              # SOUL + MEMORY + instincts carregados do store (C5)
    scratchpad: list           # raciocínio intermediário / vereditos dos guardians
    output: Optional[dict]     # resultado (só "delivered" se o modo permitir)
    citations: list            # artefatos do Brain usados (empresa queryable / C6)
    cost_tokens: int           # token-accounting (C3 / YC#7)
    mode: str                  # C4: SHADOW | PILOT | ASSISTED | AUTONOMOUS
    ledger: str                # "operating" (ROI-vs-headcount) | "billable" (C3 <= 25%)
    run_id: str
    verbose: bool              # imprime os passos do loop na demo
    _gate: str                 # roteamento interno do gate: "proceed" | "halt"
