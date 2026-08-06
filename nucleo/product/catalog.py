"""Catálogo de agentes de PRODUTO — o que o cliente-bombeiro compra.

O g2-diagnose recomenda a partir daqui: mapeia as dores do cliente -> quais agentes
de gestão ativar. Agnóstico de segmento (toda PME tem caixa, operação, inbox, etc.).
Adicionar um agente de produto = adicionar uma entrada aqui + materializar a spec.
"""

from __future__ import annotations

PRODUCT_AGENTS = [
    {
        "id": "fin-caixa",
        "nome": "Financeiro/Caixa",
        "resolve": "caixa, inadimplência e margem",
        "reconciled_with": "g10-treasury",
        "prioridade": 1,
        "status": "live",
        "trigger": lambda c: True,
    },
    {
        "id": "ops-followup",
        "nome": "Operações/Follow-up",
        "resolve": "tarefas paradas e processos sem dono",
        "reconciled_with": "g9-support-triage",
        "prioridade": 2,
        "status": "live",
        "trigger": lambda c: bool(c.get("lacks_process") or c.get("firefighter")),
    },
    {
        "id": "inbox-triage",
        "nome": "Triagem da caixa de entrada",
        "resolve": "classificar e rotear mensagens/pedidos",
        "reconciled_with": "g9-support-triage",
        "prioridade": 3,
        "status": "live",
        "trigger": lambda c: (c.get("monthly_volume", 0) or 0) >= 50
        or bool(c.get("inbound_channels")),
    },
    {
        "id": "atendimento",
        "nome": "Atendimento/Comercial",
        "resolve": "responder clientes, orçamentos e follow-up de venda",
        "reconciled_with": "g9-tier1-resolver",
        "prioridade": 4,
        "status": "live",
        "trigger": lambda c: bool(c.get("sells_well")),
    },
    {
        "id": "painel-dono",
        "nome": "Painel do dono",
        "resolve": "visibilidade da empresa para o fundador",
        "reconciled_with": "g6-dashboard-builder",
        "prioridade": 5,
        "status": "live",
        "trigger": lambda c: True,
    },
]


def recommend(client: dict) -> list:
    """Devolve os agentes de produto a ativar para este cliente, por prioridade."""
    client = client or {}
    recs = [
        {
            "id": a["id"],
            "nome": a["nome"],
            "resolve": a["resolve"],
            "reconciled_with": a.get("reconciled_with"),
            "prioridade": a["prioridade"],
            "status": a["status"],
        }
        for a in PRODUCT_AGENTS
        if a["trigger"](client)
    ]
    return sorted(recs, key=lambda r: r["prioridade"])
