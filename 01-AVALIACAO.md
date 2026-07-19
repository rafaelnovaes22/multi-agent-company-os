# 01 — Avaliação: agent-governance-framework, ECC e a fusão

## Parte A — O que o agent-governance-framework é hoje (e o que vale ouro)

O agent-governance-framework (v0.13.x) é um **framework de governança Claude Code-nativo** que transforma princípios em **trilhos auditáveis** para projetos que entregam *outcome cobrável*. O núcleo é a **Constitution** — 8 princípios imutáveis (mudança exige ADR + bump SemVer):

| Princípio | Regra | Por que importa para uma empresa AI-native de 150 agentes |
|---|---|---|
| **C1** Diagnose-before-build | nada começa sem diagnóstico aprovado | impede "caos automatizado": 150 agentes sem diagnóstico = 150× o caos |
| **C2** Outcome-first | spec começa pela cláusula de outcome (3+ exemplos positivos/negativos + evento que dispara `DELIVERED`) | dá a cada agente um **contrato verificável** — base do eval e da cobrança |
| **C3** Economic viability | custo de operar ≤ 25% do preço (hard gate) | **a maioria das empresas de agentes ignora unit economics até quebrar** |
| **C4** Pilot-before-canonical | `SHADOW→PILOT→ASSISTED→AUTONOMOUS` com janela mínima + critério | **é o mecanismo de evolução**: agente ganha autonomia provando qualidade |
| **C5** Three-tier context | L0 estratégico / L1 tático / L2 operacional; herança de leitura + cache | **economia de tokens em escala** — crítico com 150 agentes |
| **C6** Telemetry by default | todo evento crítico tem trace/audit (input/output/custo/latência/ator) | torna a empresa **auditável e queryable** (YC #3) |
| **C7** Portability over lock-in | provider/modelo isolados em camada de abstração | trocar LLM sem reescrever 150 agentes |
| **C8** Config over customization | cliente N = configuração, nunca `if (tenant === 'x')` | **escala sem explosão combinatória** de código |

Acima dos princípios, o foundry entrega:

- **10 Guardians** (subagents Opus/Sonnet) que validam cada princípio — PO-Guardian (C1/C2), Unit-Economist (C3), Promotion-Officer (C4), Tenant-Context-Curator (C8), Artifact-Architect (C5/C7), Eval-Engineer, Observability-Guardian (C6), Security-Privacy-Guardian, Code-Reviewers, Learning-Curator.
- **15 slash commands** que orquestram o pipeline: `diagnose → spec → plan → implement → eval → pre-merge-check → promote` + `aios-*`, `audit-monthly`, `playbook-extract`.
- **6 gates de promoção** com **cross-approval obrigatória** (quem aprova C2 ≠ quem aprova a transição) e anti-self-approval — uma disciplina de governança que poucos sistemas têm.
- **Self-harness** (skill L1, "herança do Hermes Agent"): 5 pilares **SOUL / MEMORY / SKILLS / LOOP / CRONS**. Memória com `confidence: [local|shadow|assisted|autonomous]` + `date` + `source_run_id`. Loop: `Stop hook → snapshot → Hermes (Railway/Codex) → assess_novelty → PR → próxima sessão`. **É exatamente a "estrutura self-harness-agent" que o desafio pede.**
- **Reviewer externo (DeepAgent, mensal)** — auditoria independente contra C1–C8 + drift detection (quality/cost/volume/prompt). Isto é "closed loop" no nível da empresa.

### Forças (o que mantemos intacto)

1. **Constituição como trilho auditável** — quase nenhum stack de agentes tem governança formal. É o nosso maior diferencial.
2. **Disciplina econômica (C3)** — antídoto contra o erro nº1 de empresas de agentes.
3. **Ciclo de promoção (C4) = evolução por confiança** — o agente *sobe* (shadow→autonomous) provando concordância. Casamento perfeito com "agentes que evoluem aprendendo".
4. **Three-tier + helper pattern (C5)** — redução de ~70% de tokens; indispensável a 150 agentes.
5. **Self-harness (loop fechado de aprendizado)** — já é YC #2 ("closed loops everywhere").
6. **Anti-customização (C8)** — escala multi-tenant sem virar consultoria disfarçada.
7. **Auditoria independente mensal** — legibilidade e confiança (YC #3).

### Lacunas para ESTE desafio (o que o ECC + LangGraph preenchem)

| Lacuna | Detalhe | Quem preenche |
|---|---|---|
| **Runtime** | O foundry é *build-time* — define skills/agents/commands em **Markdown no Claude Code**. Não é um **orquestrador de runtime** para 150 agentes vivos respondendo a eventos. | **LangGraph** (substrato de execução) |
| **Escala** | ~10 guardians + ~18 skills. Não há padrão comprovado para 150 agentes. | **ECC** (63 agentes / 243 skills → modelo de guildas) |
| **Aprendizado pesado** | self-harness/Hermes é curado por humano via PR — robusto, mas de alta fricção para 150 agentes. | **ECC instincts** (auto-extração leve, confidence-score) |
| **Topologia de orquestração** | Não há supervisor/router de runtime, nem fan-out paralelo, nem human-in-the-loop como primitiva. | **LangGraph** (supervisor, `Send`, `interrupt`) |
| **Enquadramento** | É orientado a uma **agência/SaaS² (Novais Digital)**: "cliente", "tenant", "subscription". Precisamos reenquadrar "tenant" como **função/guilda da própria empresa**. | reframe no NÚCLEO |
| **Single-harness** | Só Claude Code. | ECC é cross-harness; mas no runtime o substrato é o LangGraph de qualquer forma |

> **Conclusão da Parte A:** o foundry nos dá **o cérebro normativo** (constituição, economia, gates, self-harness). Falta o **corpo de execução em escala** (runtime + topologia + aprendizado leve). É aí que entram LangGraph e ECC.

---

## Parte B — O que o ECC (`affaan-m/ECC`, "everything-claude-code") contribui

ECC é um **sistema operador harness-native** (MIT) — "agent harness performance optimization system: skills, instincts, memory, security, research-first" — multi-harness (Claude Code, Codex, Cursor, OpenCode, Gemini, Zed, Copilot). Tem ~243 skills públicas e dezenas de subagents organizados por domínio, hooks por evento, rules por linguagem, MCP configs, e os **Hermes operator workflows** + dashboard.

> **Nota de honestidade técnica:** o ECC é, ele próprio, um *operador de harness Claude-Code* (skills/hooks em Markdown), **não** um runtime LangGraph. Portanto **adotamos seus padrões e seu modelo de aprendizado** e **os portamos para o LangGraph**. Não importamos código de runtime dele. (Também: a linhagem **"Hermes"** que o self-harness do foundry já cita vem dessa mesma família — os dois projetos conversam.)

### O que portamos do ECC, concretamente

| Componente ECC | O que é | Como entra no NÚCLEO |
|---|---|---|
| **Topologia de escala** (63 agentes / 243 skills por domínio) | prova de que 60+ agentes/240+ skills se organizam por domínio | vira o **modelo de 13 guildas** ([03](03-CATALOGO-AGENTES.md)) |
| **Instinct learning V2** (`/instinct-status`, `/instinct-import/export`, `/evolve`) | padrões auto-extraídos de sessões, com **confidence score**; `/evolve` agrupa instincts em skills | **fundido ao self-harness MEMORY**: instincts = camada rápida; `/evolve` promove a skill compartilhada da guilda/empresa |
| **eval-harness + quality-gate + test-coverage** | verificação de loop, grader types, pass@k, gate determinístico, cobertura ≥80% | a **camada de verificação de runtime** da Fábrica (YC #4 "software factories") |
| **Orquestração multi-agente** (`/multi-plan`, `/multi-execute`, worktrees + tmux) | decompõe feature em fases, agentes paralelos isolados | mapeia para **subgrafos LangGraph + `Send`** e isolamento por worktree na fabricação paralela |
| **AgentShield** (scan de configs/MCP/hooks: secrets, injection, permissões) | auditoria de segurança das próprias definições de agentes | a **Guilda de Segurança** em escala (scan contínuo dos 150 agentes) |
| **Hooks por ciclo de vida** (SessionStart, Stop, pre-compact) | injeção de contexto, snapshot, compactação estratégica | os **ganchos do self-harness wrapper** no LangGraph (entry/exit nodes + cron) |
| **Hermes operator workflows + dashboard** | console de operador, workflows públicos | o **Operator Console** (YC #3 "dashboards com tudo") |
| **Rules por linguagem** (TS/Python/Go…) | princípios "always-follow" por linguagem | **padrões da Guilda de Engenharia** |
| **Cross-harness portability** | mesma camada reutilizável move entre harnesses | reforça **C7** (portabilidade) no nível de harness, não só de LLM |

---

## Parte C — A fusão (por que 1 + 1 + 1 > 3)

```
                       Doutrina YC (operar como empresa AI-native)
                                         │
   ┌─────────────────────────────────────┼─────────────────────────────────────┐
   │                                     │                                       │
   ▼                                     ▼                                       ▼
GOVERNANÇA                          APRENDIZADO+ESCALA                       EXECUÇÃO
(agent-governance-framework)                      (ECC)                                    (LangGraph)
• Constitution C1-C8                • instincts (confidence)                 • StateGraph / subgrafos
• gates C4 (shadow→auto)            • /evolve → skills                       • checkpointer (durável)
• Unit-Economist (C3)               • eval-harness / quality-gate            • store (memória longa)
• self-harness/Hermes               • AgentShield                            • interrupt (human-in-loop)
• reviewer mensal                   • orquestração multi-agente              • Send (fan-out paralelo)
• three-tier (C5)                   • Hermes dashboard                       • supervisor/router
   │                                     │                                       │
   └─────────────────────────────────────┼───────────────────────────────────────┘
                                          ▼
                            NÚCLEO — Company-OS multi-agente
```

**Divisão de trabalho limpa, sem sobreposição:**

- **agent-governance-framework** responde *"isto pode ir a produção/cobrar?"* → constituição, gates, economia, auditoria.
- **ECC** responde *"como 150 agentes aprendem e se verificam em escala?"* → instincts, eval-harness, segurança, padrões de orquestração.
- **LangGraph** responde *"como isso roda, mantém estado e pede aprovação humana?"* → grafos com estado, checkpoint, `interrupt`.
- **YC** responde *"como isso se comporta como empresa?"* → AI-as-OS, closed loops, queryable, fábricas, sem middleware, 3 arquétipos, token-max, vantagem early-stage.

**Onde os três se reforçam (não se duplicam):**

- *Aprendizado:* self-harness (foundry, curado/PR) **+** instincts (ECC, automático) **+** store/checkpointer (LangGraph, persistência) = um único loop de memória em 3 velocidades.
- *Verificação:* eval-cases (foundry C2/C4) **+** eval-harness/quality-gate (ECC) **+** gates com `interrupt` (LangGraph) = "software factory" YC #4 com governança.
- *Evolução:* o ciclo C4 (foundry) **é** o caminho de evolução, instrumentado pelos eval (ECC) e materializado por transições de estado no grafo (LangGraph).

> Próximo: [02-ARQUITETURA.md](02-ARQUITETURA.md) — como isso vira camadas, topologia e código.
