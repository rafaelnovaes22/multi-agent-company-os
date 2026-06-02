"""Supervisor de guilda — roteia o trabalho entre os workers da guilda (YC#5: o
'gerente' é um agente). Exemplo: G08 encadeia lead-qualifier -> (se qualified) outbound-sdr.

É a hierarquia que escala para 169: o supervisor-raiz conhece 14 guildas; cada
guilda conhece seus ~12 workers. Aqui um supervisor concreto da G08.
"""
from __future__ import annotations
import uuid

from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END


class GuildState(TypedDict, total=False):
    lead: dict
    mode: str
    verbose: bool
    qualification: dict
    outreach: dict
    route: str


def _rid(prefix: str) -> str:
    return prefix + "-" + uuid.uuid4().hex[:8]


def build_g08_supervisor(qualifier_agent, outbound_agent, spec_q, spec_o, checkpointer):
    """Supervisor da G08: qualifica o lead; se qualified, dispara o outbound-sdr."""

    def qualify(state, config):
        rid = _rid("q")
        sub = {
            "task": {"agent_id": spec_q["id"], "guild": spec_q["guild"],
                     "statement": "Qualificar lead contra o ICP", "lead": state["lead"]},
            "mode": state.get("mode", "SHADOW"), "ledger": spec_q.get("ledger"),
            "run_id": rid, "verbose": state.get("verbose"),
        }
        # Subgrafo real: herda o `config` do pai (NÃO um thread_id isolado) — assim o
        # checkpoint do worker aninha no do supervisor e o interrupt() do gate C4
        # propaga até o topo p/ o DRI aprovar via Command(resume=...). run_id segue
        # único só p/ telemetria (≠ thread_id do checkpointer). Ver tests/test_subgraph_boundary.py.
        res = qualifier_agent.invoke(sub, config)
        q = res.get("output") or {}
        route = "prospect" if q.get("decision") == "qualified" else "stop"
        if state.get("verbose"):
            print(f"  [G08-sup] qualify -> {q.get('decision')} (score {q.get('score')}) => rota: {route}")
        return {"qualification": q, "route": route}

    def prospect(state, config):
        rid = _rid("o")
        sub = {
            "task": {"agent_id": spec_o["id"], "guild": spec_o["guild"],
                     "statement": "Cold B2B outreach", "lead": state["lead"],
                     "qualification": state["qualification"]},
            "mode": state.get("mode", "SHADOW"), "ledger": spec_o.get("ledger"),
            "run_id": rid, "verbose": state.get("verbose"),
        }
        res = outbound_agent.invoke(sub, config)            # subgrafo: config herdado (ver qualify)
        if state.get("verbose"):
            o = res.get("output") or {}
            print(f"  [G08-sup] prospect -> sequência de {len(o.get('sequence', []))} toques para {o.get('account_id')}")
        return {"outreach": res.get("output")}

    g = StateGraph(GuildState)
    g.add_node("qualify", qualify)
    g.add_node("prospect", prospect)
    g.add_edge(START, "qualify")
    g.add_conditional_edges("qualify", lambda s: s.get("route", "stop"),
                            {"prospect": "prospect", "stop": END})
    g.add_edge("prospect", END)
    return g.compile(checkpointer=checkpointer, name="g08-supervisor")


class FunnelState(TypedDict, total=False):
    entity: dict          # o lead/cliente que atravessa o funil
    mode: str
    verbose: bool
    qualification: dict
    diagnostic: dict
    outreach: dict
    route: str


def build_revenue_funnel(qualifier, diagnoser, outbound, spec_q, spec_d, spec_o, checkpointer):
    """Funil de receita cross-guild (G08 x G02): qualificar -> (qualified) diagnosticar ->
    (go) prospectar. Cada etapa tem um gate; o que reprova para o funil ali (sem queimar a próxima)."""

    def _invoke(agent, spec, extra_task, state, config):
        rid = _rid(spec["id"][:6])
        sub = {
            "task": {"agent_id": spec["id"], "guild": spec["guild"], **extra_task},
            "mode": state.get("mode", "SHADOW"), "ledger": spec.get("ledger"),
            "run_id": rid, "verbose": state.get("verbose"),
        }
        # config herdado do pai: cada etapa é um subgrafo real, gate C4 propaga (ver build_g08_supervisor).
        res = agent.invoke(sub, config)
        return res.get("output") or {}

    def qualify(state, config):
        q = _invoke(qualifier, spec_q, {"statement": "Qualificar lead", "lead": state["entity"]}, state, config)
        route = "diagnose" if q.get("decision") == "qualified" else "stop"
        if state.get("verbose"):
            print(f"  [funil] 1/3 qualify -> {q.get('decision')} (score {q.get('score')}) => {route}")
        return {"qualification": q, "route": route}

    def diagnose(state, config):
        d = _invoke(diagnoser, spec_d, {"statement": "Diagnosticar (C1)", "client": state["entity"]}, state, config)
        route = "prospect" if str(d.get("recommendation", "")).startswith("go") else "stop"
        if state.get("verbose"):
            b = d.get("baseline", {})
            print(f"  [funil] 2/3 diagnose -> {d.get('recommendation')} "
                  f"(baseline R${b.get('baseline_cost_brl_month')}/mês) => {route}")
        return {"diagnostic": d, "route": route}

    def prospect(state, config):
        o = _invoke(outbound, spec_o,
                    {"statement": "Cold outreach", "lead": state["entity"],
                     "qualification": state["qualification"], "diagnostic": state["diagnostic"]}, state, config)
        if state.get("verbose"):
            print(f"  [funil] 3/3 prospect -> sequência de {len(o.get('sequence', []))} toques "
                  f"(pitch: {o.get('sku_pitch')})")
        return {"outreach": o}

    g = StateGraph(FunnelState)
    g.add_node("qualify", qualify)
    g.add_node("diagnose", diagnose)
    g.add_node("prospect", prospect)
    g.add_edge(START, "qualify")
    g.add_conditional_edges("qualify", lambda s: s.get("route", "stop"),
                            {"diagnose": "diagnose", "stop": END})
    g.add_conditional_edges("diagnose", lambda s: s.get("route", "stop"),
                            {"prospect": "prospect", "stop": END})
    g.add_edge("prospect", END)
    return g.compile(checkpointer=checkpointer, name="revenue-funnel")


# --------------------------------------------------------------------------
# Supervisor-raiz (CEO-OS) — roteia intenção -> guilda. YC#5 (sem middleware humano).
# --------------------------------------------------------------------------
class RootState(TypedDict, total=False):
    intent: str
    payload: dict
    route: str
    result: dict
    verbose: bool


_ROUTING = [
    ("revenue", ["qualific", "lead", "prospec", "outbound", "receita", "funil", "vender"]),
    ("diagnose", ["diagn", "baseline", "sku", "dor do cliente"]),
    ("governance", ["valid", "outcome", "spec", "cláusula", "clausula", "gate"]),
    ("market", ["mercado", "vertical", "intel", "tam", "sizing", "concorr"]),
]


def classify_intent(text: str) -> str:
    t = (text or "").lower()
    for route, kws in _ROUTING:
        if any(k in t for k in kws):
            return route
    return "unknown"


def build_root_supervisor(routes: dict, checkpointer):
    """routes: {nome_da_rota: callable(payload)->dict}. O root classifica a intenção e despacha."""

    def route_node(state):
        r = classify_intent(state.get("intent", ""))
        if state.get("verbose"):
            print(f"  [root] intent='{state.get('intent')}' -> guilda: {r}")
        return {"route": r}

    def dispatch(state):
        fn = routes.get(state.get("route"))
        res = fn(state.get("payload", {})) if fn else {"error": f"sem rota para '{state.get('route')}'"}
        return {"result": res}

    g = StateGraph(RootState)
    g.add_node("route", route_node)
    g.add_node("dispatch", dispatch)
    g.add_edge(START, "route")
    g.add_edge("route", "dispatch")
    g.add_edge("dispatch", END)
    return g.compile(checkpointer=checkpointer, name="root-supervisor")
