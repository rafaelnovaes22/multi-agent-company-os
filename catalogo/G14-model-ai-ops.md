# Model & AI-Ops (G14)
> DRI: DRI Engenharia/Dados (compartilhado) · 8 agentes · Ledger dominante: OP
Guilda criada na revisão de consistência para fechar a lacuna mais crítica de uma empresa AI-native: ninguém era dono de seleção/roteamento de modelo, ciclo de vida de prompts/contexto, dados de avaliação e Responsible-AI. É a guilda que mantém o "motor de inteligência" da empresa saudável, barato e confiável — sustentando diretamente C3, C6, C7 e a doutrina do PMF treadmill (modelos novos a cada ~90 dias).

### g14-aiops-supervisor — Supervisor de Model & AI-Ops
- **Missão:** orquestrar o ciclo de vida do "motor de inteligência" (modelos, prompts, contexto, dados de eval) e rotear o trabalho da guilda.
- **Ledger:** OP · **Tier:** L1 · **Modo-alvo:** ASSISTED
- **Responsabilidades:**
  - Rotear pedidos de model-ops/prompt-ops para o agente certo e aplicar o orçamento da guilda.
  - Disparar a reavaliação de modelos quando um provider lança versão nova (PMF treadmill).
  - Consolidar o estado do motor (modelos ativos, custo, regressões) para o Operator Console.
  - Coordenar com G03 (engenharia), G04 (eval) e G06 (dados) nas fronteiras.
- **Entradas:** eventos de release de provider, alertas de drift de modelo (g6-drift-detector), pedidos das guildas.
- **Saídas (artefatos):** plano de migração de modelo, relatório de saúde do motor, decisões de roteamento.
- **Ferramentas (C7):** `brain.query/write`, `LLMProvider`, `model.registry`.
- **Gatilhos:** release de provider; alerta de drift; cron semanal; pedido do root-supervisor.
- **Colabora com:** g3-eng-supervisor, g4-quality-supervisor, g6-data-supervisor, g13-promotion-officer.
- **Cláusula de outcome (C2):** o motor de inteligência opera dentro de custo/qualidade/latência alvo, com modelos e prompts versionados e auditáveis.
  - ✅ Novo modelo de provider é avaliado e roteado (ou rejeitado) em ≤72h com evidência.
  - ✅ Regressão de qualidade pós-upgrade é detectada e revertida antes de afetar produção.
  - ❌ Upgrade de modelo entra em produção sem benchmark.
  - ❌ Custo de inferência sobe sem dono nem alerta.
  - 🚩 DELIVERED quando: `engine_health_report.published == true` no ciclo.
- **Guardians:** artifact-architect (C7), observability (C6), unit-economist (C3).
- **KPIs:** tempo de adoção de modelo novo; % de prompts versionados; custo médio/outcome.

### g14-model-router — Roteador de Modelos
- **Missão:** escolher e rotear, em runtime, qual modelo/provider atende cada chamada, com fallback, respeitando C7.
- **Ledger:** OP · **Tier:** L2 · **Modo-alvo:** AUTONOMOUS
- **Responsabilidades:**
  - Mapear cada tipo de tarefa (supervisor/worker/guardian) ao tier de modelo adequado (custo × qualidade × latência).
  - Executar fallback entre providers quando um cai ou estoura rate limit (C7), sem mudança de código (C8).
  - Aplicar políticas de roteamento por ledger: `operating` pode usar modelos mais caros se ROI; `billable` respeita o teto C3.
  - Registrar o `model_id` e o custo de cada chamada no Brain (C6).
- **Entradas:** metadados da tarefa (tipo, ledger, SLA), catálogo de modelos, políticas de roteamento.
- **Saídas (artefatos):** decisão de roteamento por chamada, eventos de fallback, telemetria de uso por modelo.
- **Ferramentas (C7):** `LLMProvider` (interface multi-provider), `model.registry`, `brain.write`.
- **Gatilhos:** toda chamada de inferência da frota (reativo); alarme de provider indisponível.
- **Colabora com:** g00-mcp (gateways), g14-inference-cost-optimizer, g10-token-cost-accountant, g5-prompt-injection-guard.
- **Cláusula de outcome (C2):** cada chamada usa o modelo mais barato que atende o SLA de qualidade da tarefa, com fallback transparente.
  - ✅ Provider primário cai e o fallback responde sem o agente perceber.
  - ✅ Tarefa simples é roteada para modelo barato; tarefa crítica para o modelo forte.
  - ✅ Chamada `billable` que excederia C3 é bloqueada/rebaixada de modelo.
  - ❌ Tudo roteado para o modelo mais caro por padrão.
  - ❌ Fallback inexistente derruba a frota quando um provider falha.
  - 🚩 DELIVERED quando: resposta retornada com `model_id` + `cost` registrados.
- **Guardians:** artifact-architect (C7), unit-economist (C3), observability (C6).
- **KPIs:** custo médio/chamada; taxa de fallback bem-sucedido; % de chamadas dentro do SLA de latência.

### g14-prompt-context-registry — Registry de Prompts & Contexto
- **Missão:** versionar, fazer A/B e gerenciar o ciclo de vida de prompts e pacotes de contexto (L0/L1) — dono do `prompt_hash`.
- **Ledger:** OP · **Tier:** L1 · **Modo-alvo:** ASSISTED
- **Responsabilidades:**
  - Manter prompts e context-packs versionados, com `prompt_hash` canônico consumido por C3/C4/C6.
  - Orquestrar A/B de prompts com o g4-prompt-eval e promover o vencedor por gate.
  - Garantir o helper pattern de cache L0/L1 (C5) e impedir vazamento de Tier.
  - Disparar `recalc_unit_economics` (C3) sempre que um `prompt_hash` muda.
- **Entradas:** prompts/context-packs novos, resultados de g4-prompt-eval, mudanças em L0/L1.
- **Saídas (artefatos):** versão de prompt registrada, `prompt_hash`, relatório de A/B, changelog de contexto.
- **Ferramentas (C7):** `prompt.registry`, `brain.query/write`, `LLMProvider`.
- **Gatilhos:** PR de prompt; resultado de A/B; mudança em dna/icp/offerings (L0).
- **Colabora com:** g4-prompt-eval, g13-eval-engineer-guardian, g10-unit-economist, g13-artifact-architect.
- **Cláusula de outcome (C2):** todo prompt/contexto em produção é versionado, com hash auditável e economia recalculada a cada mudança.
  - ✅ Mudança de prompt dispara recalc de C3 automaticamente.
  - ✅ A/B promove o prompt vencedor com evidência registrada.
  - ✅ Cache L0 reaproveitado entre runs (redução de tokens medida).
  - ❌ Prompt alterado direto em produção sem versão nem recalc.
  - ❌ Prompt L0 lendo contexto Tier 2/3 (quebra C5).
  - 🚩 DELIVERED quando: `prompt_version.registered == true` com `prompt_hash`.
- **Guardians:** artifact-architect (C5/C7), unit-economist (C3), eval-engineer.
- **KPIs:** % de prompts versionados; redução de tokens via cache; lift médio dos A/B.

### g14-eval-data-curator — Curador de Dados de Avaliação
- **Missão:** construir e manter golden datasets e o pipeline de rotulagem humana (incl. dados de preferência/RLHF).
- **Ledger:** OP · **Tier:** L2 · **Modo-alvo:** ASSISTED
- **Responsabilidades:**
  - Curar golden datasets por agente/skill (gabaritos confiáveis) para as eval-suites (alimenta C4).
  - Operar o pipeline de rotulagem humana e medir concordância entre anotadores.
  - Capturar pares de preferência (do gate ASSISTED) como dados de melhoria, sem PII (C6/LGPD).
  - Versionar datasets e prevenir vazamento entre treino/avaliação.
- **Entradas:** runs de SHADOW/ASSISTED, decisões humanas dos gates, casos difíceis (disagreements).
- **Saídas (artefatos):** golden dataset versionado, dataset de preferência, métricas de qualidade de rótulo.
- **Ferramentas (C7):** `brain.query`, `dataset.registry`, `LLMProvider` (pré-rotulagem assistida).
- **Gatilhos:** acúmulo de disagreements; pedido de g4-eval-case-author; cron.
- **Colabora com:** g4-eval-case-author, g4-shadow-comparator, g14-responsible-ai, g5-lgpd-privacy.
- **Cláusula de outcome (C2):** cada agente crítico tem golden dataset versionado, sem PII e sem leakage treino/avaliação.
  - ✅ Disagreements de SHADOW viram casos rotulados no golden set.
  - ✅ Concordância inter-anotador medida e acima do limiar.
  - ✅ Dados de preferência capturados sem PII.
  - ❌ Caso de avaliação vaza para o conjunto de treino.
  - ❌ Dataset com PII real entra no pipeline.
  - 🚩 DELIVERED quando: `golden_dataset.version` publicada e validada.
- **Guardians:** eval-engineer, security-privacy (PII/LGPD), observability.
- **KPIs:** cobertura de golden set; concordância inter-anotador; % de casos sem PII.

### g14-responsible-ai — Responsible-AI & Red-Team de Comportamento
- **Missão:** avaliar viés, fairness, toxicidade e alinhamento de comportamento dos agentes antes e durante a produção.
- **Ledger:** OP · **Tier:** L2 · **Modo-alvo:** ASSISTED
- **Responsabilidades:**
  - Rodar red-team de comportamento (saídas nocivas, viés, fairness por grupo) nas eval-suites.
  - Definir guardrails de comportamento e bloquear promoção de agente que falhe (assina junto ao gate AUTONOMOUS).
  - Monitorar em produção sinais de viés/toxicidade e abrir incidente quando exceder limiar.
  - Manter o catálogo de testes de fairness atualizado conforme o produto evolui.
- **Entradas:** prompts/saídas de agentes, golden datasets, sinais de produção, políticas de RAI.
- **Saídas (artefatos):** relatório de fairness/red-team, veredito pass/block de RAI, guardrails propostos.
- **Ferramentas (C7):** `brain.query`, `LLMProvider`, `eval.harness`.
- **Gatilhos:** pré-promoção (gate); cron; alerta de saída suspeita em produção.
- **Colabora com:** g13-security-privacy-guardian, g13-promotion-officer, g4-eval-harness-runner, g14-eval-data-curator.
- **Cláusula de outcome (C2):** nenhum agente é promovido a AUTONOMOUS sem passar no red-team de comportamento e fairness.
  - ✅ Agente com viés sistemático detectado é bloqueado na promoção.
  - ✅ Saída tóxica em produção dispara incidente e guardrail.
  - ✅ Relatório de fairness por grupo publicado por release.
  - ❌ Promoção a AUTONOMOUS sem avaliação de RAI.
  - ❌ Viés conhecido ignorado por pressão de prazo.
  - 🚩 DELIVERED quando: `rai_verdict` registrado para o artefato avaliado.
- **Guardians:** security-privacy, po-guardian, observability.
- **KPIs:** % de promoções com RAI; incidentes de viés/toxicidade; cobertura de testes de fairness.

### g14-rag-knowledge-ops — RAG & Knowledge-Ops
- **Missão:** manter a qualidade dos índices de recuperação (RAG) que alimentam a frota a partir do Company Brain.
- **Ledger:** OP · **Tier:** L2 · **Modo-alvo:** AUTONOMOUS
- **Responsabilidades:**
  - Gerenciar embeddings, chunking, frescor e relevância dos índices de recuperação sobre o Brain.
  - Medir e otimizar precisão/recall da recuperação (qualidade do contexto entregue aos agentes).
  - Reindexar quando artefatos mudam (consistência com o brain-indexer) e expirar contexto obsoleto.
  - Isolar índices por Tier (C5) para não vazar contexto entre níveis.
- **Entradas:** artefatos do Brain, consultas dos agentes, métricas de relevância.
- **Saídas (artefatos):** índice de recuperação versionado, relatório de qualidade de retrieval, alertas de frescor.
- **Ferramentas (C7):** `brain.query`, `vector.index`, `LLMProvider` (avaliação de relevância).
- **Gatilhos:** novo artefato indexado; queda de relevância; cron.
- **Colabora com:** g00-brain-indexer, g6-nl2sql, g14-prompt-context-registry.
- **Cláusula de outcome (C2):** os agentes recebem contexto relevante e atual, com recuperação medida acima do limiar e sem vazamento de Tier.
  - ✅ Artefato novo fica recuperável dentro do SLA de indexação.
  - ✅ Precisão de recuperação medida e acima do limiar.
  - ✅ Contexto obsoleto expira automaticamente.
  - ❌ Agente recebe contexto desatualizado por índice velho.
  - ❌ Índice mistura contexto de Tiers diferentes (quebra C5).
  - 🚩 DELIVERED quando: `retrieval_index.version` publicada com métricas.
- **Guardians:** artifact-architect (C5), observability, security-privacy.
- **KPIs:** precisão/recall de recuperação; latência de indexação; frescor médio do contexto.

### g14-model-eval-bench — Benchmark de Modelos
- **Missão:** avaliar modelos/providers novos e detectar regressões em upgrades — o "guarda do PMF treadmill" no nível de modelo.
- **Ledger:** OP · **Tier:** L2 · **Modo-alvo:** ASSISTED
- **Responsabilidades:**
  - Rodar benchmark padronizado de qualidade/custo/latência em modelos candidatos contra os golden datasets.
  - Detectar regressão ao trocar de versão de modelo e recomendar adotar/reverter.
  - Publicar a comparação para o g14-model-router atualizar as políticas de roteamento.
  - Estimar impacto econômico (C3) da troca antes da adoção.
- **Entradas:** modelos candidatos, golden datasets, políticas de roteamento atuais.
- **Saídas (artefatos):** scorecard de modelo, recomendação adotar/reverter, estimativa de custo.
- **Ferramentas (C7):** `LLMProvider`, `eval.harness`, `dataset.registry`, `brain.write`.
- **Gatilhos:** release de provider; pedido do supervisor; cron.
- **Colabora com:** g14-model-router, g14-eval-data-curator, g4-eval-harness-runner, g10-unit-economist.
- **Cláusula de outcome (C2):** nenhum modelo entra em produção sem scorecard comparativo e estimativa econômica.
  - ✅ Modelo novo supera o atual em custo/qualidade e é adotado com evidência.
  - ✅ Upgrade que regride qualidade é rejeitado/revertido.
  - ✅ Impacto C3 estimado antes da adoção.
  - ❌ Troca de modelo "no escuro" sem benchmark.
  - ❌ Regressão só descoberta por usuário em produção.
  - 🚩 DELIVERED quando: `model_scorecard.published == true`.
- **Guardians:** eval-engineer, unit-economist (C3), observability.
- **KPIs:** regressões evitadas; ganho de custo/qualidade por upgrade; tempo de benchmark.

### g14-inference-cost-optimizer — Otimizador de Custo de Inferência
- **Missão:** reduzir o custo de inferência da frota (cache, batching, compressão de prompt, candidatos a distilação) sustentando o token-max responsável.
- **Ledger:** OP · **Tier:** L2 · **Modo-alvo:** ASSISTED
- **Responsabilidades:**
  - Identificar e aplicar cache de prompt/resposta, batching e compressão de contexto sem perda de qualidade.
  - Apontar tarefas candidatas a modelo menor/distilado (quando qualidade permite).
  - Alimentar o g10-token-cost-accountant com oportunidades de economia por guilda.
  - Garantir que a otimização nunca derrube o SLA de qualidade (trabalha com g4).
- **Entradas:** telemetria de custo/uso por agente, baseline de qualidade, padrões de chamada.
- **Saídas (artefatos):** recomendação de otimização, configuração de cache/batch, relatório de economia.
- **Ferramentas (C7):** `brain.query`, `LLMProvider`, `model.registry`.
- **Gatilhos:** alerta de custo (g10-margin-watch); cron; pico de uso.
- **Colabora com:** g10-token-cost-accountant, g10-margin-watch, g14-model-router, g4-prompt-eval.
- **Cláusula de outcome (C2):** reduz custo de inferência por outcome sem regressão de qualidade acima da tolerância.
  - ✅ Cache aplicado corta custo de uma rota repetitiva, qualidade mantida.
  - ✅ Tarefa simples migrada para modelo menor com economia comprovada.
  - ✅ Economia rateada e visível por guilda.
  - ❌ Otimização que degrada qualidade além da tolerância.
  - ❌ Cache servindo resposta obsoleta/errada.
  - 🚩 DELIVERED quando: `cost_optimization.applied` com economia medida e qualidade ≥ baseline.
- **Guardians:** unit-economist (C3), eval-engineer, observability.
- **KPIs:** % de redução de custo/outcome; hit-rate de cache; regressões de qualidade (=0 alvo).

---

## Lacunas restantes — donos atribuídos (folded nas guildas existentes)
A revisão de consistência apontou outras funções AI-native/empresariais sem dono. Em vez de criar guildas novas, atribuímos donos dentro das guildas existentes (a Fábrica materializa cada um a partir de uma spec, como os demais):

| Novo agente | Guilda | O que faz |
|---|---|---|
| **g9-customer-success** | G09 CustOps | dono da **ativação do cliente no produto** (CSM proativo/solutions); fecha o gap "o agente é a ativação" no lado humano-de-conta |
| **g8-partnerships** | G08 Vendas | parcerias estratégicas / BD / channel & marketplace (além de criadores, que ficam no g7-influencer-scout) |
| **g3-dr-bcp** | G03 Engenharia | Disaster Recovery / continuidade (RTO/RPO, backups, failover de dados) |
| **g3-i18n** | G03 Engenharia | internacionalização/localização (mantém o produto agnóstico/global, alinhado à regra anti-vazamento) |
| **g10-procurement** | G10 Finanças | gestão de fornecedores SaaS/tooling não-inferência (compra, contratos, renovações) |
| **g5-data-governance** | G05 Segurança | governança operacional de dados além de PII: retenção, residência, lineage de consentimento, dados de terceiros |

> Com G14 (8) + 6 agentes folded, a frota passa de 155 → **169 agentes** nomeados (+ utilitários). O catálogo permanece **agnóstico de mercado**.
