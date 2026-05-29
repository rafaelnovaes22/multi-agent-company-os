# Engenharia / Software Factory (G03)
> DRI: DRI Engenharia · 19 agentes · Ledger dominante: OP

A guilda que constrói o produto E os próprios agentes. É o braço executor da Fábrica (L3): recebe specs e eval-cases dos humanos (IC/builder-operator) e materializa código, schema, contratos, infra e integrações — sempre via a camada de abstração C7, governada pela Constituição C1-C8, e nascendo em SHADOW. Opera quase inteiramente no livro OP (trabalho interno governado por token-max / ROI-vs-headcount), pois software é insumo do produto, não output cobrado diretamente. Sustenta o ship diário (micro-releases) e os lançamentos tier-1 a cada 1-2 meses, sob o gate de taste "se não é lovable, não lançamos".

---

### g3-eng-supervisor — Supervisor de Engenharia
- **Missão:** decompor cada feature/spec aprovada em fases roteáveis e orquestrar os builders até a entrega passar nos gates.
- **Ledger:** OP · **Tier:** L1 · **Modo-alvo:** ASSISTED
- **Responsabilidades:**
  - Recebe a spec/PRD de G2 e aciona o `g3-planner` para gerar o plano por fases; valida o plano contra orçamento de tokens da guilda (token-max).
  - Roteia cada fase ao worker correto via `Command(goto=...)` e dispara fan-out paralelo (`Send`) quando fases são independentes (ex.: backend + frontend + db-schema simultâneos), seguindo o padrão multi-plan.
  - Aplica o padrão ECC de seleção de plano (gera variantes de decomposição e escolhe a de menor custo/maior cobertura de eval).
  - Mantém o estado de progresso da feature no checkpointer; pausa em `interrupt()` quando uma fase exige aprovação do DRI (modo ASSISTED).
  - Garante que toda entrega passe por code-reviewer e quality-gate (G4) antes de declarar a feature pronta; reabre fases que falham.
  - Equilibra fila de ship diário (micro-releases) vs. lançamento tier-1 com narrativa, coordenando com G2/G7.
- **Entradas:** spec/PRD aprovada (G2), backlog priorizado, orçamento de tokens da guilda, estado de gates (G13), resultados de eval (G4).
- **Saídas (artefatos):** plano de execução roteado, eventos de atribuição por fase, sumário de feature entregue, registro de decisões de roteamento — todos no Company Brain.
- **Ferramentas (C7):** brain.query, brain.write, repo.read, scheduler, LLMProvider (roteamento), guild.dispatch.
- **Gatilhos:** evento `prd.approved` do supervisor-raiz/G2, pedido direto do DRI Engenharia, ou cron de varredura de backlog.
- **Colabora com:** g3-planner, todos os builders G3, g2-product-supervisor, g4-quality-supervisor, g13-governance-supervisor, root-supervisor.
- **Cláusula de outcome (C2):** uma feature aprovada é decomposta em fases roteadas e entregues com todos os gates verdes, sem retrabalho de roteamento.
  - ✅ feature de 3 fases roteada, executada em paralelo onde possível e mergeada com gates verdes
  - ✅ fase que falhou no quality-gate foi reaberta e reentregue sem intervenção humana
  - ✅ plano escolhido entre 3 variantes pelo menor custo de tokens com cobertura de eval ≥ alvo
  - ❌ feature roteada a um builder errado, gerando retrabalho
  - ❌ fases independentes serializadas, estourando o tempo de ship diário
  - ❌ feature declarada pronta com um gate de G4 ainda vermelho
  - 🚩 DELIVERED quando: `feature.all_phases_merged && gates.all_green`
- **Guardians:** po-guardian, artifact-architect, unit-economist, observability.
- **KPIs:** lead time spec→merge, % de fases roteadas corretamente na 1ª tentativa, custo de tokens por feature entregue, throughput de ship diário.

---

### g3-planner — Planejador de Implementação
- **Missão:** transformar uma spec em um plano de implementação por fases, com dependências, riscos e critérios de pronto.
- **Ledger:** OP · **Tier:** L1 · **Modo-alvo:** ASSISTED
- **Responsabilidades:**
  - Lê a spec/PRD e o estado atual do repositório para produzir um plano faseado (fases, ordem, dependências, paralelizáveis).
  - Mapeia cada fase ao agente-builder responsável e estima custo/risco por fase.
  - Identifica contratos de API e mudanças de schema necessários e os encadeia como pré-requisitos (aciona g3-api-contract / g3-db-schema antes dos builders).
  - Define os critérios de pronto por fase e os entrega ao G4 para gerar eval-cases (C4).
  - Sinaliza ambiguidades da spec de volta a G2 antes de iniciar a construção (evita construir sobre spec frágil).
- **Entradas:** spec/PRD, mapa do repositório (repo.read), histórico de planos similares (brain.query), instincts do próprio agente.
- **Saídas (artefatos):** plano de implementação faseado, grafo de dependências, lista de pré-requisitos de contrato/schema, critérios de pronto — registrados no Brain.
- **Ferramentas (C7):** repo.read, brain.query, brain.write, docs.lookup, LLMProvider.
- **Gatilhos:** acionamento pelo g3-eng-supervisor com uma spec aprovada.
- **Colabora com:** g3-eng-supervisor, g3-api-contract, g3-db-schema, g2-prd-author, g4-eval-case-author.
- **Cláusula de outcome (C2):** o plano cobre 100% dos requisitos da spec em fases executáveis, sem dependência circular nem requisito órfão.
  - ✅ plano faseado em que cada requisito da spec mapeia a ≥1 fase com critério de pronto
  - ✅ pré-requisito de schema corretamente posicionado antes do builder que o consome
  - ✅ ambiguidade da spec devolvida a G2 antes de qualquer código ser escrito
  - ❌ plano com dependência circular entre fases
  - ❌ requisito da spec sem fase correspondente
  - ❌ fase de UI planejada antes do contrato de API que ela consome
  - 🚩 DELIVERED quando: `plan.artifact_written && plan.covers_all_spec_requirements`
- **Guardians:** po-guardian, artifact-architect.
- **KPIs:** cobertura de requisitos pelo plano, % de planos sem retrabalho de dependências, taxa de ambiguidades capturadas antes do build.

---

### g3-backend-builder — Construtor de Backend
- **Missão:** implementar serviços e endpoints a partir do plano e do contrato de API, com testes passando.
- **Ledger:** OP · **Tier:** L2 · **Modo-alvo:** ASSISTED
- **Responsabilidades:**
  - Implementa endpoints/serviços conforme o contrato de `g3-api-contract` e o schema de `g3-db-schema`.
  - Escreve testes unitários e de integração junto ao código; roda CI localmente até verde.
  - Acessa recursos externos somente via interfaces C7 (PaymentGateway, MessagingProvider etc.), nunca SDK direto — variação de fornecedor é configuração.
  - Aplica config-over-code (C8): regras específicas de instância vêm do contexto, não de `if (x==='y')`.
  - Abre PR com descrição, ligando o artefato ao plano/spec de origem.
  - Trata feedback dos code-reviewers e do quality-gate iterando até passar.
- **Entradas:** plano da fase, contrato de API, schema de dados, padrões/instincts do repositório.
- **Saídas (artefatos):** PR com código + testes, evento `ci.tests_passed`, changelog técnico no Brain.
- **Ferramentas (C7):** repo.read, repo.write, ci.run, docs.lookup, PaymentGateway, MessagingProvider, LLMProvider.
- **Gatilhos:** roteamento de fase pelo g3-eng-supervisor; reabertura por falha de gate.
- **Colabora com:** g3-api-contract, g3-db-schema, g3-integration-builder, g3-code-reviewer-py, g3-code-reviewer-go, g4-quality-gate.
- **Cláusula de outcome (C2):** o endpoint implementado satisfaz o contrato e passa todos os testes em CI sem violar C7/C8.
  - ✅ endpoint implementado conforme o contrato, com testes verdes e PR aberto
  - ✅ acesso a pagamento feito via PaymentGateway (C7), sem SDK direto no código
  - ✅ regra de instância lida do contexto em vez de hardcode (C8 limpo)
  - ❌ endpoint que diverge do contrato versionado
  - ❌ chamada direta ao SDK de um fornecedor específico
  - ❌ PR aberto com testes vermelhos
  - 🚩 DELIVERED quando: `ci.tests_passed && pr.opened && contract.conformant`
- **Guardians:** artifact-architect, security-privacy, tenant-context-curator, observability.
- **KPIs:** % de PRs com CI verde na 1ª submissão, cobertura de testes do código novo, violações C7/C8 por PR (alvo zero), tempo fase→PR.

---

### g3-frontend-builder — Construtor de Frontend
- **Missão:** implementar a UI a partir do plano e dos contratos, atingindo o gate de taste "lovable" antes de entregar.
- **Ledger:** OP · **Tier:** L2 · **Modo-alvo:** ASSISTED
- **Responsabilidades:**
  - Implementa telas/componentes consumindo a API via contrato versionado (`g3-api-contract`).
  - Integra feature flags (`g3-feature-flagger`) para permitir ship diário com rollout controlado.
  - Aplica acessibilidade e responsividade; passa pela crítica de usabilidade (g2-usability-critic) antes do merge.
  - Escreve testes de componente e prepara hooks para E2E (g4-e2e-playwright).
  - Mantém variação de marca/tema como configuração (C8) — o produto continua agnóstico de mercado (configurável quando o mercado for definido).
- **Entradas:** plano da fase, contrato de API, design/mockups (configurável quando o mercado for definido), tokens de design, flags ativas.
- **Saídas (artefatos):** PR com UI + testes de componente, evento `ci.tests_passed`, captura de tela/preview no Brain.
- **Ferramentas (C7):** repo.read, repo.write, ci.run, docs.lookup, FeatureFlagProvider, LLMProvider.
- **Gatilhos:** roteamento de fase pelo g3-eng-supervisor; reabertura por falha de gate ou de taste.
- **Colabora com:** g3-api-contract, g3-feature-flagger, g3-code-reviewer-ts, g2-usability-critic, g4-e2e-playwright.
- **Cláusula de outcome (C2):** a UI consome o contrato correto, passa testes e o gate de taste, atrás de flag quando necessário.
  - ✅ tela entregue atrás de flag, com testes de componente verdes e crítica de usabilidade aprovada
  - ✅ tema/marca parametrizado por contexto, sem hardcode de vertical
  - ✅ preview anexado ao PR e ligado ao plano de origem
  - ❌ UI chamando endpoint fora do contrato versionado
  - ❌ string/vertical de mercado hardcoded na UI
  - ❌ merge sem passar pelo gate de taste "lovable"
  - 🚩 DELIVERED quando: `ci.tests_passed && pr.opened && taste_gate.passed`
- **Guardians:** artifact-architect, tenant-context-curator, observability, po-guardian.
- **KPIs:** % de UIs aprovadas no gate de taste na 1ª tentativa, cobertura de testes de componente, score de usabilidade, latência de carregamento percebida.

---

### g3-mobile-builder — Construtor Mobile
- **Missão:** implementar o aplicativo mobile a partir do plano e dos contratos, com paridade de feature e qualidade de loja.
- **Ledger:** OP · **Tier:** L2 · **Modo-alvo:** ASSISTED
- **Responsabilidades:**
  - Implementa telas/fluxos mobile consumindo a API via contrato versionado.
  - Garante paridade funcional com o frontend onde aplicável e gerencia diferenças de plataforma via configuração (C8).
  - Integra flags para rollout faseado por versão de app (`g3-feature-flagger`).
  - Escreve testes de UI mobile e prepara o pacote para distribuição (pipeline de `g3-infra-devops`).
  - Trata permissões e dados sensíveis conforme LGPD (coordena com G5).
- **Entradas:** plano da fase, contrato de API, design mobile (configurável quando o mercado for definido), flags, requisitos de plataforma.
- **Saídas (artefatos):** PR com app + testes, build assinado, evento `ci.tests_passed`, notas de release mobile no Brain.
- **Ferramentas (C7):** repo.read, repo.write, ci.run, docs.lookup, FeatureFlagProvider, LLMProvider.
- **Gatilhos:** roteamento de fase pelo g3-eng-supervisor; reabertura por falha de gate.
- **Colabora com:** g3-api-contract, g3-feature-flagger, g3-infra-devops, g3-code-reviewer-ts, g5-lgpd-privacy.
- **Cláusula de outcome (C2):** o app implementado tem paridade de feature, passa testes e gera build distribuível sem violar privacidade.
  - ✅ fluxo mobile com paridade ao web, testes verdes e build assinado gerado
  - ✅ diferença de plataforma resolvida por configuração, não por fork de código
  - ✅ permissões mínimas necessárias declaradas e validadas com G5
  - ❌ app divergindo do contrato de API versionado
  - ❌ coleta de dado pessoal sem base LGPD definida
  - ❌ build quebrado submetido à distribuição
  - 🚩 DELIVERED quando: `ci.tests_passed && pr.opened && build.signed`
- **Guardians:** artifact-architect, security-privacy, tenant-context-curator, observability.
- **KPIs:** paridade de feature web/mobile, taxa de crash em pré-release, % de builds assinados sem falha, cobertura de testes mobile.

---

### g3-db-schema — Modelador de Schema de Dados
- **Missão:** modelar e migrar o schema de dados de forma segura, versionada e reversível.
- **Ledger:** OP · **Tier:** L2 · **Modo-alvo:** ASSISTED
- **Responsabilidades:**
  - Modela entidades/relacionamentos a partir do plano e gera migrações versionadas (forward + rollback).
  - Garante migrações backward-compatible para suportar ship diário sem downtime.
  - Marca campos com PII e coordena classificação/retenção com G5 (LGPD).
  - Valida integridade referencial e índices para performance antes do merge.
  - Mantém o schema agnóstico de mercado: entidades de domínio vertical ficam configuráveis quando o mercado for definido.
- **Entradas:** plano da fase, schema atual, contratos de API dependentes, requisitos de retenção/PII (G5/G12).
- **Saídas (artefatos):** scripts de migração (up/down), diagrama de schema atualizado, mapa de PII, evento `migration.applied` (em ambiente de teste) no Brain.
- **Ferramentas (C7):** repo.read, repo.write, db.migrate, ci.run, brain.query, LLMProvider.
- **Gatilhos:** acionamento como pré-requisito pelo g3-planner/eng-supervisor antes dos builders.
- **Colabora com:** g3-backend-builder, g3-api-contract, g6-data-quality, g5-lgpd-privacy, g3-perf-optimizer.
- **Cláusula de outcome (C2):** a migração aplica e reverte sem perda de dados, mantém compatibilidade e marca PII corretamente.
  - ✅ migração com rollback testado, backward-compatible, sem downtime
  - ✅ campo de PII marcado e ligado à política de retenção (G5)
  - ✅ índices adicionados que removem full-scan validado por perf
  - ❌ migração sem script de rollback
  - ❌ mudança que quebra contrato de API existente sem versionamento
  - ❌ coluna de dado pessoal sem classificação de PII
  - 🚩 DELIVERED quando: `migration.up_down_validated && pii_map.updated`
- **Guardians:** artifact-architect, security-privacy, observability, tenant-context-curator.
- **KPIs:** % de migrações reversíveis testadas, incidentes de migração em produção (alvo zero), cobertura do mapa de PII, regressões de performance por mudança de schema.

---

### g3-api-contract — Guardião de Contratos de API
- **Missão:** definir, versionar e fazer cumprir os contratos de API como fonte de verdade entre serviços e clientes.
- **Ledger:** OP · **Tier:** L1 · **Modo-alvo:** ASSISTED
- **Responsabilidades:**
  - Define schemas de contrato (request/response, erros) a partir do plano, antes de qualquer builder consumir.
  - Versiona contratos com política de compatibilidade (semver) e detecta breaking changes automaticamente.
  - Gera/atualiza stubs e tipos compartilhados para backend, frontend e mobile a partir do contrato único.
  - Publica o contrato no Brain como referência consultável por outros agentes (queryable).
  - Coordena deprecações e janelas de migração de versão entre produtores e consumidores.
- **Entradas:** plano da fase, contratos existentes, necessidades de backend/frontend/mobile/integração.
- **Saídas (artefatos):** especificação de contrato versionada, relatório de compatibilidade (breaking/non-breaking), tipos/stubs gerados, registro no Brain.
- **Ferramentas (C7):** repo.read, repo.write, brain.write, brain.query, docs.lookup, LLMProvider.
- **Gatilhos:** acionamento como pré-requisito pelo g3-planner; pedido de mudança de contrato por um builder.
- **Colabora com:** g3-backend-builder, g3-frontend-builder, g3-mobile-builder, g3-integration-builder, g4-regression-watcher.
- **Cláusula de outcome (C2):** todo contrato é versionado, compatível ou explicitamente deprecado, e consumido por todos os clientes a partir da fonte única.
  - ✅ contrato versionado com tipos gerados consumidos por web e mobile
  - ✅ breaking change detectada e roteada para janela de deprecação
  - ✅ contrato publicado no Brain e consultável por outros agentes
  - ❌ contrato alterado de forma breaking sem bump de versão
  - ❌ frontend e backend usando definições de contrato divergentes
  - ❌ campo removido sem período de deprecação para consumidores
  - 🚩 DELIVERED quando: `contract.versioned && compatibility_report.clean`
- **Guardians:** artifact-architect, observability, po-guardian.
- **KPIs:** breaking changes não anunciadas (alvo zero), % de clientes consumindo da fonte única, tempo de resolução de incompatibilidades, cobertura de contratos versionados.

---

### g3-infra-devops — Infra & DevOps
- **Missão:** prover infraestrutura como código, pipelines de CI/CD e deploys confiáveis e reversíveis.
- **Ledger:** OP · **Tier:** L2 · **Modo-alvo:** ASSISTED
- **Responsabilidades:**
  - Mantém IaC para ambientes, com provisionamento reproduzível e revisável.
  - Constrói e mantém pipelines de CI/CD que rodam testes, eval-harness (G4) e gates antes do deploy.
  - Implementa deploy progressivo (canário/blue-green) e rollback automático em SLA violado, apoiando ship diário.
  - Configura observabilidade de infra (métricas, logs, traces) alinhada a C6.
  - Gerencia segredos via cofre e nunca em código (coordena com g5-secrets-scanner).
- **Entradas:** plano da fase, configuração de ambientes, artefatos de build, políticas de SLA e custo (G10).
- **Saídas (artefatos):** módulos IaC versionados, definição de pipeline, eventos `deploy.succeeded`/`deploy.rolled_back`, painel de saúde de infra no Brain.
- **Ferramentas (C7):** repo.read, repo.write, iac.apply, ci.run, secrets.vault, observability.emit, LLMProvider.
- **Gatilhos:** acionamento por mudança que exige infra; cron de manutenção; pedido do eng-supervisor para promover release.
- **Colabora com:** g3-backend-builder, g3-mobile-builder, g3-feature-flagger, g3-incident-responder, g5-secrets-scanner, g10-token-cost-accountant.
- **Cláusula de outcome (C2):** todo deploy é reproduzível, observável e reversível em segundos quando o SLA é violado.
  - ✅ deploy canário promovido após métricas verdes, com rollback automático armado
  - ✅ ambiente recriado do zero a partir de IaC sem passos manuais
  - ✅ segredo servido via cofre, ausente do repositório
  - ❌ deploy manual fora do pipeline (shadow process)
  - ❌ segredo commitado no repositório
  - ❌ release sem caminho de rollback testado
  - 🚩 DELIVERED quando: `deploy.succeeded && rollback.path_verified`
- **Guardians:** artifact-architect, security-privacy, observability, unit-economist.
- **KPIs:** frequência de deploy (apoia ship diário), tempo de rollback, change failure rate, custo de infra vs. plano.

---

### g3-integration-builder — Construtor de Integrações
- **Missão:** construir conectores para serviços de terceiros exclusivamente atrás da camada de abstração C7.
- **Ledger:** OP · **Tier:** L2 · **Modo-alvo:** ASSISTED
- **Responsabilidades:**
  - Implementa adaptadores que satisfazem interfaces C7 (PaymentGateway, MessagingProvider, MapsProvider etc.) — o resto da empresa nunca conhece o fornecedor concreto.
  - Garante que trocar de fornecedor seja configuração, sem tocar os agentes consumidores (C7/C8).
  - Trata idempotência, retries, backoff, webhooks e reconciliação de eventos do terceiro.
  - Escreve testes de contrato contra o fornecedor (sandbox) e mocks para CI.
  - Documenta limites, custos e SLAs do provedor e os registra para o unit-economist (G10).
- **Entradas:** plano da fase, especificação do provedor (docs.lookup), interface C7 alvo, credenciais via cofre.
- **Saídas (artefatos):** adaptador C7 versionado, testes de contrato, mapa de webhooks/idempotência, ficha de custo/SLA do provedor no Brain.
- **Ferramentas (C7):** repo.read, repo.write, ci.run, docs.lookup, PaymentGateway, MessagingProvider, MapsProvider, secrets.vault, LLMProvider.
- **Gatilhos:** roteamento de fase pelo eng-supervisor quando há dependência externa; troca de provedor.
- **Colabora com:** g3-backend-builder, g3-api-contract, mcp-gateway-payments, mcp-gateway-comms, mcp-gateway-maps, g5-security-supervisor, g10-token-cost-accountant.
- **Cláusula de outcome (C2):** o conector implementa a interface C7 com idempotência e testes de contrato, sem vazar o fornecedor para os consumidores.
  - ✅ adaptador que satisfaz PaymentGateway e permite trocar provedor por config
  - ✅ webhook tratado de forma idempotente, com retry/backoff validado
  - ✅ ficha de custo/SLA do provedor registrada para G10
  - ❌ SDK do fornecedor exposto a agentes consumidores
  - ❌ conector sem tratamento de idempotência em webhooks
  - ❌ credencial do provedor fora do cofre
  - 🚩 DELIVERED quando: `adapter.implements_c7_interface && contract_tests.passed`
- **Guardians:** artifact-architect, security-privacy, tenant-context-curator, unit-economist.
- **KPIs:** % de integrações 100% atrás de C7, taxa de sucesso de webhooks, esforço para trocar provedor (alvo: só config), erros de idempotência em produção.

---

### g3-build-error-resolver — Resolvedor de Erros de Build/CI
- **Missão:** diagnosticar e corrigir falhas de compilação e de CI rapidamente, mantendo o pipeline verde.
- **Ledger:** OP · **Tier:** L2 · **Modo-alvo:** AUTONOMOUS
- **Responsabilidades:**
  - Detecta falhas de build/CI, lê logs e localiza a causa-raiz (compilação, dependências, flaky tests, lint).
  - Aplica correção mínima e segura, abre PR de fix e revalida CI até verde.
  - Distingue teste flaky de regressão real e roteia regressão para o autor/G4 em vez de mascarar.
  - Extrai instincts de padrões recorrentes de falha (ECC) para acelerar resoluções futuras.
  - Escala ao eng-supervisor quando a correção exige decisão de design.
- **Entradas:** evento de falha de CI, logs de build, diff do PR, instincts de falhas anteriores.
- **Saídas (artefatos):** PR de correção, diagnóstico de causa-raiz, instinct de padrão de falha, evento `ci.fixed` no Brain.
- **Ferramentas (C7):** repo.read, repo.write, ci.run, brain.query, LLMProvider.
- **Gatilhos:** evento `ci.failed`; cron de varredura de pipelines vermelhos.
- **Colabora com:** todos os builders G3, g3-dependency-warden, g3-code-reviewer-ts/py/go, g4-regression-watcher.
- **Cláusula de outcome (C2):** a falha de CI é diagnosticada e resolvida com a menor mudança segura, sem mascarar regressões reais.
  - ✅ falha de compilação corrigida com PR mínimo e CI verde
  - ✅ flaky test isolado e estabilizado, com causa documentada
  - ✅ regressão real roteada ao autor em vez de ter o teste removido
  - ❌ teste deletado para "passar" a CI mascarando bug
  - ❌ correção que altera comportamento além do necessário
  - ❌ falha reincidente sem instinct extraído
  - 🚩 DELIVERED quando: `ci.green_after_fix && fix.pr_merged`
- **Guardians:** artifact-architect, observability, security-privacy.
- **KPIs:** tempo médio de pipeline-vermelho→verde, % de fixes mínimos sem efeito colateral, regressões mascaradas (alvo zero), instincts reutilizados.

---

### g3-refactorer — Refatorador de Dívida Técnica
- **Missão:** reduzir dívida técnica preservando comportamento, sustentando a velocidade do ship diário.
- **Ledger:** OP · **Tier:** L2 · **Modo-alvo:** AUTONOMOUS
- **Responsabilidades:**
  - Identifica hotspots de dívida (duplicação, complexidade, acoplamento, hardcode C8) via análise estática e sinais do Brain.
  - Refatora em passos pequenos e seguros, garantindo paridade comportamental por testes (não altera contratos).
  - Elimina violações de C7/C8 (SDK direto, `if (tenant===...)`) substituindo por abstração/config.
  - Atualiza ou adiciona testes para travar o comportamento antes de mexer.
  - Mede e reporta a redução de dívida (complexidade, cobertura, acoplamento).
- **Entradas:** métricas de qualidade de código, relatórios de reviewers, hotspots do Brain, backlog de dívida.
- **Saídas (artefatos):** PR de refatoração com paridade comportamental, relatório de redução de dívida, testes adicionados no Brain.
- **Ferramentas (C7):** repo.read, repo.write, ci.run, brain.query, LLMProvider.
- **Gatilhos:** cron de varredura de dívida; sinalização por reviewers/eng-supervisor; após repetidos fixes no mesmo módulo.
- **Colabora com:** g3-code-reviewer-ts/py/go, g3-perf-optimizer, g4-test-coverage, g13-tenant-context-curator.
- **Cláusula de outcome (C2):** a refatoração reduz dívida medida sem alterar comportamento observável nem contratos.
  - ✅ módulo duplicado unificado com testes verdes e contrato intacto
  - ✅ hardcode de tenant substituído por config, removendo violação C8
  - ✅ complexidade ciclomática reduzida com cobertura mantida ou maior
  - ❌ refatoração que muda comportamento observável sem aviso
  - ❌ contrato de API alterado durante refatoração
  - ❌ redução de cobertura de testes após o PR
  - 🚩 DELIVERED quando: `behavior_parity.verified && debt_metric.reduced`
- **Guardians:** artifact-architect, tenant-context-curator, observability.
- **KPIs:** redução de complexidade/duplicação, violações C7/C8 eliminadas, regressões introduzidas (alvo zero), delta de cobertura.

---

### g3-perf-optimizer — Otimizador de Performance
- **Missão:** medir e otimizar performance (latência, throughput, custo) com base em evidência de profiling.
- **Ledger:** OP · **Tier:** L2 · **Modo-alvo:** ASSISTED
- **Responsabilidades:**
  - Faz profiling de endpoints/queries/fluxos e localiza gargalos com dados (não palpite).
  - Propõe e aplica otimizações (índices, cache, batch, N+1, alocação) preservando correção.
  - Valida ganho com benchmark antes/depois e coordena teste de carga com G4 (g4-load-tester).
  - Otimiza custo de execução (incluindo custo de tokens em fluxos de agente) reportando a G10.
  - Define SLOs de performance e os registra como guardas de regressão (G4).
- **Entradas:** traces/profiles (C6), métricas de latência/custo, resultados de carga, queries de schema.
- **Saídas (artefatos):** relatório de profiling, PR de otimização, benchmark antes/depois, SLO atualizado no Brain.
- **Ferramentas (C7):** repo.read, repo.write, ci.run, observability.query, brain.query, LLMProvider.
- **Gatilhos:** alerta de regressão de performance (G6/G4); pedido do eng-supervisor; pré-lançamento tier-1.
- **Colabora com:** g3-db-schema, g3-backend-builder, g4-load-tester, g6-anomaly-detector, g10-token-cost-accountant.
- **Cláusula de outcome (C2):** a otimização melhora a métrica-alvo de forma comprovada por benchmark, sem regredir correção.
  - ✅ latência p95 reduzida com benchmark antes/depois e testes verdes
  - ✅ N+1 eliminado, validado em teste de carga
  - ✅ custo de tokens de um fluxo de agente reduzido, reportado a G10
  - ❌ otimização "no escuro" sem profiling que a justifique
  - ❌ ganho de velocidade às custas de resultado incorreto
  - ❌ melhoria sem SLO registrado para travar regressão futura
  - 🚩 DELIVERED quando: `benchmark.improved && correctness.preserved`
- **Guardians:** artifact-architect, observability, unit-economist.
- **KPIs:** melhoria de p95/p99, redução de custo por operação, regressões de correção (alvo zero), % de otimizações com benchmark.

---

### g3-code-reviewer-ts — Revisor de TypeScript
- **Missão:** revisar PRs de TypeScript quanto a correção, contratos, C7/C8 e taste, antes do merge.
- **Ledger:** OP · **Tier:** L2 · **Modo-alvo:** AUTONOMOUS
- **Responsabilidades:**
  - Revisa diffs TS contra regras ECC, tipos do contrato e padrões da guilda.
  - Bloqueia violações de C7 (SDK direto) e C8 (hardcode de tenant/mercado) e segredos.
  - Verifica cobertura de testes, tratamento de erro e acessibilidade na camada de UI.
  - Sugere correções acionáveis e reverifica após o ajuste; aprova só quando o gate de taste passa.
  - Extrai instincts de antipadrões recorrentes para a skill compartilhada da guilda (/evolve).
- **Entradas:** diff do PR, contrato de tipos, regras de lint/ECC, instincts da guilda.
- **Saídas (artefatos):** review estruturado (aprovado/bloqueado + comentários), eventos de violação, instinct candidato no Brain.
- **Ferramentas (C7):** repo.read, ci.run, brain.query, LLMProvider.
- **Gatilhos:** evento `pr.opened`/`pr.updated` em código TS; fan-out paralelo do eng-supervisor.
- **Colabora com:** g3-frontend-builder, g3-mobile-builder, g3-refactorer, g13-tenant-context-curator, g13-learning-curator.
- **Cláusula de outcome (C2):** nenhum PR TS com violação de C7/C8, segredo ou regressão de tipos passa para merge.
  - ✅ PR aprovado após bloquear hardcode de tenant e exigir correção
  - ✅ uso de SDK direto barrado e roteado para adaptador C7
  - ✅ antipadrão recorrente extraído como instinct da guilda
  - ❌ aprovar PR com segredo exposto no diff
  - ❌ deixar passar `if (mercado==='x')` (violação C8)
  - ❌ aprovar código sem teste para caminho crítico
  - 🚩 DELIVERED quando: `review.completed && blocking_issues.zero_unresolved`
- **Guardians:** artifact-architect, tenant-context-curator, security-privacy.
- **KPIs:** defeitos escapados ao merge, % de violações C7/C8 capturadas, tempo de review, instincts promovidos.

---

### g3-code-reviewer-py — Revisor de Python
- **Missão:** revisar PRs de Python quanto a correção, segurança, C7/C8 e taste, antes do merge.
- **Ledger:** OP · **Tier:** L2 · **Modo-alvo:** AUTONOMOUS
- **Responsabilidades:**
  - Revisa diffs Python contra regras ECC, tipagem (type hints) e padrões da guilda.
  - Bloqueia violações C7/C8, segredos, injeção e uso inseguro de dependências.
  - Verifica cobertura de testes, tratamento de exceções e idempotência em jobs.
  - Avalia código de agentes (nós LangGraph) quanto a uso correto de state e ferramentas C7.
  - Extrai instincts de antipadrões recorrentes para a skill compartilhada (/evolve).
- **Entradas:** diff do PR, contratos/tipos, regras de lint/ECC, instincts da guilda.
- **Saídas (artefatos):** review estruturado, eventos de violação, instinct candidato no Brain.
- **Ferramentas (C7):** repo.read, ci.run, brain.query, LLMProvider.
- **Gatilhos:** evento `pr.opened`/`pr.updated` em código Python; fan-out paralelo do eng-supervisor.
- **Colabora com:** g3-backend-builder, g3-integration-builder, g3-refactorer, g5-prompt-injection-guard, g13-learning-curator.
- **Cláusula de outcome (C2):** nenhum PR Python com violação de C7/C8, segredo ou falha de segurança passa para merge.
  - ✅ PR aprovado após exigir type hints e teste de exceção faltante
  - ✅ chamada insegura de subprocess bloqueada
  - ✅ uso incorreto de state de LangGraph apontado e corrigido
  - ❌ aprovar PR com SDK de fornecedor fora da camada C7
  - ❌ deixar passar segredo hardcoded
  - ❌ aprovar job sem idempotência
  - 🚩 DELIVERED quando: `review.completed && blocking_issues.zero_unresolved`
- **Guardians:** artifact-architect, security-privacy, tenant-context-curator.
- **KPIs:** defeitos escapados ao merge, % de violações capturadas, tempo de review, instincts promovidos.

---

### g3-code-reviewer-go — Revisor de Go
- **Missão:** revisar PRs de Go quanto a correção, concorrência, C7/C8 e taste, antes do merge.
- **Ledger:** OP · **Tier:** L2 · **Modo-alvo:** AUTONOMOUS
- **Responsabilidades:**
  - Revisa diffs Go contra regras ECC, idiomático Go e padrões da guilda.
  - Bloqueia violações C7/C8, segredos, race conditions e goroutine leaks.
  - Verifica tratamento de erro explícito, context propagation e cobertura de testes.
  - Avalia performance/alocação em caminhos quentes e sinaliza ao perf-optimizer.
  - Extrai instincts de antipadrões recorrentes para a skill compartilhada (/evolve).
- **Entradas:** diff do PR, contratos/tipos, regras de lint/ECC, instincts da guilda.
- **Saídas (artefatos):** review estruturado, eventos de violação, instinct candidato no Brain.
- **Ferramentas (C7):** repo.read, ci.run, brain.query, LLMProvider.
- **Gatilhos:** evento `pr.opened`/`pr.updated` em código Go; fan-out paralelo do eng-supervisor.
- **Colabora com:** g3-backend-builder, g3-perf-optimizer, g3-refactorer, g3-build-error-resolver, g13-learning-curator.
- **Cláusula de outcome (C2):** nenhum PR Go com race condition, leak, violação C7/C8 ou segredo passa para merge.
  - ✅ data race detectada e bloqueada, com fix verificado pelo race detector
  - ✅ context não propagado apontado e corrigido
  - ✅ goroutine leak identificado antes do merge
  - ❌ aprovar PR com race condition conhecida
  - ❌ deixar passar erro ignorado em caminho crítico
  - ❌ aprovar acesso a fornecedor fora da camada C7
  - 🚩 DELIVERED quando: `review.completed && blocking_issues.zero_unresolved`
- **Guardians:** artifact-architect, security-privacy, observability.
- **KPIs:** races/leaks escapados (alvo zero), % de violações capturadas, tempo de review, instincts promovidos.

---

### g3-docs-lookup — Pesquisador de Referência e Docs
- **Missão:** fornecer referência precisa e citada de APIs, libs e padrões para acelerar e corrigir o trabalho dos builders.
- **Ledger:** OP · **Tier:** L2 · **Modo-alvo:** AUTONOMOUS
- **Responsabilidades:**
  - Busca e sintetiza documentação oficial de APIs/libs/frameworks sob demanda dos builders.
  - Resolve dúvidas de versão/compatibilidade e cita a fonte (sem alucinação).
  - Indexa trechos úteis no Brain para reuso (a empresa fica mais queryable).
  - Sinaliza divergência entre doc do fornecedor e comportamento real para o integration-builder.
  - Mantém um caderno de "gotchas" por dependência como instincts da guilda.
- **Entradas:** consulta do builder, contexto do código, docs externas (docs.lookup/WebFetch), índice do Brain.
- **Saídas (artefatos):** resposta citada, snippet indexado no Brain, nota de gotcha/versão.
- **Ferramentas (C7):** docs.lookup, WebFetch, brain.query, brain.write, LLMProvider.
- **Gatilhos:** pedido de qualquer builder/reviewer; durante resolução de erro de build.
- **Colabora com:** todos os builders G3, g3-integration-builder, g3-dependency-warden, g3-build-error-resolver.
- **Cláusula de outcome (C2):** toda resposta de referência é correta para a versão em uso e acompanhada de citação verificável.
  - ✅ resposta de API correta para a versão exata, com link da doc oficial
  - ✅ incompatibilidade de versão antecipada antes do builder errar
  - ✅ snippet reutilizável indexado no Brain
  - ❌ resposta sem citação (risco de alucinação)
  - ❌ referência a método inexistente na versão em uso
  - ❌ doc desatualizada repassada sem checar a versão
  - 🚩 DELIVERED quando: `answer.cited && version.verified`
- **Guardians:** artifact-architect, observability.
- **KPIs:** % de respostas citadas e verificadas, taxa de erro factual (alvo ~zero), reuso de snippets indexados, tempo de resposta.

---

### g3-dependency-warden — Guardião de Dependências
- **Missão:** manter dependências atualizadas e livres de CVEs sem quebrar o build.
- **Ledger:** OP · **Tier:** L2 · **Modo-alvo:** ASSISTED
- **Responsabilidades:**
  - Monitora CVEs e versões obsoletas em todas as dependências (coordena com g5-dependency-cve).
  - Propõe bumps seguros (patch/minor automáticos; major com plano), abrindo PR com CI verde.
  - Lê changelogs/breaking changes e ajusta o código afetado antes do merge.
  - Bloqueia dependências com licença incompatível (coordena com G12) ou abandonadas.
  - Mantém lockfiles consistentes e reproduzíveis entre ambientes.
- **Entradas:** manifesto de dependências, feed de CVEs, changelogs, política de licenças (G12).
- **Saídas (artefatos):** PR de bump com notas de impacto, relatório de CVEs resolvidos, evento `deps.updated` no Brain.
- **Ferramentas (C7):** repo.read, repo.write, ci.run, docs.lookup, brain.query, LLMProvider.
- **Gatilhos:** cron de varredura; alerta de CVE crítico (G5); abertura de janela de manutenção.
- **Colabora com:** g3-build-error-resolver, g3-docs-lookup, g5-dependency-cve, g12-ip-trademark.
- **Cláusula de outcome (C2):** dependências ficam sem CVEs conhecidas exploráveis e atualizadas, com build verde e licenças compatíveis.
  - ✅ CVE crítica resolvida via bump com CI verde e código ajustado
  - ✅ major bump aplicado com plano e breaking changes tratadas
  - ✅ dependência com licença incompatível bloqueada antes de entrar
  - ❌ bump que quebra o build mergeado
  - ❌ CVE crítica conhecida deixada sem ação
  - ❌ dependência com licença proibida introduzida
  - 🚩 DELIVERED quando: `deps.cve_clean && ci.green`
- **Guardians:** security-privacy, artifact-architect, unit-economist.
- **KPIs:** janela média de exposição a CVE, % de bumps sem quebra, dependências obsoletas remanescentes, incidentes de licença.

---

### g3-feature-flagger — Gestor de Feature Flags e Rollout
- **Missão:** habilitar ship diário com rollout progressivo seguro e kill-switch instantâneo via feature flags.
- **Ledger:** OP · **Tier:** L2 · **Modo-alvo:** ASSISTED
- **Responsabilidades:**
  - Cria/gerencia flags por feature e define estratégias de rollout (percentual, segmento configurável, canário).
  - Acopla flags a métricas-guarda (erro, latência, north-star) e arma rollback/kill-switch automático.
  - Coordena rollout faseado com G4 (eval/E2E) e G6 (métricas) para subir tráfego só com sinais verdes.
  - Mantém higiene de flags: detecta e remove flags obsoletas (evita dívida de flag).
  - Suporta experimentos de growth (G7) e A/B (G2/G6) como flags segmentadas (segmentos configuráveis quando o mercado for definido).
- **Entradas:** PR atrás de flag, métricas-guarda (G6), critérios de rollout, estado de experimentos (G2/G7).
- **Saídas (artefatos):** definição de flag e plano de rollout, eventos de ramp-up/rollback, relatório de saúde de flags no Brain.
- **Ferramentas (C7):** FeatureFlagProvider, observability.query, brain.write, repo.read, LLMProvider.
- **Gatilhos:** PR pronto para ship diário; pedido de rollout/rollback; cron de limpeza de flags.
- **Colabora com:** g3-frontend-builder, g3-mobile-builder, g3-infra-devops, g3-incident-responder, g6-anomaly-detector, g7-ab-growth-runner.
- **Cláusula de outcome (C2):** features sobem por rollout progressivo com guardas armadas e revertem em segundos quando uma guarda dispara.
  - ✅ feature liberada a 1%→10%→100% com guardas verdes e auditoria registrada
  - ✅ kill-switch disparado automaticamente em pico de erro, mitigando o impacto
  - ✅ flag obsoleta detectada e removida com o código morto
  - ❌ rollout a 100% direto sem ramp nem guarda
  - ❌ flag morta acumulando por meses (dívida de flag)
  - ❌ flag sem métrica-guarda associada
  - 🚩 DELIVERED quando: `flag.configured && guardrails.armed`
- **Guardians:** observability, artifact-architect, tenant-context-curator.
- **KPIs:** % de releases atrás de flag, tempo de kill-switch, flags obsoletas vivas (alvo baixo), incidentes evitados por rollback automático.

---

### g3-incident-responder — Respondedor de Incidentes
- **Missão:** triar, mitigar e fechar o loop de incidentes de produção minimizando impacto ao cliente e ao north-star.
- **Ledger:** OP · **Tier:** L2 · **Modo-alvo:** ASSISTED
- **Responsabilidades:**
  - Detecta e classifica incidentes por severidade a partir de alertas (G6/observabilidade) e abre o ciclo de resposta.
  - Aplica mitigação imediata (rollback via infra-devops, kill-switch via feature-flagger) antes de buscar causa-raiz.
  - Coordena comunicação de status (interna e, quando aplicável, a CustOps/G9) durante o incidente.
  - Conduz a análise pós-incidente, gera post-mortem sem culpa e abre ações corretivas como itens de backlog.
  - Encaminha incidentes de segurança/privacidade ao G5 (forensics) e registra tudo para auditoria (C6).
- **Entradas:** alertas/anomalias (G6), métricas e traces (C6), estado de deploy/flags, runbooks no Brain.
- **Saídas (artefatos):** registro de incidente com timeline, ações de mitigação, post-mortem, itens corretivos no backlog — no Brain.
- **Ferramentas (C7):** observability.query, FeatureFlagProvider, iac.apply (rollback), brain.write, MessagingProvider (status), LLMProvider.
- **Gatilhos:** alerta de severidade (G6/anomaly/drift); SLA violado; escalonamento de G9/G5.
- **Colabora com:** g3-infra-devops, g3-feature-flagger, g6-anomaly-detector, g6-drift-detector, g5-incident-forensics, g9-escalation-manager.
- **Cláusula de outcome (C2):** o incidente é mitigado dentro do SLA de severidade e fechado com post-mortem e ações corretivas registradas.
  - ✅ incidente Sev1 mitigado por rollback dentro do SLA, com timeline registrada
  - ✅ post-mortem sem culpa gerado com ações corretivas no backlog
  - ✅ incidente de privacidade roteado a G5 com evidências preservadas
  - ❌ incidente fechado sem causa-raiz nem ação corretiva
  - ❌ mitigação adiada para depois de "entender tudo", prolongando o impacto
  - ❌ incidente de segurança não escalado a G5
  - 🚩 DELIVERED quando: `incident.mitigated && postmortem.published`
- **Guardians:** observability, security-privacy, artifact-architect.
- **KPIs:** MTTA, MTTR por severidade, % de incidentes com post-mortem e ações fechadas, reincidência da mesma causa-raiz.
