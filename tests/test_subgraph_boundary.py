"""Trava de regressão da fronteira supervisor->worker (gate C4 / human-in-the-loop).

Prova, com as peças reais (lead-qualifier em ASSISTED), que:
  - o padrão IMPERATIVO antigo (thread_id isolado) FURA o gate: não propaga o
    interrupt ao topo e avança sobre uma proposta NÃO aprovada;
  - o padrão SUBGRAFO real (config herdado) — aplicado em kernel/supervisor.py e
    kernel/registry.py — PRESERVA o gate: propaga o interrupt e só entrega
    (delivered=True) após o resume do DRI.

Os toy-supervisores abaixo são auto-contidos (espelham o vício vs a correção); os
testes test_real_* exercitam o build_g08_supervisor DE PRODUÇÃO. Demonstração
executável correspondente: docs/poc/subgraph_g08.py.
"""
from __future__ import annotations

import os
import uuid

from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from nucleo.kernel.brain import Brain, FileStore
from nucleo.kernel.providers.llm import get_llm
from nucleo.factory.factory import build_from_spec, load_spec
from nucleo.kernel.agent_template import build_agent
from nucleo.kernel.supervisor import build_g08_supervisor

_NUCLEO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "nucleo")
_BRAIN = os.path.join(_NUCLEO, ".brain")
_Q_SPEC = os.path.join(_NUCLEO, "guilds", "g08_vendas", "g8-lead-qualifier")
_O_SPEC = os.path.join(_NUCLEO, "guilds", "g08_vendas", "g8-outbound-sdr")

LEAD = {"id": "L-700", "company": "Decisao Humana", "revenue_brl_year": 2_500_000,
        "founder_led": True, "sells_well": True, "lacks_process": True, "firefighter": True}


class _GuildState(TypedDict, total=False):
    lead: dict
    mode: str
    qualification: dict
    route: str
    worker_paused: bool


def _mk_worker(checkpointer):
    brain = Brain(os.path.join(_BRAIN, "events"))
    store = FileStore(os.path.join(_BRAIN, "store"))
    llm = get_llm("worker")
    return build_agent(load_spec(_Q_SPEC), llm, brain, store, checkpointer)


def _worker_input(state):
    return {"task": {"agent_id": "g8-lead-qualifier", "guild": "G08-vendas-receita",
                     "statement": "Qualificar lead contra o ICP", "lead": state["lead"]},
            "mode": state.get("mode", "ASSISTED"), "ledger": "billable",
            "run_id": "w-" + uuid.uuid4().hex[:6], "verbose": False}


def _build_imperative(worker, checkpointer):
    """Vício antigo: thread_id ISOLADO em cada sub-invoke."""
    def qualify(state):
        rid = "iso-" + uuid.uuid4().hex[:8]
        res = worker.invoke(_worker_input(state), config={"configurable": {"thread_id": rid}})
        q = res.get("output") or {}
        return {"qualification": q, "worker_paused": "__interrupt__" in res,
                "route": "prospect" if q.get("decision") == "qualified" else "stop"}
    g = StateGraph(_GuildState)
    g.add_node("qualify", qualify)
    g.add_edge(START, "qualify")
    g.add_edge("qualify", END)
    return g.compile(checkpointer=checkpointer, name="g08-imperative")


def _build_subgraph(worker, checkpointer):
    """Correção: o worker herda o config do PAI (subgrafo real)."""
    def qualify(state, config):
        res = worker.invoke(_worker_input(state), config)
        q = res.get("output") or {}
        return {"qualification": q, "worker_paused": "__interrupt__" in res,
                "route": "prospect" if q.get("decision") == "qualified" else "stop"}
    g = StateGraph(_GuildState)
    g.add_node("qualify", qualify)
    g.add_edge(START, "qualify")
    g.add_edge("qualify", END)
    return g.compile(checkpointer=checkpointer, name="g08-subgraph")


# ---------------------------------------------------------------------------
def test_imperative_supervisor_fura_humanloop():
    """Documenta o BUG do padrão antigo: o interrupt do worker não chega ao topo
    e o funil avança sem aprovação. NÃO é o comportamento desejado."""
    worker = _mk_worker(MemorySaver())
    sup = _build_imperative(worker, MemorySaver())
    cfg = {"configurable": {"thread_id": "t-imp"}}

    res = sup.invoke({"lead": LEAD, "mode": "ASSISTED"}, config=cfg)

    assert res.get("worker_paused") is True, "o worker deveria ter pausado no gate ASSISTED"
    assert "__interrupt__" not in res, "o padrão imperativo NÃO propaga o interrupt (bug)"
    assert (res.get("qualification") or {}).get("delivered") is not True, "nada foi aprovado..."
    assert res.get("route") == "prospect", "...mas o funil avançou mesmo assim (gate furado)"


def test_subgraph_supervisor_preserva_gate():
    """A correção: o subgrafo real propaga o interrupt ao topo e só entrega após
    o DRI aprovar via Command(resume=...) no thread do TOPO."""
    worker = _mk_worker(None)
    sup = _build_subgraph(worker, MemorySaver())
    cfg = {"configurable": {"thread_id": "t-sub"}}

    res = sup.invoke({"lead": LEAD, "mode": "ASSISTED"}, config=cfg)

    assert "__interrupt__" in res, "o subgrafo deve propagar o interrupt ao topo (DRI consultado)"
    payload = res["__interrupt__"][0].value
    assert payload.get("type") == "approval_required"
    assert payload.get("agent") == "g8-lead-qualifier"
    assert (res.get("qualification") or {}).get("delivered") is not True

    res = sup.invoke(Command(resume={"approved": True}), config=cfg)
    q = res.get("qualification") or {}
    assert q.get("delivered") is True, "após aprovação, o worker deve entregar"
    assert q.get("decision") == "qualified"
    assert res.get("route") == "prospect"


def test_subgraph_dri_rejeita_descarta():
    """Simetria do gate: se o DRI REJEITA, o output é descartado (não entrega)."""
    worker = _mk_worker(None)
    sup = _build_subgraph(worker, MemorySaver())
    cfg = {"configurable": {"thread_id": "t-sub-rej"}}

    res = sup.invoke({"lead": LEAD, "mode": "ASSISTED"}, config=cfg)
    assert "__interrupt__" in res

    res = sup.invoke(Command(resume={"approved": False}), config=cfg)
    assert (res.get("qualification") or {}).get("delivered") is not True, "rejeição não pode entregar"


# ---------------------------------------------------------------------------
# Mesma prova, mas no SUPERVISOR DE PRODUÇÃO (build_g08_supervisor).
# ---------------------------------------------------------------------------
def _real_g08_supervisor():
    brain = Brain(os.path.join(_BRAIN, "events"))
    store = FileStore(os.path.join(_BRAIN, "store"))
    llm = get_llm("worker")
    cp = MemorySaver()
    spec_q, qualifier, _ = build_from_spec(_Q_SPEC, llm, brain, store, cp)
    spec_o, outbound, _ = build_from_spec(_O_SPEC, llm, brain, store, cp)
    return build_g08_supervisor(qualifier, outbound, spec_q, spec_o, cp)


def test_real_g08_supervisor_propaga_gate_assisted():
    """Regressão do código de produção: build_g08_supervisor em ASSISTED deve
    PAUSAR no DRI (interrupt no topo) e só entregar/encadear após o resume."""
    sup = _real_g08_supervisor()
    cfg = {"configurable": {"thread_id": "real-g08"}}

    res = sup.invoke({"lead": LEAD, "mode": "ASSISTED", "verbose": False}, config=cfg)
    assert "__interrupt__" in res, "o supervisor real deve propagar o interrupt do gate C4"
    assert res["__interrupt__"][0].value.get("agent") == "g8-lead-qualifier"
    assert res.get("outreach") in (None, {}), "não pode prospectar antes de o DRI aprovar"

    res = sup.invoke(Command(resume={"approved": True}), config=cfg)
    q = res.get("qualification") or {}
    assert q.get("delivered") is True and q.get("decision") == "qualified"


def test_real_g08_supervisor_shadow_nao_pausa():
    """Em SHADOW (sem gate humano) o supervisor real roda ponta-a-ponta sem interrupt."""
    sup = _real_g08_supervisor()
    cfg = {"configurable": {"thread_id": "real-g08-shadow"}}
    res = sup.invoke({"lead": LEAD, "mode": "SHADOW", "verbose": False}, config=cfg)
    assert "__interrupt__" not in res
    assert (res.get("qualification") or {}).get("decision") == "qualified"
