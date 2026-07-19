# 03 — Catálogo dos ~169 agentes + Anatomia de cada agente

> **Princípio central:** *não se escreve ~169 agentes à mão.* Existe **1 template universal de agente** (§B) e **~169 specs**. A Fábrica (L3) materializa cada spec em um subgrafo LangGraph. "Implementar cada agente" = escrever a spec + os eval-cases; a Fábrica gera o resto.
>
> 📂 **O detalhamento completo do que CADA agente faz** (missão, responsabilidades, entradas/saídas, ferramentas C7, gatilhos, cláusula de outcome C2, Guardians, KPIs) está nos arquivos por guilda em **[catalogo/](catalogo/)** — links no fim da seção A. Este documento é o **mapa/índice** + a anatomia universal.

Legenda das colunas: **Ledger** = `OP` (operating, governado por ROI-vs-headcount / token-max) ou `BL` (billable, governado por C3 ≤25%). **Tier** = camada de contexto C5 (L0 estratégico / L1 tático / L2 operacional). **Nasce** = modo inicial (todos nascem em SHADOW; a coluna indica o alvo de produção).

---

## A. As 13 guildas (mapa)

```
                          SUPERVISOR-RAIZ (CEO-OS)
   ┌──────────┬──────────┬──────────┬──────────┬──────────┬──────────┐
   ▼          ▼          ▼          ▼          ▼          ▼          ▼
 G1 Estrat. G2 Produto G3 Engenh.  G4 Qualid. G5 Segur.  G6 Dados   G7 Growth
   │
   ├──────────┬──────────┬──────────┬──────────┬──────────┐
   ▼          ▼          ▼          ▼          ▼          ▼
 G8 Vendas  G9 CustOps G10 Finanç. G11 Pessoas G12 Juríd. G13 Governança(Foundry)
```

| Guilda | DRI (humano) | Foco | Ledger dominante | Nº agentes |
|---|---|---|---|---|
| G1 Estratégia & Founder Office | AI Founder | direção, mercado, board | OP | 9 |
| G2 Produto & Discovery | DRI Produto | descoberta, PRD, experimentos | OP | 13 |
| G3 Engenharia / Software Factory | DRI Eng | construir o produto e os agentes (+dr-bcp, +i18n) | OP | 21 |
| G4 Qualidade & Eval | DRI Qualidade | eval, QA, regressão | OP | 10 |
| G5 Segurança & Compliance | DRI SecOps | LGPD, AgentShield, fraude/abuso (+data-governance) | OP | 12 |
| G6 Dados & Analytics | DRI Dados | pipelines, métricas, drift | OP | 12 |
| G7 Growth & Marketing | DRI Growth | aquisição, conteúdo, lifecycle | OP/BL | 14 |
| G8 Vendas & Receita | DRI Vendas | pipeline, pricing, billing (+partnerships) | OP/BL | 12 |
| G9 Customer Operations | DRI CX | suporte, onboarding (+customer-success) | BL | 14 |
| G10 Finanças & Unit Economics | DRI Finanças | FP&A, conciliação, C3 (+procurement) | OP | 11 |
| G11 Pessoas & Conhecimento | DRI Ops | recrutar camada humana, KM, notetaker | OP | 8 |
| G12 Jurídico & Risco | DRI Legal | contratos, regulatório | OP | 8 |
| G13 Governança (Foundry Guild) | AI Founder | os Guardians + reviewer | OP | 11 |
| **G14 Model & AI-Ops** | DRI Eng/Dados | model-ops, prompt registry, eval-data, Responsible-AI | OP | 8 |
| + Utilitários (root-supervisor, Hermes-loop, brain-indexer, 3 MCP gateways) | AI Founder | roteamento global + infra | OP | 6 |
| **TOTAL** | | | | **169** |

> **Nota de revisão (2026-05-29):** G14 e 6 agentes *folded* (g3-dr-bcp, g3-i18n, g5-data-governance, g8-partnerships, g9-customer-success, g10-procurement) foram adicionados após a checagem de consistência do plano, fechando lacunas AI-native (Model/LLM-Ops, prompt registry, dados de eval, Responsible-AI, ativação de cliente, DR/BCP, i18n). Detalhe em [catalogo/G14-model-ai-ops.md](catalogo/G14-model-ai-ops.md) e [catalogo/00-MAPA-E-HANDOFFS.md](catalogo/00-MAPA-E-HANDOFFS.md).

### Detalhamento agente-a-agente (catalogo/)

| Guilda | Arquivo |
|---|---|
| 🗺️ Mapa de handoffs + checagem de consistência | [00-MAPA-E-HANDOFFS.md](catalogo/00-MAPA-E-HANDOFFS.md) |
| G00 Núcleo & Utilitários | [G00-nucleo-utilitarios.md](catalogo/G00-nucleo-utilitarios.md) |
| G01 Estratégia & Founder Office | [G01-estrategia-founder-office.md](catalogo/G01-estrategia-founder-office.md) |
| G02 Produto & Discovery | [G02-produto-discovery.md](catalogo/G02-produto-discovery.md) |
| G03 Engenharia / Software Factory | [G03-engenharia.md](catalogo/G03-engenharia.md) |
| G04 Qualidade & Eval | [G04-qualidade-eval.md](catalogo/G04-qualidade-eval.md) |
| G05 Segurança & Compliance | [G05-seguranca-compliance.md](catalogo/G05-seguranca-compliance.md) |
| G06 Dados & Analytics | [G06-dados-analytics.md](catalogo/G06-dados-analytics.md) |
| G07 Growth & Marketing | [G07-growth-marketing.md](catalogo/G07-growth-marketing.md) |
| G08 Vendas & Receita | [G08-vendas-receita.md](catalogo/G08-vendas-receita.md) |
| G09 Customer Operations | [G09-customer-operations.md](catalogo/G09-customer-operations.md) |
| G10 Finanças & Unit Economics | [G10-financas.md](catalogo/G10-financas.md) |
| G11 Pessoas & Conhecimento | [G11-pessoas-conhecimento.md](catalogo/G11-pessoas-conhecimento.md) |
| G12 Jurídico & Risco | [G12-juridico-risco.md](catalogo/G12-juridico-risco.md) |
| G13 Governança (Foundry Guild) | [G13-governanca.md](catalogo/G13-governanca.md) |
| **G14 Model & AI-Ops** (novo) | [G14-model-ai-ops.md](catalogo/G14-model-ai-ops.md) |

---

## B. Anatomia universal do agente (o template que a Fábrica usa)

Todo agente — worker ou supervisor — é o **mesmo template** parametrizado por uma spec. É o que torna 150 agentes gerenciáveis (e satisfaz C8: variação é configuração, não código novo).

### B.1 A spec (o contrato — derivada do template do foundry)
```yaml
id: g3-backend-builder
guild: G3-engenharia
ledger: operating            # operating | billable  → define governança econômica
tier: L2                     # C5
ai_enabled: true             # C3/C6 bifurcação
outcome_clause:              # C2 — obrigatório
  statement: "Implementa um endpoint a partir de uma spec, com testes passando"
  positive_examples: [ "...", "...", "..." ]   # 3+
  negative_examples: [ "...", "...", "..." ]   # 3+
  delivered_event: "ci.tests_passed && pr.opened"
economics:                   # C3 — só trava se ledger=billable
  cost_model: cost_per_outcome
  max_ratio: 0.25
eval_suite: evals/g3-backend-builder/   # C4 — ≥30 casos
tools: [ repo.read, repo.write, ci.run, docs.lookup ]   # via camada de abstração C7
guardians: [ artifact-architect, code-reviewer, security-privacy ]
mode: SHADOW                 # C4 — nasce sempre aqui
soul_ref: souls/g3-backend-builder.md
memory_ref: memory/g3-backend-builder.md
```

### B.2 Estado (LangGraph) + arquivos (self-harness)
```
state (Pydantic): { task, context, scratchpad, tool_results, output,
                    citations, cost_tokens, mode, run_id }
arquivos:  souls/{id}.md        ← identidade (SOUL)
           memory/{id}.md       ← fatos § [confidence] (MEMORY)
           instincts/{id}/*.md  ← padrões auto-extraídos (ECC)
           evals/{id}/*.json    ← eval-suite (≥30)
```

### B.3 O grafo de nós (igual para todos)
```
[load_context] → [plan] → [act ⟲ tool loop] → [self_critique] → {gate?} → [emit_artifact] → [snapshot]
   carrega          decide   executa tools      Guardian da     interrupt   Company Brain   learning
   SOUL+MEMORY      passos   (react loop)        guilda critica  (se modo     + evento C6     loop
   +instincts                                                    exige humano)
```
- **`gate?`**: se `mode ∈ {ASSISTED}` → `interrupt()` pede aprovação do DRI antes de entregar. Se `SHADOW` → nunca entrega/cobra. Se `AUTONOMOUS` → entrega e audita amostra.
- **supervisores** usam o mesmo template mas o nó `act` é "rotear para worker" (`Command(goto=...)` / `Send`) em vez de tool-use.

> Código real do template em [04-IMPLEMENTACAO.md](04-IMPLEMENTACAO.md).

---

## C. Catálogo completo (os 150+)

### G1 · Estratégia & Founder Office — 9
| Agente | Papel | Ledger | Tier | Nasce |
|---|---|---|---|---|
| g1-strategy-supervisor | roteia trabalho de estratégia | OP | L0 | ASSISTED |
| g1-market-intel | monitora o mercado/concorrentes do vertical escolhido (a definir) | OP | L0 | AUTONOMOUS |
| g1-opportunity-sizer | TAM/SAM/SOM e tese de oportunidade | OP | L0 | ASSISTED |
| g1-scenario-planner | cenários e sensibilidade estratégica | OP | L0 | ASSISTED |
| g1-board-deck-author | gera deck de board a partir do Company Brain | OP | L1 | ASSISTED |
| g1-okr-steward | propõe/monitora OKRs por guilda | OP | L0 | ASSISTED |
| g1-investor-update | redige update mensal a investidores/board | OP | L1 | ASSISTED |
| g1-competitive-teardown | teardown de produto concorrente | OP | L1 | AUTONOMOUS |
| g1-narrative-synthesizer | sintetiza narrativa/positioning | OP | L0 | ASSISTED |

### G2 · Produto & Discovery — 13
| Agente | Papel | Ledger | Tier | Nasce |
|---|---|---|---|---|
| g2-product-supervisor | roteia descoberta/entrega de produto | OP | L1 | ASSISTED |
| g2-user-interview-synth | sintetiza entrevistas/transcrições | OP | L2 | AUTONOMOUS |
| g2-jobs-to-be-done | extrai JTBD de sinais de usuário | OP | L2 | AUTONOMOUS |
| g2-prd-author | escreve PRD a partir de diagnóstico (C1/C2) | OP | L1 | ASSISTED |
| g2-experiment-designer | desenha A/B e critérios de sucesso | OP | L2 | ASSISTED |
| g2-prioritizer (RICE) | prioriza backlog | OP | L1 | AUTONOMOUS |
| g2-roadmap-keeper | mantém roadmap vivo no Company Brain | OP | L1 | AUTONOMOUS |
| g2-competitor-feature-watch | rastreia features concorrentes | OP | L2 | AUTONOMOUS |
| g2-usability-critic | heurísticas de usabilidade em mockups | OP | L2 | AUTONOMOUS |
| g2-pricing-product-fit | testa willingness-to-pay | OP/BL | L1 | ASSISTED |
| g2-feedback-router | classifica e roteia feedback → guildas | OP | L2 | AUTONOMOUS |
| g2-release-notes | gera release notes a partir de PRs | OP | L2 | AUTONOMOUS |
| g2-prototype-builder | gera protótipo clicável (YC: IC traz protótipo) | OP | L2 | ASSISTED |

### G3 · Engenharia / Software Factory — 19
| Agente | Papel | Ledger | Tier | Nasce |
|---|---|---|---|---|
| g3-eng-supervisor | decompõe feature em fases, roteia (multi-plan/ECC) | OP | L1 | ASSISTED |
| g3-planner | spec → plano de implementação por fases | OP | L1 | ASSISTED |
| g3-backend-builder | implementa serviços/endpoints | OP | L2 | ASSISTED |
| g3-frontend-builder | implementa UI | OP | L2 | ASSISTED |
| g3-mobile-builder | implementa app mobile | OP | L2 | ASSISTED |
| g3-db-schema | modela/migra schema (Postgres/Drizzle) | OP | L2 | ASSISTED |
| g3-api-contract | define/versiona contratos de API | OP | L1 | ASSISTED |
| g3-infra-devops | IaC, deploy, pipelines | OP | L2 | ASSISTED |
| g3-integration-builder | conectores (pagamentos, WhatsApp, mapas) via C7 | OP | L2 | ASSISTED |
| g3-build-error-resolver | resolve falhas de compilação/CI (padrão ECC) | OP | L2 | AUTONOMOUS |
| g3-refactorer | refatora dívida técnica | OP | L2 | AUTONOMOUS |
| g3-perf-optimizer | profiling e otimização | OP | L2 | ASSISTED |
| g3-code-reviewer-ts | review TypeScript (rules ECC) | OP | L2 | AUTONOMOUS |
| g3-code-reviewer-py | review Python | OP | L2 | AUTONOMOUS |
| g3-code-reviewer-go | review Go | OP | L2 | AUTONOMOUS |
| g3-docs-lookup | pesquisa referência de API/docs | OP | L2 | AUTONOMOUS |
| g3-dependency-warden | bumps e CVEs de dependências | OP | L2 | ASSISTED |
| g3-feature-flagger | gerencia flags/rollout | OP | L2 | ASSISTED |
| g3-incident-responder | triagem e mitigação de incidentes | OP | L2 | ASSISTED |

### G4 · Qualidade & Eval — 10
| Agente | Papel | Ledger | Tier | Nasce |
|---|---|---|---|---|
| g4-quality-supervisor | orquestra eval/QA | OP | L1 | ASSISTED |
| g4-eval-case-author | escreve eval-cases (≥30) por agente (C4) | OP | L2 | ASSISTED |
| g4-eval-harness-runner | roda eval-harness, pass@k, grader (ECC) | OP | L2 | AUTONOMOUS |
| g4-quality-gate | gate determinístico pré-merge (ECC) | OP | L2 | AUTONOMOUS |
| g4-e2e-playwright | testes E2E de UI | OP | L2 | AUTONOMOUS |
| g4-regression-watcher | detecta regressões entre releases | OP | L2 | AUTONOMOUS |
| g4-test-coverage | impõe cobertura ≥80% (ECC) | OP | L2 | AUTONOMOUS |
| g4-load-tester | testes de carga/SLA | OP | L2 | ASSISTED |
| g4-prompt-eval | avalia qualidade/regressão de prompts | OP | L2 | AUTONOMOUS |
| g4-shadow-comparator | calcula agreement-rate em SHADOW (C4) | OP | L2 | AUTONOMOUS |

### G5 · Segurança & Compliance — 11
| Agente | Papel | Ledger | Tier | Nasce |
|---|---|---|---|---|
| g5-security-supervisor | orquestra segurança/compliance | OP | L1 | ASSISTED |
| g5-agentshield-scanner | scan de configs/MCP/hooks dos 150 agentes (ECC) | OP | L2 | AUTONOMOUS |
| g5-secrets-scanner | detecta secrets em código/configs | OP | L2 | AUTONOMOUS |
| g5-prompt-injection-guard | defesa contra injection em entradas | OP | L2 | AUTONOMOUS |
| g5-lgpd-privacy | conformidade LGPD, mapeia PII (C6) | OP | L1 | ASSISTED |
| g5-threat-modeler | modela ameaças por feature | OP | L2 | ASSISTED |
| g5-pentest-agent | testes de invasão (escopo autorizado) | OP | L2 | ASSISTED |
| g5-fraud-abuse-detector | detecta fraude/abuso transacional (genérico; sinais configuráveis) | Misto | L2 | ASSISTED |
| g5-access-auditor | revisa permissões/IAM | OP | L2 | AUTONOMOUS |
| g5-dependency-cve | monitora CVEs em runtime | OP | L2 | AUTONOMOUS |
| g5-incident-forensics | forense pós-incidente | OP | L2 | ASSISTED |

### G6 · Dados & Analytics — 12
| Agente | Papel | Ledger | Tier | Nasce |
|---|---|---|---|---|
| g6-data-supervisor | orquestra dados/analytics | OP | L1 | ASSISTED |
| g6-pipeline-builder | constrói/mantém pipelines ETL | OP | L2 | ASSISTED |
| g6-metrics-modeler | define métricas canônicas/semantic layer | OP | L1 | ASSISTED |
| g6-dashboard-builder | gera dashboards do Operator Console (YC#3) | OP | L2 | AUTONOMOUS |
| g6-cohort-analyst | retenção/coortes | OP | L2 | AUTONOMOUS |
| g6-churn-predictor | prevê churn | BL | L2 | ASSISTED |
| g6-experiment-analyst | lê resultados de A/B | OP | L2 | AUTONOMOUS |
| g6-anomaly-detector | detecta anomalias em métricas | OP | L2 | AUTONOMOUS |
| g6-drift-detector | drift de qualidade/custo/volume/prompt (C6/L6) | OP | L2 | AUTONOMOUS |
| g6-data-quality | valida qualidade/contratos de dados | OP | L2 | AUTONOMOUS |
| g6-nl2sql | traduz pergunta natural → query no Company Brain | OP | L2 | AUTONOMOUS |
| g6-forecaster | previsão de demanda/receita | OP | L2 | ASSISTED |

### G7 · Growth & Marketing — 14
| Agente | Papel | Ledger | Tier | Nasce |
|---|---|---|---|---|
| g7-growth-supervisor | orquestra growth | OP | L1 | ASSISTED |
| g7-seo-strategist | estratégia/keywords SEO | OP | L2 | AUTONOMOUS |
| g7-content-writer | conteúdo/blog | OP | L2 | ASSISTED |
| g7-copywriter | copy de anúncios/landing | OP/BL | L2 | ASSISTED |
| g7-landing-builder | gera landing pages | OP | L2 | ASSISTED |
| g7-paid-ads-optimizer | otimiza campanhas pagas (ROAS) | BL | L2 | ASSISTED |
| g7-social-manager | calendário/posts sociais | OP | L2 | ASSISTED |
| g7-lifecycle-crm | jornadas de e-mail/push/WhatsApp | BL | L2 | ASSISTED |
| g7-influencer-scout | identifica/avalia parcerias | OP | L2 | AUTONOMOUS |
| g7-referral-designer | desenha programa de indicação | OP | L1 | ASSISTED |
| g7-creative-generator | gera criativos (img/vídeo) | OP | L2 | ASSISTED |
| g7-ab-growth-runner | roda experimentos de growth | OP | L2 | AUTONOMOUS |
| g7-attribution-analyst | atribuição de canais | OP | L2 | AUTONOMOUS |
| g7-community-manager | gestão de comunidade | OP | L2 | ASSISTED |

### G8 · Vendas & Receita — 11
| Agente | Papel | Ledger | Tier | Nasce |
|---|---|---|---|---|
| g8-sales-supervisor | orquestra vendas/receita | OP | L1 | ASSISTED |
| g8-lead-qualifier | qualifica leads (ICP loader) | BL | L2 | ASSISTED |
| g8-outbound-sdr | prospecção outbound | OP | L2 | ASSISTED |
| g8-proposal-author | gera propostas | OP | L2 | ASSISTED |
| g8-crm-hygiene | mantém CRM limpo | OP | L2 | AUTONOMOUS |
| g8-pricing-engine | precificação dinâmica | BL | L1 | ASSISTED |
| g8-billing-agent | cobrança/faturas (C6 audit-log) | BL | L2 | ASSISTED |
| g8-dunning-agent | recuperação de inadimplência | BL | L2 | ASSISTED |
| g8-contract-closer | fluxo de fechamento/assinatura | OP | L2 | ASSISTED |
| g8-upsell-crosssell | identifica expansão | BL | L2 | ASSISTED |
| g8-revenue-reporter | relatórios de receita/NRR | OP | L1 | AUTONOMOUS |

### G9 · Customer Operations — 13
| Agente | Papel | Ledger | Tier | Nasce |
|---|---|---|---|---|
| g9-custops-supervisor | orquestra suporte/CX | BL | L1 | ASSISTED |
| g9-support-triage | classifica e roteia tickets | BL | L2 | AUTONOMOUS |
| g9-tier1-resolver | resolve tickets nível 1 | BL | L2 | ASSISTED |
| g9-escalation-manager | escala casos complexos | BL | L2 | ASSISTED |
| g9-kb-curator | mantém base de conhecimento | OP | L2 | AUTONOMOUS |
| g9-onboarding-guide | onboarding de cliente | BL | L2 | ASSISTED |
| g9-csat-analyst | analisa CSAT/NPS | OP | L2 | AUTONOMOUS |
| g9-refund-handler | processa reembolsos (com gate) | BL | L2 | ASSISTED |
| g9-messaging-concierge | atendimento em canais de mensageria (canal configurável, C7) | BL | L2 | ASSISTED |
| g9-fulfillment-tracker | acompanha o estado de uma transação/entrega de outcome (genérico) | BL | L2 | AUTONOMOUS |
| g9-dispute-mediator | media disputas entre partes de uma transação | BL | L2 | ASSISTED |
| g9-voice-of-customer | sintetiza VoC → Produto | OP | L2 | AUTONOMOUS |
| g9-sentiment-monitor | monitora sentimento em canais | OP | L2 | AUTONOMOUS |

### G10 · Finanças & Unit Economics — 10
| Agente | Papel | Ledger | Tier | Nasce |
|---|---|---|---|---|
| g10-finance-supervisor | orquestra finanças | OP | L1 | ASSISTED |
| g10-unit-economist | guarda C3 (custo ≤25% billable) | OP | L1 | ASSISTED |
| g10-fpna | planejamento/forecast financeiro | OP | L1 | ASSISTED |
| g10-reconciliation | conciliação bancária/pagamentos | OP | L2 | ASSISTED |
| g10-invoicing | emissão fiscal | OP | L2 | ASSISTED |
| g10-token-cost-accountant | rateia custo de tokens por guilda (livro OP) | OP | L2 | AUTONOMOUS |
| g10-margin-watch | alerta de compressão de margem | OP | L2 | AUTONOMOUS |
| g10-treasury | fluxo de caixa | OP | L1 | ASSISTED |
| g10-tax-compliance | obrigações fiscais (BR) | OP | L1 | ASSISTED |
| g10-burn-monitor | runway/burn vs. plano | OP | L1 | AUTONOMOUS |

### G11 · Pessoas & Conhecimento — 8
| Agente | Papel | Ledger | Tier | Nasce |
|---|---|---|---|---|
| g11-people-supervisor | orquestra pessoas/KM | OP | L1 | ASSISTED |
| g11-recruiter-sourcer | sourcing da camada humana fina (DRIs/ICs) | OP | L2 | ASSISTED |
| g11-jd-author | descreve vagas (arquétipos YC) | OP | L2 | AUTONOMOUS |
| g11-interview-scheduler | agenda/coordena entrevistas | OP | L2 | AUTONOMOUS |
| g11-onboarding-buddy | onboarding de humanos no NÚCLEO | OP | L2 | ASSISTED |
| g11-meeting-notetaker | grava/transcreve/resume reuniões → Brain (YC#3) | OP | L2 | AUTONOMOUS |
| g11-km-curator | curadoria de conhecimento da empresa | OP | L1 | AUTONOMOUS |
| g11-policy-author | políticas internas | OP | L1 | ASSISTED |

### G12 · Jurídico & Risco — 8
| Agente | Papel | Ledger | Tier | Nasce |
|---|---|---|---|---|
| g12-legal-supervisor | orquestra jurídico | OP | L1 | ASSISTED |
| g12-contract-reviewer | revisa contratos | OP | L2 | ASSISTED |
| g12-tos-privacy-author | ToS/política de privacidade | OP | L1 | ASSISTED |
| g12-regulatory-monitor | monitora regulação (LGPD + regulador setorial do mercado, a definir) | OP | L1 | AUTONOMOUS |
| g12-dpa-manager | DPAs e processadores de dados | OP | L2 | ASSISTED |
| g12-ip-trademark | marca/IP | OP | L2 | ASSISTED |
| g12-risk-register | registro/monitor de riscos corporativos | OP | L1 | ASSISTED |
| g12-litigation-tracker | acompanha disputas | OP | L2 | ASSISTED |

### G13 · Governança (Foundry Guild) — 11 · *a meta-guilda que mantém as outras honestas*
| Agente | Papel (Guardian do foundry) | Ledger | Tier | Nasce |
|---|---|---|---|---|
| g13-governance-supervisor | orquestra governança/gates | OP | L0 | ASSISTED |
| g13-po-guardian | valida C1/C2 (cláusula de outcome) | OP | L0 | ASSISTED |
| g13-unit-economist-guardian | valida C3 (espelha g10, no gate) | OP | L1 | ASSISTED |
| g13-promotion-officer | administra os 6 gates + cross-approval (C4) | OP | L1 | ASSISTED |
| g13-artifact-architect | valida C5/C7 + spec técnica | OP | L1 | ASSISTED |
| g13-tenant-context-curator | valida C8 (anti-hardcode) | OP | L1 | AUTONOMOUS |
| g13-observability-guardian | valida C6 (telemetria) | OP | L1 | AUTONOMOUS |
| g13-security-privacy-guardian | assina gate de AUTONOMOUS | OP | L1 | ASSISTED |
| g13-eval-engineer-guardian | valida qualidade da eval-suite | OP | L2 | AUTONOMOUS |
| g13-learning-curator | curadoria do self-harness/instincts | OP | L1 | AUTONOMOUS |
| g13-monthly-reviewer | reviewer independente mensal (DeepAgent) | OP | L0 | AUTONOMOUS |

### + Supervisor-raiz (1) e utilitários compartilhados (5+)
`root-supervisor` (CEO-OS) · `hermes-learning-loop` (cron de aprendizado) · `mcp-gateway-comms` · `mcp-gateway-payments` · `mcp-gateway-external` · `brain-indexer` (indexa artefatos no Company Brain).

---

## D. Padrões transversais (como 150 specs não viram 150 reinvenções)

1. **Herança de skills L0/L1 (C5):** company-dna, icp-loader, offerings-loader carregados uma vez e cacheados; todo agente herda. ~70% de economia de tokens.
2. **Skills compartilhadas por `/evolve`:** quando ≥N agentes desenvolvem o mesmo instinct, vira skill da guilda (ou da empresa). O aprendizado é coletivo.
3. **Camada de abstração C7:** `tools` referenciam interfaces (`MessagingProvider`, `PaymentGateway`, `LLMProvider`), nunca SDK direto → trocar provider não toca os 150 agentes.
4. **Config-over-code C8:** variação entre instâncias do mesmo agente é dado no contexto, nunca `if (x === 'y')`. O Tenant-Context-Curator faz lint disso em runtime.

> Próximo: [04-IMPLEMENTACAO.md](04-IMPLEMENTACAO.md) — o código que materializa este catálogo, fase a fase.
