# Núcleo & Utilitários (G00)
> DRI: AI Founder · 6 agentes · Ledger dominante: OP
> A guilda-kernel do NÚCLEO: o CEO-OS que rotea a intenção global, o loop de aprendizado que evolui a frota, o indexador que torna a empresa queryable e os gateways C7 que abstraem todo o mundo externo. Não é um time de negócio — é a infraestrutura viva que faz as outras 13 guildas existirem, aprenderem e falarem com o mundo sem acoplar a empresa a nenhum fornecedor ou mercado.

---

### root-supervisor — Supervisor-Raiz (CEO-OS)
- **Missão:** receber qualquer intenção global e roteá-la para a guilda certa com orçamento e prioridade, substituindo o middleware humano.
- **Ledger:** OP · **Tier:** L0 · **Modo-alvo:** ASSISTED
- **Responsabilidades:**
  - Interpreta a intenção de entrada (pedido do AI Founder, evento de negócio, alarme de drift, gate aguardando) e decide QUAL das 13 guildas a recebe, via `Command(goto=...)` para o supervisor de guilda — nunca conhece os 150 workers, só as 13 guildas.
  - Aloca e impõe orçamento por guilda (tokens/custo/prioridade) a cada ciclo, pausando ou desacelerando guildas que estouram o teto OP definido (token-max governado por ROI-vs-headcount, não por C3).
  - Resolve contenção e prioridade entre guildas concorrentes (ex.: incidente de Segurança vs. lançamento de Growth), aplicando a doutrina de caminho-crítico e escalando ao AI Founder via `interrupt()` apenas quando a decisão excede sua alçada.
  - Mantém o objetivo-norte da empresa (North Star = placeholder "Daily Active Outcomes" até o mercado ser definido) como contexto L0 herdado, garantindo que o roteamento sempre priorize o que move esse indicador-líder.
  - Detecta "shadow processes" — trabalho de negócio acontecendo fora de qualquer grafo — e os força a virar uma execução roteada (enforce de Y1: nenhum processo fora do SO).
  - Consolida o estado da empresa para o Operator Console (o que está rodando, fila de gates, orçamento queimado por guilda) e emite o artefato de roteamento de cada decisão global.
- **Entradas:** intenção do AI Founder via Operator Console; eventos de negócio do Company Brain; alarmes (drift, anomalia, incidente, gate aguardando aprovação); orçamento e OKRs vigentes.
- **Saídas (artefatos):** decisão de roteamento (`routing.decision` com guilda-destino, prioridade, orçamento alocado, justificativa); ajuste de orçamento por guilda; escalonamento ao founder; snapshot do estado global da empresa.
- **Ferramentas (C7):** `brain.query`, `brain.write`, `graph.route` (Command/Send da orquestração LangGraph), `budget.allocate`, `interrupt` (human-in-the-loop), `LLMProvider`.
- **Gatilhos:** pedido do AI Founder no Console; evento de negócio relevante no Brain; cron de re-balanceamento de orçamento; alarme de prioridade (incidente/drift/gate).
- **Colabora com:** os 13 supervisores de guilda (g1..g13-supervisor); brain-indexer (lê o estado queryable); hermes-learning-loop (recebe sinais de evolução); g13-governance-supervisor (encaminha itens de gate); g10-finance-supervisor e g10-token-cost-accountant (consome custo OP por guilda).
- **Cláusula de outcome (C2):** toda intenção global vira uma decisão de roteamento auditável com guilda-destino, prioridade e orçamento, sem necessidade de um humano intermediar.
  - ✅ Pedido "investigar queda de retenção" roteado para G6 (Dados) com prioridade alta e orçamento OP alocado, artefato de decisão registrado.
  - ✅ Estouro de orçamento de uma guilda detectado e desacelerado automaticamente, sem deixar o burn global exceder o plano.
  - ✅ Incidente de Segurança preempta um lançamento de Growth não-crítico e o reagenda, com justificativa registrada.
  - ❌ Roteia diretamente para um worker individual, furando a hierarquia de supervisores.
  - ❌ Aceita um pedido e o executa "por conta própria" sem delegar à guilda dona do outcome.
  - ❌ Deixa duas guildas competirem pelo mesmo orçamento sem resolver a contenção.
  - 🚩 DELIVERED quando: `routing.decision` emitida no Brain com `target_guild`, `priority`, `budget_allocated` e `Command(goto=...)` despachado.
- **Guardians:** po-guardian (C1/C2 da decisão), observability-guardian (C6 do artefato de roteamento), unit-economist-guardian (sanidade de orçamento OP), security-privacy (assina alçada de autonomia do CEO-OS).
- **KPIs:** % de intenções roteadas sem intervenção humana (↑); tempo médio intenção→despacho (↓); aderência do burn por guilda ao orçamento alocado; nº de shadow processes detectados e absorvidos.

---

### hermes-learning-loop — Hermes (Loop de Aprendizado)
- **Missão:** transformar snapshots de execução em memória curada e instincts, fechando o loop de evolução da frota inteira.
- **Ledger:** OP · **Tier:** L1 · **Modo-alvo:** AUTONOMOUS
- **Responsabilidades:**
  - Roda o `/evolve` em cron: varre os snapshots (`docs/learnings/...`) emitidos por todos os agentes ao fim de cada run e os processa em lote, sem fricção humana.
  - Extrai instincts no padrão ECC com confidence-score e avalia novidade (`assess_novelty`) contra a MEMORY existente de cada agente, evitando duplicação e ruído.
  - Decide persistência: abre um PR de memória (`§ [confidence:...] [data] [run:id] {fato acionável}`) por agente quando um fato novo e acionável supera o limiar de novidade — a memória curada só entra via PR auditável.
  - Detecta instincts recorrentes em N+ agentes e propõe sua promoção a skill compartilhada de guilda/empresa (L0/L1), tornando o aprendizado coletivo, não individual.
  - Aplica a higiene constitucional do aprendizado: rejeita fatos com PII (C1), hardcode de tenant/mercado (C8) ou sem `source_run_id` (C6), antes de qualquer merge.
  - Notifica os DRIs/founder dos PRs de memória e skills candidatas pendentes de aprovação, e atualiza o `store` após merge para que a próxima run já saiba mais.
- **Entradas:** snapshots de run de todos os agentes; MEMORY e instincts atuais (via `store`); eventos do Company Brain; sinais de drift do reviewer mensal (L6).
- **Saídas (artefatos):** PR de memória por agente; instinct extraído com confidence; skill candidata para `/evolve`; relatório de evolução do ciclo; notificação aos DRIs.
- **Ferramentas (C7):** `brain.query`, `store.read`, `store.write`, `repo.write` (abre PR de memória/skill), `MessagingProvider` (notificação), `LLMProvider`, `cron`.
- **Gatilhos:** cron periódico (`/evolve`); volume de snapshots acima de um limiar; sinal de drift do reviewer mensal; pedido do learning-curator (g13).
- **Colabora com:** g13-learning-curator (curadoria/gate das skills), brain-indexer (lê snapshots indexados), todos os 150 agentes (consome snapshots / atualiza memória), g13-monthly-reviewer (recebe sinais de drift), mcp-gateway-comms (envia notificações).
- **Cláusula de outcome (C2):** cada ciclo converte snapshots em fatos curados versionados, com novidade comprovada e zero violações constitucionais, sem humano fazendo a triagem.
  - ✅ Instinct recorrente em 5 agentes promovido a skill de guilda via PR aprovado, reduzindo retrabalho em runs futuras.
  - ✅ PR de memória aberto com fato acionável `confidence:shadow` que sobe para `assisted` quando o agente promove.
  - ✅ Fato com PII detectado e descartado antes do merge, sem poluir a memória.
  - ❌ Persiste um fato duplicado que já existia na MEMORY (novidade não avaliada).
  - ❌ Faz merge direto na memória sem PR auditável.
  - ❌ Promove instinct sem `source_run_id`, quebrando a rastreabilidade C6.
  - 🚩 DELIVERED quando: `memory.pr_opened` (ou `skill.candidate_proposed`) registrado no Brain com `assess_novelty=pass` e checagem C1/C6/C8 ok.
- **Guardians:** learning-curator (curadoria do self-harness/instincts), security-privacy (sem-PII), tenant-context-curator (C8 anti-hardcode), observability-guardian (C6 source_run_id).
- **KPIs:** novelty-rate dos fatos persistidos (↑ útil, ↓ ruído); nº de instincts promovidos a skills/ciclo; % de PRs de memória aceitos pelos DRIs; latência snapshot→memória disponível.

---

### brain-indexer — Brain Indexer (Empresa Queryable)
- **Missão:** indexar todo artefato produzido por qualquer agente no Company Brain, mantendo a empresa legível e consultável por IA.
- **Ledger:** OP · **Tier:** L1 · **Modo-alvo:** AUTONOMOUS
- **Responsabilidades:**
  - Consome cada evento/artefato emitido no `emit_artifact` de qualquer agente e o grava no event store append-only com o schema canônico (`actor`, `action`, `inputs_hash`, `outputs`, `cost`, `latency`, `trace_id`, `ts`).
  - Gera e mantém o índice vetorial sobre todos os artefatos (ADRs, specs, runs, PRDs, contratos, comms, métricas, transcrições) para busca semântica "perguntar à empresa".
  - Constrói e atualiza o grafo de conhecimento ligando artefatos a atores, guildas, outcomes, gates e decisões — a espinha que conecta causa→efeito na empresa.
  - Enforce de C6: rejeita/sinaliza execuções que terminam sem artefato ("sem artefato, a execução não conta") e reconcilia outcomes↔traces, marcando desvio > 1% como FAIL.
  - Mantém latência e frescor do índice para que NL2SQL, dashboards do Operator Console e qualquer agente que faça `brain.query` leiam dados atualizados.
  - Aplica retenção, deduplicação e particionamento do event store, preservando imutabilidade do append-only e a rastreabilidade por `trace_id`.
- **Entradas:** stream de artefatos/eventos de todos os 150+ agentes; transcrições do notetaker (g11) e comms; traces de telemetria (LangSmith/Langfuse).
- **Saídas (artefatos):** evento indexado no event store; embedding/entrada vetorial; nós e arestas do grafo de conhecimento; relatório de cobertura de artefatos e reconciliação outcomes↔traces.
- **Ferramentas (C7):** `brain.write`, `brain.query`, `vector.upsert`, `graph.write`, `telemetry.read`, `LLMProvider` (embeddings via interface, não SDK).
- **Gatilhos:** evento de `emit_artifact` (streaming, reativo); cron de reconciliação outcomes↔traces; cron de reindexação/compactação.
- **Colabora com:** todos os 150 agentes (indexa o que produzem), g6-nl2sql e g6-dashboard-builder (servem leituras do índice), g11-meeting-notetaker (ingere transcrições), observability-guardian (compartilha checagem C6), hermes-learning-loop (lê snapshots indexados).
- **Cláusula de outcome (C2):** todo artefato emitido fica indexado e consultável (event store + vetor + grafo) com desvio outcomes↔traces ≤ 1%.
  - ✅ PRD recém-emitido aparece em busca semântica e ligado no grafo ao seu PRD-pai e ao gate que o aprovou, segundos após emissão.
  - ✅ Execução que terminou sem artefato é sinalizada como não-contável (enforce C6).
  - ✅ Reconciliação noturna fecha com desvio 0,3% (≤1%), passando o gate de C6.
  - ❌ Artefato gravado sem `trace_id`/`inputs_hash`, quebrando a rastreabilidade.
  - ❌ Índice vetorial defasado faz um agente responder com dado obsoleto.
  - ❌ Permite edição/sobrescrita de um evento já gravado (viola append-only).
  - 🚩 DELIVERED quando: `brain.artifact_indexed` registrado com entrada no event store + vetor + grafo e `schema_valid=true`.
- **Guardians:** observability-guardian (C6 telemetria/cobertura), artifact-architect (C5/C7 schema do artefato), security-privacy (PII no que é indexado), tenant-context-curator (C8 nos metadados).
- **KPIs:** cobertura de artefatos indexados (% de runs com artefato, alvo ~100%); desvio outcomes↔traces (≤1%); latência emissão→consultável; recall/precisão da busca semântica.

---

### mcp-gateway-comms — Gateway de Mensageria (MessagingProvider)
- **Missão:** abstrair todos os canais de comunicação atrás de uma interface única, para que nenhum agente conheça um provedor específico.
- **Ledger:** OP · **Tier:** L2 · **Modo-alvo:** ASSISTED
- **Responsabilidades:**
  - Expõe a interface C7 `MessagingProvider` (send/receive/subscribe) e roteia mensagens de saída e de entrada entre os agentes e os canais de comunicação (configurável quando o mercado for definido — quais canais).
  - Normaliza payloads heterogêneos dos provedores num formato canônico de mensagem, isolando os 150 agentes de qualquer diferença de SDK/contrato de fornecedor (C7 puro: trocar provedor não toca os agentes).
  - Aplica rate-limiting, retry com backoff, idempotência e fila de saída para garantir entrega confiável e evitar duplicidade ou flood em qualquer canal.
  - Filtra PII e segredos no conteúdo de saída (C1) e sanitiza entradas contra prompt injection antes de repassá-las a um agente (defesa em profundidade com g5).
  - Emite no Brain o artefato de cada mensagem enviada/recebida (audit-log C6) com `trace_id`, status de entrega e provedor usado, sem expor credenciais.
  - Mantém o mapeamento de credenciais/canais por configuração (C8), permitindo failover entre provedores sem mudança de código.
- **Entradas:** pedidos de envio de qualquer agente (ex.: notificações do Hermes, comms de Growth/CustOps quando existirem); mensagens de entrada dos canais; configuração de canais/credenciais.
- **Saídas (artefatos):** mensagem canônica entregue/recebida; status de entrega e tentativas; audit-log de comunicação no Brain; alerta de falha de canal/failover.
- **Ferramentas (C7):** `MessagingProvider` (interface abstrata sobre os canais), `brain.write` (audit-log), `secrets.read` (credenciais via cofre), `LLMProvider` (sanitização opcional).
- **Gatilhos:** pedido de envio de um agente (reativo); webhook/poll de mensagem entrante; alarme de canal indisponível (failover).
- **Colabora com:** hermes-learning-loop (envia notificações de PR/skill), root-supervisor (escalonamento ao founder), g7-lifecycle-crm e g9-messaging-concierge (canais de cliente; canal configurável quando o mercado for definido), g5-prompt-injection-guard e g5-secrets-scanner (defesa de entradas/saídas), brain-indexer (indexa o audit-log).
- **Cláusula de outcome (C2):** toda mensagem é entregue (ou falha de forma rastreável) pela interface única, sem PII/segredo vazado e com audit-log registrado.
  - ✅ Notificação do Hermes entregue ao DRI no canal configurado, com confirmação e audit-log no Brain.
  - ✅ Provedor primário cai e o gateway faz failover para o secundário sem que nenhum agente perceba (C7/C8).
  - ✅ Conteúdo com PII detectado e mascarado antes do envio externo.
  - ❌ Um agente importa o SDK de um provedor específico em vez de usar `MessagingProvider`.
  - ❌ Mesma mensagem enviada duas vezes por falta de idempotência.
  - ❌ Credencial de canal logada no audit-log em texto claro.
  - 🚩 DELIVERED quando: `comms.message_delivered` (ou `comms.message_failed`) registrado com `provider`, `trace_id`, `status` e checagem PII ok.
- **Guardians:** artifact-architect (C7 interface), security-privacy (PII/segredos C1), tenant-context-curator (C8 credenciais/canais por config), observability-guardian (C6 audit-log).
- **KPIs:** taxa de entrega (↑) e taxa de erro por canal (↓); p95 de latência de envio; incidentes de vazamento de PII/segredo (=0); tempo de failover entre provedores.

---

### mcp-gateway-payments — Gateway de Pagamentos (PaymentGateway)
- **Missão:** abstrair provedores de pagamento atrás de uma interface única, isolando a empresa de qualquer processador específico.
- **Ledger:** OP · **Tier:** L2 · **Modo-alvo:** ASSISTED
- **Responsabilidades:**
  - Expõe a interface C7 `PaymentGateway` (charge/refund/payout/status/webhook) sobre os provedores de pagamento (quais provedores e métodos: configurável quando o mercado for definido), respeitando a jurisdição Brasil (meios e tributos BR são jurisdição, não mercado).
  - Normaliza requisições e respostas de cobrança, reembolso e repasse para um contrato canônico, garantindo que Vendas/Finanças nunca acoplem a um SDK de processador (trocar provedor não toca os agentes).
  - Garante idempotência forte de transações financeiras (chave por operação), retry seguro e reconciliação de estado via webhooks, evitando cobrança/estorno duplicado.
  - Aplica e enforce os gates humanos onde exigido (ex.: reembolso acima de limite via `interrupt`, em coordenação com g9-refund-handler), nunca executando movimento financeiro autônomo fora de alçada em modo ASSISTED.
  - Emite audit-log financeiro imutável no Brain por transação (C6) com `trace_id`, provedor, valor, status e referência de outcome — sem armazenar dados sensíveis de cartão (PCI/LGPD).
  - Suporta o pricing em 3 camadas da empresa (assinatura + top-ups + outcome-based) expondo operações que Vendas/Finanças orquestram, e provê os dados de custo de transação para o cálculo de C3 (custo billable ≤ 25% do preço).
- **Entradas:** pedidos de cobrança/reembolso/repasse de agentes de Vendas/Finanças/CustOps; webhooks dos provedores; configuração de provedores/credenciais; limites de alçada.
- **Saídas (artefatos):** resultado de transação canônico (status, id, provedor); audit-log financeiro no Brain; evento de reconciliação; pedido de aprovação humana quando acima de alçada.
- **Ferramentas (C7):** `PaymentGateway` (interface abstrata sobre os processadores), `brain.write` (audit-log financeiro), `secrets.read` (credenciais), `interrupt` (gate de alçada).
- **Gatilhos:** pedido de transação de um agente (reativo); webhook de provedor (atualização de status); cron de reconciliação de pendentes.
- **Colabora com:** g8-billing-agent, g8-dunning-agent e g8-pricing-engine (orquestram cobranças), g9-refund-handler (reembolsos com gate), g10-reconciliation e g10-unit-economist (conciliação e C3), g5-fraud-detector (sinal de fraude antes de capturar), brain-indexer (indexa audit-log).
- **Cláusula de outcome (C2):** toda operação financeira é executada exatamente uma vez (idempotente), reconciliada por webhook e auditada, sem dado sensível armazenado e respeitando alçada.
  - ✅ Cobrança processada com chave de idempotência; retry de rede não gera segunda cobrança; audit-log no Brain.
  - ✅ Reembolso acima do limite pausa em `interrupt` e só executa após aprovação do DRI (alçada ASSISTED).
  - ✅ Webhook de "captura confirmada" reconcilia uma transação que estava pendente, sem intervenção humana.
  - ❌ Move dinheiro de forma autônoma acima da alçada sem gate.
  - ❌ Armazena dados de cartão (viola PCI/LGPD).
  - ❌ Vendas acopla diretamente ao SDK de um processador em vez de usar `PaymentGateway`.
  - 🚩 DELIVERED quando: `payment.transaction_settled` (ou `payment.refund_settled`) registrado com `idempotency_key`, `provider`, `status` e audit-log financeiro ok.
- **Guardians:** unit-economist-guardian (C3/custo de transação para billable), security-privacy (PCI/LGPD, sem dado sensível), artifact-architect (C7 interface), observability-guardian (C6 audit financeiro).
- **KPIs:** taxa de sucesso de transação (↑) e chargebacks/erros (↓); incidentes de cobrança/estorno duplicado (=0); tempo de reconciliação de pendentes; custo de transação por outcome (insumo de C3).

---

### mcp-gateway-external — Gateway de APIs Externas (Genérico, C7)
- **Missão:** prover um ponto único e governado de acesso a APIs de terceiros genéricas, isolando a frota de qualquer fornecedor específico.
- **Ledger:** OP · **Tier:** L2 · **Modo-alvo:** ASSISTED
- **Responsabilidades:**
  - Expõe interfaces C7 genéricas (ex.: `HttpProvider`, `ExternalAPIProvider`) sobre APIs de terceiros, com adaptadores plugáveis por configuração — quais APIs/integrações depende do mercado (configurável quando o mercado for definido).
  - Centraliza autenticação, rotação de credenciais e gestão de cota/quota por integração, mantendo segredos no cofre e fora do código e dos logs (C1/C8).
  - Aplica resiliência: rate-limiting por fornecedor, retry com backoff, circuit-breaker, timeout e cache de respostas idempotentes, protegendo a frota de instabilidade externa.
  - Normaliza respostas externas para contratos canônicos e valida/sanitiza payloads de entrada contra injection e dados maliciosos antes de devolvê-los a um agente.
  - Enforce de C7: é o único caminho permitido para tráfego externo de terceiros — qualquer agente que tente chamar uma API direto é bloqueado/sinalizado, garantindo que trocar de fornecedor não toque os 150 agentes.
  - Emite audit-log de cada chamada externa no Brain (C6) com fornecedor, endpoint, latência, custo, status e `trace_id`, alimentando o rateio de custo OP e a observabilidade.
- **Entradas:** pedidos de chamada externa de qualquer agente (ex.: enriquecimento de dados, lookups, integrações de negócio quando existirem); configuração de adaptadores/credenciais/quotas.
- **Saídas (artefatos):** resposta externa normalizada; audit-log de chamada no Brain; alerta de quota/falha/circuit-breaker aberto; métrica de custo por integração.
- **Ferramentas (C7):** `HttpProvider`/`ExternalAPIProvider` (interfaces abstratas), `brain.write` (audit-log), `secrets.read` (credenciais), `cache.read/write`.
- **Gatilhos:** pedido de chamada externa de um agente (reativo); cron de health-check/rotação de credenciais; alarme de quota próxima do limite.
- **Colabora com:** g3-integration-builder (constrói adaptadores plugáveis), g1-market-intel e g6-pipeline-builder (consomem dados externos), g5-secrets-scanner e g5-dependency-cve (segurança das integrações), g10-token-cost-accountant (rateio de custo OP de chamadas externas), brain-indexer (indexa audit-log).
- **Cláusula de outcome (C2):** toda chamada a terceiros passa pela interface única, resiliente e auditada, sem vazar segredo e sem agente acoplar a um fornecedor específico.
  - ✅ Lookup externo servido com cache e circuit-breaker, mantendo a frota estável durante instabilidade do fornecedor.
  - ✅ Novo fornecedor plugado por configuração (novo adaptador) sem alterar nenhum dos 150 agentes (C7/C8).
  - ✅ Credencial rotacionada automaticamente sem downtime nem segredo em log.
  - ❌ Um agente chama uma API de terceiro diretamente, furando o gateway.
  - ❌ Credencial de fornecedor exposta no audit-log.
  - ❌ Falha externa propaga e derruba uma execução por falta de timeout/circuit-breaker.
  - 🚩 DELIVERED quando: `external.call_completed` (ou `external.call_failed`) registrado com `provider`, `endpoint`, `latency`, `cost`, `trace_id` e segredo redigido.
- **Guardians:** artifact-architect (C7 interfaces/adaptadores), security-privacy (segredos/injection C1), tenant-context-curator (C8 config por integração), observability-guardian (C6 audit/custo).
- **KPIs:** taxa de sucesso por integração (↑) e erros/timeouts (↓); cache hit-rate; incidentes de vazamento de credencial (=0); custo OP de chamadas externas por outcome.
