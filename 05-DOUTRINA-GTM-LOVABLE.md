# 05 — Doutrina de Growth & Cultura (adaptada da Lovable)

> **Status:** doutrina operacional (v1, 2026-05-29) · complementa a Constituição C1–C8 e a doutrina YC Y1–Y8 ([02-ARQUITETURA.md](02-ARQUITETURA.md) §3).
> **Mercado/vertical:** _(configurável quando o mercado for definido)_. Esta doutrina é agnóstica de setor; onde algo depende do mercado, está marcado.

## O paralelo: 146 pessoas / 400M ARR → ~150 agentes + camada humana fina

A Lovable foi de **0 a ~400M ARR em 14 meses com 146 pessoas** e **quase zero mídia paga até ~300M ARR**. Não foi sorte de canal: foi um sistema de growth onde **product-led, build-in-public e freemium** se reforçavam, executado por um time de altíssima densidade que **shippava todo dia**.

No NÚCLEO o trabalho não é feito por 146 pessoas — é feito por **~150 agentes** (as 13 guildas de [03-CATALOGO-AGENTES.md](03-CATALOGO-AGENTES.md)), amplificados por uma **camada humana fina e fixa**: **1 AI Founder + ~6 DRIs + ~4 ICs** ([04-IMPLEMENTACAO.md](04-IMPLEMENTACAO.md) §6). Esse é o twist: **cada alavanca da Lovable fica mais forte quando executada por uma frota que nunca para de shippar, nunca dorme e emite um artefato a cada ação.**

Por que o modelo agent-run amplifica cada alavanca:
- **Volume sem custo marginal humano.** Build-in-public na Lovable competia com o tempo dos engenheiros. Aqui, **todo ship já produz um artefato no Company Brain** (regra C6/Y3) — virar isso em post candidato é grátis e contínuo.
- **Cadência infinita.** "Ship diário" é um esforço heroico para humanos; para a Software Factory L3 é o estado-base. A frequência de aprendizado vira o fosso (cultura Lovable + loop self-harness/`evolve`).
- **Loop fechado nativo.** Cada agente mede o outcome do que entrega (Y2). Growth deixa de ser intuição e vira **experimento instrumentado** lido do Brain (empresa queryable, Y3).
- **Densidade humana levada ao extremo.** "Hire for slope" com ~11 humanos: cada contratação é alavanca sobre 150 agentes, não sobre uma cadeira a mais.

---

## As alavancas da Lovable, traduzidas para uma empresa agent-run

Formato de cada alavanca: **(Lovable)** o que fizeram → **(NÚCLEO)** como traduzimos → **(Agentes)** quem executa, com ids reais.

### (a) Founder brand como canal permissionless / build-in-public
- **Lovable:** o fundador construiu em público; a marca pessoal virou canal de distribuição que não pede permissão a nenhuma plataforma.
- **NÚCLEO:** o **AI Founder** mantém presença build-in-public, mas o conteúdo é **manufaturado pela frota a partir de fatos reais do Brain** (não opinião inventada). O Founder cura e assina; os agentes produzem o lastro. Permissionless = não dependemos de ad networks.
- **Agentes:** `g1-narrative-synthesizer` (positioning/narrativa), `g7-content-writer` (drafts), `g7-social-manager` (publicação/calendário), `g7-copywriter` (hooks).

### (b) Hire for slope / densidade de talento (camada humana fina)
- **Lovable:** contratou pela trajetória/inclinação (slope), não pelo currículo; manteve densidade altíssima.
- **NÚCLEO:** a camada humana é **deliberadamente fina** (1+6+4). Cada humano é alavanca sobre dezenas de agentes; contratamos quem tem slope para **operar a Fábrica e desenvolver convicção sobre agentes** (Y6: IC traz protótipo funcional, não slide).
- **Agentes:** `g11-recruiter-sourcer` (sourcing de DRIs/ICs), `g11-jd-author` (vagas nos arquétipos YC).

### (c) Beeswarming → beeswarming amplificado por agentes
- **Lovable:** o time inteiro "enxameava" cada lançamento — todos amplificavam o mesmo momento.
- **NÚCLEO:** **todo ship vira post candidato, automaticamente.** O artefato emitido no fim de cada run (C6) é matéria-prima; o enxame deixa de ser 146 pessoas postando e vira a frota gerando N variações + a camada humana escolhendo a melhor. Enxame contínuo, não episódico.
- **Agentes:** `g2-release-notes` (transforma PRs em notas), `g7-social-manager`, `g7-creative-generator` (variações de criativo), `g7-content-writer`.

### (d) Freemium como verba de marketing (ledger OP) + Referral Propensity Score (nosso "Lovable Score")
- **Lovable:** o tier grátis _era_ o orçamento de marketing; o "Lovable Score" identificava quem tinha alta propensão a indicar/converter.
- **NÚCLEO:** o **custo do free tier roda no livro-razão OPERATING** (token-max, Y7 / README §tensão) — é verba de aquisição, não custo a cortar; **nunca** entra no gate C3 (que só trava `billable`). Construímos um **Referral Propensity Score** ("Lovable Score" do NÚCLEO): modelo que pontua cada usuário por probabilidade de indicar/expandir e dispara o programa de indicação nos de score alto.
- **Agentes:** `g6-metrics-modeler` (define o score como métrica canônica), `g6-cohort-analyst` (sinais comportamentais), `g7-referral-designer` (desenha o programa acionado pelo score), `g7-lifecycle-crm` (dispara), `g10-token-cost-accountant` (contabiliza o free como verba OP).

### (e) Ship diário + lançamentos tier-1 a cada 1–2 meses
- **Lovable:** shippava melhorias diariamente e fazia lançamentos "grandes" a cada ~1–2 meses para concentrar atenção.
- **NÚCLEO:** **mapeado direto na Software Factory L3** (`diagnose→spec→plan→implement→eval→promote`). Ship diário é o output natural da Fábrica; o **tier-1 mensal** é um ritmo de growth que empacota o acumulado num momento de marca.
- **Agentes:** `g3-eng-supervisor` + `g3-backend-builder`/`g3-frontend-builder` (ship), `g3-feature-flagger` (rollout controlado do tier-1), `g4-quality-gate` (gate antes de cada ship), `g2-release-notes` (empacota o tier-1).

### (f) Co-marketing / parcerias como transferência de credibilidade
- **Lovable:** parcerias e co-marketing transferiam credibilidade de marcas estabelecidas para a nova.
- **NÚCLEO:** agentes **identificam e priorizam parceiros** por fit e por credibilidade-transferível; a camada humana fecha. Parceria = atalho de confiança que não se compra com ads.
- **Agentes:** `g7-influencer-scout` (mapeia parceiros/criadores), `g1-market-intel` (adjacências de mercado — _alvos configuráveis quando o mercado for definido_), `g7-content-writer` (assets de co-marketing).

### (g) Comunidade semeada por builders
- **Lovable:** a comunidade foi semeada por quem realmente construía o produto — credibilidade de builder, não de social media manager.
- **NÚCLEO:** a comunidade é **semeada pela frota com lastro técnico** — respostas e conteúdo nascem de fatos reais do Brain; a voz de builder é mantida pela camada humana que cura. Comunidade é canal de retenção e de feedback (alimenta Produto).
- **Agentes:** `g7-community-manager` (gestão/seeding), `g9-voice-of-customer` (comunidade → Produto), `g2-feedback-router` (roteia sinais às guildas).

### (h) O agente É a ativação (ativação na camada de produto)
- **Lovable:** o produto se ativava sozinho — o primeiro uso já entregava valor ("aha" embutido no produto).
- **NÚCLEO:** **ativação acontece na camada de PRODUTO, não em growth.** O próprio agente que o usuário toca _é_ o onboarding e o primeiro valor. Por isso **growth foca aquisição + expansão**, e deixa ativação para o produto — separação limpa de responsabilidades.
- **Agentes:** `g9-onboarding-guide` (ativação no produto/CustOps), `g2-prototype-builder` (a experiência de primeiro valor). Growth (G7) **não** "ativa": entrega usuário ativado para expansão via `g8-upsell-crosssell`.

### (i) Sem mídia paga como canal primário até tração orgânica
- **Lovable:** quase zero ads até ~300M ARR; só então usou paga — e para **educar o mercado** e **amplificar criadores**, não para comprar instalações.
- **NÚCLEO:** **earned-before-paid é regra (GR1).** `g7-paid-ads-optimizer` nasce em SHADOW e **só é promovido quando há tração orgânica comprovada** (north-star crescendo organicamente). Quando ligado, paga serve **educação de mercado + amplificação de criadores**, não aquisição fria.
- **Agentes:** `g7-paid-ads-optimizer` (BL, fica adormecido até o gate), `g7-attribution-analyst` (prova que o orgânico é o motor antes de liberar paga).

### (j) Monetização em 3 camadas — e por que somos OUTCOME-NATIVE desde o dia 1
- **Lovable:** assinatura + top-ups (créditos) + componente outcome-based.
- **NÚCLEO:** **3 camadas — assinatura + top-ups + outcome-based.** A vantagem early-stage (Y8): a Lovable teve que _migrar_ para outcome-based; **nós nascemos outcome-native**, porque o modelo econômico já é por-outcome via **C2** (toda spec declara cláusula de outcome) e **C3** (custo ≤25% do preço _por outcome_ no livro `billable`). Cobrar por resultado não é um retrofit — é o default da arquitetura.
- **Agentes:** `g8-pricing-engine` (3 camadas/precificação por outcome), `g2-pricing-product-fit` (willingness-to-pay), `g8-billing-agent` (cobrança por outcome), `g10-unit-economist` (guarda C3 só no billable).

### (k) North star = indicador-líder dos dois lados do valor; ignorar LTV cedo; rastrear retenção
- **Lovable:** escolheu um north-star que era **indicador-líder** do valor entregue (não receita defasada); ignorou LTV nos primeiros anos (ruidoso demais cedo) e perseguiu **retenção**.
- **NÚCLEO:** north-star é um **indicador-líder que captura os dois lados do valor** _(definição exata configurável quando o mercado for definido)_. **Ignoramos LTV nos primeiros anos** (GR6) e **rastreamos retenção dura (ex.: D30)** como sinal de PMF.
- **Agentes:** `g6-metrics-modeler` (define north-star + retenção como métricas canônicas), `g6-cohort-analyst` (D30/coortes), `g6-dashboard-builder` (expõe no Operator Console).

### (l) Marca/distribuição como único fosso não-copiável
- **Lovable:** features são copiáveis em semanas por concorrentes (inclusive os próprios LLMs); **marca + distribuição** não.
- **NÚCLEO:** assumimos que **qualquer feature será copiada**; investimos no que não se copia — **marca e distribuição** construídas por build-in-public, comunidade e founder brand. É o fosso de longo prazo (GR7).
- **Agentes:** `g1-narrative-synthesizer` (marca/positioning), `g7-community-manager` + `g7-social-manager` (distribuição), `g7-attribution-analyst` (mede a saúde do fosso).

### (m) Cultura: gate de taste, PMF treadmill, construir o avião em pleno voo, velocidade de aprendizado como fosso
- **Lovable:** "se não é lovable, não lançamos" (gate de taste/qualidade); **PMF treadmill** (PMF não é destino — reseta e se reconquista a cada ~90 dias); construir o avião em pleno voo; **velocidade de aprendizado é o fosso real**.
- **NÚCLEO:** amarrado à arquitetura:
  - **Gate de lovability (taste):** vira um Guardian de qualidade no caminho de promoção — `g4-quality-gate` ganha um critério de "lovability" alimentado por `g9-csat-analyst`/`g9-voice-of-customer`. **Se não passa no gate de taste, não shippa** (GR8).
  - **PMF treadmill:** trimestral, fazemos **reset/re-spec** — o reviewer e a re-especificação reavaliam se ainda há PMF _(critérios de PMF configuráveis quando o mercado for definido)_.
  - **Construir o avião em pleno voo:** os agentes nascem em SHADOW e são promovidos enquanto o produto já roda; a Fábrica refaz peças sem parar o avião.
  - **Velocidade de aprendizado como fosso:** é literalmente o **loop self-harness → `/evolve` → drift detection** ([02-ARQUITETURA.md](02-ARQUITETURA.md) §4/§7). Aprender mais rápido que o concorrente é mensurável (fatos promovidos/mês, skills criadas) e é o fosso técnico.
- **Agentes:** `g4-quality-gate` (gate de taste), `g13-monthly-reviewer` + `g2-prd-author` (reset/re-spec trimestral), `g6-drift-detector` (rebaixa o que degrada), `g13-learning-curator` + `hermes-learning-loop` (velocidade de aprendizado).

---

## Constituição de Growth (GR1–GR10)

Regras acionáveis que **complementam** a Constituição C1–C8 e a doutrina YC Y1–Y8. Formato: **nome — regra — dono**.

| # | Nome | Regra | Dono |
|---|---|---|---|
| **GR1** | Earned-before-paid | Mídia paga não é canal primário; `g7-paid-ads-optimizer` só sai de SHADOW após tração orgânica provada, e então serve educação + criadores. | DRI Growth / `g7-growth-supervisor` |
| **GR2** | Delight-grátis > pago | O free tier é verba de marketing no livro OPERATING (Y7); é custo a maximizar enquanto converte, nunca a cortar — não entra no gate C3. | `g10-token-cost-accountant` / DRI Finanças |
| **GR3** | Ship diário + tier-1 mensal | A Fábrica L3 shippa todo dia; um lançamento tier-1 a cada 1–2 meses concentra atenção de marca. | `g3-eng-supervisor` + `g7-growth-supervisor` |
| **GR4** | Todo ship vira artefato build-in-public | Cada run emite artefato (C6); todo artefato relevante é post candidato curado pela camada humana. | `g2-release-notes` + `g7-social-manager` |
| **GR5** | Outcome-based é o destino | Monetização em 3 camadas com outcome-native desde o dia 1 via C2/C3; preço se ancora em resultado, não em assento. | `g8-pricing-engine` / `g10-unit-economist` |
| **GR6** | North-star líder, LTV depois | Perseguir um indicador-líder dos dois lados do valor e retenção dura (ex.: D30); ignorar LTV nos primeiros anos. | `g6-metrics-modeler` / DRI Dados |
| **GR7** | Marca/distribuição é o fosso | Tratar features como copiáveis; investir o excedente em marca, comunidade e distribuição — o único fosso não-copiável. | `g1-narrative-synthesizer` + `g7-community-manager` |
| **GR8** | Gate de lovability | Se não é lovable, não lança: nenhum ship passa sem o critério de taste no `g4-quality-gate`. | DRI Qualidade / `g4-quality-gate` |
| **GR9** | Hire-for-slope | Contratar a camada humana fina por trajetória/inclinação e capacidade de operar a Fábrica (Y6), não por currículo. | AI Founder / `g11-recruiter-sourcer` |
| **GR10** | Assumir o PMF treadmill | PMF não é permanente; a cada ~90 dias resetar e re-especificar para reconquistá-lo. | AI Founder + `g13-monthly-reviewer` |

---

## Cadência operacional

Quem dispara cada ritmo (agente/guilda) e o que produz.

| Ritmo | Quando | O que acontece | Agentes que disparam |
|---|---|---|---|
| **Diário** | todo dia | **Ship** (feature/fix via Fábrica) + **Post** (artefato do ship vira build-in-public). | `g3-eng-supervisor` → `g3-backend-builder`/`g3-frontend-builder` (ship); `g2-release-notes` + `g7-social-manager` (post); `g4-quality-gate` (gate de taste antes de cada ship) |
| **Semanal** | toda semana | **`/evolve`** (instincts recorrentes → skills) + **experimentos de growth** (desenhar/rodar/ler A/B). | `hermes-learning-loop` + `g13-learning-curator` (`/evolve`); `g7-ab-growth-runner` + `g2-experiment-designer` + `g6-experiment-analyst` (experimentos) |
| **Mensal** | todo mês | **Lançamento tier-1** (empacota o acumulado) + **reviewer** independente (audita C1–C8, amostra outcomes). | `g7-growth-supervisor` + `g2-release-notes` + `g3-feature-flagger` (tier-1); `g13-monthly-reviewer` (auditoria) |
| **Trimestral** | a cada ~90 dias | **Reset do PMF treadmill** + **re-spec** (reavaliar PMF, re-especificar produto/posicionamento). | `g13-monthly-reviewer` + `g1-narrative-synthesizer` + `g2-prd-author` (re-spec); AI Founder (decisão) |

---

## Métricas e fosso

Tudo abaixo é métrica canônica definida por `g6-metrics-modeler` e exposta no **Operator Console** por `g6-dashboard-builder` — a empresa é **queryable** (Y3): qualquer um (humano ou agente, via `g6-nl2sql`) pergunta e obtém resposta lastreada no Company Brain.

| Métrica | O que mede | Por que importa | Agente fonte |
|---|---|---|---|
| **North-star** | indicador-líder dos dois lados do valor _(definição configurável quando o mercado for definido)_ | sinal antecipado de PMF, não receita defasada (GR6) | `g6-metrics-modeler` |
| **Referral Propensity Score** ("Lovable Score") | probabilidade de cada usuário indicar/expandir | aciona o programa de indicação nos de score alto (alavanca d) | `g6-cohort-analyst` → `g7-referral-designer` |
| **Retenção (ex.: D30)** | quantos voltam/permanecem após 30 dias | retenção dura é o teste real de PMF; perseguida desde cedo | `g6-cohort-analyst` |
| **NDR / NRR** | expansão líquida de receita da base | prova que o motor de expansão (não só aquisição) funciona | `g8-revenue-reporter` + `g8-upsell-crosssell` |
| **Eficiência de capital (burn / runway)** | quanto ARR por dólar/token queimado | a tese 400M ARR / 146 pessoas = eficiência radical; aqui é 150 agentes | `g10-burn-monitor` + `g10-token-cost-accountant` |

**O fosso, medido:** marca/distribuição (GR7) + **velocidade de aprendizado**. Esta última é quantificável — fatos promovidos `local→shadow→assisted` por mês e skills criadas por `/evolve` ([04-IMPLEMENTACAO.md](04-IMPLEMENTACAO.md) §5). `g6-drift-detector` garante que o que degrada é rebaixado antes de corroer o fosso. Note a separação de livros-razão: o burn do free tier é OPERATING (verba, GR2) e **não** contamina a margem `billable` (C3).

---

## Como isto se conecta ao resto do plano

- **[README.md](README.md)** — esta doutrina é a camada de **growth & cultura** sobre o Company-OS; a tensão "token-max × C3" do README é o que torna **GR2 (free como verba OP)** e **GR5 (outcome-based billable)** coexistentes sem contradição.
- **[02-ARQUITETURA.md](02-ARQUITETURA.md)** — cada alavanca aterrissa em uma decisão YC (Y1–Y8): build-in-public usa o Company Brain (Y3); ship diário é a Software Factory (Y4); camada humana fina é Y5/Y6; free como verba é o livro OPERATING (Y7); outcome-native é a vantagem early-stage (Y8). A "velocidade de aprendizado como fosso" **é** o loop self-harness/`evolve`/drift (§4/§7).
- **[03-CATALOGO-AGENTES.md](03-CATALOGO-AGENTES.md)** — todos os ids usados aqui são reais do catálogo, com peso em **G7 Growth & Marketing**, **G2 Produto**, **G6 Dados**, **G8 Vendas** e **G13 Governança**. Os DRIs donos das regras GR são os mesmos das guildas.
- **[04-IMPLEMENTACAO.md](04-IMPLEMENTACAO.md)** — a cadência operacional roda sobre os ritmos já previstos (learning loop diário, `/evolve` semanal, reviewer mensal, drift contínuo); as métricas desta doutrina entram nos dashboards de §5.
- **`catalogo/`** — _(quando materializada)_ as specs `spec.yaml` dos agentes G7/G2/G6/G8 citados aqui devem declarar as cláusulas de outcome (C2) e o `ledger` correto (OP para free/marca, BL para o que é vendido), tornando GR1–GR10 verificáveis em runtime.
