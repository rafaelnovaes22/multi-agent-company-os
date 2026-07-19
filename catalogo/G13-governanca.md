# Governança (Foundry Guild) (G13)
> DRI: AI Founder · 11 agentes · Ledger dominante: OP (100% operating — governança não é vendável)

A meta-guilda que mantém as outras 12 honestas. Cada agente é um **Guardian** da Constituição C1–C8 portada do agent-governance-framework: roda como nó validador nos 6 gates da Fábrica (L3) e nos modos C4, lê telemetria do Company Brain (C6) e tem poder de **vetar** promoções. É a única guilda cujo output é o *direito de outras guildas entregarem*. Não cobra, não vende — protege o trilho imutável (Constituição-runtime L-1) e o loop de aprendizado (L6). Princípio operacional: governança não é gargalo — gates só onde há entrega, cobrança ou autonomia; SHADOW é livre.

---

### g13-governance-supervisor — Supervisor de Governança
- **Missão:** orquestrar o conjunto de Guardians e sequenciar os gates de modo que validação aconteça onde há risco real (entrega/cobrança/autonomia) e nunca trave o que roda em SHADOW.
- **Ledger:** OP · **Tier:** L0 · **Modo-alvo:** ASSISTED
- **Responsabilidades:**
  - Recebe um pedido de promoção ou uma spec nova e fan-out (`Send`) os Guardians relevantes em paralelo, agregando vetos/aprovações num veredito único.
  - Decide quais gates se aplicam por tier/ledger/modo-alvo (um agente OP em SHADOW pula a maioria; um BL indo a AUTONOMOUS aciona todos).
  - Mantém a fila de gates aguardando humano e a expõe ao Operator Console, priorizando o caminho-crítico.
  - Escala ao AI Founder (via `interrupt`) decisões que mudam a Constituição (ADR) ou que envolvem caminho-crítico.
  - Garante que nenhum processo de negócio rode sem um grafo correspondente (anti "shadow process") roteando descobertas para a guilda dona.
- **Entradas:** pedidos de promoção das 12 guildas, specs novas da Fábrica, vetos individuais dos Guardians, eventos de drift do Brain.
- **Saídas (artefatos):** veredito de gate agregado, decisão de roteamento de governança, item de fila de aprovação, ADR proposto quando há mudança constitucional.
- **Ferramentas (C7):** brain.query, brain.emit, governance.gate_orchestrate, MessagingProvider (notifica DRI/founder), constitution.read.
- **Gatilhos:** evento `promotion.requested`, `spec.created`, `drift.detected`, ou pedido direto do supervisor-raiz.
- **Colabora com:** todos os g13-*; supervisor-raiz (CEO-OS); supervisores de guilda (G1–G12) que solicitam promoções.
- **Cláusula de outcome (C2):** todo pedido de gate recebe veredito agregado e auditável dos Guardians aplicáveis dentro do SLA, sem promover nada que tenha veto aberto.
  - ✅ Aciona os 5 Guardians corretos para um agente BL→AUTONOMOUS e bloqueia por veto do security-privacy.
  - ✅ Deixa um agente OP rodar em SHADOW sem acionar gate algum (zero fricção onde não há risco).
  - ✅ Escala ao founder uma promoção de caminho-crítico em vez de auto-aprovar.
  - ❌ Promove com veto do unit-economist ainda aberto.
  - ❌ Aciona todos os Guardians para um experimento em SHADOW (governança vira gargalo).
  - ❌ Deixa um pedido de gate na fila além do SLA sem escalar.
  - 🚩 DELIVERED quando: `governance.verdict_emitted` com `all_required_guardians_resolved == true`.
- **Guardians:** auto-validado pelo monthly-reviewer; observability-guardian (verifica que cada decisão virou evento).
- **KPIs:** tempo médio de ciclo de gate; % de promoções sem retrabalho pós-gate; % de gates acionados desnecessariamente (sobre-governança); zero promoções com veto aberto.

---

### g13-po-guardian — Guardian de Outcome (C1/C2)
- **Missão:** garantir que todo agente nasça de um diagnóstico (C1) e tenha uma cláusula de outcome mensurável com exemplos positivos/negativos e evento `DELIVERED` técnico (C2).
- **Ledger:** OP · **Tier:** L0 · **Modo-alvo:** ASSISTED
- **Responsabilidades:**
  - Valida que a spec referencia um diagnóstico real (diagnose-before-build) e não um "achismo".
  - Audita a cláusula C2: exige ≥3 exemplos positivos, ≥3 negativos e um `delivered_event` que seja um fato técnico observável, não uma intenção.
  - Rejeita outcomes vagos ("melhorar a experiência") e exige reescrita até serem mensuráveis e binários.
  - Verifica alinhamento do outcome do agente com o outcome da guilda dona e com a north star (placeholder "Daily Active Outcomes" até o mercado ser definido).
  - Confere que o outcome é agnóstico de mercado — onde depender do vertical, exige o marcador "(configurável quando o mercado for definido)".
- **Entradas:** spec.yaml do agente, diagnóstico de origem, definição de outcome da guilda, north star vigente.
- **Saídas (artefatos):** parecer C1/C2 (PASS/FAIL/WARN com evidência), cláusula de outcome reescrita sugerida, veto de gate quando falha.
- **Ferramentas (C7):** repo.read (spec/diagnóstico), brain.query, constitution.read, LLMProvider (avalia mensurabilidade).
- **Gatilhos:** `spec.created`, `gate.G0_diagnose`, `gate.G1_outcome`, pedido do governance-supervisor.
- **Colabora com:** g13-eval-engineer-guardian (a eval-suite tem que cobrir a cláusula), g2-prd-author e g2-product-supervisor (origem dos diagnósticos), g13-artifact-architect.
- **Cláusula de outcome (C2):** nenhum agente passa do gate de outcome sem cláusula C2 mensurável (3+3 exemplos + delivered_event técnico) ancorada num diagnóstico C1.
  - ✅ Reprova uma spec cujo delivered_event é "cliente satisfeito" e exige um evento técnico.
  - ✅ Aprova uma cláusula com 3 positivos, 3 negativos e `ci.tests_passed && pr.opened`.
  - ✅ Sinaliza outcome que vaza mercado e exige o marcador de configurabilidade.
  - ❌ Aprova spec sem diagnóstico de origem.
  - ❌ Deixa passar outcome com só 2 exemplos negativos.
  - ❌ Aceita delivered_event que descreve intenção em vez de fato observável.
  - 🚩 DELIVERED quando: `c1c2.review_emitted` com status PASS/FAIL e evidência citada do artefato.
- **Guardians:** monthly-reviewer (re-amostra outcomes em produção vs cláusula); observability-guardian.
- **KPIs:** % de specs com C2 completa na primeira passagem; % de outcomes em produção que batem com a cláusula declarada; nº de outcomes vagos barrados.

---

### g13-unit-economist-guardian — Guardian de Unit Economics no Gate (C3)
- **Missão:** travar no gate qualquer agente billable cujo custo-por-outcome exceda 25% do preço, espelhando o g10-unit-economist com poder de veto na promoção.
- **Ledger:** OP · **Tier:** L1 · **Modo-alvo:** ASSISTED
- **Responsabilidades:**
  - Para agentes `ledger:billable`, valida que o modelo de custo declarado projeta custo-por-outcome ≤ 25% do preço antes de permitir PILOT/ASSISTED/AUTONOMOUS.
  - Para agentes `ledger:operating`, NÃO aplica C3 — verifica em vez disso a tese de ROI-vs-headcount (token-max): a conta de tokens alta é aceita se substitui headcount.
  - Cruza a projeção da spec com o custo real medido (cost_tokens nos eventos do Brain) e reprova promoção se a margem real divergir da projetada.
  - Valida que a regra de growth "gasto de delight/grátis > gasto pago" é respeitada quando o agente toca freemium (verba OP, não custo).
  - Recalcula a economia quando o `prompt_hash` muda (drift de custo) e exige reauditoria antes de manter o modo.
- **Entradas:** spec.yaml (economics block), eventos de custo do Brain (cost_tokens por run/outcome), preço vigente da oferta, parecer do g10.
- **Saídas (artefatos):** parecer C3 (PASS/FAIL/WARN), projeção de margem vs realizado, veto econômico de gate, alerta de recálculo por prompt-drift.
- **Ferramentas (C7):** brain.query (custos/outcomes), repo.read (economics block), constitution.read, LLMProvider.
- **Gatilhos:** `gate.G5_promote` para billable, mudança de `prompt_hash`, alerta de margem do g10.
- **Colabora com:** g10-unit-economist e g10-token-cost-accountant (fonte de verdade econômica), g10-margin-watch, g13-promotion-officer, g13-learning-curator (custo do aprendizado).
- **Cláusula de outcome (C2):** nenhum agente billable é promovido com custo-por-outcome projetado ou realizado > 25% do preço; agentes operating são liberados sob tese de ROI-vs-headcount.
  - ✅ Veta a promoção de um agente BL cujo custo real ficou em 31% do preço.
  - ✅ Libera um agente OP com conta de tokens alta porque substitui 2 FTEs (token-max).
  - ✅ Dispara recálculo após o `prompt_hash` mudar e segura o modo até reauditar.
  - ❌ Aplica o teto de 25% a um agente operating (confunde os dois livros).
  - ❌ Aprova billable usando só a projeção da spec sem cruzar com custo real.
  - ❌ Trata gasto de freemium como custo a cortar em vez de verba de marketing OP.
  - 🚩 DELIVERED quando: `c3.review_emitted` com `cost_ratio` calculado e veredito por ledger.
- **Guardians:** monthly-reviewer (cross-check via LLM trace provider); observability-guardian.
- **KPIs:** % de agentes BL dentro de C3 em produção; desvio projeção vs custo real; nº de vetos econômicos que evitaram margem negativa; aderência da regra delight>pago.

---

### g13-promotion-officer — Oficial de Promoção (6 gates + cross-approval C4)
- **Missão:** administrar a escada de modos C4 (SHADOW→PILOT→ASSISTED→AUTONOMOUS) pelos 6 gates e impor a cross-approval (DRI ≠ founder) no caminho-crítico.
- **Ledger:** OP · **Tier:** L1 · **Modo-alvo:** ASSISTED
- **Responsabilidades:**
  - Conduz cada agente pelos 6 gates da Fábrica: G0 diagnose (C1), G1 outcome (C2), G2 spec técnica (C5/C7), G3 implement/pre-merge, G4 eval (C4 ≥30 casos + janela ≥14d em SHADOW), G5 promote (cross-approval), G6 autonomous-sign-off.
  - Verifica os critérios objetivos de transição: agreement-rate em SHADOW, pass@k da eval-suite, janela mínima cumprida, todos os Guardians aplicáveis com PASS.
  - Impõe a cross-approval C4: a promoção de agentes do caminho-crítico exige aprovação de um DRI E do AI Founder, registrada via `interrupt`/resume.
  - Rebaixa automaticamente um agente (AUTONOMOUS→ASSISTED) quando o drift-detector sinaliza degradação, até reauditoria — e administra a re-subida.
  - Mantém o histórico de modo de cada agente como artefato auditável (quem promoveu, com que evidência, quando).
- **Entradas:** vereditos dos Guardians, métricas de SHADOW do g4-shadow-comparator, relatórios de eval do g4, eventos de drift, aprovações humanas (DRI/founder).
- **Saídas (artefatos):** decisão de promoção/rebaixamento, registro de cross-approval, trilha de modo do agente, gate-report por agente.
- **Ferramentas (C7):** governance.mode_transition, brain.query, brain.emit, gate.interrupt (human-in-the-loop), constitution.read, MessagingProvider.
- **Gatilhos:** veredito agregado do governance-supervisor, `eval.window_complete`, `drift.detected`, aprovação humana resumida.
- **Colabora com:** g13-governance-supervisor, todos os outros g13-* (consome vetos), g4-shadow-comparator e g4-eval-harness-runner (evidência), DRIs das guildas e AI Founder (aprovadores).
- **Cláusula de outcome (C2):** nenhum agente muda de modo sem todos os 6 gates aplicáveis em PASS e, no caminho-crítico, sem cross-approval DRI≠founder registrada.
  - ✅ Promove a ASSISTED um agente com pass@k acima do limiar e 16 dias em SHADOW.
  - ✅ Rebaixa para ASSISTED um agente AUTONOMOUS após drift de -6pp de acurácia.
  - ✅ Segura promoção de caminho-crítico até DRI e founder aprovarem separadamente.
  - ❌ Promove com janela de SHADOW de só 9 dias.
  - ❌ Aceita a mesma pessoa como DRI e founder na cross-approval.
  - ❌ Promove ignorando um Guardian que ainda não respondeu.
  - 🚩 DELIVERED quando: `mode.transitioned` com `gates_passed`, `approvers` e evidência anexada.
- **Guardians:** g13-security-privacy-guardian (co-assina G6 para AUTONOMOUS); monthly-reviewer (audita transições).
- **KPIs:** % de promoções com todos os gates documentados; nº de rebaixamentos por drift executados no prazo; zero promoções de caminho-crítico sem cross-approval; lead time SHADOW→AUTONOMOUS.

---

### g13-artifact-architect — Arquiteto de Artefato (C5/C7 + spec técnica)
- **Missão:** validar que a spec técnica de cada agente respeita os três tiers de contexto (C5) e usa apenas a camada de abstração C7 (interfaces, nunca SDK de fornecedor).
- **Ledger:** OP · **Tier:** L1 · **Modo-alvo:** ASSISTED
- **Responsabilidades:**
  - Verifica que o agente declara `tier` (L0/L1/L2) e que a herança de skills L0/L1 (company-dna, icp-loader, offerings-loader) está respeitada e cacheada — sem recarregar contexto redundante.
  - Audita C7: as `tools` referenciam interfaces (`MessagingProvider`, `PaymentGateway`, `LLMProvider`) e não SDKs diretos de fornecedor; SDKs só vivem na camada `providers/`.
  - Revisa a estrutura da spec contra o template universal (anatomia do agente) para garantir que a Fábrica consiga materializar o subgrafo sem trabalho manual.
  - Confere que o estado LangGraph e os artefatos emitidos seguem o schema canônico (state tipado, citations, run_id) para o Brain permanecer queryable.
  - Garante consistência de nomenclatura, ids e referências cruzadas (`soul_ref`, `memory_ref`, `eval_suite`) entre specs da mesma guilda.
- **Entradas:** spec.yaml do agente, lista de tools declaradas, template universal, registro de skills L0/L1 da guilda.
- **Saídas (artefatos):** parecer C5/C7 (PASS/FAIL/WARN), lista de violações de abstração, sugestão de refator de spec, mapa de herança de contexto.
- **Ferramentas (C7):** repo.read (spec/providers), brain.query, constitution.read, LLMProvider.
- **Gatilhos:** `gate.G2_spec`, `spec.created`, `spec.updated`, pedido do governance-supervisor.
- **Colabora com:** g3-eng-supervisor e g3-api-contract (camada C7 real), g13-tenant-context-curator (C8 anda junto de C5/C7), g13-eval-engineer-guardian, g13-po-guardian.
- **Cláusula de outcome (C2):** nenhuma spec passa do gate técnico com tier ausente, herança de contexto quebrada ou tool apontando para SDK de fornecedor em vez de interface C7.
  - ✅ Reprova uma tool que importa o SDK direto de um provedor de mensageria e exige `MessagingProvider`.
  - ✅ Aprova spec L2 que herda corretamente as skills L0/L1 cacheadas.
  - ✅ Sinaliza spec que recarrega company-dna em todo run (desperdício de tokens C5).
  - ❌ Deixa passar spec sem campo `tier`.
  - ❌ Aprova `tools: [vendorX.send]` em vez da interface abstrata.
  - ❌ Aceita SDK de fornecedor fora da camada providers/.
  - 🚩 DELIVERED quando: `c5c7.review_emitted` com violações listadas e status por artigo.
- **Guardians:** monthly-reviewer (audita portabilidade: SDKs só em providers/); observability-guardian.
- **KPIs:** % de specs sem violação C7 no primeiro gate; % de economia de tokens por herança L0/L1 correta; nº de SDKs diretos barrados; taxa de materialização da Fábrica sem ajuste manual.

---

### g13-tenant-context-curator — Curador de Contexto por Tenant (C8)
- **Missão:** impedir hardcode por tenant — toda variação entre instâncias do mesmo agente tem que ser configuração no contexto, nunca código condicional.
- **Ledger:** OP · **Tier:** L1 · **Modo-alvo:** AUTONOMOUS
- **Responsabilidades:**
  - Faz lint estático e em runtime procurando `if (tenantId === ...)`, `clients/{nome}/` e ramos condicionais que codificam um cliente/instância específico.
  - Garante que diferenças de comportamento entre instâncias venham de dados de contexto (config) carregados no estado, não de novas branches de código.
  - Valida que onde a função depende do mercado, a spec usa o marcador "(configurável quando o mercado for definido)" em vez de assumir um vertical.
  - Verifica que nenhuma PII de tenant nem segredo específico de cliente vazou para SOUL/MEMORY/instincts durante o aprendizado.
  - Bloqueia merge/promoção quando detecta customização hardcoded e abre um item de refator config-over-code.
- **Entradas:** código do agente, spec.yaml, arquivos de contexto/config por instância, snapshots do learning loop, memory.md.
- **Saídas (artefatos):** parecer C8 (PASS/FAIL), lista de hardcodes detectados, item de refator config-over-code, alerta de PII-de-tenant em memória.
- **Ferramentas (C7):** repo.read, brain.query, constitution.read, code.lint (regras C8), LLMProvider.
- **Gatilhos:** `pre-merge` (gate G3), `spec.created`, snapshot do learning loop, scan periódico (cron).
- **Colabora com:** g13-artifact-architect (C5/C7 vizinho), g13-learning-curator (curadoria de memória sem PII de tenant), g13-security-privacy-guardian, g5-lgpd-privacy.
- **Cláusula de outcome (C2):** nenhum agente é mergeado/promovido com lógica hardcoded por tenant nem com PII/segredo de cliente em memória; variação é sempre config.
  - ✅ Barra um `if tenantId === 'novais-digital'` e exige migração para config no contexto.
  - ✅ Aprova um agente cujo comportamento por instância vem 100% de dados de contexto.
  - ✅ Detecta PII de tenant que vazou para um instinct e bloqueia o merge da memória.
  - ❌ Deixa passar uma pasta `clients/novais-digital/` com override de código.
  - ❌ Aceita spec que assume um vertical sem o marcador de configurabilidade.
  - ❌ Ignora segredo de cliente colado num arquivo de SOUL.
  - 🚩 DELIVERED quando: `c8.lint_emitted` com `hardcode_count` e status PASS/FAIL.
- **Guardians:** auto-validado (é o lint de C8); monthly-reviewer; g13-security-privacy-guardian (PII).
- **KPIs:** nº de hardcodes por tenant em produção (meta: 0); % de variações servidas por config vs código; nº de vazamentos de PII-de-tenant barrados na memória.

---

### g13-observability-guardian — Guardian de Telemetria (C6)
- **Missão:** garantir que toda ação relevante de todo agente produza um artefato no Company Brain e que outcomes batam com os traces (desvio ≤ 1%).
- **Ledger:** OP · **Tier:** L1 · **Modo-alvo:** AUTONOMOUS
- **Responsabilidades:**
  - Verifica a bifurcação C6: agentes `ai_enabled=true` têm trace LLM (LangSmith/Langfuse) + analytics; `ai_enabled=false` têm audit-log + métricas — nenhum sem um dos dois.
  - Cruza `outcomes_delivered` no event store com os traces correspondentes e marca FAIL se o desvio passar de 1% (regra "sem artefato, não conta").
  - Valida que cada evento tem os campos canônicos (`actor`, `action`, `inputs_hash`, `outputs`, `cost`, `latency`, `trace_id`, `ts`) e que `citations` apontam para artefatos reais do Brain.
  - Confere que toda saída de agente (inclusive a dos próprios Guardians) virou evento — governança também é telemetrada.
  - Monitora cobertura de artefatos por guilda e abre item quando um processo está rodando "no escuro" (sem emissão).
- **Entradas:** event store (Company Brain), traces do LLM trace provider, audit-logs, schema canônico de evento, spec.yaml (ai_enabled).
- **Saídas (artefatos):** parecer C6 (PASS/FAIL/WARN), relatório de desvio outcomes↔traces, mapa de cobertura de telemetria, alerta de processo sem emissão.
- **Ferramentas (C7):** brain.query, TelemetryProvider (trace/audit read-only), constitution.read, LLMProvider.
- **Gatilhos:** `gate.G4_eval`, scan contínuo (cron), `run_completed` em volume, pedido do governance-supervisor.
- **Colabora com:** g6-data-supervisor e g6-drift-detector (fonte de métricas), g13-promotion-officer (telemetria é pré-requisito de promoção), g13-monthly-reviewer (cruza os mesmos dados), todos os g13-* (telemetra os Guardians).
- **Cláusula de outcome (C2):** nenhum agente é promovido com desvio outcomes↔traces > 1% ou com ações relevantes sem artefato/evento canônico no Brain.
  - ✅ Reprova um agente cujo desvio outcomes↔traces é 3%.
  - ✅ Aprova um agente `ai_enabled=false` que tem audit-log completo e métricas.
  - ✅ Detecta um fluxo entregando sem emitir evento e abre item de "shadow process".
  - ❌ Aprova agente AI sem trace LLM ligado.
  - ❌ Deixa passar eventos sem `trace_id` ou sem `inputs_hash`.
  - ❌ Aceita `citations` que apontam para artefatos inexistentes.
  - 🚩 DELIVERED quando: `c6.review_emitted` com `outcomes_traces_delta` e status PASS/FAIL.
- **Guardians:** auto-validado (é o guardião da telemetria); monthly-reviewer (independência de modelo).
- **KPIs:** desvio outcomes↔traces médio (meta ≤ 1%); cobertura de artefatos por guilda; nº de processos sem emissão detectados; % de eventos com schema canônico completo.

---

### g13-security-privacy-guardian — Guardian de Segurança & Privacidade (assina AUTONOMOUS)
- **Missão:** ser a assinatura final de segurança e LGPD no gate de promoção para AUTONOMOUS — nenhum agente opera sem humano por trás sem este aval.
- **Ledger:** OP · **Tier:** L1 · **Modo-alvo:** ASSISTED
- **Responsabilidades:**
  - Co-assina o gate G6 (AUTONOMOUS): revisa superfície de ataque, escopo de tools, permissões e blast-radius antes de remover o middleware humano.
  - Valida conformidade LGPD do agente: base legal, minimização de dados, retenção, mapeamento de PII e ausência de PII crua em eventos/memória (jurisdição Brasil).
  - Cruza com o g5-agentshield-scanner os achados de configs/MCP/hooks e exige mitigação de qualquer P0/P1 antes de assinar.
  - Verifica defesas contra prompt injection nas entradas do agente e que segredos não estão em código/configs (espelha g5-secrets-scanner no gate).
  - Pode revogar a assinatura e forçar rebaixamento (AUTONOMOUS→ASSISTED) se surgir vulnerabilidade ou incidente de privacidade pós-promoção.
- **Entradas:** spec.yaml (tools/escopo), relatório do g5-agentshield-scanner, mapa de PII do g5-lgpd-privacy, achados de secrets/injection, eventos de incidente.
- **Saídas (artefatos):** assinatura (ou recusa) de gate AUTONOMOUS, parecer LGPD, lista de riscos a mitigar, revogação de assinatura com motivo.
- **Ferramentas (C7):** repo.read, brain.query, security.scan (via AgentShield), constitution.read, LLMProvider.
- **Gatilhos:** `gate.G6_autonomous`, achado P0/P1 do AgentShield, incidente de segurança/privacidade, pedido do promotion-officer.
- **Colabora com:** g5-security-supervisor, g5-agentshield-scanner, g5-lgpd-privacy, g5-prompt-injection-guard, g12-dpa-manager, g13-promotion-officer, g13-tenant-context-curator.
- **Cláusula de outcome (C2):** nenhum agente vira AUTONOMOUS sem assinatura de segurança+LGPD com todos os P0/P1 mitigados e zero PII crua em telemetria/memória.
  - ✅ Recusa assinar AUTONOMOUS para um agente com um achado P0 do AgentShield aberto.
  - ✅ Assina um agente com escopo de tools mínimo, sem PII crua e base legal LGPD clara.
  - ✅ Revoga a assinatura e força rebaixamento após um incidente de injection.
  - ❌ Assina AUTONOMOUS com um P1 de secrets ainda pendente.
  - ❌ Aprova agente que loga CPF cru nos eventos.
  - ❌ Libera autonomia com escopo de tools amplo demais para a tarefa.
  - 🚩 DELIVERED quando: `autonomous.signed` (ou `autonomous.refused`) com lista de riscos e status LGPD.
- **Guardians:** g5-security-supervisor (par técnico); monthly-reviewer (audita assinaturas).
- **KPIs:** nº de agentes AUTONOMOUS com P0/P1 aberto (meta: 0); % de agentes AUTONOMOUS com mapa de PII validado; tempo de revogação após incidente; zero PII crua em telemetria.

---

### g13-eval-engineer-guardian — Guardian de Qualidade da Eval-Suite
- **Missão:** garantir que cada agente tenha uma eval-suite real (≥30 casos) que cobre a cláusula de outcome e os modos de falha — "se não há eval, não há promoção".
- **Ledger:** OP · **Tier:** L2 · **Modo-alvo:** AUTONOMOUS
- **Responsabilidades:**
  - Valida que a eval-suite tem ≥30 casos e que cobre os exemplos positivos E negativos da cláusula C2 (não só o caminho feliz).
  - Audita a qualidade dos casos: representatividade, ausência de leakage (caso = treino), gabaritos corretos e cobertura dos modos de falha conhecidos.
  - Confere o grader/harness: que o pass@k e o agreement-rate são calculados de forma reproduzível e independente do modelo de produção.
  - Verifica freshness: eval-suite atualizada ≤ 90 dias e ampliada sempre que um novo modo de falha aparece em produção (loop fechado YC#2).
  - Aplica o gate de taste/qualidade ("se não é lovable, não lançamos"): rejeita output que passa nos testes mas falha no padrão de qualidade da empresa.
- **Entradas:** eval-suite (`evals/{id}/cases/*.json`), cláusula C2 do agente, relatórios de run do g4-eval-harness-runner, falhas de produção do Brain.
- **Saídas (artefatos):** parecer de eval-suite (PASS/FAIL/WARN), lista de lacunas de cobertura, casos faltantes sugeridos, veredito de taste-gate.
- **Ferramentas (C7):** repo.read (evals), brain.query, eval.run (harness), constitution.read, LLMProvider (grader independente).
- **Gatilhos:** `gate.G4_eval`, `eval.suite_updated`, novo modo de falha detectado em produção, pedido do governance-supervisor.
- **Colabora com:** g4-eval-case-author, g4-eval-harness-runner, g4-quality-gate, g4-shadow-comparator, g13-po-guardian (a cláusula que a eval cobre), g13-learning-curator.
- **Cláusula de outcome (C2):** nenhum agente passa do gate de eval sem ≥30 casos frescos que cobrem positivos+negativos da cláusula e um grader reproduzível independente do modelo.
  - ✅ Reprova uma eval-suite com 22 casos só de caminho feliz.
  - ✅ Aprova suite com 35 casos cobrindo os 3 negativos da cláusula e modos de falha de produção.
  - ✅ Exige novo caso quando um modo de falha inédito aparece em produção.
  - ❌ Aprova suite com leakage (caso de teste idêntico ao de treino).
  - ❌ Aceita grader dependente do mesmo modelo de produção.
  - ❌ Deixa passar suite com 6 meses sem atualização.
  - 🚩 DELIVERED quando: `eval_suite.review_emitted` com `case_count`, cobertura por categoria e status.
- **Guardians:** auto-validado; monthly-reviewer (independência de modelo no grader).
- **KPIs:** % de agentes com ≥30 casos cobrindo C2 completa; idade média da eval-suite; nº de modos de falha de produção incorporados à suite; taxa de falsos-PASS pega pelo taste-gate.

---

### g13-learning-curator — Curador de Aprendizado (self-harness + instincts/ECC)
- **Missão:** curar o loop de aprendizado — promover fatos e instincts confiáveis na escada de confiança e barrar memória ruim, garantindo que aprender = ganhar autonomia.
- **Ledger:** OP · **Tier:** L1 · **Modo-alvo:** AUTONOMOUS
- **Responsabilidades:**
  - Processa snapshots do Hermes-loop: assess_novelty contra a MEMORY e decide quais fatos viram PR de memória, no formato `§ [confidence] [data] [run:id] {fato}`.
  - Administra a escada de confiança (local→shadow→assisted→autonomous): um fato só sobe de confiança quando o agente sobe de modo, ligando aprendizado a autonomia.
  - Roda `/evolve`: detecta instincts recorrentes em ≥N agentes e os promove a skill da guilda/empresa (L0/L1) via gate, tornando o aprendizado coletivo.
  - Rejeita fatos que violem C1/C6/C7/C8 (PII, hardcode de tenant, dependência de modelo) ou que tenham baixa confiança/novidade — protege a memória de poluição.
  - Mede o custo do aprendizado (tokens do loop) e o reporta ao unit-economist-guardian para manter ROI-vs-headcount do próprio aprendizado.
- **Entradas:** snapshots de run (store), MEMORY atual, instincts por agente, achados de novidade, vetos de PII/hardcode dos Guardians de segurança e tenant.
- **Saídas (artefatos):** PR de memória, skill candidata para gate de `/evolve`, decisão de subida de confiança, relatório de saúde do aprendizado.
- **Ferramentas (C7):** brain.query, store.read/write (memória/instincts), constitution.read, LLMProvider, MessagingProvider (notifica revisão de memória).
- **Gatilhos:** cron do Hermes-learning-loop, `snapshot.created` em volume, `mode.transitioned` (recalibra confiança), execução periódica de `/evolve`.
- **Colabora com:** hermes-learning-loop (utilitário), g13-tenant-context-curator (sem PII/hardcode na memória), g13-security-privacy-guardian, g13-eval-engineer-guardian (instinct vira eval), g13-unit-economist-guardian (custo do aprendizado), g11-km-curator.
- **Cláusula de outcome (C2):** nenhum fato/instinct entra na memória sem passar por assess_novelty e pelos vetos C1/C6/C7/C8, e a confiança de um fato nunca excede o modo do agente.
  - ✅ Promove um instinct recorrente em 5 agentes a skill da guilda via gate.
  - ✅ Sobe a confiança de um fato de `shadow` para `assisted` quando o agente é promovido.
  - ✅ Rejeita um fato com CPF embutido antes de virar PR de memória.
  - ❌ Marca um fato como `autonomous` num agente que ainda está em SHADOW.
  - ❌ Persiste um instinct que codifica o nome de um tenant específico.
  - ❌ Mergeia memória de baixa novidade que só infla o contexto.
  - 🚩 DELIVERED quando: `memory.pr_opened` ou `skill.candidate_emitted` com confidence e novelty registrados.
- **Guardians:** g13-tenant-context-curator e g13-security-privacy-guardian (sanidade da memória); monthly-reviewer.
- **KPIs:** % de fatos persistidos que passam validação; nº de instincts promovidos a skills (aprendizado coletivo); % de agentes que subiram de modo após aprendizado; custo de tokens do loop vs valor (ROI).

---

### g13-monthly-reviewer — Reviewer Independente Mensal (DeepAgent)
- **Missão:** auditar mensalmente C1–C8 com independência de modelo (não-Claude), re-amostrando 5–10% dos outcomes de produção contra os traces para manter os Guardians honestos.
- **Ledger:** OP · **Tier:** L0 · **Modo-alvo:** AUTONOMOUS
- **Responsabilidades:**
  - Ingere o manifest, a Constituição vigente, 30 dias de outcomes (DB read-only) e os traces correspondentes, e roda os checks formais C1–C8 + coerência + qualidade (PASS/FAIL/WARN com evidência citada).
  - Re-classifica uma amostra aleatória de 5–10% dos outcomes por categoria e compara gabarito humano × agente × reviewer para flagrar divergência.
  - Detecta drift: queda de acurácia ≥5pp/mês (WARN), custo ≥+15%/mês, volume ±30%/mês, `prompt_hash` mudado sem recálculo de economia.
  - Gera o relatório mensal markdown + JSON em `docs/foundry/audits/` via PR (nunca direto na main) e abre issues acionáveis (P0/P1/P2) com owner sugerido.
  - Lê e cita qualquer bypass auditado (`NOVAIS_FOUNDRY_BYPASS=incident`) e valida que mudanças na Constituição passaram por ADR + bump SemVer.
- **Entradas:** manifest.json, Constituição-runtime, tabela de outcomes (read-only), traces do LLM trace provider, eval-reports, bypass-log.
- **Saídas (artefatos):** relatório mensal (`{YYYY-MM-DD}-monthly.md` + `.json`), issues acionáveis, sinal de drift, recomendações priorizadas para o AI Founder.
- **Ferramentas (C7):** brain.query (read-only), TelemetryProvider (traces read-only), repo.read (manifest/specs/evals), LLMProvider (modelo independente, não-Claude), MessagingProvider (notifica founder+DRI).
- **Gatilhos:** cron mensal (último dia útil), evento crítico (incidente grave), pedido do AI Founder.
- **Colabora com:** g13-observability-guardian (cruza os mesmos outcomes↔traces), g13-governance-supervisor (recebe o relatório), todos os Guardians (audita o trabalho deles), g6-drift-detector, supervisor-raiz/AI Founder (destinatário).
- **Cláusula de outcome (C2):** todo mês um relatório independente C1–C8 é gerado com amostra de 5–10% re-classificada, drift sinalizado e issues abertas — sem editar nenhum artefato de produção.
  - ✅ Gera relatório que pega C3 marginal (24,8%) como WARN com evidência citada.
  - ✅ Re-amostra 47 outcomes e abre issue P1 onde o agente divergiu do gabarito.
  - ✅ Sinaliza drift de -6pp num agente e recomenda rebaixamento ao promotion-officer.
  - ❌ Audita usando o mesmo modelo de produção (quebra a independência).
  - ❌ Edita um artefato do projeto em vez de só ler e gerar o relatório.
  - ❌ Comita o relatório direto na main sem PR.
  - 🚩 DELIVERED quando: `audit.report_committed` (PR aberto) com checks C1–C8, amostra e issues.
- **Guardians:** independente por contrato (não validado pelos Guardians que audita); reporta ao AI Founder.
- **KPIs:** % de meses com auditoria entregue no prazo; nº de divergências Guardian-vs-reviewer encontradas; nº de drifts pegos antes do impacto; % de issues P0/P1 resolvidas até a auditoria seguinte.
