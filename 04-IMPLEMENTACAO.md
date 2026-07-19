# 04 — Implementação: código LangGraph, roadmap e riscos

## 1. Stack e estrutura do repositório

| Camada | Tecnologia | Justificativa |
|---|---|---|
| Runtime de agentes | **LangGraph** (Python) + LangGraph Platform p/ deploy/cron | grafos com estado, checkpoint durável, `interrupt` nativo |
| Estado/memória | **Postgres** (`PostgresSaver` checkpointer + `PostgresStore`) | durabilidade, resumibilidade, memória longa namespaced |
| Company Brain | Postgres (event store) + **pgvector** (índice) + grafo (Neo4j/age opcional) | empresa queryable (YC#3) |
| LLM | abstração `LLMProvider` (C7); default Claude (Opus p/ supervisores/Guardians, Sonnet/Haiku p/ workers) | portabilidade + custo |
| Tracing | **LangSmith** (ou Langfuse) | C6, drift, auditoria |
| Governança | **agent-governance-framework** portado (Constitution, commands, Guardians) | C1–C8 |
| Aprendizado | self-harness (foundry) + instincts (ECC) | evolução |
| Fila/cron | LangGraph Platform crons / Railway (Hermes) | learning loop, auditoria mensal |
| Front operador | Operator Console (Next.js) sobre o Brain | dashboards YC#3 |

```
nucleo/
├── constitution/            # C1-C8 + doutrina YC (versionado, SemVer)
├── brain/                   # event store, indexer, nl2sql, schemas
├── kernel/
│   ├── state.py             # AgentState (Pydantic)
│   ├── self_harness.py      # wrapper: load_context / snapshot / emit_artifact
│   ├── agent_template.py    # fábrica de subgrafo de worker
│   ├── supervisor.py        # supervisor de guilda + supervisor-raiz
│   ├── gates.py             # interrupt() dos gates C4
│   └── providers/           # C7: llm/, infra/, integrations/, auth/
├── guilds/
│   ├── g1_strategy/ ... g13_governance/
│   │   └── <agent_id>/
│   │       ├── spec.yaml     # contrato (C1/C2/C3/C5)
│   │       ├── soul.md       # SOUL
│   │       ├── memory.md     # MEMORY (§ confidence)
│   │       ├── instincts/    # ECC
│   │       └── evals/        # ≥30 casos (C4)
├── factory/                 # diagnose→spec→plan→implement→eval→promote
├── learning/                # hermes loop, /evolve
├── reviewer/                # DeepAgent mensal (foundry)
└── console/                 # Operator Console (YC#3)
```

---

## 2. O kernel em código (LangGraph)

### 2.1 Estado universal do agente — `kernel/state.py`
```python
from typing import Annotated, Literal
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from pydantic import BaseModel

Mode = Literal["SHADOW", "PILOT", "ASSISTED", "AUTONOMOUS"]

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    task: dict                       # outcome solicitado (cláusula C2)
    context: dict                    # SOUL + MEMORY + instincts + skills L0/L1 (cache C5)
    scratchpad: list                 # raciocínio intermediário
    output: dict | None              # resultado (só "entregue" se modo permite)
    citations: list                  # artefatos do Brain usados (queryable)
    cost_tokens: int                 # C3 / token-accounting
    mode: Mode                       # C4
    run_id: str
    ledger: Literal["operating", "billable"]   # governança econômica (YC#7 × C3)
```

### 2.2 Self-harness wrapper — `kernel/self_harness.py`
O coração da evolução. Carrega memória no início, emite artefato + snapshot no fim. Usa o `store` do LangGraph.
```python
from langgraph.store.base import BaseStore

def load_context(state: AgentState, *, store: BaseStore) -> dict:
    aid = state["task"]["agent_id"]
    ns = ("agent", aid)
    soul   = store.get(ns, "soul")
    memory = store.search(ns, query=state["task"]["statement"], limit=12)  # fatos relevantes
    instincts = store.search(("instincts", aid), query=state["task"]["statement"], limit=8)
    skills = store.search(("skills", state["task"]["guild"]), query=state["task"]["statement"])
    # C5: L0/L1 (dna/icp/offerings) vêm cacheados via helper pattern
    return {"context": {"soul": soul, "memory": memory,
                        "instincts": instincts, "skills": skills}}

def emit_artifact(state: AgentState, *, store: BaseStore) -> dict:
    # C6 + YC#3: toda ação produz artefato no Company Brain
    brain_emit_event({
        "actor": state["task"]["agent_id"], "action": "run_completed",
        "run_id": state["run_id"], "output": state["output"],
        "cost_tokens": state["cost_tokens"], "mode": state["mode"],
        "ledger": state["ledger"], "citations": state["citations"],
    })
    return {}

def snapshot(state: AgentState, *, store: BaseStore) -> dict:
    # Stop-hook equivalente: grava snapshot p/ o learning loop processar depois
    store.put(("snapshots", state["task"]["agent_id"]), state["run_id"], {
        "task": state["task"], "output": state["output"],
        "scratchpad": state["scratchpad"], "mode": state["mode"],
        "cost_tokens": state["cost_tokens"],
    })
    return {}
```

### 2.3 Template do worker — `kernel/agent_template.py`
Uma função que recebe a spec e **devolve um subgrafo compilado**. É isto que a Fábrica chama 150 vezes.
```python
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import create_react_agent
from langgraph.types import interrupt, Command
from kernel.self_harness import load_context, emit_artifact, snapshot
from kernel.providers.llm import get_llm
from kernel.gates import needs_human_gate

def build_agent(spec: dict, tools: list, checkpointer, store):
    llm = get_llm(role=spec.get("model_role", "worker"))      # C7
    react = create_react_agent(llm, tools)                    # loop tool-use

    def act(state: AgentState):
        result = react.invoke({"messages": state["messages"], "context": state["context"]})
        return {"messages": result["messages"], "output": result.get("structured"),
                "cost_tokens": state["cost_tokens"] + result["usage"]["total_tokens"]}

    def self_critique(state: AgentState):
        # Guardian da guilda critica ANTES de entregar (closed loop YC#2)
        verdict = run_guardians(spec["guardians"], state)
        return {"scratchpad": state["scratchpad"] + [verdict]}

    def gate(state: AgentState):
        # C4: SHADOW nunca entrega; ASSISTED pede aprovação humana via interrupt
        if state["mode"] == "SHADOW":
            return Command(goto="emit_artifact", update={"output": _mark_undelivered(state["output"])})
        if state["mode"] == "ASSISTED":
            decision = interrupt({                       # ← human-in-the-loop (DRI)
                "type": "approval_required", "agent": spec["id"],
                "proposed_output": state["output"], "cost": state["cost_tokens"],
            })
            if not decision["approved"]:
                return Command(goto=END, update={"output": None})
        return Command(goto="emit_artifact")             # AUTONOMOUS/PILOT entregam

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
    g.add_edge("emit_artifact", "snapshot")
    g.add_edge("snapshot", END)
    return g.compile(checkpointer=checkpointer, store=store, name=spec["id"])
```

### 2.4 Supervisor de guilda e supervisor-raiz — `kernel/supervisor.py`
Hierárquico. O supervisor-raiz só conhece 13 guildas; cada guilda só conhece seus ~12 workers.
```python
from langgraph_supervisor import create_supervisor
from kernel.providers.llm import get_llm

def build_guild(guild_id: str, worker_graphs: list, checkpointer, store):
    return create_supervisor(
        agents=worker_graphs,                       # subgrafos da guilda
        model=get_llm(role="supervisor"),           # Opus
        prompt=GUILD_PROMPT[guild_id],              # roteia + aplica orçamento da guilda
        output_mode="last_message",
    ).compile(checkpointer=checkpointer, store=store, name=guild_id)

def build_root(guild_graphs: list, checkpointer, store):
    return create_supervisor(
        agents=guild_graphs,                        # as 13 guildas como subgrafos
        model=get_llm(role="root"),                 # Opus, contexto estratégico L0
        prompt=ROOT_PROMPT,                         # "o que precisa ser feito? qual guilda?"
        output_mode="full_history",
    ).compile(checkpointer=checkpointer, store=store, name="root-supervisor")
```
> Para fan-out paralelo (ex.: rodar 8 code-reviewers de linguagem ao mesmo tempo) usa-se `Send("reviewer", sub_state)` dentro do supervisor da G3 — map-reduce nativo do LangGraph.

### 2.5 A Fábrica — `factory/` (materializa o catálogo)
```python
def factory_build_all(specs_dir, tools_registry, checkpointer, store):
    guilds = {}
    for spec_path in glob(f"{specs_dir}/**/spec.yaml"):
        spec = load_yaml(spec_path)
        # GATE de fábrica (C1/C2/C4) ANTES de materializar:
        assert po_guardian_ok(spec)          # C1/C2: cláusula de outcome válida
        assert eval_suite_size(spec) >= 30   # C4
        if spec["ledger"] == "billable":
            assert unit_economist_ok(spec)   # C3 (só billable)
        tools = resolve_tools(spec["tools"], tools_registry)   # C7
        agent = build_agent(spec, tools, checkpointer, store)
        guilds.setdefault(spec["guild"], []).append(agent)
    guild_graphs = [build_guild(gid, ws, checkpointer, store) for gid, ws in guilds.items()]
    return build_root(guild_graphs, checkpointer, store)
```
> Na fase 2 (fabricação em massa) cada `build_agent` roda em **worktree isolado** (padrão ECC) para gerar/testar em paralelo sem conflito.

### 2.6 O loop de aprendizado — `learning/hermes_loop.py` (cron)
Roda fora do caminho de execução (LangGraph Platform cron / Railway). Fecha o loop.
```python
def hermes_learning_cron(store):
    for snap in store.search(("snapshots",), filter={"processed": False}):
        instincts = extract_instincts(snap)            # ECC: padrões auto-extraídos
        novelty   = assess_novelty(snap, store)        # vs MEMORY atual
        keep      = decide_persist(snap, instincts, novelty)   # custo/valor (C3-aware)
        if keep:
            facts = format_facts(keep, confidence=mode_to_confidence(snap["mode"]))
            propose_memory_pr(snap["agent_id"], facts)  # § [confidence] ... (C6: source_run_id)
            notify_operator(snap["agent_id"], facts)
        mark_processed(store, snap)

def evolve_cron(store):
    # /evolve: instincts recorrentes em ≥N agentes → skill compartilhada da guilda/empresa
    clusters = cluster_instincts_across_agents(store, min_agents=3)
    for c in clusters:
        skill = synthesize_skill(c)
        open_skill_promotion_gate(skill)               # passa por gate antes de virar L0/L1
```

---

## 3. Roadmap até o MVP (com 150+ agentes)

A vantagem early-stage (YC#8): greenfield, sem legado. Construímos a **Fábrica primeiro**, depois ela fabrica os 150.

### Fase 0 — Kernel (Semanas 0–2) · ~5 agentes
**Entrega:** Constituição-runtime; Company Brain (event store + checkpointer + store em Postgres); `self_harness.py`, `agent_template.py`, `supervisor.py`, `gates.py`; telemetria LangSmith; supervisor-raiz vazio; **a Fábrica** mínima (`build_agent` + `factory_build_all`).
**Critério de saída:** 1 agente "hello-outcome" passa por todo o grafo (load→act→gate→emit→snapshot) em SHADOW, com trace no LangSmith e artefato no Brain.

### Fase 1 — Agentes que fazem agentes (Semanas 2–5) · ~35 agentes (SHADOW)
**Entrega:** Guildas **G13 Governança** (os 10 Guardians como nós validadores), **G3 Engenharia**, **G4 Qualidade/Eval** (eval-harness + quality-gate do ECC), **G5 Segurança** (AgentShield). Estes são "a Fábrica em forma agêntica".
**Critério de saída:** a Fábrica consegue receber uma spec nova e produzir um agente em SHADOW **sem humano escrever código** (YC#4 software factory); gates C4 funcionam com `interrupt`.

### Fase 2 — Fabricação em massa (Semanas 5–9) · **150+ agentes** (SHADOW/PILOT)
**Entrega:** escrever as **specs + eval-cases** das guildas de negócio (G1, G2, G6–G12) e deixar a Fábrica materializar em paralelo (worktrees). Company Brain povoado; Operator Console no ar.
**Critério de saída:** 150+ agentes instanciados, todos com trace, eval-suite ≥30, SOUL/MEMORY iniciais; supervisor-raiz roteia para as 13 guildas; nenhum entrega/cobra ainda (SHADOW).

### Fase 3 — MVP (Semanas 9–12) · 150+ (modo misto)
**Entrega:** rodar SHADOW dos agentes do caminho-crítico do produto; medir `agreement_rate`; promover via gates (PILOT→ASSISTED→AUTONOMOUS) os que passam; hardening econômico (Unit-Economist nos billable); **launch do MVP**.
**Critério de saída:** produto no ar operado pela frota; agentes do caminho-crítico em ASSISTED/AUTONOMOUS; dashboards de receita/custo/qualidade vivos; primeira auditoria do reviewer agendada.

### Fase ∞ — Evolução (contínuo)
Learning loop diário; `/evolve` semanal; reviewer mensal; drift detection rebaixa modos automaticamente; novas guildas/agentes via Fábrica conforme o negócio cresce.

```
Fase0  Fase1            Fase2                   Fase3            ∞
kernel │ 35 ag (Fábrica) │ 150+ ag (SHADOW)       │ MVP (misto)    │ evolução
─────► │ ──────────────► │ ─────────────────────► │ ─────────────► │ ───────►
  ▲ a Fábrica            ▲ a Fábrica produz        ▲ gates promovem  ▲ loops
    nasce primeiro         os 150 de specs           os que provam     fecham
```

---

## 4. Riscos e mitigação (detalhado)

| # | Risco | Impacto | Mitigação no NÚCLEO |
|---|---|---|---|
| R1 | 150 agentes autônomos = erro/custo em cascata | alto | **nascem em SHADOW** (output não entregue/cobrado); promoção só por gate C4; drift rebaixa automaticamente AUTONOMOUS→ASSISTED |
| R2 | Conta de tokens descontrolada | alto | dois livros-razão; **orçamento por guilda** no supervisor (corta execução ao estourar); C3 trava billable; token-cost-accountant rateia em tempo real |
| R3 | Aprendizado polui memória (fato ruim / PII / hardcode) | alto | confidence-score + `assess_novelty` + g5-lgpd-privacy + lint C8 do tenant-curator; fato só sobe de confiança com o modo |
| R4 | Loops/deadlocks entre agentes | médio | hierarquia (raiz→guilda→worker), limite de profundidade/recursão, checkpointer + timeouts, supervisor corta ciclos |
| R5 | Governança vira gargalo a 150 agentes | médio | gates **só** onde há entrega/cobrança/autonomia; SHADOW é livre; cross-approval só no caminho-crítico; Guardians autônomos quando provados |
| R6 | Alucinação em decisões de negócio | alto | self-critique obrigatório + citações do Brain (toda saída cita fonte); `interrupt` humano em ASSISTED; eval-suite por agente |
| R7 | Lock-in de provider (LLM/pagamento/infra) | médio | C7: toda dependência em camada de abstração; specs não citam provider |
| R8 | Camada humana fina vira gargalo de aprovação | médio | só DRIs aprovam, e só na sua guilda; AUTONOMOUS remove aprovação rotineira; fila de gates priorizada no Console |
| R9 | Segurança: injection/secrets em 150 superfícies | alto | G5 AgentShield faz scan contínuo de todos os agentes/MCP/hooks; prompt-injection-guard nas entradas |
| R10 | Auditabilidade falha (desvio outcomes↔traces) | alto | C6 enforced: sem artefato não conta; reviewer mensal compara traces×DB (desvio >1% = FAIL) |

---

## 5. Métricas de sucesso (o que o Operator Console mostra)

| Dimensão | Métrica | Alvo MVP |
|---|---|---|
| Escala | agentes instanciados | ≥150 antes do launch |
| Autonomia | % de agentes do caminho-crítico em ASSISTED+AUTONOMOUS | ≥ 60% no launch |
| Aprendizado | fatos promovidos `local→shadow→assisted` / mês; skills criadas por `/evolve` | tendência crescente |
| Qualidade | agreement_rate médio em SHADOW; pass-rate de eval-suite | ≥85% p/ promover |
| Economia | razão custo/preço (billable); custo-token vs headcount-equivalente (operating) | billable ≤25%; operating ROI > 1 |
| Legibilidade (YC#3) | % de ações com artefato no Brain; desvio outcomes↔traces | ~100%; desvio <1% |
| Velocidade (YC#5) | nº de humanos por outcome; lead time spec→agente-em-produção | decrescente |

---

## 6. O que escrever a seguir (handoff para a construção)

1. **`constitution/`** — portar `CONSTITUTION.md` (C1–C8) do foundry + anexar doutrina YC (Y1–Y8 de [02](02-ARQUITETURA.md) §3).
2. **`kernel/`** — implementar os 6 arquivos de §2 (state, self_harness, agent_template, supervisor, gates, providers).
3. **`factory/`** — portar os commands do foundry (`diagnose/spec/plan/implement/eval/promote`) como passos da Fábrica.
4. **`guilds/*/spec.yaml`** — escrever as **150 specs** (o trabalho dos ICs; cada spec = §B.1 de [03](03-CATALOGO-AGENTES.md)). Começar por G13/G3/G4/G5 (fase 1).
5. **`learning/`** — `hermes_loop.py` + `evolve_cron.py` (fundir self-harness do foundry com instincts do ECC).
6. **`console/`** — dashboards sobre o Brain (YC#3).

> Pré-requisito de pessoas (camada humana fina, YC#6): 1 **AI Founder** + ~6 **DRIs** (um por cluster de guildas) + ~4 **ICs/builder-operators** que escrevem specs e operam a Fábrica. ~11 humanos operando 150+ agentes.
