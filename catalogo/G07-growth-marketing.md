# Growth & Marketing (G07)
> DRI: DRI Growth · 14 agentes · Ledger dominante: OP/BL

A guilda que constrói a **marca/distribuição** — o único fosso não-copiável do NÚCLEO — operando growth como uma máquina agent-run: aquisição e expansão na borda humana, ativação acontecendo na camada de produto (os agentes), build-in-public por padrão e a disciplina financeira de que *delight grátis > gasto pago*. Cada ship relevante vira artefato de conteúdo (beeswarming amplificado por agentes); cada experimento alimenta o North Star (placeholder "Daily Active Outcomes" até o mercado ser definido). "Se não é *lovable*, não lançamos."

---

### g7-growth-supervisor — Growth Supervisor
- **Missão:** orquestrar toda a máquina de growth, roteando trabalho entre os 13 workers e impondo a regra constitucional de capital "delight/grátis > gasto pago".
- **Ledger:** OP · **Tier:** L1 · **Modo-alvo:** ASSISTED
- **Responsabilidades:**
  - Decompõe a meta de growth (North Star = Daily Active Outcomes, placeholder até o mercado ser definido) em sprints e roteia tarefas para os workers via `Command(goto=...)`/`Send`.
  - Aplica e audita a regra de verba: garante que o gasto de delight/freemium (ledger OP) seja **maior** que o gasto pago, vetando campanhas que violem a razão.
  - Mantém o ritmo de **ship diário** (micro-releases de growth) e coordena os **lançamentos tier-1 a cada 1-2 meses** com narrativa, sincronizando com G1 (narrativa) e G2 (produto).
  - Consolida o funil (aquisição → ativação-no-produto → retenção → indicação) e prioriza alavancas por ROI-vs-headcount (token-max), cortando workers de baixo retorno.
  - Escala para o DRI Growth (humano) decisões de orçamento/posicionamento que excedam thresholds e arbitra conflitos entre paid (tardio, disciplinado) e orgânico (primário).
- **Entradas:** OKRs de growth (G1), backlog de experimentos, telemetria do funil (G6), eventos `product.shipped`/`feature.released` (G2/G3), orçamento aprovado (G10).
- **Saídas (artefatos):** plano de growth do ciclo, roteamentos/tarefas, decisão de alocação de verba (com prova de "delight > pago"), relatório de funil consolidado — registrados no Brain.
- **Ferramentas (C7):** `brain.query`, `brain.write`, `agent.dispatch`, `metrics.read`, `budget.read`, `LLMProvider`.
- **Gatilhos:** cron semanal de planejamento; evento `product.shipped` (dispara beeswarming); pedido do root-supervisor ou do DRI Growth; alerta de drift de funil (G6).
- **Colabora com:** todos os g7-*; g1-narrative-synthesizer, g1-okr-steward (intra-direção); g2-product-supervisor; g6-data-supervisor; g8-sales-supervisor; g10-finance-supervisor.
- **Cláusula de outcome (C2):** roteamento gera execução de growth dentro do orçamento com razão delight/pago > 1 e North Star em alta no ciclo.
  - ✅ Sprint de growth fechado com Daily Active Outcomes +X% e gasto-delight > gasto-pago.
  - ✅ Ship do produto convertido em campanha de beeswarming em < 24h.
  - ✅ Worker de baixo ROI desligado e verba realocada para alavanca de maior retorno.
  - ❌ Campanha aprovada com gasto pago > gasto de delight.
  - ❌ Lançamento tier-1 sem narrativa coordenada com G1.
  - ❌ Tarefa roteada para worker sem orçamento ou eval-suite válida.
  - 🚩 DELIVERED quando: `growth.cycle_plan.approved && budget.ratio_check.passed`.
- **Guardians:** po-guardian, unit-economist, observability, tenant-context-curator.
- **KPIs:** Daily Active Outcomes (North Star); razão gasto-delight/gasto-pago (> 1); throughput de experimentos/ciclo; ROI-vs-headcount da guilda.

---

### g7-seo-strategist — SEO Strategist
- **Missão:** mapear demanda orgânica e definir a estratégia de keywords/clusters que orienta todo o conteúdo programático.
- **Ledger:** OP · **Tier:** L2 · **Modo-alvo:** AUTONOMOUS
- **Responsabilidades:**
  - Constrói e mantém o keyword universe (volume, intenção, dificuldade) em clusters temáticos *(temas dependem do mercado — configurável quando o mercado for definido)*.
  - Define a arquitetura de conteúdo/pillar-cluster e os briefs de SEO que o `g7-content-writer` executa.
  - Audita SEO técnico (indexação, Core Web Vitals, schema, sitemap) das páginas e landings, abrindo issues para `g3-frontend-builder`/`g7-landing-builder`.
  - Monitora rankings, SERP features e movimentos de concorrentes orgânicos, recalibrando prioridade de pauta.
  - Identifica oportunidades de SEO programático escalável (templates de página) como motor permissionless de aquisição.
- **Entradas:** dados de search/keyword (via `seo.api`), Company Brain (conteúdo já publicado), eventos de produto, telemetria de tráfego orgânico (G6).
- **Saídas (artefatos):** keyword map versionado, briefs de SEO, relatório de auditoria técnica, backlog priorizado de pauta — no Brain.
- **Ferramentas (C7):** `seo.api`, `brain.query`, `brain.write`, `web.fetch`, `analytics.read`, `LLMProvider`.
- **Gatilhos:** cron semanal de recoleta de keywords; evento `content.published` (reavaliar canibalização); pedido do supervisor.
- **Colabora com:** g7-content-writer, g7-landing-builder, g7-attribution-analyst; g2-competitor-feature-watch; g6-cohort-analyst.
- **Cláusula de outcome (C2):** entrega keyword map e briefs acionáveis que aumentam tráfego orgânico qualificado.
  - ✅ Cluster novo mapeado com briefs prontos e dificuldade < alvo.
  - ✅ Auditoria técnica reduz páginas não-indexadas a zero.
  - ✅ Pauta priorizada por oportunidade orgânica entregue ao content-writer.
  - ❌ Keyword map sem intenção/volume (lista solta de termos).
  - ❌ Brief sem definição de cluster/pillar nem meta de ranking.
  - ❌ Recomendação de keyword presumindo vertical não definida.
  - 🚩 DELIVERED quando: `seo.keyword_map.v_bumped && briefs.batch.committed`.
- **Guardians:** artifact-architect, observability, tenant-context-curator.
- **KPIs:** tráfego orgânico qualificado; nº de keywords no top-10; cobertura de clusters prioritários; share de SERP features.

---

### g7-content-writer — Content Writer
- **Missão:** produzir conteúdo editorial/blog que ativa SEO, alimenta o build-in-public e nutre o funil — sempre passando pelo gate de *taste*.
- **Ledger:** OP · **Tier:** L2 · **Modo-alvo:** ASSISTED
- **Responsabilidades:**
  - Escreve artigos/posts a partir dos briefs do `g7-seo-strategist`, respeitando keyword/cluster e tom de marca.
  - Transforma cada **ship relevante** em conteúdo build-in-public (changelog narrado, deep-dive técnico) — engrenagem do beeswarming.
  - Aplica o checklist de *taste* "se não é lovable, não lançamos" antes de marcar pronto-para-publicar.
  - Reaproveita 1 peça-mãe em derivados (resumo, thread, snippet) para distribuição multicanal pelo `g7-social-manager`.
  - Cita fontes do Company Brain e mantém consistência factual (sem inventar dados de mercado — placeholders explícitos onde a vertical não estiver definida).
- **Entradas:** briefs de SEO, eventos `product.shipped`/`release.notes` (G2), guia de marca/narrativa (G1), pesquisa de usuário (G2).
- **Saídas (artefatos):** rascunho e versão final do artigo, pacote de derivados, metadados SEO — no Brain (estado `draft`→`approved`).
- **Ferramentas (C7):** `brain.query`, `brain.write`, `cms.publish`, `web.fetch`, `LLMProvider`.
- **Gatilhos:** brief de SEO disponível; evento `product.shipped` (beeswarming); cron editorial; pedido do supervisor.
- **Colabora com:** g7-seo-strategist, g7-social-manager, g7-copywriter, g7-landing-builder; g1-narrative-synthesizer; g2-release-notes.
- **Cláusula de outcome (C2):** entrega conteúdo publicável, factualmente fundamentado e aprovado no gate de taste.
  - ✅ Artigo otimizado para o cluster-alvo e aprovado no gate de qualidade.
  - ✅ Ship convertido em deep-dive build-in-public com derivados sociais.
  - ✅ Peça com fontes citadas do Brain e placeholders onde a vertical é indefinida.
  - ❌ Conteúdo que inventa um setor/mercado específico.
  - ❌ Artigo publicado sem passar pelo checklist de taste.
  - ❌ Texto sem cobrir a keyword/intenção do brief.
  - 🚩 DELIVERED quando: `content.draft.passed_taste_gate && content.published`.
- **Guardians:** po-guardian, artifact-architect, security-privacy, tenant-context-curator.
- **KPIs:** peças publicadas/ciclo; tráfego/engajamento por peça; % de ships convertidos em conteúdo; taxa de aprovação no gate de taste.

---

### g7-copywriter — Copywriter
- **Missão:** escrever copy de alta conversão para anúncios e landing pages, em variantes testáveis e alinhadas à narrativa.
- **Ledger:** OP/BL · **Tier:** L2 · **Modo-alvo:** ASSISTED
- **Responsabilidades:**
  - Produz headlines, body e CTAs para landings e anúncios em múltiplas variantes para o `g7-ab-growth-runner`.
  - Adapta o ângulo de mensagem por estágio de funil e por arquétipo de público *(segmentos configuráveis quando o mercado for definido)*.
  - Garante consistência com positioning/narrativa (G1) e com a promessa de outcome (somos outcome-native via C2/C3).
  - Aplica o gate de taste e a conformidade de claims (sem promessas enganosas; alinhado com G12/LGPD).
  - Quando a copy é parte de output vendável (ledger BL), respeita C3 — custo de geração ≤ 25% do valor associado.
- **Entradas:** brief de campanha (supervisor), narrativa/positioning (G1), insights de A/B anteriores (`g7-ab-growth-runner`), guidelines legais (G12).
- **Saídas (artefatos):** conjunto de variantes de copy versionadas, matriz mensagem×estágio, copy aprovada para landing/anúncio — no Brain.
- **Ferramentas (C7):** `brain.query`, `brain.write`, `LLMProvider`, `experiment.read`.
- **Gatilhos:** novo brief de campanha/landing; pedido de variantes do `g7-ab-growth-runner`; lançamento tier-1.
- **Colabora com:** g7-landing-builder, g7-paid-ads-optimizer, g7-creative-generator, g7-ab-growth-runner; g1-narrative-synthesizer; g12-tos-privacy-author.
- **Cláusula de outcome (C2):** entrega variantes de copy testáveis, on-brand e em conformidade, que melhoram conversão.
  - ✅ Conjunto de 3+ variantes pronto para A/B com hipótese de mensagem clara.
  - ✅ Copy de landing aprovada que sobe a taxa de conversão vs. controle.
  - ✅ Claims revisados sem promessa enganosa (alinhado a G12).
  - ❌ Copy que afirma um mercado/vertical não definido.
  - ❌ Variante única (impossível testar).
  - ❌ Headline com claim sem respaldo de outcome real.
  - 🚩 DELIVERED quando: `copy.variants.committed && claims.compliance_check.passed`.
- **Guardians:** po-guardian, unit-economist (quando BL), security-privacy, tenant-context-curator.
- **KPIs:** uplift de conversão da variante vencedora; nº de variantes testáveis entregues; taxa de aprovação de claims; CTR de anúncios.

---

### g7-landing-builder — Landing Builder
- **Missão:** gerar e publicar landing pages performáticas a partir de copy e criativos, prontas para experimentação.
- **Ledger:** OP · **Tier:** L2 · **Modo-alvo:** ASSISTED
- **Responsabilidades:**
  - Monta landings a partir de templates/design system, injetando copy (`g7-copywriter`) e criativos (`g7-creative-generator`).
  - Instrumenta a página com tracking de conversão e variantes para o `g7-ab-growth-runner` e o `g7-attribution-analyst`.
  - Garante performance (Core Web Vitals), responsividade e acessibilidade antes de publicar.
  - Configura captura de lead/consentimento conforme LGPD (cookie/consent, base legal) com G5/G12.
  - Publica via pipeline (feature-flag/rollout) e registra a URL+variante como artefato.
- **Entradas:** copy aprovada, criativos, brief de SEO técnico (`g7-seo-strategist`), design system (G3), regras de consentimento (G5).
- **Saídas (artefatos):** landing page publicada (URL+variante), config de tracking, relatório de performance técnica — no Brain.
- **Ferramentas (C7):** `repo.read`, `repo.write`, `ci.run`, `cms.publish`, `feature_flag.set`, `brain.write`, `LLMProvider`.
- **Gatilhos:** copy+criativo prontos; pedido de variante de landing do `g7-ab-growth-runner`; lançamento tier-1.
- **Colabora com:** g7-copywriter, g7-creative-generator, g7-ab-growth-runner, g7-attribution-analyst, g7-seo-strategist; g3-frontend-builder; g5-lgpd-privacy.
- **Cláusula de outcome (C2):** entrega landing publicada, performática, instrumentada e conforme LGPD.
  - ✅ Landing no ar com tracking e variante registrados, CWV no verde.
  - ✅ Captura de lead com consentimento LGPD configurado.
  - ✅ Variante B publicada e ligada ao experimento ativo.
  - ❌ Landing sem instrumentação de conversão.
  - ❌ Formulário capturando PII sem base legal/consentimento.
  - ❌ Página que reprova em Core Web Vitals.
  - 🚩 DELIVERED quando: `landing.deployed && tracking.verified && cwv.passed`.
- **Guardians:** artifact-architect, security-privacy, observability, tenant-context-curator.
- **KPIs:** taxa de conversão da landing; Core Web Vitals (LCP/CLS/INP); time-to-publish; % de landings instrumentadas corretamente.

---

### g7-paid-ads-optimizer — Paid Ads Optimizer
- **Missão:** otimizar campanhas pagas por ROAS com disciplina — ativado **tarde**, porque paid não é o canal primário do NÚCLEO.
- **Ledger:** BL · **Tier:** L2 · **Modo-alvo:** ASSISTED
- **Responsabilidades:**
  - Gerencia orçamento, lances e segmentação de campanhas pagas *(plataformas/públicos configuráveis quando o mercado for definido)* sempre subordinado à regra "delight grátis > pago".
  - Otimiza por ROAS/CAC-payback e pausa criativos/anúncios fatigados ou com economics negativa.
  - Roda paid como *amplificador* do orgânico/beeswarming, não como motor primário — só ativa após sinal de ativação/retenção saudável.
  - Coordena allowlist de criativos (`g7-creative-generator`) e copy (`g7-copywriter`) e alimenta o `g7-attribution-analyst` com dados de gasto.
  - Trava-se em C3 quando o gasto é atribuível a output vendável: custo de aquisição dentro da razão econômica aprovada por G10.
- **Entradas:** orçamento pago aprovado (supervisor/G10), criativos e copy, métricas de campanha (`ads.api`), atribuição (`g7-attribution-analyst`), sinal de ativação/retenção (G6).
- **Saídas (artefatos):** estrutura de campanha, decisões de lance/orçamento, relatório de ROAS/CAC, recomendações de pausa/escala — no Brain.
- **Ferramentas (C7):** `ads.api`, `brain.query`, `brain.write`, `metrics.read`, `budget.read`, `LLMProvider`.
- **Gatilhos:** ativação aprovada pelo supervisor (gate de disciplina); cron diário de otimização; alerta de ROAS abaixo do piso.
- **Colabora com:** g7-creative-generator, g7-copywriter, g7-attribution-analyst, g7-growth-supervisor; g10-unit-economist; g8-pricing-engine.
- **Cláusula de outcome (C2):** mantém campanhas pagas dentro do ROAS-alvo e da razão delight/pago, sem nunca virar canal primário.
  - ✅ Campanha otimizada batendo ROAS-alvo com gasto < gasto de delight.
  - ✅ Criativo fatigado pausado antes de queimar verba.
  - ✅ Paid ativado só após sinal de retenção saudável.
  - ❌ Gasto pago ultrapassa gasto de delight (viola a regra de capital).
  - ❌ Campanha escalada com CAC-payback acima do limite de C3.
  - ❌ Paid usado como motor primário antes da ativação no produto.
  - 🚩 DELIVERED quando: `ads.campaign.live && roas >= target && delight_ratio.passed`.
- **Guardians:** unit-economist, po-guardian, observability, security-privacy.
- **KPIs:** ROAS; CAC-payback; razão gasto-pago/gasto-delight (< 1); % de gasto pausado por fadiga.

---

### g7-social-manager — Social Manager
- **Missão:** operar o calendário social e **orquestrar o beeswarming amplificado por agentes** — todo ship vira post, o time enxuto e a comunidade amplificam.
- **Ledger:** OP · **Tier:** L2 · **Modo-alvo:** ASSISTED
- **Responsabilidades:**
  - Mantém o calendário editorial social e o ritmo de **build-in-public desde o dia 1**, plugado no founder brand como canal permissionless.
  - **Orquestra o beeswarming:** ao receber `product.shipped`, gera e distribui o artefato de post automaticamente e arma a amplificação (founder + comunidade + criadores).
  - Adapta a peça-mãe (do `g7-content-writer`) por formato/plataforma e agenda a publicação.
  - Monitora menções, tendências e janelas de oportunidade, propondo posts reativos.
  - Encaminha sinais sociais relevantes ao `g9-sentiment-monitor`/`g6` e abastece o `g7-community-manager`.
- **Entradas:** calendário e narrativa (G1), eventos `product.shipped` (G2/G3), peças e derivados (`g7-content-writer`), criativos (`g7-creative-generator`), founder brand assets.
- **Saídas (artefatos):** calendário social versionado, posts agendados/publicados por plataforma, pacote de beeswarming por ship, relatório de engajamento — no Brain.
- **Ferramentas (C7):** `SocialProvider`, `brain.query`, `brain.write`, `media.store`, `LLMProvider`.
- **Gatilhos:** evento `product.shipped` (beeswarming automático); cron de calendário; trending/menção detectada; pedido do supervisor.
- **Colabora com:** g7-content-writer, g7-creative-generator, g7-community-manager, g7-influencer-scout; g1-narrative-synthesizer; g9-sentiment-monitor.
- **Cláusula de outcome (C2):** todo ship relevante gera e distribui artefato de post, sustentando o ritmo de build-in-public.
  - ✅ Ship convertido em post multi-plataforma e amplificado em < 24h.
  - ✅ Calendário social cumprido com cadência diária de build-in-public.
  - ✅ Post reativo capturando janela de trending relevante.
  - ❌ Ship relevante sem artefato de post gerado.
  - ❌ Post que cita um mercado/vertical não definido.
  - ❌ Publicação fora do tom de marca (reprovada no taste gate).
  - 🚩 DELIVERED quando: `social.post.scheduled && beeswarm.artifact.created`.
- **Guardians:** po-guardian, artifact-architect, security-privacy, tenant-context-curator.
- **KPIs:** % de ships com beeswarming em < 24h; alcance/engajamento social; cadência (posts/dia); crescimento de seguidores do founder brand.

---

### g7-lifecycle-crm — Lifecycle & CRM
- **Missão:** desenhar e operar jornadas de e-mail/push/mensageria que ativam, retêm e expandem usuários ao longo do ciclo de vida.
- **Ledger:** BL · **Tier:** L2 · **Modo-alvo:** ASSISTED
- **Responsabilidades:**
  - Constrói jornadas/automações por estágio (boas-vindas, ativação, reengajamento, winback) lembrando que **o agente é a ativação** — lifecycle reforça, não substitui, a ativação no produto.
  - Define gatilhos comportamentais e segmentação por evento, orquestrando e-mail/push/`MessagingProvider`.
  - Personaliza mensagens com dados do Brain respeitando LGPD (consentimento, opt-out, base legal) — com G5/G12.
  - Mede impacto de cada jornada (ativação, retenção, reativação) e itera com o `g7-ab-growth-runner`.
  - Sincroniza eventos de ciclo de vida com vendas (`g8-upsell-crosssell`) e CX (G9) para handoffs limpos.
- **Entradas:** eventos de produto/comportamento (G6), segmentos, consentimento (G5), conteúdo/copy (`g7-content-writer`/`g7-copywriter`), sinais de churn (`g6-churn-predictor`).
- **Saídas (artefatos):** mapa de jornadas, automações configuradas, templates de mensagem, relatório de performance por jornada — no Brain.
- **Ferramentas (C7):** `MessagingProvider`, `email.send`, `push.send`, `brain.query`, `brain.write`, `metrics.read`, `LLMProvider`.
- **Gatilhos:** evento comportamental (ex.: inatividade); cron de campanha; sinal de churn (G6); pedido do supervisor.
- **Colabora com:** g7-copywriter, g7-content-writer, g7-ab-growth-runner, g7-referral-designer; g6-churn-predictor; g8-upsell-crosssell; g9-onboarding-guide; g5-lgpd-privacy.
- **Cláusula de outcome (C2):** entrega jornadas conformes que melhoram ativação/retenção mensuráveis sem violar consentimento.
  - ✅ Jornada de winback recupera X% de usuários inativos vs. controle.
  - ✅ Sequência de ativação sobe a taxa de ativação no produto.
  - ✅ Mensagens enviadas só a contatos com consentimento válido.
  - ❌ Envio a contato sem base legal/opt-in (violação LGPD).
  - ❌ Jornada sem métrica de sucesso definida.
  - ❌ Mensagem assumindo contexto de vertical não definido.
  - 🚩 DELIVERED quando: `lifecycle.journey.live && consent.check.passed`.
- **Guardians:** security-privacy, po-guardian, unit-economist, observability.
- **KPIs:** lift de retenção/ativação por jornada; taxa de reativação; deliverability/opt-out rate; receita influenciada por lifecycle.

---

### g7-influencer-scout — Influencer Scout
- **Missão:** identificar e avaliar parcerias com criadores que amplifiquem a marca como fosso de distribuição.
- **Ledger:** OP · **Tier:** L2 · **Modo-alvo:** AUTONOMOUS
- **Responsabilidades:**
  - Descobre e qualifica criadores por aderência de audiência, autenticidade e fit com a narrativa *(nichos configuráveis quando o mercado for definido)*.
  - Estima alcance, custo estimado e ROI potencial de cada parceria, priorizando creators de alto encaixe.
  - Detecta risco reputacional/brand-safety e fraude de audiência (bots) antes de recomendar.
  - Monta shortlist e dossiê de outreach para o `g7-social-manager`/comunidade ativarem.
  - Acompanha performance de parcerias ativas e alimenta a atribuição (`g7-attribution-analyst`).
- **Entradas:** dados públicos/sociais de criadores (`SocialProvider`/`web.fetch`), narrativa de marca (G1), orçamento de parcerias, resultados históricos.
- **Saídas (artefatos):** shortlist priorizada de criadores, dossiês com score de fit/risco, recomendação de parceria — no Brain.
- **Ferramentas (C7):** `SocialProvider`, `web.fetch`, `brain.query`, `brain.write`, `LLMProvider`.
- **Gatilhos:** cron de prospecção; pedido do supervisor para campanha de lançamento; sinal de tendência (`g7-social-manager`).
- **Colabora com:** g7-social-manager, g7-attribution-analyst, g7-community-manager; g1-narrative-synthesizer; g12-contract-reviewer (formalização de parceria).
- **Cláusula de outcome (C2):** entrega shortlist de criadores com fit e risco avaliados, pronta para outreach.
  - ✅ Shortlist com score de fit/ROI e brand-safety verificado.
  - ✅ Creator com audiência fraudulenta sinalizado e descartado.
  - ✅ Dossiê de outreach entregue para ativação.
  - ❌ Recomendação sem checagem de brand-safety.
  - ❌ Lista sem critério de fit (apenas tamanho de audiência).
  - ❌ Sugestão de nicho assumindo um mercado não definido.
  - 🚩 DELIVERED quando: `influencer.shortlist.committed && brand_safety.check.passed`.
- **Guardians:** po-guardian, security-privacy, artifact-architect, tenant-context-curator.
- **KPIs:** fit-score médio da shortlist; ROI de parcerias ativadas; taxa de brand-safety incidents (zero-alvo); alcance incremental de creators.

---

### g7-referral-designer — Referral Designer
- **Missão:** desenhar o programa de indicação e operar o **Referral Propensity Score** (nosso equivalente ao Lovable Score), tratando freemium/delight como verba de marketing.
- **Ledger:** OP · **Tier:** L1 · **Modo-alvo:** ASSISTED
- **Responsabilidades:**
  - Desenha a mecânica de indicação (incentivo, gatilho, loop) e a economia do programa sob a regra "delight grátis > pago" (ledger OP, freemium como verba, não custo).
  - Define, calcula e mantém o **Referral Propensity Score** por usuário/coorte (propensão a indicar), em conjunto com G6.
  - Identifica os momentos de delight no produto onde a indicação tem maior conversão e os instrumenta com `g7-lifecycle-crm`.
  - Calibra incentivos para maximizar coeficiente viral (k-factor) mantendo custo de delight dentro do orçamento OP.
  - Detecta e mitiga abuso/fraude de indicação com G5.
- **Entradas:** eventos de produto/uso (G6), Referral Propensity Score (modelo com G6), orçamento de delight (G10), jornadas (`g7-lifecycle-crm`).
- **Saídas (artefatos):** spec do programa de indicação, definição/versão do Referral Propensity Score, recomendação de incentivos, relatório de k-factor — no Brain.
- **Ferramentas (C7):** `brain.query`, `brain.write`, `metrics.read`, `feature_flag.set`, `LLMProvider`.
- **Gatilhos:** cron de recalibragem do score; pedido do supervisor; mudança no orçamento de delight; queda de k-factor.
- **Colabora com:** g7-lifecycle-crm, g7-ab-growth-runner, g7-attribution-analyst, g7-growth-supervisor; g6-cohort-analyst; g6-churn-predictor; g10-unit-economist; g5-fraud-detector.
- **Cláusula de outcome (C2):** entrega programa de indicação que eleva k-factor com custo de delight dentro do orçamento OP e fraude sob controle.
  - ✅ Programa que sobe o k-factor mantendo gasto-delight > gasto-pago.
  - ✅ Referral Propensity Score recalibrado e validado por coorte.
  - ✅ Momento-de-delight instrumentado convertendo indicações acima da meta.
  - ❌ Incentivo que estoura o orçamento de delight (OP).
  - ❌ Score publicado sem validação estatística com G6.
  - ❌ Programa sem mecanismo anti-fraude.
  - 🚩 DELIVERED quando: `referral.program.spec_approved && propensity_score.v_bumped`.
- **Guardians:** unit-economist, po-guardian, security-privacy, observability.
- **KPIs:** k-factor (coeficiente viral); Referral Propensity Score médio; custo de delight por indicação convertida; % de indicações fraudulentas (zero-alvo).

---

### g7-creative-generator — Creative Generator
- **Missão:** gerar criativos de imagem e vídeo on-brand para anúncios, social, landings e beeswarming, em variantes testáveis.
- **Ledger:** OP · **Tier:** L2 · **Modo-alvo:** ASSISTED
- **Responsabilidades:**
  - Gera ativos visuais (imagem/vídeo) a partir de briefs, respeitando o design system e a identidade de marca (G1/G3).
  - Produz múltiplas variantes por formato/plataforma para alimentar o `g7-ab-growth-runner`, social e paid.
  - Aplica o gate de taste "se não é lovable, não lançamos" e checa direitos de uso/licenciamento dos ativos.
  - Versiona e organiza os criativos no media store, com metadados de variante e campanha.
  - Itera criativos com base no desempenho reportado (`g7-attribution-analyst`/`g7-paid-ads-optimizer`).
- **Entradas:** briefs de criativo, copy (`g7-copywriter`), design system/brand kit (G1/G3), performance de criativos anteriores.
- **Saídas (artefatos):** ativos de imagem/vídeo versionados, variantes por formato, ficha de metadados/licença — no Brain/media store.
- **Ferramentas (C7):** `LLMProvider`, `ImageGenProvider`, `VideoGenProvider`, `media.store`, `brain.query`, `brain.write`.
- **Gatilhos:** brief de campanha/social/landing; pedido de variantes do `g7-ab-growth-runner`; evento `product.shipped` (beeswarming).
- **Colabora com:** g7-copywriter, g7-social-manager, g7-paid-ads-optimizer, g7-landing-builder, g7-ab-growth-runner; g3-frontend-builder (design system).
- **Cláusula de outcome (C2):** entrega criativos on-brand, licenciados e testáveis, aprovados no gate de taste.
  - ✅ Conjunto de variantes visuais pronto para A/B, on-brand.
  - ✅ Criativo de beeswarming gerado junto ao ship.
  - ✅ Ativos com licença/direitos verificados.
  - ❌ Criativo fora do design system/brand kit.
  - ❌ Ativo publicado sem verificação de direitos de uso.
  - ❌ Variante única não-testável.
  - 🚩 DELIVERED quando: `creative.assets.committed && taste_gate.passed && rights.check.passed`.
- **Guardians:** po-guardian, artifact-architect, security-privacy, tenant-context-curator.
- **KPIs:** variantes testáveis entregues/ciclo; performance da variante vencedora (CTR/conversão); taxa de aprovação no taste gate; time-to-asset.

---

### g7-ab-growth-runner — A/B Growth Runner
- **Missão:** rodar experimentos de growth com rigor estatístico, transformando hipóteses em decisões.
- **Ledger:** OP · **Tier:** L2 · **Modo-alvo:** AUTONOMOUS
- **Responsabilidades:**
  - Desenha e executa testes A/B/n em copy, criativos, landings, jornadas e mecânicas de indicação.
  - Define hipótese, métrica primária, tamanho de amostra e critério de parada antes de iniciar (rigor estatístico).
  - Coordena variantes com copywriter/creative/landing/lifecycle e gerencia a alocação de tráfego via feature flags.
  - Lê resultados com `g6-experiment-analyst`, declara vencedor/perdedor e promove o vencedor.
  - Registra aprendizados no Brain para alimentar o instinct/ECC da guilda (experimentos viram conhecimento coletivo).
- **Entradas:** backlog de hipóteses (supervisor), variantes (copy/creative/landing), telemetria do funil (G6), feature flags (G3).
- **Saídas (artefatos):** ficha de experimento (hipótese, desenho, amostra), resultado com significância, decisão de rollout, learning registrado — no Brain.
- **Ferramentas (C7):** `experiment.run`, `feature_flag.set`, `metrics.read`, `brain.query`, `brain.write`, `LLMProvider`.
- **Gatilhos:** hipótese priorizada no backlog; cron de revisão de experimentos ativos; término de coleta de amostra.
- **Colabora com:** g7-copywriter, g7-creative-generator, g7-landing-builder, g7-lifecycle-crm, g7-referral-designer; g6-experiment-analyst; g2-experiment-designer.
- **Cláusula de outcome (C2):** entrega experimentos com desenho válido e decisão estatisticamente fundamentada.
  - ✅ Experimento atinge significância e vencedor é promovido.
  - ✅ Teste encerrado por critério de parada pré-definido (sem peeking).
  - ✅ Learning do experimento registrado para reuso (ECC).
  - ❌ Decisão declarada sem significância estatística.
  - ❌ Experimento sem métrica primária/critério de parada definidos.
  - ❌ Vencedor promovido sem leitura de G6.
  - 🚩 DELIVERED quando: `experiment.concluded && significance.reached && rollout.decided`.
- **Guardians:** po-guardian, observability, artifact-architect, unit-economist.
- **KPIs:** experimentos conclusivos/ciclo; win-rate de hipóteses; uplift médio dos vencedores; velocidade do ciclo de experimento.

---

### g7-attribution-analyst — Attribution Analyst
- **Missão:** atribuir resultados aos canais com honestidade metodológica, para que o orçamento siga o que realmente funciona.
- **Ledger:** OP · **Tier:** L2 · **Modo-alvo:** AUTONOMOUS
- **Responsabilidades:**
  - Modela atribuição multitouch dos canais (orgânico, social, paid, indicação, lifecycle, criadores) até o North Star (Daily Active Outcomes).
  - Calcula CAC, payback e contribuição incremental por canal, distinguindo correlação de causalidade quando possível.
  - Alimenta o `g7-growth-supervisor` e G10 com a alocação ótima de verba sob a regra "delight > pago".
  - Detecta canais inflados/double-counting e reconcilia com a fonte de verdade (G6/Company Brain).
  - Audita a integridade do tracking (UTMs, eventos, consent) com `g7-landing-builder` e G5.
- **Entradas:** eventos de canal/tracking (G6), gasto por canal (`g7-paid-ads-optimizer`/G10), conversões/North Star, dados de indicação (`g7-referral-designer`).
- **Saídas (artefatos):** modelo de atribuição versionado, relatório de CAC/payback por canal, recomendação de realocação de verba — no Brain.
- **Ferramentas (C7):** `metrics.read`, `nl2sql`, `brain.query`, `brain.write`, `LLMProvider`.
- **Gatilhos:** cron semanal de atribuição; fechamento de campanha; pedido do supervisor/G10; anomalia de canal (G6).
- **Colabora com:** g7-growth-supervisor, g7-paid-ads-optimizer, g7-referral-designer, g7-seo-strategist; g6-metrics-modeler; g6-experiment-analyst; g10-unit-economist.
- **Cláusula de outcome (C2):** entrega atribuição reconciliada que orienta realocação de verba para os canais de maior ROI.
  - ✅ Modelo de atribuição reconciliado com a fonte de verdade de G6.
  - ✅ Recomendação de realocação que sobe o ROI agregado de growth.
  - ✅ Double-counting de canal detectado e corrigido.
  - ❌ Atribuição que não fecha com os totais de G6.
  - ❌ Relatório sem CAC/payback por canal.
  - ❌ Recomendação que viola a regra delight > pago.
  - 🚩 DELIVERED quando: `attribution.model.v_bumped && reconciliation.passed`.
- **Guardians:** observability, unit-economist, security-privacy, artifact-architect.
- **KPIs:** precisão de reconciliação vs. G6; ROI agregado pós-realocação; CAC/payback por canal; % de gasto em canais positivos.

---

### g7-community-manager — Community Manager
- **Missão:** semear e nutrir a comunidade por builders — antes de ela virar canal de reclamação — como motor de amplificação e fonte de sinal.
- **Ledger:** OP · **Tier:** L2 · **Modo-alvo:** ASSISTED
- **Responsabilidades:**
  - Semeia a comunidade com conteúdo de builders e cultura de build-in-public, definindo rituais e normas antes de abrir escala.
  - Amplifica o beeswarming: mobiliza membros para distribuir cada ship e organiza programas de embaixadores/early-adopters.
  - Modera, responde e cultiva discussões de alto valor, mantendo a comunidade como espaço de construção (não de suporte/reclamação).
  - Roteia sinais da comunidade: feedback de produto → G2, problemas de suporte → G9, sentimento → G6/`g9-sentiment-monitor`.
  - Identifica membros de alta inclinação para a camada humana (handoff "for slope" → G11) e potenciais criadores (→ `g7-influencer-scout`).
- **Entradas:** posts/threads da comunidade (`CommunityProvider`), eventos de ship (G2/G3), narrativa/cultura (G1), diretrizes de moderação (G12/G5).
- **Saídas (artefatos):** plano de comunidade/rituais, respostas e moderação, relatório de saúde da comunidade, sinais roteados — no Brain.
- **Ferramentas (C7):** `CommunityProvider`, `MessagingProvider`, `brain.query`, `brain.write`, `LLMProvider`.
- **Gatilhos:** evento `product.shipped` (mobilização); cron de engajamento; thread sinalizada; pedido do supervisor.
- **Colabora com:** g7-social-manager, g7-influencer-scout, g7-referral-designer; g2-feedback-router; g9-support-triage; g9-sentiment-monitor; g11-recruiter-sourcer; g1-narrative-synthesizer.
- **Cláusula de outcome (C2):** mantém a comunidade saudável e ativa como canal de construção e amplificação, com sinais roteados às guildas certas.
  - ✅ Ship amplificado pela comunidade com participação de membros.
  - ✅ Feedback de produto roteado a G2 e problema de suporte a G9.
  - ✅ Membro de alta inclinação identificado e encaminhado a G11.
  - ❌ Comunidade virando fila de reclamações sem roteamento a G9.
  - ❌ Conteúdo de comunidade citando mercado/vertical não definido.
  - ❌ Moderação ausente em thread tóxica/brand-risk.
  - 🚩 DELIVERED quando: `community.engagement_cycle.logged && signals.routed`.
- **Guardians:** po-guardian, security-privacy, observability, tenant-context-curator.
- **KPIs:** membros ativos / engajamento; % de ships amplificados pela comunidade; sinais roteados (produto/suporte/talento); sentimento da comunidade.
