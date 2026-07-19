# 02 — Arquitetura do NÚCLEO

## 1. As 7 camadas

O NÚCLEO é o sistema operacional da empresa (YC #1 — "AI as OS, not tool"). Tudo flui por ele.

```
┌───────────────────────────────────────────────────────────────────────────┐
│ L6 · AUDITORIA & EVOLUÇÃO   reviewer mensal independente (DeepAgent),       │
│                            drift detection, /evolve (instincts→skills)      │  ← closed loop da empresa (YC#2)
├───────────────────────────────────────────────────────────────────────────┤
│ L5 · TELEMETRIA & OPERATOR  LangSmith (traces LLM) + event store +          │
│                            Operator Console / dashboards (Hermes)           │  ← queryable (YC#3) / C6
├───────────────────────────────────────────────────────────────────────────┤
│ L4 · GUARDIANS              PO, Unit-Economist, Promotion-Officer,          │
│                            Artifact-Architect, Observability, Security,     │  ← constituição C1-C8 em runtime
│                            Tenant-Curator, Eval-Engineer + AgentShield      │
├───────────────────────────────────────────────────────────────────────────┤
│ L3 · A FÁBRICA (AIOS)       diagnose→spec→plan→implement→eval→promote;      │
│                            eval-harness + quality-gate; fabrica agentes     │  ← software factory (YC#4)
├───────────────────────────────────────────────────────────────────────────┤
│ L2 · SELF-HARNESS WRAPPER   SOUL/MEMORY/SKILLS/LOOP/CRONS + instincts;      │
│                            envolve TODO agente; loop de aprendizado         │  ← agentes que evoluem
├───────────────────────────────────────────────────────────────────────────┤
│ L1 · ORQUESTRAÇÃO (LangGraph)  supervisor-raiz → 13 supervisores de guilda  │
│                            → 150+ workers (subgrafos); interrupt nos gates  │  ← runtime / no middleware (YC#5)
├───────────────────────────────────────────────────────────────────────────┤
│ L0 · COMPANY BRAIN          event store append-only + grafo de             │
│                            conhecimento + índice vetorial + store/          │  ← legível p/ IA (YC#3)
│                            checkpointer LangGraph (Postgres)                │
├───────────────────────────────────────────────────────────────────────────┤
│ L-1 · CONSTITUIÇÃO-RUNTIME  C1-C8 + doutrina YC, versionada (SemVer/ADR)    │  ← trilho imutável
└───────────────────────────────────────────────────────────────────────────┘
```

### L-1 · Constituição-runtime
A `CONSTITUTION` do foundry (C1–C8) portada para um objeto carregado pelo kernel e lido por todo Guardian em runtime. **Estendida** com a doutrina YC como princípios operacionais (Y1–Y8, ver §3). Mudança = ADR + bump SemVer + notificação ao reviewer.

### L0 · Company Brain — a empresa queryable (YC #3)
A fonte única de verdade que torna a empresa **legível para IA**. Três stores:
- **Event store (append-only)** — cada ação de cada agente emite um evento estruturado (`actor`, `action`, `inputs_hash`, `outputs`, `cost`, `latency`, `trace_id`, `ts`). É a espinha dorsal de C6 e da auditoria.
- **Knowledge graph + índice vetorial** — sobre todos os artefatos (ADRs, specs, runs, PRDs, contratos, comms, métricas). Permite "perguntar à empresa". Notetakers de reunião e e-mails alimentam aqui (YC: "record meetings, embed agents in comms").
- **LangGraph `store` + `checkpointer` (Postgres)** — memória de longo prazo dos agentes (store) e estado durável/resumível das execuções (checkpointer). É o que dá *durabilidade* a workflows longos e human-in-the-loop.

> Regra de ouro (YC): *"toda ação importante produz um artefato que a inteligência no centro da empresa pode aprender"*. No NÚCLEO isso é **enforced**: o self-harness wrapper (L2) emite o artefato no fim de cada execução; sem artefato, a execução não conta (espelha C6).

### L1 · Orquestração — LangGraph (detalhe em §2)
### L2 · Self-harness wrapper (detalhe em §4)
### L3 · A Fábrica (detalhe em §5)
### L4 · Guardians — os 10 do foundry como **nós validadores** + AgentShield. Rodam nos gates (não só no build).
### L5 · Telemetria & Operator Console (detalhe em §6)
### L6 · Auditoria & Evolução — reviewer mensal + drift + `/evolve` (detalhe em §7)

---

## 2. Topologia LangGraph — como 150+ agentes não viram caos

Padrão **hierárquico de supervisores** (supervisor-of-supervisors). Três níveis:

```
                         ┌──────────────────────────┐
                         │   SUPERVISOR-RAIZ (CEO-OS)│  roteia intenção → guilda
                         │   "o que precisa ser      │  aplica orçamento / prioridade
                         │    feito? quem faz?"      │  (substitui middleware humano)
                         └────────────┬──────────────┘
            ┌─────────────┬───────────┼───────────┬──────────────┐
            ▼             ▼           ▼           ▼              ▼
     ┌────────────┐┌────────────┐┌──────────┐┌──────────┐ ... (13 guildas)
     │ SUP Produto││ SUP Engenh.││ SUP Growth││ SUP CustOps│
     └─────┬──────┘└─────┬──────┘└────┬─────┘└────┬──────┘
       ┌───┴───┐    ┌────┴────┐   ┌───┴───┐   ┌───┴───┐
       ▼   ▼   ▼    ▼    ▼    ▼   ▼   ▼   ▼   ▼   ▼   ▼
     workers (subgrafos LangGraph) — ~10-14 por guilda → 150+
```

**Por que hierárquico (e não um grafo plano de 150 nós):**
- O supervisor-raiz só conhece **13 guildas**, não 150 agentes → roteamento tratável e barato em tokens.
- Cada supervisor de guilda conhece só os seus ~12 workers.
- Espelha um organograma — mas o "gerente" é um agente (YC #5: "no human middleware").

**Primitivas LangGraph usadas:**

| Primitiva | Uso no NÚCLEO |
|---|---|
| `StateGraph` + state tipado (Pydantic/TypedDict) | cada agente e cada supervisor é um grafo com estado |
| **subgrafos** (compilar um grafo e usá-lo como nó) | cada worker é um subgrafo reusável; cada guilda é um subgrafo |
| `Command(goto=..., update=...)` | supervisor decide próximo nó e atualiza estado (roteamento dinâmico) |
| `Send(node, state)` | **fan-out paralelo** (map-reduce): ex. 8 reviewers de linguagem em paralelo |
| `interrupt(payload)` + `Command(resume=...)` | **human-in-the-loop** nos gates C4 (aprovação de DRI/founder) |
| `checkpointer` (Postgres) | execução **durável e resumível** — agente pausa no gate por dias e retoma |
| `store` (namespaced) | memória longa por agente (SOUL/MEMORY/instincts) |
| `create_react_agent` (prebuilt) | base do loop tool-use de cada worker |
| `langgraph-supervisor` / `create_supervisor` | base dos supervisores de guilda |

> Esqueletos de código em [04-IMPLEMENTACAO.md](04-IMPLEMENTACAO.md).

---

## 3. Mapa dos 8 princípios YC → decisões de arquitetura

Cada princípio das imagens vira uma decisão **concreta e verificável** no NÚCLEO.

| # | Princípio YC | Decisão de arquitetura no NÚCLEO | Onde vive | Como verifico |
|---|---|---|---|---|
| **Y1** | **AI as OS, not tool** | O NÚCLEO **é** o SO da empresa; todo workflow/decisão passa pela camada inteligente (supervisor-raiz). Não há processo "fora" do grafo. | L-1…L6 | nenhum processo de negócio sem um grafo correspondente; auditoria detecta "shadow process" |
| **Y2** | **Closed loops everywhere** | Todo agente é um loop fechado: emite output → mede outcome → ajusta. Três loops: per-run (self-harness), per-mês (reviewer/drift), per-evolução (`/evolve`). | L2, L6 | cada agente tem eval contínuo + snapshot; drift monitorado |
| **Y3** | **Make your company queryable** | Company Brain (event store + grafo + vetor). Toda ação → artefato. Notetakers e comms alimentam. Dashboards no Operator Console. | L0, L5 | desvio outcomes↔traces > 1% = FAIL (C6); cobertura de artefatos |
| **Y4** | **Software factories** | A Fábrica (L3): humanos escrevem **spec + eval-cases**; agentes geram implementação e iteram até passar (eval-harness/quality-gate). Humano define o quê e julga; agente faz o código. | L3 | todo agente nasce de spec+evals; `quality-gate` determinístico |
| **Y5** | **No more human middleware** | Supervisores são **agentes**, não gerentes. Humanos só nos nós DRI/IC/founder via `interrupt`. Roteamento = grafo. | L1 | organograma = grafo; nº de humanos por outcome ↓; "every layer of human routing removed = speed gain" |
| **Y6** | **3 arquétipos** (IC/builder-operator, DRI, AI founder) | Mapeados a **quem aprova qual gate** e **quem possui qual guilda** (ver §3.1). IC traz protótipo funcional, não slide. | L1 (interrupt), L4 | matriz de aprovação por arquétipo; cross-approval (C4 Gate 5) |
| **Y7** | **Token-max, not headcount-max** | Dois livros-razão (OPERATING vs BILLABLE). Agentes internos rodam quentes (ROI-vs-headcount); só billable é limitado por C3. | L4 (Unit-Economist) | C3 aplicado só a `ledger:billable`; conta de API alta é aceita no operating |
| **Y8** | **Early-stage advantage** | Greenfield: nascemos queryable, artifact-rich, agent-first. Sem legado para desfazer. A Fábrica fabrica os 150 desde o dia 1. | roadmap (fase 0-3) | nenhum processo humano-legado a migrar; convicção construída "sentando com os agentes" |

### 3.1 Os 3 arquétipos YC ↔ modelo operacional humano

A camada humana é **fina e fixa**. Mapeia para os arquétipos da imagem (per Jack Dorsey):

| Arquétipo YC | Quem é | No NÚCLEO faz | Gate que aprova |
|---|---|---|---|
| **AI Founder** | fundador(es) da venture | define convicção/estratégia, "senta com os agentes", possui o supervisor-raiz e a Guilda de Estratégia | Gate final de AUTONOMOUS de agentes do caminho-crítico; mudanças na Constituição (ADR) |
| **DRI** (Directly Responsible Individual) | 1 humano por guilda/outcome | dono do outcome da guilda; aprova promoções (C4) da sua guilda; "one person, one outcome, no hiding" | Gate 5 (cross-approval) de promoção dos agentes da guilda |
| **IC / builder-operator** | poucos engenheiros/operadores | escreve **spec + eval-cases**, opera a Fábrica, traz **protótipo funcional** (não pitch deck); revisa output de agentes | Gate de pre-merge / aprovação ASSISTED |

> "You cannot outsource your conviction on these tools — develop it by sitting with coding agents." (YC). No NÚCLEO, o AI Founder **usa a Fábrica diretamente** no Operator Console.

---

## 4. O Self-harness wrapper — como agentes evoluem aprendendo

Todo agente (worker e supervisor) é **embrulhado** pelo mesmo wrapper. Não é opcional. Implementa os 5 pilares do self-harness do foundry + os instincts do ECC, sobre o `store` do LangGraph.

```
                 ┌──────────────── ciclo de uma execução (run) ────────────────┐
 entrada → [load_context] → [plan] → [act (tool loop)] → [self-critique] →      │
           carrega de store:                              (Guardian da guilda)  │
           SOUL + MEMORY + instincts + skills aprendidas          │            │
                                                                  ▼            │
                                              [emit_artifact] → Company Brain   │
                                                                  │            │
                                              [snapshot] → docs/learnings/...   │
                 └──────────────────────────────────────────────┼─────────────┘
                                                                 ▼
                              ┌─────────── LOOP DE APRENDIZADO (assíncrono) ──────────┐
                              │ cron (LangGraph Platform / Railway):                   │
                              │  1. parse_snapshot   2. extract_instincts (ECC)        │
                              │  3. assess_novelty (vs MEMORY)  4. decide_persist      │
                              │  5. propose memory-PR  6. notify (Telegram/Slack)      │
                              │  → merge → store atualizado → próxima run já sabe mais │
                              └────────────────────────────────────────────────────────┘
```

**As três velocidades de memória (a fusão foundry × ECC × LangGraph):**

| Velocidade | Fonte | Mecanismo | Confiança |
|---|---|---|---|
| **Quente / automática** | **ECC instincts** | auto-extraídos por sessão, com confidence-score; baixa fricção | `local` |
| **Curada / durável** | **foundry self-harness** | snapshot → Hermes → assess_novelty → **PR de memória** | sobe com o modo: `shadow→assisted→autonomous` |
| **Persistente / compartilhada** | **`/evolve` (ECC) + skills (foundry)** | instincts recorrentes em vários agentes → **skill da guilda/empresa** (L0/L1) | promovida via gate |

**Formato de fato (do foundry, mantido):**
```
§ [confidence:{local|shadow|assisted|autonomous}] [YYYY-MM-DD] [run:{id}] {fato acionável}
```
Regras C1/C5/C6/C7/C8 preservadas: nada de PII, nada de hardcode de tenant, markdown agnóstico de modelo, todo fato com `source_run_id`.

**Por que isto É "evoluir aprendendo" (requisito do desafio):**
- Um agente em SHADOW só tem fatos `confidence:local/shadow`. Ao passar nos gates e virar ASSISTED/AUTONOMOUS, seus fatos ganham confiança e ele recebe mais autonomia. **Aprender = subir na escada de confiança = ganhar autonomia.**
- `/evolve` faz o aprendizado de *um* agente virar capacidade de *toda a guilda* — a empresa fica mais inteligente, não só o indivíduo.

---

## 5. A Fábrica (L3) — software factory com governança (YC #4)

Pipeline que **fabrica e promove** agentes. Reusa os commands do foundry + eval-harness do ECC. **Humanos escrevem spec + tests; agentes escrevem a implementação e iteram até passar** (definição YC de "software factory").

```
/diagnose ─► /spec ─► /plan ─► /implement ─► /eval ─► /pre-merge ─► /promote
  (C1)       (C2)     (C5/C7)   (gera código)  (C4)     (gates)      (C4 transição)
   │           │                                │                       │
 PO-Guard   PO-Guard                       Eval-Engineer          Promotion-Officer
                                          + eval-harness(ECC)     + cross-approval
                                          + quality-gate(ECC)     (DRI ≠ founder)
```

**Saída:** um novo agente (subgrafo LangGraph) materializado a partir do template ([03](03-CATALOGO-AGENTES.md) §Anatomia), já com SOUL/MEMORY iniciais, eval-suite (≥30 casos), telemetria e modo `SHADOW`. **Ninguém escreve 150 agentes à mão — a Fábrica os produz a partir de specs.**

A fabricação em massa (fase 2 do roadmap) usa **isolamento por worktree** (padrão ECC) para gerar muitos agentes em paralelo sem conflito.

---

## 6. Telemetria, economia e o Operator Console (L5)

- **C6 bifurcado:** agentes `ai_enabled=true` → tracing LLM (LangSmith/Langfuse) + analytics; agentes `ai_enabled=false` → audit-log + métricas. Desvio outcomes↔traces > 1% = FAIL.
- **Operator Console (Hermes/dashboard):** painéis com *tudo* (YC #3) — receita, eng, vendas, ops, custo de tokens por guilda, taxa de concordância por agente em SHADOW, fila de gates aguardando aprovação humana.
- **Modelo econômico (ver README §tensão):** todo agente declara `ledger: operating | billable`. Unit-Economist aplica C3 só a `billable`. `operating` é avaliado por **ROI-vs-headcount** (token-max, YC #7). Dois painéis de custo distintos no Console.

---

## 7. Auditoria & Evolução (L6) — o loop da empresa (YC #2)

- **Reviewer mensal independente** (DeepAgent, do foundry) audita C1–C8 + extensões, amostra 5–10% dos outcomes (traces vs DB), gera `docs/audits/{YYYY-MM}.md`.
- **Drift detection:** quality (acurácia ↓≥5pp/mês), cost (↑≥15%/mês), volume (±30%/mês), prompt (`prompt_hash` muda sem recalc de economia). Drift → rebaixa modo do agente automaticamente (AUTONOMOUS→ASSISTED) até reauditoria.
- **`/evolve` (ECC):** roda periodicamente, agrupa instincts recorrentes em skills candidatas; skills passam por gate antes de entrar em L0/L1.

---

## 8. Riscos arquiteturais e mitigação (resumo; detalhe em [04](04-IMPLEMENTACAO.md) §riscos)

| Risco | Mitigação |
|---|---|
| 150 agentes autônomos = explosão de erro/custo | nascem em SHADOW (output não entregue/cobrado); promoção só por gate; drift rebaixa |
| Conta de tokens descontrolada | dois livros-razão; orçamento por guilda no supervisor; C3 trava billable |
| Aprendizado polui memória (fatos ruins/PII) | confidence-score + assess_novelty + Guardian de segurança + sem-PII enforced |
| Loops/deadlocks entre agentes | hierarquia (supervisor-of-supervisors), limites de profundidade, checkpointer + timeouts |
| Governança vira gargalo a 150 agentes | gates só onde há entrega/cobrança/autonomia; SHADOW é livre; cross-approval só no caminho-crítico |

> Próximo: [03-CATALOGO-AGENTES.md](03-CATALOGO-AGENTES.md) — as 13 guildas, os 150+ agentes e a anatomia de cada um.
