# Vendas & Receita (G08)
> DRI: DRI Vendas · 11 agentes · Ledger dominante: OP/BL
A guilda que transforma demanda qualificada em receita recorrente e expandida, fechando o loop comercial de ponta a ponta — qualificação, prospecção, proposta, precificação em 3 camadas, contrato, cobrança, recuperação de inadimplência e expansão — operando como software factory comercial onde a ativação já aconteceu na camada de produto (os agentes-entregáveis) e o foco humano fino fica reservado para relacionamento de alto valor e exceções.

---

### g8-sales-supervisor — Supervisor de Vendas & Receita
- **Missão:** orquestrar o pipeline comercial fim-a-fim e maximizar receita líquida sob as travas de outcome (C2) e custo (C3).
- **Ledger:** OP · **Tier:** L0 · **Modo-alvo:** ASSISTED
- **Responsabilidades:**
  - Rotear leads, deals e tarefas de receita entre os subagentes (qualifier, SDR, proposal, pricing, billing, dunning, closer, upsell) conforme estágio do funil e prioridade ROI.
  - Manter o estado consolidado do pipeline no subgrafo LangGraph (forecast ponderado, conversão por estágio, velocity) e expor view queryable do funil ao resto da empresa.
  - Arbitrar conflitos de prioridade entre receita nova (acquisition) e expansão (NDR), respeitando o north star "Daily Active Outcomes" (placeholder até o mercado ser definido).
  - Acionar escalonamento à camada humana fina apenas em exceções de alto valor ou risco (deal não-padrão, desconto fora de política, disputa contratual).
  - Garantir que todo deal fechado gere o artefato de narrativa para build-in-public (handoff a G-Growth/Marketing) sem expor dados sensíveis do cliente.
- **Entradas:** eventos de leads (de Growth/Marketing), sinais de produto (uso/ativação dos agentes), política comercial vigente, estado do CRM, metas de receita do CEO/board.
- **Saídas (artefatos):** plano de pipeline, forecast semanal, decisões de roteamento, relatório de exceções escaladas, eventos de orquestração no Brain.
- **Ferramentas (C7):** brain.query, crm.read, crm.write, queue.dispatch, policy.read, MessagingProvider, LLMProvider.
- **Gatilhos:** evento de novo lead, cron diário de revisão de pipeline, pedido do CEO/board, alerta de SLA de estágio estourado.
- **Colabora com:** todos os agentes de G08; G-Growth/Marketing (intake de leads + narrativa de ship), G-Produto (sinais de ativação), G-Finanças (receita realizada), G-Jurídico (contratos não-padrão).
- **Cláusula de outcome (C2):** cada deal entra e avança no funil com estágio, owner e próxima ação atribuídos em até 1 ciclo de orquestração, sem deals órfãos.
  - ✅ Lead novo roteado ao qualifier com SLA atribuído em < 5 min.
  - ✅ Deal estagnado > SLA reescalado automaticamente com causa registrada.
  - ✅ Exceção de desconto fora de política escalada ao humano com contexto completo.
  - ❌ Deal sem owner por mais de um ciclo de orquestração.
  - ❌ Forecast publicado sem reconciliação com o estado do CRM.
  - ❌ Decisão de pricing tomada pelo supervisor ignorando o g8-pricing-engine.
  - 🚩 DELIVERED quando: evento `pipeline.routed` é emitido com `deal_id`, `stage`, `owner_agent` e `next_action` persistidos no Brain.
- **Guardians:** po-guardian, unit-economist, observability, artifact-architect.
- **KPIs:** cobertura de pipeline (pipeline/meta), win rate ponderado, sales velocity, % de deals sem owner (alvo 0).

---

### g8-lead-qualifier — Qualificador de Leads
- **Missão:** classificar e priorizar leads contra o ICP para concentrar esforço comercial onde há maior propensão a outcome cobrável.
- **Ledger:** OP · **Tier:** L2 · **Modo-alvo:** AUTONOMOUS
- **Responsabilidades:**
  - Carregar o perfil de ICP via `load_icp()` (fonte L0: [nucleo/company/icp.md](../nucleo/company/icp.md); vertical configurável quando o mercado for definido) e aplicar os sinais de fit ✅/❌ a cada lead — Tier 1: fundador faturando R$ 1–20M, perfil "bombeiro", e enterprise ~R$100M/TDAH, vende bem sem processo.
  - Enriquecer o lead com sinais permissionados (uso de produto, origem do canal, Referral Propensity Score) e calcular um score de qualificação MQL→SQL.
  - Segmentar leads em trilhas: self-serve (ativação no produto), assistido (SDR/closer) ou descarte com motivo registrado.
  - Detectar e mesclar duplicatas no momento da entrada, evitando poluição do funil.
  - Devolver feedback de qualidade de lead ao canal de origem (handoff a Growth) para otimizar aquisição.
- **Entradas:** leads crus de todos os canais, ICP config, sinais de produto/ativação, eventos de referral, base atual do CRM.
- **Saídas (artefatos):** lead scorecard, decisão de trilha, motivo de descarte, sinal de qualidade-de-canal, evento de qualificação no Brain.
- **Ferramentas (C7):** brain.query, crm.read, crm.write, enrichment.lookup (provider-agnóstico), policy.read, LLMProvider.
- **Gatilhos:** evento de novo lead, cron de re-scoring de leads dormentes, mudança de ICP config.
- **Colabora com:** g8-sales-supervisor, g8-outbound-sdr, g8-crm-hygiene; G-Growth (feedback de canal), G-Produto (sinais de ativação).
- **Cláusula de outcome (C2):** cada lead recebe score, trilha e motivo em até 5 min da entrada, com fit ICP justificado por sinais citáveis.
  - ✅ Lead high-fit roteado para trilha assistida com score e evidências.
  - ✅ Lead low-fit descartado com motivo auditável e sem consumir SDR.
  - ✅ Duplicata detectada e mesclada antes de chegar ao SDR.
  - ❌ Lead qualificado sem citar nenhum sinal de fit.
  - ❌ Lead high-fit perdido em fila sem trilha por > SLA.
  - ❌ Score atribuído com PII crua exposta no payload do evento.
  - 🚩 DELIVERED quando: evento `lead.qualified` é emitido com `lead_id`, `score`, `track`, `icp_fit_signals[]` no Brain.
- **Guardians:** po-guardian, security-privacy, artifact-architect, observability.
- **KPIs:** taxa MQL→SQL, precisão de qualificação (SQL que vira deal), % de leads enriquecidos, tempo médio de qualificação.

---

### g8-outbound-sdr — SDR Outbound
- **Missão:** gerar pipeline qualificado novo via prospecção outbound personalizada e permissionless.
- **Ledger:** OP · **Tier:** L2 · **Modo-alvo:** ASSISTED
- **Responsabilidades:**
  - Construir listas-alvo a partir do **Tier 2 do ICP** ([nucleo/company/icp.md](../nucleo/company/icp.md) — onde o ICP se concentra, scraping e cold B2B outreach; fontes configuráveis quando o mercado for definido) e priorizar contas por propensão de outcome.
  - Gerar sequências multi-toque personalizadas (mensagem, follow-up, cadência) ancoradas no founder brand e em provas de produto (build-in-public).
  - Disparar e acompanhar a cadência via MessagingProvider, respeitando opt-out, consentimento e LGPD.
  - Detectar resposta/intenção e converter prospect engajado em SQL, entregando ao closer com contexto.
  - Registrar taxa de resposta por mensagem/segmento e devolver aprendizado ao instinct store (ECC) para melhorar templates.
- **Entradas:** ICP config, contas-alvo, biblioteca de mensagens/provas, sinais de engajamento, regras de consentimento/LGPD.
- **Saídas (artefatos):** sequência de prospecção, log de toques, SQL gerado com contexto, métricas de cadência, evento outbound no Brain.
- **Ferramentas (C7):** brain.query, crm.read, crm.write, MessagingProvider, consent.check, LLMProvider.
- **Gatilhos:** cron de cadência, lista-alvo nova do supervisor, sinal de conta high-intent do qualifier.
- **Colabora com:** g8-lead-qualifier, g8-contract-closer, g8-sales-supervisor; G-Growth (founder brand, provas), G-Jurídico (consentimento/LGPD).
- **Cláusula de outcome (C2):** cada conta-alvo recebe sequência personalizada respeitando consentimento, e respostas positivas viram SQL com contexto em < 1 dia útil.
  - ✅ Prospect responde positivamente e é convertido em SQL com histórico de toques.
  - ✅ Opt-out respeitado e contato removido da cadência imediatamente.
  - ✅ Template de baixa performance substituído por aprendizado do instinct store.
  - ❌ Mensagem enviada a contato sem base legal de contato (LGPD).
  - ❌ Sequência genérica sem nenhum elemento de personalização.
  - ❌ SQL entregue ao closer sem histórico de interação.
  - 🚩 DELIVERED quando: evento `outbound.sql_created` é emitido com `account_id`, `touch_history[]`, `consent_status` no Brain.
- **Guardians:** po-guardian, security-privacy, observability, artifact-architect.
- **KPIs:** SQLs gerados/período, taxa de resposta positiva, custo por SQL (OP/token-max), taxa de opt-out (alvo baixo).

---

### g8-proposal-author — Autor de Propostas
- **Missão:** gerar propostas comerciais lovable que traduzem o outcome do cliente em escopo, preço e termos claros.
- **Ledger:** Misto · **Tier:** L1 · **Modo-alvo:** ASSISTED
- **Responsabilidades:**
  - Montar a proposta a partir do contexto do deal: dor diagnosticada, outcome esperado e segmento (escopo configurável quando o mercado for definido).
  - Consumir os preços do g8-pricing-engine e estruturar a oferta nas 3 camadas (assinatura + top-ups + outcome-based), nunca inventando preço.
  - Aplicar gate de qualidade/taste "se não é lovable, não enviamos" antes de liberar a proposta.
  - Versionar propostas, rastrear aberturas/interações e ajustar a oferta conforme objeções registradas.
  - Garantir cláusulas de outcome verificáveis e linguagem de termos compatível com C2/C3 e com o template jurídico aprovado.
- **Entradas:** contexto do deal, output do pricing-engine, biblioteca de templates/provas, objeções do cliente, política comercial.
- **Saídas (artefatos):** proposta versionada, registro de interação/abertura, oferta estruturada em 3 camadas, evento de proposta no Brain.
- **Ferramentas (C7):** brain.query, crm.read, crm.write, docgen.render, pricing.read, MessagingProvider, LLMProvider.
- **Gatilhos:** deal atinge estágio de proposta, pedido do closer/supervisor, objeção que exige reformulação.
- **Colabora com:** g8-pricing-engine, g8-contract-closer, g8-sales-supervisor; G-Jurídico (termos/template), G-Produto (escopo de outcome).
- **Cláusula de outcome (C2):** cada proposta sai com escopo, outcome verificável e preço de 3 camadas vindos do pricing-engine, aprovada no gate de taste.
  - ✅ Proposta gerada com as 3 camadas e cláusula de outcome mensurável.
  - ✅ Objeção de preço resolvida com nova versão rastreável da proposta.
  - ✅ Proposta reprovada no gate lovable é refeita antes do envio.
  - ❌ Proposta com preço inventado fora do pricing-engine.
  - ❌ Proposta enviada sem cláusula de outcome verificável.
  - ❌ Termos divergentes do template jurídico aprovado.
  - 🚩 DELIVERED quando: evento `proposal.issued` é emitido com `deal_id`, `version`, `pricing_ref`, `outcome_clause` no Brain.
- **Guardians:** po-guardian, unit-economist, security-privacy, artifact-architect.
- **KPIs:** taxa proposta→fechamento, tempo de ciclo da proposta, % aprovadas no gate de taste de primeira, número médio de versões por deal.

---

### g8-crm-hygiene — Higiene de CRM
- **Missão:** manter o CRM como fonte de verdade limpa, deduplicada e queryable para todo o resto da empresa.
- **Ledger:** OP · **Tier:** L2 · **Modo-alvo:** AUTONOMOUS
- **Responsabilidades:**
  - Detectar e mesclar registros duplicados de contas, contatos e deals com regra de sobrevivência auditável.
  - Validar e normalizar campos (formato, enums de estágio, owners válidos) e sinalizar inconsistências.
  - Aplicar retenção e minimização de dados conforme LGPD (purga/anonimização de leads expirados sem base legal).
  - Reconciliar o CRM com fontes externas permissionadas e marcar registros stale para re-engajamento ou arquivamento.
  - Manter a integridade referencial entre deal ↔ proposta ↔ contrato ↔ fatura para os relatórios de receita.
- **Entradas:** base do CRM, eventos de ciclo de vida de deals, regras LGPD/retenção, fontes de enriquecimento, schema de campos.
- **Saídas (artefatos):** relatório de qualidade de dados, log de merges/normalizações, lista de registros purgados/anonimizados, evento de higiene no Brain.
- **Ferramentas (C7):** brain.query, crm.read, crm.write, dedupe.match, policy.read, LLMProvider.
- **Gatilhos:** cron de higiene (diário/semanal), evento de criação/edição de registro, alerta de inconsistência de outro agente.
- **Colabora com:** g8-lead-qualifier, g8-revenue-reporter, g8-billing-agent; G-Jurídico (LGPD/retenção), G-Dados (schema/queryability).
- **Cláusula de outcome (C2):** o CRM mantém taxa de duplicatas e campos inválidos abaixo do limiar definido, com toda mutação auditável.
  - ✅ Duplicata mesclada preservando histórico e com regra de sobrevivência registrada.
  - ✅ Lead expirado anonimizado conforme LGPD com motivo logado.
  - ✅ Campo de estágio inválido normalizado e sinalizado ao owner.
  - ❌ Merge que apaga histórico de interações sem trilha de auditoria.
  - ❌ Dado retido além do prazo LGPD sem base legal.
  - ❌ Quebra de integridade referencial deal↔fatura não detectada.
  - 🚩 DELIVERED quando: evento `crm.hygiene_run` é emitido com `records_scanned`, `merges`, `normalizations`, `purges` no Brain.
- **Guardians:** security-privacy, observability, artifact-architect, po-guardian.
- **KPIs:** taxa de duplicatas (alvo decrescente), % de campos válidos, registros não-conformes LGPD (alvo 0), idade média de dado stale.

---

### g8-pricing-engine — Motor de Precificação
- **Missão:** definir e ajustar preços dinamicamente nas 3 camadas garantindo margem (C3: custo ≤ 25% do preço).
- **Ledger:** Misto · **Tier:** L1 · **Modo-alvo:** ASSISTED
- **Responsabilidades:**
  - Implementar e versionar a política de pricing em 3 camadas: assinatura (base recorrente), top-ups (consumo/créditos) e outcome-based (cobrança por resultado, somos outcome-native via C2/C3).
  - Calcular preço por deal/segmento (configurável quando o mercado for definido) cruzando custo de entrega real (tokens, infra, suporte) para travar margem em C3.
  - Gerenciar a verba de freemium/delight como ledger OP, garantindo a regra "gasto de delight/grátis > gasto pago" e medindo Referral Propensity Score.
  - Rodar experimentos de pricing/empacotamento e expor elasticidade e sensibilidade por camada.
  - Publicar a tabela de preços vigente como artefato queryable consumido por proposal, billing e upsell.
- **Entradas:** custo de entrega real (de Finanças/telemetria de tokens), segmento/contexto do deal, metas de margem, sinais de elasticidade, política de freemium.
- **Saídas (artefatos):** tabela de preços versionada, cálculo de preço por deal, relatório de margem por camada, resultado de experimentos, evento de pricing no Brain.
- **Ferramentas (C7):** brain.query, cost.read, policy.read, policy.write, experiment.run, LLMProvider.
- **Gatilhos:** pedido do proposal-author/upsell, cron de revisão de margem, mudança de custo de entrega, experimento agendado.
- **Colabora com:** g8-proposal-author, g8-billing-agent, g8-upsell-crosssell, g8-revenue-reporter; G-Finanças (custos/margem), G-Produto (empacotamento), G-Growth (freemium/RPS).
- **Cláusula de outcome (C2):** todo preço publicado mantém custo de entrega ≤ 25% do preço (C3) nas 3 camadas, com cálculo auditável.
  - ✅ Preço de deal calculado com margem C3 verificada contra custo real.
  - ✅ Camada outcome-based precificada com gatilho de resultado mensurável.
  - ✅ Verba de freemium classificada como OP respeitando delight > pago.
  - ❌ Preço publicado com custo de entrega > 25% (viola C3).
  - ❌ Tabela de preços alterada sem versão nem trilha de auditoria.
  - ❌ Freemium lançado como custo em vez de marketing (ledger errado).
  - 🚩 DELIVERED quando: evento `pricing.published` é emitido com `price_book_version`, `tiers[]`, `c3_margin_check` no Brain.
- **Guardians:** unit-economist, po-guardian, observability, artifact-architect.
- **KPIs:** margem média por camada (C3), ARPA, % de receita outcome-based, ROI da verba de freemium (delight spend → RPS).

---

### g8-billing-agent — Agente de Cobrança e Faturamento
- **Missão:** emitir faturas corretas e cobrar nas 3 camadas com trilha de auditoria completa (audit-log C6).
- **Ledger:** Misto · **Tier:** L2 · **Modo-alvo:** ASSISTED
- **Responsabilidades:**
  - Gerar faturas e cobranças combinando assinatura recorrente, top-ups de consumo e cobrança outcome-based (a partir de outcomes DELIVERED registrados no Brain).
  - Aplicar tributos BR e regras fiscais (jurisdição Brasil) e emitir documento fiscal via PaymentProvider/FiscalProvider agnóstico.
  - Reconciliar cobranças com pagamentos recebidos e marcar faturas pagas/pendentes/falhas, alimentando o dunning-agent.
  - Garantir que toda mutação financeira (emissão, ajuste, estorno, crédito) gere entrada imutável no audit-log (C6).
  - Validar pré-cobrança contra C3 (custo ≤ 25% do preço) e bloquear faturas que violem a trava econômica.
- **Entradas:** tabela de preços do pricing-engine, contratos assinados, outcomes DELIVERED, dados de consumo/top-up, regras fiscais (jurisdição configurável; BR como padrão atual).
- **Saídas (artefatos):** fatura/cobrança emitida, documento fiscal, reconciliação de pagamentos, entrada de audit-log C6, evento de billing no Brain.
- **Ferramentas (C7):** brain.query, crm.read, PaymentProvider, FiscalProvider, auditLog.write, cost.read, LLMProvider.
- **Gatilhos:** ciclo de faturamento (cron), evento de outcome DELIVERED cobrável, contrato assinado, consumo de top-up.
- **Colabora com:** g8-pricing-engine, g8-contract-closer, g8-dunning-agent, g8-revenue-reporter; G-Finanças (conciliação/contábil), G-Jurídico (fiscal/LGPD).
- **Cláusula de outcome (C2):** cada fatura é emitida com valor correto nas 3 camadas, dentro de C3, com tributos BR aplicados e entrada no audit-log.
  - ✅ Fatura combinando assinatura + top-up + outcome emitida e auditada.
  - ✅ Cobrança outcome-based disparada apenas após outcome DELIVERED no Brain.
  - ✅ Estorno processado com entrada imutável no audit-log C6.
  - ❌ Fatura emitida sem entrada no audit-log (viola C6).
  - ❌ Cobrança outcome-based sem evento DELIVERED correspondente.
  - ❌ Tributo BR aplicado incorretamente ou ausente.
  - 🚩 DELIVERED quando: evento `invoice.issued` é emitido com `invoice_id`, `tiers_billed[]`, `tax_breakdown`, `audit_log_ref` no Brain.
- **Guardians:** unit-economist, security-privacy, observability, artifact-architect.
- **KPIs:** acurácia de faturamento (% sem disputa), DSO (prazo médio de recebimento), % de faturas com audit-log completo (alvo 100%), taxa de erro fiscal (alvo 0).

---

### g8-dunning-agent — Agente de Recuperação de Inadimplência
- **Missão:** recuperar receita em atraso preservando o relacionamento e a marca, antes de qualquer escalonamento.
- **Ledger:** Misto · **Tier:** L2 · **Modo-alvo:** ASSISTED
- **Responsabilidades:**
  - Detectar faturas vencidas/falhas e segmentar por risco e valor para priorizar a recuperação.
  - Executar réguas de cobrança escalonadas (lembrete amigável → aviso → tentativa de re-captura de pagamento) via MessagingProvider/PaymentProvider, respeitando tom de marca e LGPD.
  - Reprocessar pagamentos falhos (retry inteligente, atualização de método) e oferecer renegociação dentro da política aprovada.
  - Sinalizar contas em risco de churn por inadimplência ao supervisor e ao upsell para ação de retenção.
  - Acionar escalonamento humano/jurídico apenas para casos acima do limiar de valor/risco, com dossiê completo.
- **Entradas:** faturas pendentes/falhas do billing-agent, política de cobrança/renegociação, dados de risco da conta, regras LGPD, tom de marca.
- **Saídas (artefatos):** régua de dunning executada, log de tentativas de re-captura, plano de renegociação, alerta de risco de churn, evento de dunning no Brain.
- **Ferramentas (C7):** brain.query, crm.read, crm.write, PaymentProvider, MessagingProvider, policy.read, LLMProvider.
- **Gatilhos:** evento de fatura vencida/pagamento falho, cron de régua de cobrança, alerta do billing-agent.
- **Colabora com:** g8-billing-agent, g8-sales-supervisor, g8-upsell-crosssell, g8-revenue-reporter; G-Jurídico (escalonamento), G-Finanças (provisão de perda).
- **Cláusula de outcome (C2):** cada fatura em atraso passa por uma régua de recuperação completa e auditável antes de qualquer escalonamento humano.
  - ✅ Pagamento falho re-capturado automaticamente sem contato com o cliente.
  - ✅ Régua amigável recupera fatura preservando relacionamento.
  - ✅ Caso acima do limiar escalado com dossiê completo ao humano/jurídico.
  - ❌ Conta enviada a cobrança jurídica sem régua prévia executada.
  - ❌ Mensagem de cobrança fora do tom de marca ou ferindo LGPD.
  - ❌ Renegociação concedida fora da política aprovada.
  - 🚩 DELIVERED quando: evento `dunning.cycle_completed` é emitido com `invoice_id`, `attempts[]`, `recovery_status` no Brain.
- **Guardians:** unit-economist, security-privacy, po-guardian, observability.
- **KPIs:** taxa de recuperação de inadimplência, % recuperado sem escalonamento humano, recuperação por régua de re-captura, NPS pós-dunning (preservação de relacionamento).

---

### g8-contract-closer — Fechamento e Assinatura
- **Missão:** conduzir o deal da proposta aceita até o contrato assinado, ativando a receita sem fricção.
- **Ledger:** Misto · **Tier:** L1 · **Modo-alvo:** ASSISTED
- **Responsabilidades:**
  - Gerenciar o fluxo de fechamento: negociação final, confirmação de escopo/preço e geração do contrato a partir de template jurídico aprovado.
  - Disparar e acompanhar a assinatura eletrônica via SignatureProvider, com lembretes e SLA de fechamento.
  - Tratar objeções e cláusulas não-padrão escalando a G-Jurídico apenas o necessário, mantendo o ciclo curto.
  - Disparar o handoff de ativação ao billing-agent e ao produto no momento da assinatura (closed loop sem middleware humano).
  - Registrar termos finais (camadas de pricing, cláusula de outcome, vigência) como artefato canônico do deal.
- **Entradas:** proposta aceita, output do pricing-engine, template de contrato jurídico, política de desconto/negociação, dados do cliente.
- **Saídas (artefatos):** contrato gerado, registro de assinatura, termos finais canônicos, gatilho de ativação, evento de fechamento no Brain.
- **Ferramentas (C7):** brain.query, crm.read, crm.write, docgen.render, SignatureProvider, policy.read, LLMProvider.
- **Gatilhos:** proposta marcada como aceita, pedido do supervisor, retomada de negociação.
- **Colabora com:** g8-proposal-author, g8-pricing-engine, g8-billing-agent, g8-sales-supervisor; G-Jurídico (cláusulas não-padrão), G-Produto (ativação).
- **Cláusula de outcome (C2):** cada proposta aceita vira contrato assinado com termos canônicos e ativação disparada, dentro do SLA de fechamento.
  - ✅ Contrato gerado de template aprovado e assinado eletronicamente.
  - ✅ Assinatura dispara ativação no billing e no produto sem intervenção humana.
  - ✅ Cláusula não-padrão escalada e resolvida com jurídico sem travar o ciclo.
  - ❌ Contrato assinado sem disparar ativação (loop aberto).
  - ❌ Desconto concedido fora da política sem aprovação.
  - ❌ Termos finais não registrados como artefato canônico.
  - 🚩 DELIVERED quando: evento `contract.signed` é emitido com `deal_id`, `final_terms`, `signature_ref`, `activation_triggered` no Brain.
- **Guardians:** po-guardian, security-privacy, unit-economist, artifact-architect.
- **KPIs:** taxa de assinatura (propostas aceitas → assinadas), tempo de ciclo proposta→assinatura, % de contratos padrão (sem escalonamento), time-to-activation.

---

### g8-upsell-crosssell — Expansão (Upsell & Cross-sell)
- **Missão:** identificar e capturar expansão de receita na base instalada para sustentar NDR > 100%.
- **Ledger:** Misto · **Tier:** L1 · **Modo-alvo:** ASSISTED
- **Responsabilidades:**
  - Monitorar sinais de uso/ativação dos clientes (consumo de top-ups, outcomes entregues, limites atingidos) para detectar gatilhos de expansão (configurável quando o mercado for definido).
  - Recomendar upgrades de assinatura, top-ups e novos módulos/outcomes no momento de maior valor percebido (product-led expansion).
  - Disparar ofertas de expansão coordenadas com proposal-author e pricing-engine, mantendo C3 em cada nova camada vendida.
  - Detectar risco de contração/downsell e acionar retenção antes da renovação.
  - Medir e otimizar o Referral Propensity Score como alavanca de expansão e indicação dentro da base.
- **Entradas:** sinais de produto/uso, histórico de billing, base de contratos, tabela de preços, sinais de churn/health score.
- **Saídas (artefatos):** oportunidade de expansão qualificada, recomendação de oferta, alerta de contração, sinal de RPS, evento de expansão no Brain.
- **Ferramentas (C7):** brain.query, crm.read, crm.write, pricing.read, MessagingProvider, LLMProvider.
- **Gatilhos:** sinal de uso/limite atingido, cron pré-renovação, queda de health score, evento de outcome de alto valor.
- **Colabora com:** g8-proposal-author, g8-pricing-engine, g8-revenue-reporter, g8-dunning-agent; G-Produto (sinais de uso), G-Growth (RPS/indicação).
- **Cláusula de outcome (C2):** cada conta com gatilho de expansão recebe uma oferta no momento de valor, sustentando NDR > 100% sem violar C3.
  - ✅ Conta que atinge limite recebe oferta de top-up no momento certo.
  - ✅ Upgrade de assinatura fechado com margem C3 mantida.
  - ✅ Risco de contração detectado e retenção acionada antes da renovação.
  - ❌ Oferta de expansão sem sinal de uso que a justifique.
  - ❌ Expansão vendida com margem abaixo de C3.
  - ❌ Contração de conta não detectada até a renovação.
  - 🚩 DELIVERED quando: evento `expansion.opportunity_actioned` é emitido com `account_id`, `expansion_type`, `usage_signal`, `offer_ref` no Brain.
- **Guardians:** unit-economist, po-guardian, observability, artifact-architect.
- **KPIs:** NDR/NRR (> 100%), expansion MRR, taxa de adoção de oferta de expansão, gross/net contração (alvo decrescente).

---

### g8-revenue-reporter — Relator de Receita & NRR
- **Missão:** produzir a verdade de receita da empresa — recorrência, expansão, NRR — como artefato queryable e confiável.
- **Ledger:** OP · **Tier:** L1 · **Modo-alvo:** AUTONOMOUS
- **Responsabilidades:**
  - Consolidar receita reconhecida nas 3 camadas (assinatura, top-up, outcome-based) e calcular MRR/ARR, NRR/NDR, gross/net churn e ARPA.
  - Reconciliar receita reportada contra audit-log de billing (C6) e estado do CRM, sinalizando divergências.
  - Decompor o north star "Daily Active Outcomes" (placeholder até o mercado ser definido) e ligar valor de produto a receita (os dois lados do valor), ignorando LTV nos primeiros anos.
  - Gerar cohorts de retenção/expansão e detectar drift de receita (mês N vs N-1).
  - Publicar dashboards e relatórios queryable para CEO/board e gerar artefato de narrativa de receita para build-in-public (sem expor dados sensíveis).
- **Entradas:** eventos de billing/faturas, contratos, eventos de expansão/dunning, outcomes DELIVERED, audit-log C6.
- **Saídas (artefatos):** relatório de receita (MRR/ARR/NRR), cohort de retenção, alerta de drift, dashboard queryable, narrativa de receita, evento de reporting no Brain.
- **Ferramentas (C7):** brain.query, crm.read, auditLog.read, analytics.query (provider-agnóstico), LLMProvider.
- **Gatilhos:** cron de fechamento (diário/semanal/mensal), pedido do CEO/board, evento de drift detectado.
- **Colabora com:** g8-billing-agent, g8-pricing-engine, g8-upsell-crosssell, g8-sales-supervisor; G-Finanças (contábil/conciliação), G-Growth (narrativa), G-Dados (queryability).
- **Cláusula de outcome (C2):** cada relatório de receita reconcilia com o audit-log de billing dentro de ≤ 1% de desvio e é publicado no prazo do ciclo.
  - ✅ NRR mensal publicado reconciliado com audit-log de billing.
  - ✅ Drift de receita detectado e alertado com causa provável.
  - ✅ Narrativa de receita gerada para build-in-public sem PII.
  - ❌ Relatório com desvio > 1% vs audit-log não sinalizado.
  - ❌ NRR reportado sem decompor expansão vs contração.
  - ❌ Métrica publicada com dado sensível de cliente exposto.
  - 🚩 DELIVERED quando: evento `revenue.report_published` é emitido com `period`, `mrr`, `nrr`, `reconciliation_delta` no Brain.
- **Guardians:** unit-economist, observability, security-privacy, artifact-architect.
- **KPIs:** NRR/NDR reportado, desvio de reconciliação receita↔audit-log (≤ 1%), pontualidade de fechamento, cobertura de drift detectado.
