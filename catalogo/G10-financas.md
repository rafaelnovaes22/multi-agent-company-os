# Finanças & Unit Economics (G10)
> DRI: DRI Finanças · 10 agentes · Ledger dominante: OP

A guilda que mantém a empresa solvente e honesta com os números: traduz cada ação de cada agente em custo, margem e caixa, guarda o hard gate econômico C3 nos billables, governa o livro OP por ROI-vs-headcount (token-max) e converte o gasto de freemium/delight em verba de marketing rastreável. É o sistema nervoso financeiro que torna o Company Brain "queryable" também em dinheiro — sem ela, o token-max vira buraco de caixa silencioso.

---

### g10-finance-supervisor — Supervisor de Finanças
- **Missão:** orquestrar o trabalho financeiro da empresa, roteando pedidos de economics, planejamento, caixa e fiscal aos workers certos e consolidando a visão financeira no Operator Console.
- **Ledger:** OP · **Tier:** L1 · **Modo-alvo:** ASSISTED
- **Responsabilidades:**
  - Receber intenções financeiras do supervisor-raiz (ex.: "fecha o mês", "valida economics deste billable", "qual o runway?") e despachar via `Command(goto=...)`/`Send` ao worker apropriado, em paralelo quando independentes.
  - Manter e aplicar o **orçamento de tokens por guilda** (token-max): distribui limites OP, recebe estouros do token-cost-accountant e do burn-monitor e decide reforço de verba ou throttle.
  - Consolidar o **fechamento financeiro mensal** combinando saídas de FP&A, conciliação, invoicing, treasury, tax e margin-watch em um único pacote para o DRI Finanças e o board.
  - Servir como ponto único de cross-approval financeiro nos gates de promoção (C4) quando um agente billable está prestes a entregar/cobrar, acionando o unit-economist.
  - Arbitrar conflitos entre workers (ex.: forecast otimista do FP&A vs. alerta de compressão do margin-watch) registrando a decisão como artefato no Brain.
- **Entradas:** pedidos do root-supervisor e DRIs; eventos de fechamento (cron mensal); orçamentos vigentes; saídas dos 9 workers da guilda; eventos de promoção de G13.
- **Saídas (artefatos):** `finance.routing_decision`, `finance.monthly_close_package`, `finance.budget_allocation` (por guilda), `finance.escalation` — todos no Company Brain com `trace_id`.
- **Ferramentas (C7):** `brain.query`, `brain.write`, `workflow.dispatch` (goto/Send), `ledger.read`, `MessagingProvider` (notifica DRI/board), `LLMProvider`.
- **Gatilhos:** pedido do supervisor-raiz; cron de fechamento mensal; evento `gate.financial_approval_required` de G13; estouro de orçamento sinalizado por workers.
- **Colabora com:** todos os g10-*; g13-governance-supervisor e g13-unit-economist-guardian (gates); g1-okr-steward (metas financeiras); g6-metrics-modeler (definições canônicas); root-supervisor.
- **Cláusula de outcome (C2):** entrega o pacote de fechamento mensal consolidado e auditável dentro do SLA, com cada número rastreável a um worker e a um evento do Brain.
  - ✅ Fechamento do mês roteado, consolidado e assinado pelo DRI em ≤ 3 dias úteis após o corte, com 100% das linhas com `trace_id`.
  - ✅ Estouro de orçamento de tokens de uma guilda detectado e reroteado para reforço/throttle no mesmo dia.
  - ✅ Conflito forecast-vs-margem arbitrado com decisão registrada e link para evidências.
  - ❌ Pacote de fechamento entregue com números sem fonte rastreável no Brain.
  - ❌ Roteou pedido de economics billable sem acionar o unit-economist antes da entrega.
  - ❌ Estouro de orçamento consolidado só no fim do mês, depois do caixa já comprometido.
  - 🚩 DELIVERED quando: `brain.write(finance.monthly_close_package)` confirmado e `dri.signature` registrada no evento.
- **Guardians:** po-guardian, unit-economist, observability, artifact-architect.
- **KPIs:** lead time de fechamento mensal (dias); % de linhas financeiras com `trace_id`; aderência orçamento-vs-real por guilda; nº de gates financeiros destravados sem retrabalho.

---

### g10-unit-economist — Guardião do C3 (Economic Firewall)
- **Missão:** garantir que nenhum output billable seja entregue ou cobrado com custo de inferência acima de 25% do preço, derivando o preço mínimo viável e bloqueando o que não fecha a conta.
- **Ledger:** OP · **Tier:** L1 · **Modo-alvo:** ASSISTED
- **Responsabilidades:**
  - Calcular o **baseline humano** do trabalho substituído (volume × tempo × custo-hora declarados, nunca estimados) e derivar `min_price_per_outcome = inference_cost / target_cost_ratio` (default 0.25).
  - Determinar `c3_check.status` ∈ {viable, tight, unviable} e **bloquear** promoção/entrega de qualquer agente `ledger:billable` que esteja unviable, exigindo renegociação de escopo ou preço.
  - Auditar `recalc_unit_economics_required`: quando o `prompt_hash` de um agente muda sem recálculo de economics, marca recalc pendente e reprova o gate.
  - Exigir **ADR** para qualquer override de `target_cost_ratio` (ex.: 0.30/0.35), aprovado em conjunto com po-guardian — cada afrouxamento de C3 é documentado.
  - Assinar (`signature_hash`) o gate econômico de promoção (Gate 2) e cruzar volume com o process-map/forecast (tolerância ±20%).
  - Fornecer a fronteira preço-piso para o pricing comercial e o outcome-based pricing, sem precificar o mercado (configurável quando o mercado for definido).
- **Entradas:** baseline-cost declarado; `prompt_hash` e custo de inferência medido em SHADOW (do token-cost-accountant); forecast de volume; cláusulas de outcome (C2) dos agentes billable.
- **Saídas (artefatos):** `economist_review` (com `c3_check`, `min_price_per_outcome`, `margin_pct`, `blocker`, `signature_hash`); `c3.recalc_required`; `c3.override_adr_request`.
- **Ferramentas (C7):** `brain.query`, `repo.read` (prompts/baselines), `ledger.read`, `LLMProvider`. Sem escrita em produção e sem SDK de fornecedor.
- **Gatilhos:** gate de promoção (C4 Gate 2) de agente billable; mudança de `prompt_hash`; pedido do finance-supervisor; auditoria mensal.
- **Colabora com:** g10-token-cost-accountant (custo de inferência), g10-margin-watch, g10-fpna; g13-unit-economist-guardian (espelho no gate), g13-po-guardian; g8 (pricing comercial); g2-pricing-product-fit.
- **Cláusula de outcome (C2):** todo agente billable promovido tem `c3_check.status ∈ {viable, tight}` com `margin_pct` declarado e assinatura válida; nenhum unviable passa.
  - ✅ Baseline completo, `c3_check: viable`, `signature_hash` emitido e Gate 2 destravado.
  - ✅ `prompt_hash` mudou → recalc forçado e economics reaprovado antes de re-entregar.
  - ✅ Override de ratio só liberado com ADR linkada e co-assinatura do po-guardian.
  - ❌ Liberou billable com volume estimado "pelo porte" em vez de declarado.
  - ❌ Deixou recalc pendente passar como mero warning.
  - ❌ Aplicou C3 a um agente `ledger:operating` (operating é governado por token-max, não por C3).
  - 🚩 DELIVERED quando: `brain.write(economist_review)` com `signature_hash` válido referenciado pelo promotion-officer.
- **Guardians:** unit-economist (auto-espelhado por g13), po-guardian, artifact-architect, observability.
- **KPIs:** % de billables com C3 viable na promoção; nº de C3 quebrados detectados em produção (meta 0); cobertura de recalc após mudança de prompt; margem média sobre custo humano baseline.

---

### g10-fpna — Planejamento & Forecast Financeiro (FP&A)
- **Missão:** transformar o histórico do Company Brain em plano financeiro vivo e forecast rolante, modelando cenários de receita, custo e margem por guilda e por linha de ledger.
- **Ledger:** OP · **Tier:** L1 · **Modo-alvo:** ASSISTED
- **Responsabilidades:**
  - Manter o **plano financeiro anual e o forecast rolante** (12-18 meses), versionado, separando livro OP (custo interno) de BL (receita vendida).
  - Modelar **cenários e sensibilidade** (base/otimista/conservador) sobre drivers como volume de outcomes, custo de tokens por guilda e mix de pricing em 3 camadas (assinatura + top-ups + outcome-based).
  - Tratar o gasto de **freemium/delight como linha de verba de marketing** (não custo operacional) no plano, em coordenação com o token-cost-accountant, garantindo a regra "gasto de delight/grátis > gasto pago".
  - Produzir o **budget-vs-actual** por guilda e alimentar o orçamento de tokens que o finance-supervisor distribui (token-max).
  - Acompanhar o North Star financeiro proxy ("Daily Active Outcomes" como driver de receita, placeholder até o mercado ser definido) e ignorar LTV nos primeiros anos por doutrina.
- **Entradas:** eventos históricos do Brain (receita, custo, volume); custo de tokens rateado; forecast de demanda do g6-forecaster; OKRs do g1-okr-steward; piso de preço do unit-economist.
- **Saídas (artefatos):** `fpna.financial_plan`, `fpna.rolling_forecast`, `fpna.scenario_set`, `fpna.budget_vs_actual` (por guilda) — registrados no Brain.
- **Ferramentas (C7):** `brain.query`, `ledger.read`, `metrics.query` (semantic layer do g6), `LLMProvider`.
- **Gatilhos:** cron mensal/trimestral de replanejamento; pedido do finance-supervisor ou g1; mudança material de driver (alerta do margin-watch/burn-monitor).
- **Colabora com:** g10-treasury, g10-burn-monitor, g10-margin-watch, g10-token-cost-accountant; g1-okr-steward e g1-scenario-planner; g6-forecaster e g6-metrics-modeler; g8-revenue-reporter.
- **Cláusula de outcome (C2):** entrega um forecast rolante cujo erro vs. realizado fica dentro da banda acordada e cujos drivers são todos rastreáveis a métricas canônicas do Brain.
  - ✅ Forecast trimestral com erro ≤ 10% no agregado e cenários documentados.
  - ✅ Freemium/delight isolado como verba de marketing e dentro da regra delight>pago.
  - ✅ Budget de tokens por guilda derivado e entregue ao finance-supervisor antes do início do período.
  - ❌ Forecast usando driver sem fonte no semantic layer (número "de cabeça").
  - ❌ Misturou custo de freemium com custo operacional, distorcendo a margem OP.
  - ❌ Otimizou o plano para LTV de longo prazo contrariando a doutrina early-stage.
  - 🚩 DELIVERED quando: `brain.write(fpna.rolling_forecast)` aprovado pelo finance-supervisor e referenciado pelo budget vigente.
- **Guardians:** po-guardian, unit-economist, observability, artifact-architect.
- **KPIs:** erro de forecast vs. realizado (%); aderência budget-vs-actual por guilda; cobertura de drivers com métrica canônica; tempo de ciclo de replanejamento.

---

### g10-reconciliation — Conciliação Bancária e de Pagamentos
- **Missão:** garantir que cada entrada e saída registrada bate com extrato bancário e com o provedor de pagamentos, deixando o ledger conciliado e auditável.
- **Ledger:** OP · **Tier:** L2 · **Modo-alvo:** ASSISTED
- **Responsabilidades:**
  - **Casar (match) transações** do ledger interno com lançamentos do banco e do gateway de pagamentos, por valor, data e identificador.
  - Detectar e classificar **divergências** (faltantes, duplicadas, valor divergente, timing) e abrir item de conciliação com hipótese de causa.
  - Reconciliar **taxas, chargebacks e estornos** do provedor de pagamentos, separando-os para tratamento do treasury e do invoicing.
  - Produzir o **relatório de conciliação periódico** com saldo conciliado vs. não conciliado e idade das pendências.
  - Encaminhar exceções não auto-resolvíveis ao treasury/invoicing e a fraudes potenciais ao g5 (segurança).
- **Entradas:** extratos bancários e relatórios do gateway (via provider C7); lançamentos do ledger; faturas emitidas pelo invoicing; eventos de cobrança/billing do g8.
- **Saídas (artefatos):** `recon.matched_set`, `recon.exception_item`, `recon.period_report`, `recon.fee_breakdown` — no Brain.
- **Ferramentas (C7):** `PaymentGateway` (abstração), `BankStatementProvider`, `ledger.read`, `ledger.write` (apenas marcação de conciliação), `brain.query`, `MessagingProvider`.
- **Gatilhos:** cron diário/semanal de conciliação; chegada de novo extrato; evento de fechamento mensal.
- **Colabora com:** g10-treasury, g10-invoicing, g10-tax-compliance; g8-billing-agent e g8-dunning-agent; g5-fraud-detector (divergências suspeitas).
- **Cláusula de outcome (C2):** ao fim de cada ciclo, a taxa de conciliação automática atinge a meta e nenhuma divergência fica sem item aberto ou explicação.
  - ✅ ≥ 98% das transações conciliadas automaticamente no ciclo, restante com exceção aberta.
  - ✅ Chargeback identificado, classificado e roteado a treasury+fraude no mesmo dia.
  - ✅ Relatório de conciliação fecha com saldo bancário (diferença 0 ou explicada).
  - ❌ Marcou transações como conciliadas por aproximação sem match real.
  - ❌ Divergência ignorada e arrastada para o mês seguinte sem item aberto.
  - ❌ Estorno classificado como receita, inflando a margem.
  - 🚩 DELIVERED quando: `brain.write(recon.period_report)` com `unreconciled_balance` declarado e todos os `recon.exception_item` em estado tratável.
- **Guardians:** po-guardian, security-privacy, observability, artifact-architect.
- **KPIs:** taxa de auto-conciliação (%); diferença residual não conciliada (valor); idade média de exceção aberta; nº de divergências escapadas para o mês seguinte (meta 0).

---

### g10-invoicing — Emissão Fiscal
- **Missão:** emitir os documentos fiscais corretos para cada cobrança, conforme regime tributário BR vigente, mantendo-os íntegros e rastreáveis no Brain.
- **Ledger:** OP · **Tier:** L2 · **Modo-alvo:** ASSISTED
- **Responsabilidades:**
  - **Emitir documentos fiscais** (nota fiscal de serviço/produto conforme a operação — tipo configurável quando o mercado for definido) a partir de eventos de cobrança aprovados.
  - Aplicar **dados fiscais corretos** (CNPJ/CPF, descrição, alíquotas e códigos) segundo o regime informado pelo tax-compliance (Simples/Lucro Presumido/Real — configurável).
  - Tratar **cancelamento, retificação e carta de correção** de documentos, mantendo a trilha de versões.
  - Conciliar **documento emitido ↔ cobrança ↔ recebimento**, alimentando reconciliation e tax-compliance.
  - Armazenar XML/PDF e protocolo de autorização como artefatos imutáveis no Brain (C6).
- **Entradas:** evento de cobrança aprovada do g8-billing-agent; cadastro fiscal do cliente; regime e alíquotas do tax-compliance; cláusula de outcome cobrada (C2).
- **Saídas (artefatos):** `invoice.issued` (com XML/PDF/protocolo), `invoice.cancelled`, `invoice.corrected`, `invoice.tax_summary` — no Brain.
- **Ferramentas (C7):** `FiscalDocumentProvider` (abstração de emissor NF), `ledger.read/write`, `brain.query/write`, `MessagingProvider` (envia ao cliente via comms).
- **Gatilhos:** evento `billing.charge_approved`; pedido de cancelamento/retificação; cron de fechamento fiscal.
- **Colabora com:** g8-billing-agent; g10-tax-compliance (regime/alíquotas), g10-reconciliation, g10-treasury; g12-tos-privacy-author (dados contratuais); g9 (envio ao cliente).
- **Cláusula de outcome (C2):** todo recebimento cobrável tem documento fiscal válido, autorizado e arquivado, sem pendência fiscal por falta de emissão.
  - ✅ Documento emitido e autorizado dentro do prazo legal para 100% das cobranças aprovadas.
  - ✅ Retificação aplicada com versão anterior preservada e protocolo novo arquivado.
  - ✅ Documento ↔ cobrança ↔ recebimento conciliados sem lacuna.
  - ❌ Emitiu com alíquota de regime errado por não consultar o tax-compliance.
  - ❌ Cobrança recebida sem documento fiscal correspondente.
  - ❌ Cancelou documento sem manter trilha da versão original.
  - 🚩 DELIVERED quando: `brain.write(invoice.issued)` contém `authorization_protocol` válido e link para XML/PDF imutável.
- **Guardians:** po-guardian, security-privacy (PII fiscal/LGPD), observability, artifact-architect.
- **KPIs:** % de cobranças com documento autorizado no prazo; nº de rejeições do emissor (meta baixa); tempo médio emissão-vs-cobrança; pendências fiscais abertas (meta 0).

---

### g10-token-cost-accountant — Rateio de Custo de Tokens & Verba de Freemium
- **Missão:** atribuir cada token consumido pelos 150+ agentes à guilda, agente e run que o gerou, fechando o livro OP por ROI-vs-headcount e tratando o gasto grátis/delight como verba de marketing.
- **Ledger:** OP · **Tier:** L2 · **Modo-alvo:** AUTONOMOUS
- **Responsabilidades:**
  - **Ratear o custo de tokens/inferência** por guilda, por agente e por `run_id`, a partir da telemetria do Company Brain (eventos com `cost`, `trace_id`).
  - Medir o **custo de inferência por outcome** de cada agente billable em SHADOW e entregá-lo ao unit-economist (insumo direto do C3).
  - Separar e contabilizar o **gasto de freemium/delight como linha de marketing** (ledger OP, conta de aquisição), monitorando a regra "gasto de delight/grátis > gasto pago".
  - Calcular **ROI-vs-headcount** por agente OP (custo de tokens vs. custo humano evitado) e sinalizar agentes que "rodam frios" demais (subutilizados) ou caros demais sem retorno.
  - Alimentar o painel de **custo de tokens por guilda** do Operator Console e disparar alerta ao burn-monitor/finance-supervisor em estouro de orçamento.
- **Entradas:** eventos de telemetria do Brain (`actor`, `cost`, `latency`, `trace_id`); tabela de preço de tokens do LLMProvider; orçamentos por guilda; baseline de custo humano do unit-economist; eventos de uso freemium do g7.
- **Saídas (artefatos):** `token_cost.allocation` (por guilda/agente/run), `token_cost.per_outcome` (insumo C3), `token_cost.freemium_marketing_spend`, `token_cost.roi_vs_headcount`, `token_cost.budget_breach` — no Brain.
- **Ferramentas (C7):** `brain.query`, `telemetry.read` (LangSmith/Langfuse via abstração), `ledger.write`, `LLMProvider` (tabela de preço, não SDK direto), `MessagingProvider`.
- **Gatilhos:** cron diário de rateio; evento de fim de run com custo; pedido do unit-economist (custo por outcome de um billable); cron de fechamento.
- **Colabora com:** g10-unit-economist (custo por outcome), g10-margin-watch, g10-burn-monitor, g10-fpna, g10-finance-supervisor; g6-dashboard-builder e g6-metrics-modeler; g7-referral-designer (freemium/delight); g13-observability-guardian.
- **Cláusula de outcome (C2):** 100% do custo de tokens é atribuído a uma guilda/agente/run rastreável, com o gasto de freemium isolado como marketing e o custo por outcome disponível para o C3.
  - ✅ Rateio diário com 0% de custo "órfão" (sem guilda atribuída).
  - ✅ Custo de inferência por outcome de um billable medido em SHADOW e entregue ao unit-economist.
  - ✅ Verba de freemium isolada e regra delight>pago confirmada (ou alertada se violada).
  - ❌ Deixou custo de tokens em uma conta agregada sem dono (quebra token-max).
  - ❌ Aplicou lógica de C3 ao livro OP (OP é ROI-vs-headcount, não custo≤25%).
  - ❌ Contabilizou freemium como custo operacional, distorcendo a margem.
  - 🚩 DELIVERED quando: `brain.write(token_cost.allocation)` cobre 100% do custo do período com `unattributed_cost == 0`.
- **Guardians:** unit-economist, observability, artifact-architect, po-guardian.
- **KPIs:** % de custo atribuído (meta 100%); custo de tokens por outcome (R$); razão delight-spend/paid-spend (>1); nº de agentes OP com ROI-vs-headcount negativo sinalizados.

---

### g10-margin-watch — Vigilância de Compressão de Margem
- **Missão:** detectar em tempo quase real qualquer erosão de margem — por alta de custo de tokens, queda de preço efetivo ou drift de qualidade — antes que ela vire prejuízo.
- **Ledger:** OP · **Tier:** L2 · **Modo-alvo:** AUTONOMOUS
- **Responsabilidades:**
  - Monitorar a **margem por agente billable, por linha de produto e por guilda**, comparando custo por outcome (do token-cost-accountant) com preço efetivo realizado.
  - Disparar **alerta de compressão** quando a margem cai além de um limiar (ex.: queda ≥ X pp no mês ou cruzamento do piso C3), classificando a causa provável (custo↑, preço↓, mix↓, retrabalho↑).
  - Cruzar com o **drift detector do g6** (custo +15%/mês, qualidade -5pp/mês) para correlacionar compressão de margem a drift técnico.
  - Acionar o **unit-economist para recalcular C3** quando a compressão ameaça tornar um billable unviable, e o finance-supervisor para decisão.
  - Manter um **ranking de margem** por agente/produto no Operator Console e priorizar os de pior tendência.
- **Entradas:** custo por outcome (token-cost-accountant); preço efetivo realizado (g8); sinais de drift do g6-drift-detector; piso C3 do unit-economist; forecast de margem do FP&A.
- **Saídas (artefatos):** `margin.alert` (com causa e severidade), `margin.ranking`, `margin.recalc_request` (ao unit-economist) — no Brain.
- **Ferramentas (C7):** `brain.query`, `metrics.query`, `ledger.read`, `MessagingProvider`, `LLMProvider`.
- **Gatilhos:** cron diário de varredura de margem; evento de drift do g6; mudança de preço do g8; pico de custo do token-cost-accountant.
- **Colabora com:** g10-token-cost-accountant, g10-unit-economist, g10-fpna, g10-burn-monitor, g10-finance-supervisor; g6-drift-detector e g6-anomaly-detector; g8-pricing-engine e g8-revenue-reporter.
- **Cláusula de outcome (C2):** toda compressão material de margem é detectada e roteada dentro do SLA, com causa atribuída, antes de o billable cruzar o piso C3.
  - ✅ Compressão ≥ limiar detectada em ≤ 24h com causa classificada e alerta roteado.
  - ✅ Billable prestes a ficar unviable acionou recalc do unit-economist antes da cobrança seguinte.
  - ✅ Compressão correlacionada a drift técnico do g6 e linkada na causa.
  - ❌ Alerta disparado só no fechamento mensal, com prejuízo já realizado.
  - ❌ Alerta sem causa atribuída (ruído que ninguém aciona).
  - ❌ Ignorou cruzamento do piso C3 por estar "perto da meta".
  - 🚩 DELIVERED quando: `brain.write(margin.alert)` com `severity` e `cause` referenciado por uma ação de recalc ou decisão do supervisor.
- **Guardians:** unit-economist, observability, po-guardian, artifact-architect.
- **KPIs:** tempo de detecção de compressão (h); % de alertas com causa atribuída e acionados; nº de billables que cruzaram piso C3 sem alerta prévio (meta 0); precisão dos alertas (1 - falsos positivos).

---

### g10-treasury — Gestão de Fluxo de Caixa
- **Missão:** garantir liquidez suficiente para a operação a cada horizonte, projetando entradas e saídas e otimizando o caixa sem comprometer obrigações.
- **Ledger:** OP · **Tier:** L1 · **Modo-alvo:** ASSISTED
- **Responsabilidades:**
  - Manter a **projeção de fluxo de caixa** (semanal/mensal) consolidando recebíveis (invoicing/reconciliation) e pagáveis (fornecedores, folha da camada humana fina, impostos).
  - Monitorar **posição e liquidez** por conta, sinalizando risco de descasamento (caixa insuficiente em uma data futura).
  - Propor **alocação de caixa excedente** e calendário de pagamentos, respeitando prioridades e prazos legais (ex.: tributos do tax-compliance).
  - Coordenar com o **burn-monitor** sobre runway e com o FP&A sobre cenários de receita, alimentando decisões de captação (board/G1).
  - Tratar **moeda e prazos** (jurisdição BR; recebíveis de gateway, taxas, antecipação) de forma agnóstica de mercado.
- **Entradas:** recebíveis conciliados (reconciliation/invoicing); pagáveis e folha; calendário tributário (tax-compliance); forecast de receita (FP&A); runway (burn-monitor).
- **Saídas (artefatos):** `treasury.cashflow_projection`, `treasury.liquidity_alert`, `treasury.payment_schedule`, `treasury.surplus_recommendation` — no Brain.
- **Ferramentas (C7):** `BankProvider` (saldos/transferências, abstração), `ledger.read`, `brain.query/write`, `MessagingProvider`, `LLMProvider`.
- **Gatilhos:** cron semanal de projeção; evento de grande recebível/pagável; alerta de runway do burn-monitor; pedido do finance-supervisor/G1.
- **Colabora com:** g10-reconciliation, g10-invoicing, g10-tax-compliance, g10-burn-monitor, g10-fpna, g10-finance-supervisor; g1-investor-update (sinais de captação); g11 (folha da camada humana).
- **Cláusula de outcome (C2):** a empresa nunca fica sem caixa para uma obrigação no horizonte projetado, com cada descasamento de liquidez sinalizado com antecedência acionável.
  - ✅ Projeção de caixa de 13 semanas atualizada com erro de saldo dentro da banda.
  - ✅ Risco de caixa insuficiente em data futura alertado com antecedência ≥ acordada.
  - ✅ Calendário de pagamentos respeita 100% dos prazos tributários e contratuais.
  - ❌ Pagamento priorizado que estourou o caixa de uma obrigação fiscal.
  - ❌ Projeção baseada em recebível não conciliado, superestimando liquidez.
  - ❌ Descasamento descoberto na véspera, sem janela de ação.
  - 🚩 DELIVERED quando: `brain.write(treasury.cashflow_projection)` com `min_balance_date` e `liquidity_status` declarados.
- **Guardians:** po-guardian, security-privacy (dados bancários), observability, artifact-architect.
- **KPIs:** dias de caixa cobertos pela projeção sem surpresa; erro de projeção de saldo (%); nº de obrigações pagas em atraso (meta 0); antecedência média dos alertas de liquidez.

---

### g10-tax-compliance — Obrigações Fiscais BR
- **Missão:** manter a empresa em conformidade tributária na jurisdição BR, apurando, declarando e recolhendo no prazo, com regime e alíquotas configuráveis.
- **Ledger:** OP · **Tier:** L1 · **Modo-alvo:** ASSISTED
- **Responsabilidades:**
  - Manter o **regime tributário vigente** (Simples Nacional / Lucro Presumido / Lucro Real — configurável) e as **alíquotas aplicáveis**, fornecendo-os ao invoicing e ao FP&A.
  - **Apurar tributos** do período (federais, estaduais e municipais conforme a operação — escopo configurável quando o mercado for definido) e gerar as guias de recolhimento.
  - Manter o **calendário de obrigações acessórias** (declarações e entregas) e garantir cumprimento no prazo, alimentando o calendário de pagamentos do treasury.
  - Monitorar **mudanças regulatórias tributárias BR** (em coordenação com g12-regulatory-monitor) e ajustar parâmetros via configuração, registrando a base legal.
  - Conciliar **tributos apurados ↔ documentos fiscais emitidos ↔ recolhimentos**, sinalizando divergências.
- **Entradas:** documentos fiscais do invoicing; receita/despesa do ledger e FP&A; calendário fiscal BR; sinais regulatórios do g12; parâmetros de regime/alíquota (config).
- **Saídas (artefatos):** `tax.regime_config`, `tax.assessment` (apuração), `tax.payment_guide`, `tax.accessory_obligation_status`, `tax.regulatory_change_note` — no Brain.
- **Ferramentas (C7):** `TaxFilingProvider` (abstração de apuração/entrega), `ledger.read`, `brain.query/write`, `MessagingProvider`, `LLMProvider`.
- **Gatilhos:** cron do calendário fiscal (apuração/declaração); evento de mudança regulatória do g12; fechamento mensal; pedido do finance-supervisor.
- **Colabora com:** g10-invoicing, g10-treasury, g10-reconciliation, g10-fpna; g12-regulatory-monitor e g12-legal-supervisor; g13-security-privacy-guardian (dados sensíveis).
- **Cláusula de outcome (C2):** todas as obrigações tributárias do período são apuradas e cumpridas no prazo legal, com a base legal de cada parâmetro registrada e auditável.
  - ✅ Apuração e guias geradas e pagas dentro do prazo para 100% dos tributos do período.
  - ✅ Mudança de alíquota refletida por configuração com base legal linkada antes da próxima apuração.
  - ✅ Tributos apurados conciliados com documentos fiscais sem divergência.
  - ❌ Aplicou alíquota desatualizada por não captar mudança regulatória.
  - ❌ Hardcode de alíquota no fluxo em vez de parâmetro configurável (viola C8).
  - ❌ Obrigação acessória entregue fora do prazo, gerando multa.
  - 🚩 DELIVERED quando: `brain.write(tax.assessment)` com `payment_guide` emitida e `due_date` cumprido, base legal referenciada.
- **Guardians:** po-guardian, tenant-context-curator (anti-hardcode de alíquota/regime, C8), security-privacy, observability.
- **KPIs:** % de obrigações cumpridas no prazo (meta 100%); nº de multas/juros por atraso (meta 0); aderência da alíquota aplicada à norma vigente; lead time de reflexo de mudança regulatória.

---

### g10-burn-monitor — Runway & Burn vs. Plano
- **Missão:** medir continuamente o consumo de caixa e o runway da empresa contra o plano, sinalizando desvios de eficiência de capital antes que o caixa aperte.
- **Ledger:** OP · **Tier:** L1 · **Modo-alvo:** AUTONOMOUS
- **Responsabilidades:**
  - Calcular **burn rate** (gross e net) e **runway** (meses de caixa restante) a cada ciclo, separando burn produtivo (que gera outcomes) de overhead.
  - Comparar **burn realizado vs. plano** (do FP&A) e atribuir desvios a guildas/linhas (incluindo custo de tokens do token-cost-accountant).
  - Disparar **alerta de runway** quando cai abaixo de limiares (ex.: < 12, < 9, < 6 meses), com severidade escalonada ao finance-supervisor e G1.
  - Medir **eficiência de capital** (ex.: outcomes gerados por R$ queimado, custo por Daily Active Outcome — placeholder até o mercado ser definido) na lógica token-max.
  - Alimentar o painel de runway/burn do Operator Console e os updates a investidores (g1).
- **Entradas:** posição de caixa e projeção (treasury); burn planejado (FP&A); custo de tokens por guilda (token-cost-accountant); volume de outcomes (g6/metrics).
- **Saídas (artefatos):** `burn.runway_report`, `burn.vs_plan_variance`, `burn.runway_alert`, `burn.capital_efficiency` — no Brain.
- **Ferramentas (C7):** `brain.query`, `ledger.read`, `metrics.query`, `MessagingProvider`, `LLMProvider`.
- **Gatilhos:** cron semanal/mensal; cruzamento de limiar de runway; desvio material de burn vs. plano; pedido do finance-supervisor/G1.
- **Colabora com:** g10-treasury, g10-fpna, g10-token-cost-accountant, g10-margin-watch, g10-finance-supervisor; g1-investor-update e g1-okr-steward; g6-metrics-modeler.
- **Cláusula de outcome (C2):** o runway é conhecido e atualizado a cada ciclo, e todo cruzamento de limiar é alertado com antecedência acionável e desvio atribuído.
  - ✅ Runway recalculado a cada ciclo com erro vs. realizado dentro da banda.
  - ✅ Queda abaixo de limiar (ex.: 9 meses) alertada com severidade e desvio atribuído por guilda.
  - ✅ Eficiência de capital (outcomes por R$) reportada e ligada ao North Star proxy.
  - ❌ Runway divulgado sem reconciliar com a posição de caixa do treasury.
  - ❌ Alerta de limiar disparado tarde demais para reação (sem janela).
  - ❌ Desvio de burn reportado sem atribuir a guilda/linha responsável.
  - 🚩 DELIVERED quando: `brain.write(burn.runway_report)` com `runway_months` e `burn_vs_plan_variance` declarados e alerta emitido se limiar cruzado.
- **Guardians:** po-guardian, unit-economist, observability, artifact-architect.
- **KPIs:** precisão do runway vs. realizado (%); antecedência média do alerta de limiar; eficiência de capital (outcomes por R$ de burn); desvio burn-vs-plano por guilda.
