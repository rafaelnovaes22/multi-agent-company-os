"""PoC — subgrafo REAL vs `.invoke()` imperativo na fronteira supervisor->worker (G08).

Demonstração executável do problema que motivou a correção aplicada em
nucleo/kernel/supervisor.py e nucleo/kernel/registry.py: o human-in-the-loop
(gate C4 em ASSISTED, via `interrupt()` em kernel/gates.py:39) só SOBREVIVE à
fronteira supervisor->worker quando o worker é um SUBGRAFO real (o sub-invoke
herda o `config`/checkpoint do pai). No padrão antigo — `.invoke()` com um
`thread_id` ISOLADO — o `interrupt` era ENGOLIDO e o funil avançava sobre uma
PROPOSTA não aprovada, furando o gate.

A trava de regressão correspondente vive em tests/test_subgraph_boundary.py
(que prova o mesmo contra o build_g08_supervisor de produção).

Rode:  python docs/poc/subgraph_g08.py
"""

from __future__ import annotations

import os
import sys
import uuid

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # acentos no Windows (vide foundry_check)

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))  # docs/poc -> docs -> raiz do repo
sys.path.insert(0, REPO)

from langgraph.checkpoint.memory import MemorySaver  # noqa: E402
from langgraph.graph import END, START, StateGraph  # noqa: E402
from langgraph.types import Command  # noqa: E402
from typing_extensions import TypedDict  # noqa: E402

from nucleo.factory.factory import load_spec  # noqa: E402
from nucleo.kernel.agent_template import build_agent  # noqa: E402
from nucleo.kernel.brain import Brain, FileStore  # noqa: E402
from nucleo.kernel.providers.llm import get_llm  # noqa: E402

NUCLEO = os.path.join(REPO, "nucleo")
BRAIN_DIR = os.path.join(NUCLEO, ".brain")
SPEC_DIR = os.path.join(NUCLEO, "guilds", "g08_vendas", "g8-lead-qualifier")

LEAD = {
    "id": "L-700",
    "company": "Decisao Humana",
    "revenue_brl_year": 2_500_000,
    "founder_led": True,
    "sells_well": True,
    "lacks_process": True,
    "firefighter": True,
}


class GuildState(TypedDict, total=False):
    lead: dict
    mode: str
    qualification: dict
    route: str
    worker_paused: bool  # o worker sinalizou interrupt() durante o qualify?


def _worker_input(state: dict) -> dict:
    """GuildState -> AgentState de entrada do worker (mapeamento manual, igual ao
    que os supervisores já fazem hoje)."""
    return {
        "task": {
            "agent_id": "g8-lead-qualifier",
            "guild": "G08-vendas-receita",
            "statement": "Qualificar lead contra o ICP",
            "lead": state["lead"],
        },
        "mode": state.get("mode", "ASSISTED"),
        "ledger": "billable",
        "run_id": "w-" + uuid.uuid4().hex[:6],
        "verbose": False,
    }


# ---------------------------------------------------------------------------
# Cenário A — IMPERATIVO (o vício antigo): thread_id ISOLADO
# ---------------------------------------------------------------------------
def build_supervisor_imperative(worker, checkpointer):
    def qualify(state):
        rid = "iso-" + uuid.uuid4().hex[:8]  # <-- thread_id ISOLADO
        res = worker.invoke(_worker_input(state), config={"configurable": {"thread_id": rid}})
        paused = "__interrupt__" in res  # o worker pausou...
        q = res.get("output") or {}  # ...mas o interrupt é descartado
        route = "prospect" if q.get("decision") == "qualified" else "stop"
        return {"qualification": q, "route": route, "worker_paused": paused}

    g = StateGraph(GuildState)
    g.add_node("qualify", qualify)
    g.add_edge(START, "qualify")
    g.add_edge("qualify", END)
    return g.compile(checkpointer=checkpointer, name="g08-imperative")


# ---------------------------------------------------------------------------
# Cenário B — SUBGRAFO REAL (a correção aplicada): o worker herda o config do PAI
# ---------------------------------------------------------------------------
def build_supervisor_subgraph(worker, checkpointer):
    def qualify(state, config):  # <-- recebe o config do PAI
        res = worker.invoke(_worker_input(state), config)  # <-- herda thread + checkpoint_ns
        paused = "__interrupt__" in res
        q = res.get("output") or {}
        route = "prospect" if q.get("decision") == "qualified" else "stop"
        return {"qualification": q, "route": route, "worker_paused": paused}

    g = StateGraph(GuildState)
    g.add_node("qualify", qualify)
    g.add_edge(START, "qualify")
    g.add_edge("qualify", END)
    return g.compile(checkpointer=checkpointer, name="g08-subgraph")


def _mk_worker(checkpointer):
    brain = Brain(os.path.join(BRAIN_DIR, "events"))
    store = FileStore(os.path.join(BRAIN_DIR, "store"))
    llm = get_llm("worker")
    spec = load_spec(SPEC_DIR)
    return build_agent(spec, llm, brain, store, checkpointer)


def run_imperative():
    print("\n" + "=" * 72)
    print("CENÁRIO A — supervisor IMPERATIVO (vício antigo, thread_id isolado)")
    print("=" * 72)
    worker = _mk_worker(MemorySaver())
    sup = build_supervisor_imperative(worker, MemorySaver())
    cfg = {"configurable": {"thread_id": "sup-A"}}
    res = sup.invoke({"lead": LEAD, "mode": "ASSISTED"}, config=cfg)

    top_interrupt = "__interrupt__" in res
    q = res.get("qualification") or {}
    delivered = q.get("delivered") is True
    print(f"  worker pausou internamente (interrupt)? .......... {res.get('worker_paused')}")
    print(f"  o supervisor (topo) EXPÔS __interrupt__ ao DRI? .. {top_interrupt}")
    print(f"  output aprovado pelo DRI (delivered=True)? ....... {delivered}")
    print(f"  ...mas o supervisor já roteou o funil para ....... {res.get('route')!r}")
    print("  >> PIOR que engolir: o worker PAUSOU para aprovação, mas o sub-invoke")
    print("     devolveu a PROPOSTA pendente (decision=qualified) junto com o interrupt.")
    print("     O supervisor leu a proposta como decisão final e avançou o funil")
    print("     SEM o DRI aprovar (delivered≠True). O gate C4 foi FURADO.")
    return {"top_interrupt": top_interrupt, "delivered": delivered, "route": res.get("route")}


def run_subgraph():
    print("\n" + "=" * 72)
    print("CENÁRIO B — supervisor com SUBGRAFO real (config herdado — a correção)")
    print("=" * 72)
    worker = _mk_worker(None)
    sup = build_supervisor_subgraph(worker, MemorySaver())
    cfg = {"configurable": {"thread_id": "sup-B"}}

    res = sup.invoke({"lead": LEAD, "mode": "ASSISTED"}, config=cfg)
    top_interrupt = "__interrupt__" in res
    print(f"  o supervisor (topo) EXPÔS __interrupt__ ao DRI? .. {top_interrupt}")
    if top_interrupt:
        payload = res["__interrupt__"][0].value
        prop = payload.get("proposed_output") or {}
        print(
            f"  PAUSA propagou do worker -> topo: agente={payload.get('agent')} "
            f"decision={prop.get('decision')} score={prop.get('score')}"
        )
        res = sup.invoke(Command(resume={"approved": True}), config=cfg)

    q = res.get("qualification") or {}
    delivered = q.get("delivered") is True
    print(
        f"  após resume(approved=True): output ENTREGUE? ..... {delivered} "
        f"(delivered={q.get('delivered')})"
    )
    print(
        f"  decision/score/track ............................. "
        f"{q.get('decision')}/{q.get('score')}/{q.get('track')}"
    )
    print(f"  rota decidida .................................... {res.get('route')}")
    print("  >> O interrupt SOBREVIVEU à fronteira: o DRI decidiu, o worker retomou")
    print("     no ponto exato e SÓ ENTÃO entregou. Human-in-the-loop PRESERVADO.")
    return {"top_interrupt": top_interrupt, "delivered": delivered, "route": res.get("route")}


def main():
    a = run_imperative()
    b = run_subgraph()
    print("\n" + "=" * 72)
    print("VEREDITO")
    print("=" * 72)
    print(
        f"  A (imperativo): DRI consultado? {a['top_interrupt']!s:5} | "
        f"funil avançou p/ {a['route']!r} com aprovação? {a['delivered']}"
    )
    print(
        f"  B (subgrafo):   DRI consultado? {b['top_interrupt']!s:5} | "
        f"entregou só após aprovação (delivered)? {b['delivered']}"
    )
    ok = (not a["top_interrupt"]) and (not a["delivered"]) and b["top_interrupt"] and b["delivered"]
    print(
        f"\n  PoC {'CONFIRMA' if ok else 'NÃO confirmou'} a tese: subgrafo real preserva o gate C4 "
        f"(entrega só após o DRI);\n  `.invoke()` isolado o fura (avança o funil sobre proposta pendente)."
    )


if __name__ == "__main__":
    main()
