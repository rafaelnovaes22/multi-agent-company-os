"""Registry / bootstrap config-driven da frota.

Descobre TODAS as specs, materializa cada agente (1 template + N specs), monta um
supervisor por guilda (N workers) e um supervisor-raiz (CEO-OS) que roteia a
intenção em linguagem natural para a guilda certa. É o que faz a frota de ~163
agentes subir sem hardcode.

Coexiste com `supervisor.py` (build_g08_supervisor / build_revenue_funnel /
build_root_supervisor continuam servindo os demos antigos, intactos).
"""

from __future__ import annotations

import glob
import os
import re
import uuid

from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from ..factory.factory import build_from_spec

_GUILD_RE = re.compile(r"(G\d{2})")

# Keywords de roteamento por guilda (config-driven; estende-se acrescentando termos).
GUILD_KEYWORDS = {
    "G00": [
        "nucleo",
        "núcleo",
        "gateway",
        "infra",
        "roteamento",
        "brain",
        "utilitario",
        "utilitário",
    ],
    "G01": [
        "estrategia",
        "estratégia",
        "okr",
        "mercado",
        "vertical",
        "tam",
        "sizing",
        "narrativa",
        "founder",
    ],
    "G02": [
        "produto",
        "discovery",
        "prd",
        "roadmap",
        "feature",
        "lovability",
        "prototipo",
        "protótipo",
        "packaging",
    ],
    "G03": [
        "engenharia",
        "deploy",
        "release",
        "codigo",
        "código",
        "build",
        "ci",
        "contrato",
        "incidente",
    ],
    "G04": ["eval", "qualidade", "regress", "teste", "robustez", "cobertura", "carga"],
    "G05": [
        "seguranca",
        "segurança",
        "fraude",
        "lgpd",
        "pii",
        "ameaca",
        "ameaça",
        "agentshield",
        "injection",
    ],
    "G06": [
        "dados",
        "analytics",
        "metrica",
        "métrica",
        "forecast",
        "north-star",
        "nl2sql",
        "dashboard",
        "drift",
        "coorte",
    ],
    "G07": [
        "growth",
        "marketing",
        "conteudo",
        "conteúdo",
        "comunidade",
        "referral",
        "distribuicao",
        "distribuição",
        "social",
    ],
    "G08": [
        "vendas",
        "lead",
        "qualific",
        "prospec",
        "outbound",
        "receita",
        "funil",
        "pricing",
        "billing",
        "cobranca",
        "cobrança",
        "dunning",
    ],
    "G09": ["suporte", "atendimento", "custops", "voc", "reembolso", "ticket", "churn", "disputa"],
    "G10": [
        "financ",
        "finanças",
        "caixa",
        "fluxo",
        "runway",
        "burn",
        "margem",
        "fiscal",
        "tributo",
        "imposto",
        "conciliacao",
        "conciliação",
        "tesouraria",
        "fatura",
        "nota",
        "economics",
        "unit",
    ],
    "G11": [
        "pessoas",
        "rh",
        "recrutamento",
        "vaga",
        "onboarding",
        "cultura",
        "conhecimento",
        "folha",
        "clima",
    ],
    "G12": [
        "juridico",
        "jurídico",
        "contrato",
        "legal",
        "compliance",
        "regulatorio",
        "regulatório",
        "risco",
        "dpa",
    ],
    "G13": [
        "governanca",
        "governança",
        "constituicao",
        "constituição",
        "promocao",
        "promoção",
        "auditoria",
        "reviewer",
        "gate",
        "outcome",
        "spec",
        "clausula",
        "cláusula",
    ],
    "G14": ["modelo", "model", "llm", "prompt", "inferencia", "inferência", "fine-tune", "ai-ops"],
}


def discover_specs(root: str) -> list:
    """Todos os diretórios de spec sob guilds/**/spec.yaml (mesmo glob dos demos)."""
    return sorted(
        os.path.dirname(p)
        for p in glob.glob(os.path.join(root, "guilds", "**", "spec.yaml"), recursive=True)
    )


def _guild_key(guild_field: str) -> str:
    m = _GUILD_RE.search(guild_field or "")
    return m.group(1) if m else "G00"


def build_fleet(root, llm, brain, store, checkpointer) -> dict:
    """Materializa TODOS os agentes descobertos e agrupa por guilda.
    Retorna {guild_key: [(spec, agent), ...]}."""
    fleet: dict = {}
    for sd in discover_specs(root):
        spec, agent, _gate = build_from_spec(sd, llm, brain, store, checkpointer)
        fleet.setdefault(_guild_key(spec["guild"]), []).append((spec, agent))
    return fleet


# ---------------------------------------------------------------------------
# Supervisor de guilda GENÉRICO (generaliza build_g08_supervisor p/ N workers).
# ---------------------------------------------------------------------------
class GenGuildState(TypedDict, total=False):
    payload: dict
    statement: str
    mode: str
    verbose: bool
    route: str
    results: dict


def _kw_for_worker(spec: dict) -> list:
    """Keywords ingênuas do id (g10-cash-flow -> ['cash','flow']) + tokens do id."""
    return [p for p in spec["id"].split("-")[1:] if len(p) > 2]


def build_guild_supervisor(workers, checkpointer, *, guild_key="G?"):
    """Supervisor de guilda p/ N workers: roteia a intenção a UM worker por keyword
    (derivada do id), com fallback ao 1º worker (ordem). Pula o supervisor declarado."""
    by_id = {spec["id"]: (spec, agent) for spec, agent in workers}
    order = [spec["id"] for spec, _ in workers]
    sup_ids = {sid for sid in order if by_id[sid][0].get("act_handler") == "supervisor_route"}
    routable = [sid for sid in order if sid not in sup_ids] or order

    def route_node(state):
        intent = (state.get("statement") or "").lower()
        # best-match por contagem de keywords (desempate pela ordem dos workers).
        scored = [
            (sum(1 for k in _kw_for_worker(by_id[sid][0]) if k in intent), sid) for sid in routable
        ]
        best = max(scored, default=(0, None))
        chosen = best[1] if best[0] > 0 else (routable[0] if routable else None)
        if state.get("verbose"):
            print(f"  [{guild_key}-sup] intent='{intent}' -> worker: {chosen}")
        return {"route": chosen}

    def dispatch(state, config):
        sid = state.get("route")
        if not sid or sid not in by_id:
            return {"results": {}}
        spec, agent = by_id[sid]
        rid = sid[:8] + "-" + uuid.uuid4().hex[:6]
        sub = {
            "task": {
                "agent_id": spec["id"],
                "guild": spec["guild"],
                "statement": state.get("statement", ""),
                **(state.get("payload") or {}),
            },
            "mode": state.get("mode", "SHADOW"),
            "ledger": spec.get("ledger"),
            "run_id": rid,
            "verbose": state.get("verbose"),
        }
        # config herdado: o worker é subgrafo do supervisor (gate C4 propaga); rid só p/ telemetria.
        out = agent.invoke(sub, config).get("output")
        return {"results": {sid: out}}

    g = StateGraph(GenGuildState)
    g.add_node("route", route_node)
    g.add_node("dispatch", dispatch)
    g.add_edge(START, "route")
    g.add_edge("route", "dispatch")
    g.add_edge("dispatch", END)
    return g.compile(checkpointer=checkpointer, name=f"{guild_key.lower()}-supervisor")


# ---------------------------------------------------------------------------
# Supervisor-raiz (CEO-OS) derivado das guildas descobertas.
# ---------------------------------------------------------------------------
class CompanyState(TypedDict, total=False):
    intent: str
    payload: dict
    route: str
    result: dict
    verbose: bool


def classify_guild(text: str):
    """Classifica a intenção -> guild_key pela maior contagem de keywords. None se nada bate."""
    t = (text or "").lower()
    best, best_hits = None, 0
    for gk, kws in GUILD_KEYWORDS.items():
        hits = sum(1 for k in kws if k in t)
        if hits > best_hits:
            best, best_hits = gk, hits
    return best


def build_company(root, llm, brain, store, checkpointer):
    """Monta a frota inteira: workers -> supervisor por guilda -> CEO-OS.
    Retorna (root_graph, guild_sups, fleet)."""
    fleet = build_fleet(root, llm, brain, store, checkpointer)
    guild_sups = {
        gk: build_guild_supervisor(ws, checkpointer, guild_key=gk) for gk, ws in fleet.items()
    }

    def route_node(state):
        gk = classify_guild(state.get("intent", "")) or (
            sorted(guild_sups)[0] if guild_sups else None
        )
        if state.get("verbose"):
            print(f"  [CEO-OS] intent='{state.get('intent')}' -> guilda: {gk}")
        return {"route": gk}

    def dispatch(state, config):
        gk = state.get("route")
        sup = guild_sups.get(gk)
        if not sup:
            return {"result": {"error": f"sem guilda para '{gk}'"}}
        payload = state.get("payload") or {}
        statement = payload.get("statement") or state.get("intent", "")
        # config herdado: guilda (e seus workers) são subgrafos do CEO-OS — cadeia de 3 níveis
        # compartilha o checkpoint do topo, então interrupt/resume atravessa company->guild->worker.
        out = sup.invoke(
            {
                "payload": payload,
                "statement": statement,
                "mode": state.get("mode", "SHADOW"),
                "verbose": state.get("verbose"),
            },
            config,
        )
        return {"result": {"guild": gk, "results": out.get("results")}}

    g = StateGraph(CompanyState)
    g.add_node("route", route_node)
    g.add_node("dispatch", dispatch)
    g.add_edge(START, "route")
    g.add_edge("route", "dispatch")
    g.add_edge("dispatch", END)
    root_graph = g.compile(checkpointer=checkpointer, name="ceo-os")
    return root_graph, guild_sups, fleet
