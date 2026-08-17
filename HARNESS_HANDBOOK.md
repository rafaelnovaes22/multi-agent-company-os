# Harness Handbook — multi-agent-company-os (NÚCLEO)

> Gerado por /handbook em 2026-07-23. Commit base: 23aae84.
> Regra de uso: leia L1; desça para L2/L3 só quando a tarefa exigir. Âncoras ⚠️ FROZEN precisam de verificação antes do uso.

## L1 — Visão do sistema

Company-OS multi-agente sobre LangGraph: uma "empresa" de ~164 agentes organizados em 14 guildas (G00–G14), materializados por 1 template universal a partir de specs YAML. Cada agente roda o mesmo loop (load_context → act → self_critique → gate → emit → snapshot) sob uma constituição (C1–C8): modos de autonomia (SHADOW/PILOT/ASSISTED/AUTONOMOUS), unit economics (C3), multi-tenant (C8) e aprendizado contínuo (Hermes/Evolve). O produto vendido a PMEs é o próprio núcleo (agentes de produto: caixa, inbox, follow-up, atendimento, painel).

- **Arquitetura**: `nucleo/kernel` (template, estado, gate, skills/handlers, toolbox, LLM providers, execução/verificação) · `nucleo/factory` (materialização por spec) · `nucleo/governance` (promoção/demoção/kill-switch/perímetro CI) · `nucleo/learning` (Hermes + Evolve) · `nucleo/quality` (eval-harness, graders, exec_report, gates de CI, red-team) · `nucleo/security` (AgentShield) · `nucleo/product` (catálogo + onboarding de tenant) · `nucleo/guilds/**/spec.yaml` (as specs da frota) · `demo/live/server.py` (demo web servindo a frota real).
- **Modelo de execução**: intenção em linguagem natural → CEO-OS classifica guilda → supervisor da guilda roteia a 1 worker → worker roda o loop do template → gate C4 decide entregar/cobrar → evento no Brain + snapshot no store.
- **Estágios**: [E1 Inicialização/bootstrap](#e1-inicialização--bootstrap-da-frota) · [E2 Recebimento/triggers](#e2-recebimento--triggers) · [E3 Roteamento](#e3-roteamento-ceo-os--guilda--worker) · [E4 Execução do agente](#e4-execução-do-agente-template-universal) · [E5 Gate C4/entrega](#e5-gate-c4--entrega-e-cobrança) · [E6 Persistência](#e6-persistência-brain--store) · [E7 Aprendizado](#e7-aprendizado-hermes--evolve) · [E8 Governança/promoção](#e8-governança--promoção) · [E9 Qualidade/verificação](#e9-qualidade--verificação) · [E10 Produto/onboarding](#e10-produto--onboarding-de-tenant)
- **Fluxo de dados global**: specs YAML + docs L0 (`nucleo/company/*.md`) entram na materialização; o run produz eventos append-only (`events.jsonl` via `Brain`) e snapshots/memória no `FileStore` (`.brain*/store`); Hermes lê snapshots e escreve memória; Evolve promove memória a `company/skills/*.md`; promoção lê evals/exec_report e escreve `("modes", aid)`.

## L2 — Estágios

### E1: Inicialização / bootstrap da frota
- **Propósito**: descobrir specs e materializar todos os agentes + supervisores.
- **Gatilho**: startup de demo/servidor (`build_company`) ou build individual (`build_from_spec`).
- **Input/Output**: `nucleo/guilds/**/spec.yaml` → grafos LangGraph compilados (fleet, guild_sups, ceo-os).
- **Estados que lê/escreve**: lê specs e `evals/cases.json` (eval_count); nada persistido.
- **Depende de**: E4 (template), providers LLM.
- **Unidades**: discover_specs, build_fleet, build_company, load_spec, factory_gate, build_from_spec, build_agent, get_llm, bootstrap do server.

### E2: Recebimento / triggers
- **Propósito**: pontos de entrada que disparam a frota.
- **Gatilho**: HTTP POST na demo viva, `python -m nucleo.demo_*`, gates de CI, cron do Hermes.
- **Input/Output**: intenção NL / payload de task → estado inicial (`AgentState`/`CompanyState`).
- **Estados que lê/escreve**: cria `run_id`, `mode`, `task`; server escreve `.brain-web/`.
- **Depende de**: E3.
- **Unidades**: server run_intent/Handler, demo_company.main (e demais `nucleo/demo_*.py`, mesmo padrão).

### E3: Roteamento (CEO-OS → guilda → worker)
- **Propósito**: levar a intenção ao worker certo, preservando checkpoint/interrupt na cadeia.
- **Gatilho**: invoke do grafo `ceo-os` ou de um supervisor de guilda.
- **Input/Output**: `intent`/`statement` → `route` (guild_key / worker id) → `results`.
- **Estados que lê/escreve**: `CompanyState.route/result`, `GenGuildState.route/results`; config herdado (subgrafo real) para o `interrupt()` do gate propagar.
- **Depende de**: E1 (fleet), E4 (workers).
- **Unidades**: classify_guild, GUILD_KEYWORDS, build_guild_supervisor, classify_intent, build_root_supervisor, build_g08_supervisor, build_revenue_funnel.

### E4: Execução do agente (template universal)
- **Propósito**: o loop de 6 nós igual para todos os agentes; só o miolo do `act` (handler) varia por spec.
- **Gatilho**: `agent.invoke(state, config)` vindo de E2/E3/E9.
- **Input/Output**: `AgentState.task` → `output` + `citations` + `cost_tokens`.
- **Estados que lê/escreve**: lê SOUL/MEMORY/instincts/perfil de tenant (store, namespaced por tenant); escreve `scratchpad` (crítica dos guardians).
- **Depende de**: E5, E6, toolbox (least-privilege), loaders L0.
- **Unidades**: build_agent (grafo), load_context, _ns, registry de handlers (register/get_handler), _spec_citations, handlers de exemplo (lead_qualifier, _score_lead_against_icp, spec_executor, _catalog_agent_output), famílias skills_gXX, run_guardians, validate_outcome_clause, guarded/ToolBox, loaders L0, LLMProvider.

### E5: Gate C4 / entrega e cobrança
- **Propósito**: decidir se o output vira entrega/cobrança conforme o modo e o kill-switch.
- **Gatilho**: nó `gate` após `self_critique`.
- **Input/Output**: `output` proposto → `output.delivered/billing_amount` + `_gate` ("proceed"|"halt").
- **Estados que lê/escreve**: lê `("fleet",) kill_switch` e env `FLEET_KILL_SWITCH`; em ASSISTED pausa via `interrupt()` (human-in-the-loop).
- **Depende de**: E8 (quem seta modo/kill-switch).
- **Unidades**: gate, kill_switch_on.

### E6: Persistência (Brain + store)
- **Propósito**: empresa queryable (C6): todo run vira evento append-only + snapshot p/ aprendizado.
- **Gatilho**: nós `emit_artifact`/`snapshot` (só se gate = proceed).
- **Input/Output**: estado final do run → linha em `events.jsonl` + JSON em `("snapshots", aid)`.
- **Estados que lê/escreve**: escreve `events.jsonl`, `("snapshots"[, tenant], aid)`.
- **Depende de**: —
- **Unidades**: Brain, FileStore, emit_artifact, snapshot.

### E7: Aprendizado (Hermes / Evolve)
- **Propósito**: fechar o loop "evoluir aprendendo" fora do caminho de execução (cron).
- **Gatilho**: `run_hermes` / `run_evolve` (demos demo_hermes/demo_evolve).
- **Input/Output**: snapshots não processados → fatos ("instincts") na MEMORY; memória recorrente → skills da empresa.
- **Estados que lê/escreve**: lê/marca `("snapshots", aid)` (`processed=True`); escreve `("agent", aid, "memory")` e `company/skills/*.md`; emite eventos `memory_proposed`/`skills_evolved`.
- **Depende de**: E6.
- **Unidades**: run_hermes, extract_instincts, assess_novelty, run_evolve.

### E8: Governança / promoção
- **Propósito**: único caminho para subir de modo (G1–G7 + cross-approval); descer nunca tem gate.
- **Gatilho**: `promote`/`demote`/`set_fleet_kill_switch` (demo_promote, operação).
- **Input/Output**: spec_dir + aprovações (`req`) → veredito por gate + modo persistido.
- **Estados que lê/escreve**: lê evals (E9) e exec_report; escreve `("modes", aid) current`, `("promotions", aid) log`, `("fleet",) kill_switch`; audita tudo no Brain.
- **Depende de**: E9 (G4/G7), perímetro CI.
- **Unidades**: promote, _gate (G1–G7), current_mode, demote, set_fleet_kill_switch, fetch_perimeter_summary.

### E9: Qualidade / verificação
- **Propósito**: provar capacidade e segurança: eval-suites, oráculo executável (verify-in-eval), red-team e gates de CI.
- **Gatilho**: promoção (G4/G7), CI/nightly, CLIs `python -m nucleo.quality.*`.
- **Input/Output**: `evals/cases.json` + `security_cases.json` → pass-rate; artefato de código → static_ok/delivered_ok.
- **Estados que lê/escreve**: lê specs/cases; `exec_report` roda agentes em SHADOW; `foundry_check` lê/escreve `foundry_baseline.json`.
- **Depende de**: E1/E4 (materializa agentes p/ avaliar), executor Docker.
- **Unidades**: run_evals, run_security_evals, security_grade, graders, verify_code, verify_browser, verify_structure, InertExecutor, DockerExecutor, get_executor, generate_red_green, exec_report (run/run_generative/summarize), redteam, judge_eval, foundry_check, pre_pr_gate, exec_artifact_gate, diff_homogeneity, AgentShield.

### E10: Produto / onboarding de tenant
- **Propósito**: operacionalizar a venda: diagnosticar o cliente e ativar agentes de produto em SHADOW na conta dele.
- **Gatilho**: `onboard(tenant_id, ...)` (demo_onboarding).
- **Input/Output**: perfil + sinais + dados do cliente → agentes ativados + métricas agregadas (painel-dono).
- **Estados que lê/escreve**: escreve `("tenant", tid) profile`; runs por tenant caem nos namespaces de E6.
- **Depende de**: E1, E4, catálogo de produto.
- **Unidades**: recommend, onboard.

## L3 — Unidades

### discover_specs
- **Âncora**: `nucleo/kernel/registry.py:46`
- **Comportamento**: glob de `guilds/**/spec.yaml` → lista ordenada de diretórios de spec.
- **Estados**: só filesystem.

### build_fleet
- **Âncora**: `nucleo/kernel/registry.py:57`
- **Comportamento**: materializa todos os agentes via `build_from_spec` e agrupa por guilda (`{guild_key: [(spec, agent)]}`).
- **Estados**: nenhum persistido.

### build_company
- **Âncora**: `nucleo/kernel/registry.py:149`
- **Comportamento**: monta workers → supervisor por guilda → grafo raiz `ceo-os`; retorna (root_graph, guild_sups, fleet). Dispatch invoca a guilda como subgrafo (config herdado, interrupt atravessa 3 níveis).
- **Estados**: `CompanyState.route/result`.

### load_spec
- **Âncora**: `nucleo/factory/factory.py:20`
- **Comportamento**: lê `spec.yaml`, anexa `eval_count` (len de evals/cases.json) e `_spec_dir`.

### factory_gate
- **Âncora**: `nucleo/factory/factory.py:36`
- **Comportamento**: valida C2 (statement + ≥3 positivos + ≥3 negativos + delivered_event), C3 (billable exige economics) e C4 (<30 casos = warning) antes de materializar.
- **Casos excepcionais**: `strict=True` levanta `FactoryGateError`.

### build_from_spec
- **Âncora**: `nucleo/factory/factory.py:64`
- **Comportamento**: load_spec → factory_gate → build_agent; retorna (spec, agente compilado, resultado do gate).

### build_agent
- **Âncora**: `nucleo/kernel/agent_template.py:32`
- **Comportamento**: constrói o grafo universal load_context → act → self_critique → gate → (emit_artifact → snapshot)|END; o `act` chama o handler declarado em `spec.act_handler` com llm/store embrulhados pelo toolbox.
- **Estados**: `AgentState` (`nucleo/kernel/state.py:8`).

### get_llm
- **Âncora**: `nucleo/kernel/providers/llm.py:198`
- **Comportamento**: resolve o provider por env `LLM_PROVIDER` (anthropic|google|vertex|fake); default e fallback de qualquer falha = `FakeLLMProvider` offline. Modelo por papel via `_pick_model` (`llm.py:180`, precedência `<PROVIDER>_MODEL_<ROLE>` > `<PROVIDER>_MODEL` > `LLM_MODEL`).
- **Casos excepcionais**: retry/backoff em `_with_retry` (`llm.py:34`, 429 espera 15s·2^i); timeout via `LLM_TIMEOUT_S`.

### bootstrap do servidor da demo
- **Âncora**: `demo/live/server.py:41-65`
- **Comportamento**: `_bootstrap_gcp_adc` materializa credencial Vertex de env; instancia Brain/FileStore em `.brain-web/` e `build_company` no startup.

### run_intent / Handler (demo viva)
- **Âncora**: `demo/live/server.py:83` (run_intent) e `demo/live/server.py:119` (Handler; do_POST em `:144`)
- **Comportamento**: POST /api/intent → `ROOT_GRAPH.invoke` em SHADOW → trace JSON truncado (`_safe`, `:68`) para o front.

### demo_company.main
- **Âncora**: `nucleo/demo_company.py:27`
- **Comportamento**: CLI que materializa a frota e roteia intenções de exemplo pelo CEO-OS (padrão dos demais `nucleo/demo_*.py`: montar deps + invocar).

### classify_guild
- **Âncora**: `nucleo/kernel/registry.py:138`
- **Comportamento**: intenção → guild_key pela maior contagem de `GUILD_KEYWORDS` (`registry.py:25`); None se nada bate (fallback: 1ª guilda ordenada).

### build_guild_supervisor
- **Âncora**: `nucleo/kernel/registry.py:84`
- **Comportamento**: supervisor genérico de N workers: roteia por keywords derivadas do id do worker (`_kw_for_worker`, `:79`), pula workers `supervisor_route`, fallback ao 1º; dispatch monta a task e invoca o worker como subgrafo.

### classify_intent / build_root_supervisor (demos antigos)
- **Âncora**: `nucleo/kernel/supervisor.py:156` e `:164`
- **Comportamento**: roteador legado por lista `_ROUTING` (`:148`) → callable por rota. Coexiste com o registry (não usar em código novo).

### build_g08_supervisor
- **Âncora**: `nucleo/kernel/supervisor.py:27`
- **Comportamento**: encadeia lead-qualifier → (qualified) outbound-sdr; worker como subgrafo real com config herdado (interrupt do gate propaga — ver tests/test_subgraph_boundary.py).

### build_revenue_funnel
- **Âncora**: `nucleo/kernel/supervisor.py:84`
- **Comportamento**: funil cross-guild qualify → diagnose → prospect com gate por etapa; para no primeiro "stop".

### load_context
- **Âncora**: `nucleo/kernel/self_harness.py:26`
- **Comportamento**: carrega SOUL + MEMORY(12) + instincts(8) + perfil do tenant; zera scratchpad/citations/cost_tokens.
- **Estados**: lê `("agent", aid)`/`("tenant", tid, "agent", aid)` conforme `_ns` (`self_harness.py:15`) e `("instincts", aid)`.

### registry de handlers (register/get_handler)
- **Âncora**: `nucleo/kernel/skills.py:21` e `:28`
- **Comportamento**: decorator popula `_HANDLERS`; fallback = `outcome_clause_validator`. Assinatura: `handler(state, *, llm, store, spec) -> {output, cost_tokens, citations}`.

### _spec_citations
- **Âncora**: `nucleo/kernel/skills.py:36`
- **Comportamento**: deriva citations da spec (consumes_l0/tools/delivered_event/tenant); nunca vazio (guardians exigem citação).

### lead_qualifier / _score_lead_against_icp
- **Âncora**: `nucleo/kernel/skills.py:75` e `:852`
- **Comportamento**: qualifica lead contra o ICP (score, sinais, rota `_route` `:935`); exemplo canônico de handler determinístico.

### spec_executor
- **Âncora**: `nucleo/kernel/skills_exec.py:22`
- **Comportamento**: handler dos agentes de código: passa o artefato pelo `verify_code` com o executor corrente (delivered_ok só com execução real).

### _catalog_agent_output / _build_generative_prompt
- **Âncora**: `nucleo/kernel/skills.py:333` e `:285`
- **Comportamento**: saída-contrato dos agentes de catálogo (handler_kind/artifact_type/risk/requires_review) com prompt generativo montado do SOUL (`_load_soul`, `:268`).

### famílias skills_gXX / skills_finance / skills_custops
- **Âncora**: `nucleo/kernel/skills_g00.py` … `skills_g14.py`, `skills_finance.py`, `skills_custops.py` (1 arquivo por guilda; cada handler `def nome(state, *, llm, store, spec)`)
- **Comportamento**: handlers determinísticos por guilda (ex.: `rice_score` `skills_g02.py:30`, `churn_risk_score` `skills_g06.py:53`, `fin_runway` `skills_finance.py:28`, `model_routing_decision` `skills_g14.py:34`). Todos usam um `_out` local + `_spec_citations`.

### run_guardians / validate_outcome_clause
- **Âncora**: `nucleo/kernel/guardians.py:29` e `:10`
- **Comportamento**: self-critique mínimo (exige rationale + citations) e validação C2 de spec-alvo.

### ToolBox (guarded / grants_from_spec / _Guard.check)
- **Âncora**: `nucleo/kernel/toolbox.py:130`, `:44`, `:73`
- **Comportamento**: least-privilege do handler: `spec.tools` vira permissão (llm.complete / brain.query / brain.write). Violação audita `tool_denied` no Brain; com `tools_enforce: true` levanta `ToolDenied` (`:36`).

### loaders L0
- **Âncora**: `nucleo/kernel/loaders.py:12` (`_load_doc`; load_icp `:24`, load_dna `:29`, load_offerings `:34`)
- **Comportamento**: carrega e cacheia docs estratégicos de `nucleo/company/*.md` uma vez por processo.

### gate
- **Âncora**: `nucleo/kernel/gates.py:34`
- **Comportamento**: SHADOW nunca entrega/cobra; PILOT/AUTONOMOUS entrega direto (salvo bloqueio C3 `c3_ok=False`/`status=blocked`); ASSISTED pausa via `interrupt()` e halt se não aprovado; kill-switch força comportamento SHADOW para todos.
- **Estados**: lê `("fleet",) kill_switch` via `kill_switch_on` (`gates.py:25`) e env `FLEET_KILL_SWITCH`.

### Brain
- **Âncora**: `nucleo/kernel/brain.py:25`
- **Comportamento**: event store append-only (`events.jsonl`, com lock de thread); `events()` lê tudo.

### FileStore
- **Âncora**: `nucleo/kernel/brain.py:45`
- **Comportamento**: memória longa em arquivos com API do store LangGraph (get/put/search/items/subdirs), namespaces viram diretórios.

### emit_artifact
- **Âncora**: `nucleo/kernel/self_harness.py:42`
- **Comportamento**: registra `run_completed` no Brain (tenant, mode, ledger, delivered, billing, output, citations, cost_tokens).

### snapshot
- **Âncora**: `nucleo/kernel/self_harness.py:58`
- **Comportamento**: grava o snapshot do run (`processed=False`) no namespace por tenant/agente — insumo do Hermes.

### run_hermes
- **Âncora**: `nucleo/learning/hermes.py:54`
- **Comportamento**: para cada agente: snapshots não processados → `extract_instincts` (`:20`) → `assess_novelty` (`:48`, dedup textual) → "PR de memória" em `("agent", aid, "memory")`; marca `processed=True` (idempotente) e emite `memory_proposed`.
- **Estados**: confiança do fato derivada do modo (`mode_to_confidence`, `:15`).

### run_evolve
- **Âncora**: `nucleo/learning/evolve.py:35`
- **Comportamento**: agrupa toda a memória da frota por tópico (`_TOPICS`); com suporte ≥2 escreve skill em `company/skills/<topic>.md` e emite `skills_evolved`.

### promote
- **Âncora**: `nucleo/governance/promote.py:140`
- **Comportamento**: aplica os gates exigidos pela transição (`REQUIRED`, `:37`); AUTONOMOUS exige assinatura de segurança extra; grava `promotion_attempt` no Brain e, se passou, `("modes", aid) current` + log append-only.

### _gate (G1–G7)
- **Âncora**: `nucleo/governance/promote.py:67`
- **Comportamento**: G1 C2 · G2 C3 (billable max_ratio ≤ 0.25) · G3 SLA · G4 eval ≥90% + security 100% · G5 cross-approval · G6 CI/CD · G7 delivered_eligible_rate ≥95% via oráculo executável — fail-closed sem executor real, sem casos elegíveis, ou com falso-positivo de entrega (HARD-FAIL).

### demote / set_fleet_kill_switch
- **Âncora**: `nucleo/governance/promote.py:171` e `:192`
- **Comportamento**: demoção para SHADOW sem gates (idempotente); kill-switch de frota escreve `("fleet",) kill_switch` sem tocar nos modos persistidos. Ambos auditados no Brain.

### current_mode
- **Âncora**: `nucleo/governance/promote.py:58`
- **Comportamento**: lê `("modes", aid) current`; default SHADOW.

### fetch_perimeter_summary
- **Âncora**: `nucleo/governance/perimeter.py:62`
- **Comportamento**: prova de entrega do G7 vinda do nightly `foundry-exec.yml` verde em main (via `gh`); qualquer erro → None (fail-closed, nunca degrada p/ prova local). Runs confiáveis: só `schedule`/`workflow_dispatch`, idade < 7 dias.

### run_evals
- **Âncora**: `nucleo/quality/eval_harness.py:23`
- **Comportamento**: roda `evals/cases.json` do agente em SHADOW; grader específico por handler ou `generic_contract_grader`; retorna pass-rate (motor do Gate G4).

### run_security_evals / security_grade
- **Âncora**: `nucleo/quality/eval_harness.py:116` e `:68`
- **Comportamento**: suite adversarial invertida (`security_cases.json`): passa se o agente NÃO obedece ao ataque — invariantes not_delivered/no_billing/no_write_denials + canários `forbid_strings` + `expect`. `run_security_case` (`:98`) semeia o store e roda 1 caso (reusado pelo red-team).

### graders
- **Âncora**: `nucleo/quality/graders.py:11` (register), `:18` (get_grader), `:38` (generic_contract_grader)
- **Comportamento**: registro de graders por act_handler; o genérico valida `expected` contra o top-level do output com tolerância de 1%.

### verify_code
- **Âncora**: `nucleo/kernel/verification.py:201`
- **Comportamento**: oráculo offline de artefato de código: 7 checks NECESSÁRIOS (`NECESSARIOS`, `:41` — parseável, toca o bug, protegidos intactos por sha, held-out não declarado, AST válida, sem gaming) → static_ok; delivered_ok = static_ok E tests_pass em execução real.
- **Casos excepcionais**: tokens de burla em `_GAMING_TOKENS` (`:71`).

### verify_browser / verify_structure
- **Âncora**: `nucleo/kernel/verification.py:333` e `:395`
- **Comportamento**: naturezas browser/E2E e estrutural (postmortem): checks estáticos necessários; delivered_ok sempre False (sem execução real dessas naturezas).

### ExecutionProvider / InertExecutor / DockerExecutor / get_executor
- **Âncora**: `nucleo/kernel/execution.py:32`, `:62`, `:119`, `:229`
- **Comportamento**: seam de execução análoga ao LLMProvider. Default InertExecutor (não executa → UNVERIFIED). DockerExecutor roda `test_cmd` em contêiner hardened (sem rede, cap-drop, read-only, non-root, limites por runtime `_RESOURCE_LIMITS` `:100`); paths sanitizados por `_safe_files` (`:79`).

### generate_red_green
- **Âncora**: `nucleo/kernel/generate.py:104`
- **Comportamento**: gera artefato com LLM real e itera contra os testes VISÍVEIS até verde ou budget (`GEN_MAX_ITERS`, default 4); held-out e oráculo jamais entram no prompt; patch em path held-out é descartado.

### exec_report (run / run_generative / summarize)
- **Âncora**: `nucleo/quality/exec_report.py:54`, `:92`, `:151`
- **Comportamento**: roda os eval-cases de agentes `spec_executor` pelo caminho real e publica static_pass_rate, delivered_rate e delivered_eligible_rate (o número do SLA G7); `mark_audit_only` (`:233`) para relatórios não-prova.

### red-team
- **Âncora**: `nucleo/quality/redteam.py:135` (run_redteam; redteam_agent `:105`, variants_for `:84`)
- **Comportamento**: gera variantes dos security-cases (paráfrases LLM + mutações) e roda contra agentes escopados; bypass descoberto deve virar caso permanente.

### judge_eval
- **Âncora**: `nucleo/quality/judge_eval.py:189`
- **Comportamento**: LLM-judge externo (gemini/claude via `_make_judge` `:61`) pontua outputs de agentes de catálogo contra a outcome clause.

### foundry_check
- **Âncora**: `nucleo/quality/foundry_check.py:68` (collect) e `:164` (main)
- **Comportamento**: gate de qualidade da Fábrica em modelo RATCHET: regras duras sempre reprovam; catracas só reprovam violações novas fora de `foundry_baseline.json` (baseline só encolhe; `--update-baseline` deliberado).

### pre_pr_gate
- **Âncora**: `nucleo/quality/pre_pr_gate.py:183` (main; _audit_agent `:107`)
- **Comportamento**: HARD-FAIL antes de abrir PR (sem grandfather): exige critério held-out p/ naturezas build/ops/browser, `provenance` válida em todo caso determinístico com lastro verificável, e baseline que só encolhe (P2 exige BASELINE-CHANGE.md).

### exec_artifact_gate
- **Âncora**: `nucleo/quality/exec_artifact_gate.py:99` (evaluate_paths)
- **Comportamento**: valida artefatos de exec_report do CI (fail-closed em campos ausentes/falso-positivo).

### diff_homogeneity
- **Âncora**: `nucleo/quality/diff_homogeneity.py:175` (scan)
- **Comportamento**: anti eval-theater: detecta casos clonados/homogêneos adicionados no diff (fingerprint + clusters).

### AgentShield
- **Âncora**: `nucleo/security/agentshield.py:31` (scan_agent), `:69` (scan_fleet), `:74` (scan_c8)
- **Comportamento**: scan de higiene das specs da frota (secrets/PII/C2/C3/C4/C7) com severidades; `scan_c8` caça hardcode por tenant no código.

### recommend (catálogo de produto)
- **Âncora**: `nucleo/product/catalog.py:25`
- **Comportamento**: mapeia dores do cliente → agentes de produto a ativar (`PRODUCT_AGENTS`, `:9`, triggers lambda por perfil), ordenado por prioridade.

### onboard
- **Âncora**: `nucleo/product/onboarding.py:25`
- **Comportamento**: grava perfil do tenant, roda g2-diagnose, ativa em SHADOW os agentes de produto recomendados (`nucleo/product/<id>/`), agrega métricas e roda o painel-dono.

## Registro de estados compartilhados
| Estado | Onde vive | Escrito por | Lido por |
|---|---|---|---|
| `events.jsonl` (eventos append-only) | `Brain` (`.brain*/events`) | emit_artifact, promote/demote/kill-switch, run_hermes, run_evolve, ToolBox (`tool_denied`) | `Brain.events()` → security_grade, auditoria |
| SOUL / MEMORY / instincts | FileStore `("agent", aid[...])` ou `("tenant", tid, "agent", aid[...])` | Hermes (memory `learned-*`) | load_context |
| Snapshots de run | FileStore `("snapshots", aid)` / `("tenant", tid, "snapshots", aid)` | snapshot | run_hermes (marca processed), run_evolve (subdirs) |
| Modo do agente | FileStore `("modes", aid) current` | promote, demote | current_mode → quem monta o state (`mode`) |
| Log de promoções | FileStore `("promotions", aid) log` | promote, demote | auditoria |
| Kill-switch de frota | FileStore `("fleet",) kill_switch` + env `FLEET_KILL_SWITCH` | set_fleet_kill_switch | kill_switch_on (gate) |
| Perfil do tenant | FileStore `("tenant", tid) profile` | onboard | load_context |
| Docs L0 (DNA/ICP/ofertas) | `nucleo/company/*.md` | humanos; skills por run_evolve (`company/skills/`) | loaders L0, handlers |
| Baseline da catraca | `nucleo/quality/foundry_baseline.json` | foundry_check `--update-baseline` | foundry_check, pre_pr_gate (P2) |
| `AgentState` (por run) | LangGraph checkpointer (MemorySaver nos demos) | nós do template | nós seguintes; interrupt/resume |

## Mapa comportamento → código
<!-- "Quando mexer em X, os pontos são..." -->
- **Roteamento intenção→guilda→worker**: `nucleo/kernel/registry.py:138` (classify_guild), `:25` (GUILD_KEYWORDS), `:84` (build_guild_supervisor), `:79` (_kw_for_worker)
- **Adicionar/alterar um agente da frota**: `nucleo/guilds/<gXX>/<id>/spec.yaml` (+soul.md, evals/cases.json), `nucleo/factory/factory.py:64`, handler em `nucleo/kernel/skills*.py` + `skills.py:21` (register)
- **Loop universal do agente (nós/ordem)**: `nucleo/kernel/agent_template.py:32`, `nucleo/kernel/state.py:8`
- **Regra de entrega/cobrança por modo (SHADOW/ASSISTED/...)**: `nucleo/kernel/gates.py:34`; aprovação humana via `interrupt()` `gates.py:66-78`
- **Kill-switch da frota**: `nucleo/kernel/gates.py:25`, `nucleo/governance/promote.py:192`
- **Promoção/demoção de modo e seus gates**: `nucleo/governance/promote.py:140`, `:67` (G1–G7), `:171`; prova por CI `nucleo/governance/perimeter.py:62`
- **Permissões de tools do handler (least-privilege)**: `nucleo/kernel/toolbox.py:44`, `:73`, `:130`
- **Trocar modelo/provider de LLM, timeout, retry**: `nucleo/kernel/providers/llm.py:198`, `:180`, `:34`
- **Memória/aprendizado do agente**: `nucleo/learning/hermes.py:54`, `nucleo/learning/evolve.py:35`, `nucleo/kernel/self_harness.py:58`
- **Isolamento multi-tenant (namespaces)**: `nucleo/kernel/self_harness.py:15` (_ns), `nucleo/product/onboarding.py:25`
- **Rodar/mudar evals de um agente**: `nucleo/quality/eval_harness.py:23`, graders `nucleo/quality/graders.py:18`
- **Evals de segurança / red-team**: `nucleo/quality/eval_harness.py:68`, `:116`, `nucleo/quality/redteam.py:135`
- **Verificação executável de artefatos (delivered)**: `nucleo/kernel/verification.py:201`, `nucleo/kernel/execution.py:119`, `nucleo/quality/exec_report.py:151`
- **Geração red→green com LLM**: `nucleo/kernel/generate.py:104`, `nucleo/kernel/skills_exec.py:22`
- **Gates de CI da Fábrica (catraca / pre-PR)**: `nucleo/quality/foundry_check.py:164`, `nucleo/quality/pre_pr_gate.py:183`, `nucleo/quality/exec_artifact_gate.py:99`, `nucleo/quality/diff_homogeneity.py:175`
- **Onboarding de cliente / catálogo de produto**: `nucleo/product/onboarding.py:25`, `nucleo/product/catalog.py:25`
- **Demo web (frota real via HTTP)**: `demo/live/server.py:83`, `:119`

## Não coberto / Não resolvido
- `demo/live/gen_fleet.py` — gerador de JSON estático p/ o index.html da demo (tooling, fora do runtime).
- `docs/poc/subgraph_g08.py` — PoC executável da fronteira subgrafo vs invoke (documentação viva; a trava real é tests/test_subgraph_boundary.py).
- `nucleo/quality/graders_exec.py` e `nucleo/quality/security_eval.py` — wrappers finos de E9 (grader do spec_executor / CLI da suite security); não ganharam entrada L3 própria.
- `nucleo/demo_*.py` (16 CLIs) — cobertos genericamente em E2 via demo_company; cada um monta deps + invoca um pedaço da frota.
- Conteúdo não-código: `catalogo/*.md`, `workshop/*.md`, `docs/*.md`, `*.md` da raiz (visão/planejamento), `nucleo/guilds/**` (specs/soul/memory — dados da frota, não código), `tests/*` (espelham os módulos que testam).
- `railway.json` / `demo/live/Dockerfile` — deploy da demo; não inspecionados em profundidade.
