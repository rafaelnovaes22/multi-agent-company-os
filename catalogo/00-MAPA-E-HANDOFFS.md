# Mapa de handoffs e checagem de consistência

> Agente de consistência do NÚCLEO. Entrada: interfaces declaradas (provides/needs/handoffs) das 14 guildas (G00–G13) + 10 regras de growth (GR1–GR10).
> Data: 2026-05-29. Mercado/vertical: **NÃO DEFINIDO** (decisão pendente do AI Founder).

---

## 1. Matriz de handoffs inter-guilda

Linha = guilda **emissora** (quem entrega). Coluna = guilda **destino** (quem recebe). Célula = artefato/entregável principal.

| De \ Para | G00 Núcleo | G01 Estrat. | G02 Produto | G03 Eng. | G04 Eval | G05 Seg. | G06 Dados | G07 Growth | G08 Vendas | G09 CustOps | G10 Finanças | G11 Pessoas | G12 Jurídico | G13 Gov. |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **G00 Núcleo** | — | routing.decision; snapshot global; interrupt | | adaptadores via mcp-gateway-external | | | event store + índice vetorial + grafo (Brain) | MessagingProvider (comms) | PaymentGateway | MessagingProvider (comms) | PaymentGateway + audit-logs custo OP | | | learning-loop (skills/PRs memória); C6 |
| **G01 Estratégia** | (consome OKRs/orçamento) | — | teardown.opportunity_map + wedges | | | | | content.post_artifact + narrative.canonical + amplification_brief | | | pedido runway + premissas econômicas | (headcount-plan via needs G11) | | |
| **G02 Produto** | | sinais competitivos; alertas de tema; horizonte roadmap | — | PRD (C2) + critérios→evals + protótipo; bugs roteados | | | leituras A/B; insights retenção | drafts beeswarming; RPS; veredito lovability; packaging 3 camadas | | | | | | |
| **G03 Engenharia** | | | features entregues; contratos publicados; release notes | — | PRs CI verde; contratos; novos eval-cases adversariais | mapa PII; escopo C7; incidentes | eventos C6; schema/contratos; SLOs | artefato de release por ship; flags segmentadas | | status incidente; flags mitigação | ficha custo/SLA provedores; custo infra/tokens | | | artefatos de agentes; evidências C5/C6/C7/C8; instincts |
| **G04 Eval** | | | Quality Verdict; gate lovability; promoção de modo C4 | gate.result PASS/FAIL; regressão/cobertura/carga; eval-cases adversariais | — | robustez injeção; flags PII/LGPD | eval-runs por trace_id; sinais drift | | | | custo eval (token-max); custo/outcome vs C3 | | | (sinal de gate consumido) |
| **G05 Segurança** | | | | achados AgentShield/secrets; controles threat model; CVE; contenção | casos de regressão de segurança | — | regras sanitização PII; demanda streams fraude | proteção verba freemium (OP) | | decisões fraude/ATO; casos disputa | perda por fraude evitada; razão C3 | gatilho revogação acesso (offboarding) | avaliação LGPD; DPAs; risk register | veredito gate segurança + assinatura AUTONOMOUS |
| **G06 Dados** | | north-star + RPS; forecast receita/cenários | leituras experimentos; retenção por coorte | alertas anomalia↔deploys | | | — | RPS; coortes/retenção; A/B; listas churn | | | forecast demanda/receita; alertas/drift custo | | | sinais drift + gatilho rebaixamento; histórico reviewer |
| **G07 Growth** | | conteúdo build-in-public; marca/distribuição como fosso | sinais mercado/comunidade; consumo product.shipped | | | (consome anti-fraude indicação) | eventos tracking/atribuição; co-modelagem RPS | — | leads ativados; sinais expansão; pricing outcome-native na copy | problemas suporte da comunidade; sentimento social | gasto/canal; CAC/payback; prova delight>pago (C3) | membros high-slope→recruiter | copy/claims; contratos criadores p/ revisão | |
| **G08 Vendas** | | (metas receita via board) | gatilho ativação no contrato; sinais expansão | | | | eventos funil/billing/receita no Brain | narrativa deals; feedback canal; RPS | — | (handoff conta via G9) | faturas; MRR/ARR/NRR; inadimplência; custo entrega→C3 | | cláusulas não-padrão; cobrança; LGPD/fiscal | |
| **G09 CustOps** | | | VoC priorizado; fricções ativação | padrões incidente/causa-raiz; bugs com repro | (agreement-rate SHADOW→G13) | sinais abuso reembolso; suspeita fraude | sentimento como feature; outcome entregue; contas risco churn | promotores/detratores; RPS; narrativa | contas qualificadas p/ expansão | — | ordens reembolso aprovadas | | casos escalonamento/disputa | telemetria agreement-rate; propostas promoção |
| **G10 Finanças** | (custo OP consumido) | runway; burn; forecast p/ investor-update/OKRs | (custo outcome→C3 via needs G02/G04) | | (piso C3 consumido p/ gate) | divergências conciliação suspeitas fraude | token_cost.allocation p/ Operator Console | verba freemium/delight (ledger OP) | min_price (piso C3); NF; conciliação | | — | calendário pagamentos + provisão folha humana | consumo notas tributárias; base legal alíquotas | economist_review + c3_check + signature_hash p/ Gate 2 |
| **G11 Pessoas** | | action items↔OKRs; saúde da guilda p/ founder office | | | | provisionamento acesso least-priv; flags PII transcrições; guardrails | artefatos conhecimento→nl2sql/data-quality | vagas/JDs como conteúdo; pedido sourcing inbound | | | (custo via needs G10) | — | JDs/contratos colaborador p/ revisão trabalhista | políticas/taxonomia/acesso p/ guardrail/C8 |
| **G12 Jurídico** | | heatmap risco; sumário regulatório p/ board | clearance nomes feature; req. privacidade/consentimento | conformidade licenças OSS; DPA antes de ferramenta c/ PII | | controles regulatórios; DPAs (incidente, transf. internacional) | bases legais LGPD; RoPA sobre fluxos | | redlines contratos cliente; cláusulas aprovadas | | parecer casos sensíveis (via needs G9) | provisão contencioso; termos financeiros revisados | acompanhamento casos trabalhistas; políticas legais pessoas | — | artefatos legais p/ gates C1/C2 + Guardians |
| **G13 Governança** | (learning-curator gateia skills do G00) | relatório mensal C1-C8; ADRs; escalonamento promoções | (vereditos consumidos) | violações C5/C7/C8; refator config-over-code | lacunas cobertura; taste-gate; modos de falha | exigência mitigação P0/P1; revogações pós-incidente; vazamento PII | desvio outcomes↔traces (C6); shadow process | | | | veto econômico C3; custo token learning loop | | | — |

Notas de leitura:
- Células vazias = sem handoff direto declarado (relação pode existir só via `needs`, não como entrega ativa).
- "Todas as guildas": G01 entrega `okr.proposal`+`northstar` a todas; G06 entrega Operator Console + NL2SQL a todas; G13 entrega vereditos de gate a G2–G12; G00 entrega routing.decision às 13 guildas.

---

## 2. Inconsistências

### 2.1 Needs sem provider correspondente / handoff órfão

| ID | Severidade | Inconsistência |
|---|---|---|
| C-01 | high | **G08 Vendas não recebe handoff explícito de Growth (G07) nem de Produto.** G08 declara `needs`: "Intake de leads dos canais de aquisição (G-Growth)", "Founder brand / provas de produto (G-Growth)", "Sinais de uso/ativação dos agentes-produto (G-Produto)". G07 **tem** handoff "para G08: leads ativados + sinais expansão", logo o lead-intake está coberto; porém **nenhuma guilda entrega a G08 "sinais de uso/ativação dos agentes-produto"** — G02 só entrega "gatilho de ativação no contrato" *de* G08, não *para* G08. Loop de ativação→produto está invertido. |
| C-02 | high | **G08 e G02 ambos definem pricing/packaging em 3 camadas** sem dono único. G02 provê "estudos de WTP e recomendação de packaging em 3 camadas"; G08 provê "Tabela de preços versionada em 3 camadas com checagem C3 (g8-pricing-engine)"; G01 também entrega "diretriz outcome-based de 3 camadas" para uma "Guilda de Pricing". **Duplicação de responsabilidade** — ver também M-01 (a "Guilda de Pricing" não existe). |
| C-03 | high | **G01 entrega para "Guilda de Pricing" (handoff) que não existe no roster G00–G13.** Handoff órfão: `teardown.pricing_observed` + diretriz 3 camadas vão para destino inexistente. O pricing real mora em G08 (pricing-engine) e G10 (unit-economist/C3). Reroteamento necessário. |
| C-04 | med | **G05 needs "Verba de freemium/marketing como livro OP (G7/G10)" — provider é G10**, que entrega "verba freemium/delight isolada (ledger OP)" para G07, não para G05. G05 quer *proteger* a integridade do OP (anti-abuso), mas não há handoff G10→G05 nem G07→G05 entregando visibilidade do ledger OP. Loop anti-abuso de incentivos sem feed de dados. |
| C-05 | med | **G06 needs "Experimentos de growth a serem lidos (g7-ab-growth-runner)" — G07 não declara handoff entregando experimentos brutos para G06.** G07→G06 entrega "eventos de tracking/atribuição + co-modelagem RPS + leitura de A/B", mas a leitura estatística é *provida por G06*. Ambos reivindicam "leitura de A/B" (G06 provê "leituras estatísticas A/B com ship/kill/iterate"; G02 provê "vereditos A/B"; G07 provê "resultados de experimentos de growth"). **Tripla sobreposição em leitura de experimento A/B.** |
| C-06 | med | **G06 needs lista agentes nomeados de G10 (g10-fpna, g10-treasury, g10-burn-monitor) para forecast**, mas G10 só tem 10 agentes e seu `provides` cita "FP&A", "Tesouraria", "burn vs plano" — o handoff G06↔G10 é mútuo (forecast↔custo) e consistente, porém **G06 needs "forecast de demanda (g6-forecaster)" de si mesma** misturado com needs de FP&A: a fronteira forecast-de-demanda (G06) vs forecast-financeiro (G10) precisa de ADR para evitar dupla fonte de verdade de receita. |
| C-07 | low | **G09 needs "Execução financeira de reembolsos (G10)"**; G09 entrega "ordens de reembolso aprovadas no gate humano" para G10, e G10 declara needs "Eventos de cobrança aprovada do G8" mas **não declara needs de ordens de reembolso de G09**. Falta o lado receptor em G10 (a NF/estorno existe em G08-dunning, não em G10). Reembolso fica entre G08, G09 e G10 sem dono de execução claro. |
| C-08 | low | **G11 needs "Decisão de ROI-vs-headcount de G10"**; G11 entrega "pedidos de contratação com tese ROI" para G10; G10 entrega "calendário de pagamentos + provisão de folha" para G11 — mas **G10 não declara em `provides` nenhuma "decisão de ROI-vs-headcount / aprovar-ou-não-abrir-vaga"**. O veredito econômico de abertura de vaga não tem produtor explícito. |
| C-09 | low | **G13 needs "DPAs (g12-dpa-manager)" e "Mapa de PII (g5-lgpd-privacy)"** — ambos cobertos. Porém G13 needs "Constituição-runtime C1-C8 versionada e manifest auditável" **não tem provider declarado em nenhuma guilda** (é auto-referente/insumo do próprio Foundry). Artefato fundacional sem dono de manutenção. |
| C-10 | med | **Loop de incidente fechado por G09 mas sem retorno a G09.** G03 entrega "status incidente/flags mitigação" para G09; G09 entrega "padrões de incidente/causa-raiz" para G03. Consistente. Mas **G05 incident-responder entrega contenção para G03**, e G09 (que fala com cliente) não recebe handoff de G05 sobre incidentes de segurança que afetam clientes — só de fraude. Gap de comunicação cliente em incidente de segurança. |

### 2.2 Duplicação de responsabilidade entre guildas

| ID | Severidade | Duplicação |
|---|---|---|
| D-01 | high | **Referral Propensity Score (RPS)** é "provido" por G01, G02, G06, G07, G08, G09 simultaneamente. G06 declara ser a **métrica canônica** (single source of truth). Os demais deveriam *consumir/alimentar*, não *prover*. Risco de múltiplas definições do mesmo score. |
| D-02 | high | **North-star / Daily Active Outcomes** aparece como provide em G01 (northstar.daily_value), G06 (métrica canônica versionada) e G07 (North Star de growth). GR6 atribui dono a g6-metrics-modeler; G01 define a *meta*, G06 *modela/versiona*. Precisa separar "definição de OKR" (G01) de "instrumentação canônica" (G06). |
| D-03 | med | **Build-in-public / artefato de post por ship** provido por G01 (content.post_artifact), G02 (drafts de post), G03 (artefato de release), G07 (beeswarming/distribuição), G09 (artefatos de conhecimento). GR4 atribui dono a g2-release-notes + g7-social-manager. Cadeia OK (G03 gera release → G02 nota → G07 distribui) mas G01 também produzir "content.post_artifact" sobrepõe a G07. |
| D-04 | med | **Packaging/pricing 3 camadas** — ver C-02/C-03. G01, G02, G08, G10 todos tocam. Dono GR5 = g8-pricing-engine / g10-unit-economist. G01 e G02 deveriam só *recomendar*, G08 *versiona a tabela*, G10 *trava C3*. |
| D-05 | med | **Leitura de experimentos A/B** — G02 (vereditos), G06 (leituras estatísticas ship/kill/iterate), G07 (resultados de growth). Ver C-05. G06 deve ser leitura estatística canônica; G02/G07 desenham e executam, não leem. |
| D-06 | low | **Company Brain queryable** provido por G00 (brain-indexer: event store+vetor+grafo), G06 (NL2SQL/Operator Console) e G11 (Company Brain de transcrições humanas). São camadas distintas (G00=infra, G06=interface analítica, G11=KM humano) mas o nome colide; precisa de nomenclatura distinta para evitar confusão de fonte de verdade. |
| D-07 | low | **Veredito de gate de segurança / promoção AUTONOMOUS** — G05 provê "veredito de gate de segurança + assinatura" e G13 provê "assinatura de segurança+LGPD para gate AUTONOMOUS". A assinatura final é de G13 (promotion-officer) consumindo o sinal de G05; está coerente mas a palavra "assinatura" nos dois lados pode gerar ambiguidade de autoridade. |

---

## 3. Vazamento de mercado (suposições de setor)

O mercado **ainda não foi definido**; tudo deve estar agnóstico. Indícios de vazamento de vertical encontrados:

1. **G08 Finanças/Vendas — "Documentos fiscais BR" / "Regime e alíquotas tributárias BR" / "documentos fiscais BR (NF)"** (G08-billing-agent, G10): assume **jurisdição Brasil**. É premissa de jurisdição, não de mercado-produto; aceitável se "BR" for decisão deliberada do AI Founder, mas deve ser marcado como configurável (atualmente G10 diz "configuráveis" — OK; G08 diz "BR" hard, marcar configurável).
2. **G00 — "PaymentGateway ... jurisdição BR"** (mcp-gateway-payments): mesma premissa BR embutida na camada C7. Deveria ser provider-config, não hardcode de jurisdição.
3. **G00 — "whatsapp-concierge"** citado no handoff de MessagingProvider: **WhatsApp é canal específico**. Embora o handoff diga "configurável quando o mercado for definido", nomear whatsapp-concierge como agente já presume canal de mensageria dominante (típico de varejo/serviços/food/delivery BR). Vazamento de canal.
4. **G03 — conectores "pagamentos, mensageria, mapas"** (C7): **"mapas"** é um conector de domínio específico (logística/delivery/mobilidade/marketplace de localização). Pagamentos e mensageria são genéricos; **mapas presume vertical com geolocalização** (food delivery, mobilidade, field service). Vazamento mais forte do conjunto.
5. **Pricing "outcome-based / Daily Active Outcomes"** repetido em G01/G05/G06/G07/G08: "outcome" é modelo de negócio agnóstico (OK), mas "Daily Active **Outcomes**" como north-star presume que o produto entrega "outcomes diários" — consistente com produto AI-as-a-service, **não** vaza vertical. Sem ação.
6. **G07 — "lifecycle (e-mail/push/mensageria)"** e G09 "whatsapp" implícito: canais de mensageria já assumidos. Marcar como configuráveis.

> Resumo de leak: 2 premissas de **jurisdição BR** (fiscal + payment gateway), e 2 premissas de **canal/vertical** ("mapas" em C7 e "whatsapp-concierge"). "Mapas" e "whatsapp" são os vazamentos de mercado mais concretos a remover/configurar antes da definição do vertical.

---

## 4. Lacunas de cobertura (funções AI-native sem dono)

| ID | Lacuna | Detalhe |
|---|---|---|
| L-01 | **Model/LLM Ops e gestão de provedores de modelo** | Há custo de tokens (G10), eval de prompt (G04) e drift (G06), mas **nenhum agente é dono da seleção/roteamento de modelo, fallback entre LLMs, fine-tune/versionamento de modelo e contratos de provider de inferência**. G00 cobre gateways de comms/payments/external, não de *modelos*. |
| L-02 | **Gestão de prompt/contexto como artefato versionado** | prompt_hash é consumido (G10/G04) mas nenhum agente **versiona, faz curadoria e A/B de prompts/contexto** como ciclo de vida próprio (prompt registry / context engineering owner). |
| L-03 | **Annotation / human-labeling / RLHF data ops** | G04 usa "gabarito humano/baseline" e G13 "aprovação humana", mas **não há dono do pipeline de rotulagem humana e geração de dados de avaliação/treino** (golden datasets além de eval-cases). |
| L-04 | **Customer onboarding/implementação (lado cliente, não pessoas)** | G09 cobre suporte/VoC/reembolso; G11 cobre onboarding **humano interno**. **Onboarding/ativação do cliente no produto** (solutions/implementation/CSM proativo) não tem dono claro — só "fricções de ativação" reportadas. |
| L-05 | **Data Governance / catálogo de dados além de PII** | G05 cobre PII/LGPD, G06 cobre semantic layer/data-quality. Falta **dono de governança de dados de terceiros, retenção, lineage de consentimento e residência de dados** como função transversal (parcialmente em G12 RoPA, mas sem agente de data-governance operacional). |
| L-06 | **Partnerships / BD / ecossistema** (não-criadores) | G07 cobre criadores/influenciadores; G08 cobre vendas diretas. **Parcerias estratégicas, integrações de ecossistema e channel/marketplace partnerships** não têm dono. |
| L-07 | **Procurement / vendor management (custo SaaS/infra não-token)** | G10 cobre tokens e burn; G03 cobre infra. **Compra e gestão de fornecedores SaaS/tooling (custo não-inferência)** não tem dono dedicado. |
| L-08 | **Sustainability/Responsible-AI/ethics & red-team de viés** | G05 cobre segurança/injection/fraude; G04 cobre robustez. **Avaliação de viés, fairness, alinhamento de comportamento do agente e responsible-AI** não tem dono explícito (G13 é constitucional/processo, não testes de fairness). |
| L-09 | **Localization / i18n** | Implícito que tudo é BR/pt; **nenhum agente dono de internacionalização**, o que conflita com a meta de manter agnóstico/global. |
| L-10 | **Disaster recovery / business continuity** | G03 tem "deploys reversíveis" e G05 "incident-responder", mas **BCP/DR formal (RTO/RPO, backups, failover de dados)** não é provide de nenhuma guilda. |

---

## 5. Donos das regras de growth (GR1–GR10)

| GR | Regra | Dono declarado | Dono existe no roster? | Observação |
|---|---|---|---|---|
| GR1 | Earned-before-paid | g7-growth-supervisor | Sim (G07, 14 agentes) | OK. |
| GR2 | Delight-grátis > pago (OP fora de C3) | g10-token-cost-accountant | Sim (G10) | OK — mas ver C-04: visibilidade do ledger OP não chega a G05 (anti-abuso). |
| GR3 | Ship diário + tier-1 mensal | g3-eng-supervisor + g7-growth-supervisor | Sim (G03, G07) | OK — dono compartilhado coerente (Fábrica + lançamento). |
| GR4 | Todo ship vira build-in-public | g2-release-notes + g7-social-manager | Sim (G02, G07) | OK — cadeia G03(release)→G02(notes)→G07(distribuição). Ver D-03 (G01 sobrepõe). |
| GR5 | Outcome-based é o destino (3 camadas) | g8-pricing-engine / g10-unit-economist | Sim (G08, G10) | OK no dono, MAS ver C-02/C-03/D-04: G01 roteia pricing para "Guilda de Pricing" inexistente. |
| GR6 | North-star líder, LTV depois | g6-metrics-modeler | Sim (G06) | OK — mas ver D-02: G01 e G07 também "provêm" north-star. |
| GR7 | Marca/distribuição é o fosso | g1-narrative-synthesizer + g7-community-manager | Sim (G01, G07) | OK. |
| GR8 | Gate de lovability | g4-quality-gate | Sim (G04) | OK — G02 emite "veredito do gate de lovability"; checar se é G02 quem decide ou G04. Possível duplicação de autoridade (G02 provê veredito, GR8 diz dono é G04). |
| GR9 | Hire-for-slope | AI Founder / g11-recruiter-sourcer | Parcial | g11-recruiter-sourcer **não aparece nominalmente** nos handoffs de G11 (que cita g11-jd-author, notetaker, onboarding-buddy, policy-author, km-curator, people-supervisor). G11 tem só 8 agentes; recruiter-sourcer é referenciado por G07 ("→ recruiter-sourcer") e GR9, então provavelmente existe, mas não está explícito no interface de G11. **Confirmar existência.** |
| GR10 | PMF treadmill (reset ~90 dias) | AI Founder + g13-monthly-reviewer | Sim (G13) | OK — g13-monthly-reviewer aparece no handoff de G13 (relatório mensal). |

**Veredito GR:** 9/10 com dono confirmado no roster. **GR9 tem dono parcialmente confirmado** (g11-recruiter-sourcer citado mas ausente da lista de agentes nomeados de G11). GR8 tem ambiguidade de autoridade entre G02 (emite veredito) e G04 (dono do gate).

---

## 6. Ações prioritárias (top 5)

1. **Criar/rerotear pricing:** eliminar a "Guilda de Pricing" fantasma de G01; rotear `teardown.pricing_observed` + diretriz 3 camadas para G08 (pricing-engine) e C3 para G10 (C-03/D-04/GR5).
2. **Canonizar RPS e North-star em G06:** mudar provide de G01/G02/G07/G08/G09 para "alimenta/consome" (D-01/D-02).
3. **Remover vazamentos de mercado:** tornar "mapas" (C7), "whatsapp-concierge" e jurisdição BR configuráveis/agnósticos até definição do vertical (leaks 1–4).
4. **Fechar loops de ativação/reembolso:** definir produtor de "sinais de uso/ativação do produto → G08" e dono de execução de reembolso entre G08/G09/G10 (C-01/C-07).
5. **Cobrir lacunas AI-native críticas:** atribuir donos para Model/LLM-Ops (L-01), Prompt/Context registry (L-02) e Customer onboarding do produto (L-04).
