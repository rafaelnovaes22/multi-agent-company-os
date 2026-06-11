"""Template universal de agente — a função que a Fábrica chama N vezes.

Recebe uma spec + dependências (llm, brain, store, checkpointer) e devolve um
subgrafo LangGraph COMPILADO. O grafo é IGUAL para todos os agentes:

    load_context -> act -> self_critique -> gate -> (emit_artifact -> snapshot) | END

O miolo do `act` é plugável por `act_handler` na spec (ver kernel/skills.py) —
é o que faz 1 template servir para os ~169 agentes (C8). Ver 03-CATALOGO §B.
"""
from __future__ import annotations
from langgraph.graph import StateGraph, START, END

from .state import AgentState
from . import self_harness as sh
from .gates import gate as gate_node
from .guardians import run_guardians
from .skills import get_handler


def _brief(out: dict) -> str:
    if not out:
        return "(sem output)"
    if "verdict" in out:
        return f"verdict.valid={out['verdict'].get('valid')}"
    if "decision" in out:
        return f"decision={out['decision']} score={out.get('score')} track='{out.get('track')}'"
    return str(out)[:60]


def build_agent(spec: dict, llm, brain, store, checkpointer):
    """Materializa um agente (subgrafo LangGraph) a partir da spec."""
    aid = spec["id"]
    handler_name = spec.get("act_handler", "outcome_clause_validator")
    handler = get_handler(handler_name)

    def load_context(state):
        return sh.load_context(state, store=store, spec=spec)

    def act(state):
        res = handler(state, llm=llm, store=store, spec=spec)
        if state.get("verbose"):
            print(f"  -> act[{handler_name}]: {_brief(res.get('output'))} (llm={llm.name})")
        return {
            "output": res.get("output"),
            "cost_tokens": state.get("cost_tokens", 0) + res.get("cost_tokens", 0),
            "citations": res.get("citations", []),
        }

    def self_critique(state):
        crit = run_guardians(spec.get("guardians", []), state)
        if state.get("verbose"):
            print(f"  -> self_critique: guardians ok={crit['ok']} notes={crit['notes']}")
        return {"scratchpad": (state.get("scratchpad") or []) + [crit]}

    def gate(state):
        return gate_node(state, spec=spec, store=store)

    def emit_artifact(state):
        return sh.emit_artifact(state, brain=brain, spec=spec)

    def snapshot(state):
        return sh.snapshot(state, store=store, spec=spec)

    g = StateGraph(AgentState)
    g.add_node("load_context", load_context)
    g.add_node("act", act)
    g.add_node("self_critique", self_critique)
    g.add_node("gate", gate)
    g.add_node("emit_artifact", emit_artifact)
    g.add_node("snapshot", snapshot)

    g.add_edge(START, "load_context")
    g.add_edge("load_context", "act")
    g.add_edge("act", "self_critique")
    g.add_edge("self_critique", "gate")
    g.add_conditional_edges("gate", lambda s: s.get("_gate", "proceed"),
                            {"proceed": "emit_artifact", "halt": END})
    g.add_edge("emit_artifact", "snapshot")
    g.add_edge("snapshot", END)

    return g.compile(checkpointer=checkpointer, name=aid)
