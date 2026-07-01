# AGENTS.md — como construir no NÚCLEO (leia antes de qualquer tarefa)

> Este arquivo é a **fonte da verdade operacional** para qualquer agente (hermes-agent,
> Claude Code, humano) que for materializar ou alterar agentes da frota. O objetivo é
> **convergência**: que todo trabalho saia no mesmo padrão de qualidade, sem divergências
> para reconciliar depois.

## 0. Regras de ouro (não-negociáveis)

1. **Ramifique SEMPRE do `origin/main` mais recente** (`git fetch && git switch -c <branch> origin/main`).
   `origin/main` é o ÚNICO estado canônico. Nunca trabalhe a partir de um clone defasado nem
   deixe trabalho melhor fora do versionamento — foi exatamente isso que gerou dois fleets
   paralelos conflitantes. Se você produziu algo melhor, **commite e abra PR**; não deixe untracked.
2. **O gate de qualidade é `forge_check` — não o `demo_eval` verde.** `demo_eval 100%` prova só
   que a materialização é bem-formada, NÃO que os agentes fazem o que prometem. A definition-of-done
   é `python -m nucleo.quality.forge_check` passar (exit 0), além das suítes abaixo.
3. **Materializar é TRADUZIR o catálogo, não inventar.** O gabarito é `catalogo/G00–G14.md`
   (missão, tier, ledger, modo-alvo, responsabilidades, C7, gatilhos, cláusula C2, guardians, KPIs).
   Não invente conteúdo fora do catálogo; não achate guardians/tools para um set genérico.
4. **Fechar catraca NÃO é prova de valor — e isto é HARD-FAIL, sem grandfather** (lição #30/#31/#32:
   evals tautológicos passaram em todos os gates verdes). Todo handler determinístico exige PROVA
   INDEPENDENTE, autorada FORA do próprio handler:
   - **Proveniência obrigatória:** todo eval-case declara `provenance` ∈ `{catalog, human, independent}`.
     `replay`/`handler`/`derived`/ausente é proibido — é o sinal do `expected` = eco do handler.
   - **Critério por natureza:** build/ops/browser → critério **held-out** em `oracle`
     (`heldout_files`/`structure`/`browser`/`bug_markers`) que o agente nunca vê; cálculo/decisão →
     **≥1 caso `human`/`independent`** (valor de referência que não sai do handler).
   - **Baseline só encolhe:** `forge_baseline.json` nunca cresce; toda alteração exige
     `nucleo/quality/BASELINE-CHANGE.md` justificando (PR que "fecha métrica" = auditável).
   Gate executável: `python -m nucleo.quality.pre_pr_gate` (§3). Reprovou → **não abra PR**.
5. **O `hermes-agent` é AUDITOR, não autor — e isto vale para QUALQUER tarefa dada a ele.**
   O Hermes **nunca** materializa nem altera agentes da frota (`spec`/`soul`/`memory`/`handler`)
   e **nunca faz merge**. Autoria de agente é tarefa de humano/Claude Code. O papel único do Hermes
   é **auditar**: rodar o oráculo executável e reportar se a frota/projeto entrega o que promete.
   Por que: o vetor de gaming que derrubou os gates (#30-32, #66-80) é **o mesmo ator autorar o
   artefato E atestar a própria prova**. Tirar a autoria do auditor fecha o vetor por construção,
   não por disciplina.
   - **Veredito ancorado em EXECUÇÃO, jamais em opinião.** Uma auditoria só "passa" pelo oráculo
     executável (`delivered_rate`, exit-code de `pre_pr_gate`/`forge_check`/`diff_homogeneity`,
     VERIFY-IN-EVAL), nunca por nota de LLM-juiz ("parece bom"). O juiz (gpt-5, família OpenAI)
     mede qualidade generativa e é **opinião que informa, não decide** — e por ser mesma família
     do Codex do Hermes, concordância entre eles **não é independência** (`CONTRATO §8.3`).
   - **Proibido auto-atestar.** O Hermes não carimba `provenance:"independent"` na própria saída
     nem rotula a própria prova; quem prova tem credencial diferente de quem foi auditado (G-PERÍMETRO).
   - **Limite do "auditor de rota":** gerar o **oráculo held-out a partir do contrato** (Schema A,
     sem ver `handler`/`soul`/`memory`) é **instrumento de auditoria, não autoria de agente** — é
     produzir a régua independente, não o objeto medido. Continua permitido sob o `CONTRATO-NUCLEO-HERMES-ORACULO`.

## 1. Definition of Done de um agente

Um agente só está "pronto" quando TUDO abaixo é verdade (o `forge_check` checa o que é automatizável):

- **Spec fiel ao catálogo:** `id`, `guild`, `tier`, `ledger` (operating|billable), **`target_mode`**
  (o modo de promoção que o catálogo define — não só `mode: SHADOW`), responsabilidades, `tools` (C7
  reais do catálogo, não decorativas), guardians **por risco** (inclua `security-privacy` em todo
  agente que toca PII/LGPD; `unit-economist` onde há custo/preço), e **KPIs** do catálogo.
- **Cláusula C2 completa:** `outcome_clause` com `statement`, ≥3 `positive_examples`, ≥3
  `negative_examples` e `delivered_event` — fiéis à missão (não template genérico).
- **C3 (se billable):** `economics.max_ratio` declarado **E enforçado em runtime** pelo handler
  (cobrança só com `delivered=True` e `cost_ratio <= max_ratio`). Billable com handler genérico = proibido.
- **Handler REAL para capacidade nomeada:** se o agente promete cálculo/decisão (RICE, forecast,
  scoring, conciliação, NL→SQL, detecção...), ele NÃO pode usar `spec_driven`/`guardian_check`/
  `supervisor_route` (eco genérico). Implemente o handler determinístico no módulo da guilda
  (`nucleo/kernel/skills_gNN.py`), no padrão de `skills_finance.py`/`skills_g03.py`: cálculo real,
  campos no top-level do output, `rationale` + `by`. Genérico só vale para agentes cuja função
  REAL é só rotear (supervisores) ou checar contrato.
- **Eval de DOMÍNIO, não theater:** os casos (`evals/cases.json`) devem testar o resultado de
  domínio (campos calculados em `expected`), não só `risk/status/routed_to`. `≥30` casos é o alvo;
  use cenários variados (limites, bordas, bloqueios). NUNCA ponha `delivered`/`billing_amount` em
  `expected` (em SHADOW o gate força `delivered=False`). **Cada caso declara `provenance`**
  (`catalog`/`human`/`independent`) e o agente carrega prova independente da natureza — ver regra
  de ouro #4; o `pre_pr_gate` reprova (hard-fail) quem não tiver.
- **SLA de entrega (promoção, decisão CEO 2026-06-30):** um agente só promove a ASSISTED/AUTONOMOUS
  quando o **`delivered_rate` do oráculo executável** (`run_evals`+VERIFY-IN-EVAL, NÃO o `rate`
  estático do contrato-grader) for **>= 95%**, medido por agente. Os **<=5% restantes** têm de cair
  num **fail-safe declarado** — escalar a humano ou retornar não-entrega explícita com motivo —
  **nunca** resposta errada silenciosa (resposta errada não-detectada nos 5% é HARD-FAIL). Meta =
  100% de comportamento não-danoso (95% entrega + 5% fail-safe). Consequência assumida: o teto
  generativo medido (N=5, não cede a prompt) faz 95% só alcançável com tooling + fonte-certa-por-
  domínio; agente puramente generativo de cálculo/decisão que não bate 95% **fica em SHADOW/PILOT**.

## 2. Arquitetura de handlers (1 template + N specs, mas capacidade real)

- O nó `act` é um registry plugável por `act_handler` (`nucleo/kernel/skills.py`).
- **Camadas:** genéricos (`spec_driven`/`supervisor_route`/`guardian_check`) para roteamento/checagem
  de contrato; **determinísticos por guilda** (`skills_gNN.py`, `skills_finance.py`, `skills_custops.py`)
  para a lógica de domínio — importados por side-effect no fim de `skills.py`.
- O grader genérico de contrato (`generic_contract_grader`) avalia `expected` de domínio contra o
  top-level do output (tolerância 1%). Logo um handler determinístico **não precisa de grader nominal** —
  basta pôr os campos calculados no output e o `expected` de domínio no caso.
- **ICP é dado, fonte única:** `nucleo/company/icp.md` + `_score_lead_against_icp` em `skills.py`.
  Nunca redefina ICP em código (C8). Dois perfis: ICP-1 bombeiro R$1–20M; ICP-2 enterprise **>R$100M
  (aberto)** **ou setor público**, com sinais (processos desorganizados / time grande / custo de
  pessoal). `tests/test_icp_segments.py` é guarda de regressão — não o afrouxe.

## 3. Gate antes de abrir PR (rode tudo; tudo verde)

```bash
rm -rf nucleo/.brain* .brain*                       # estado regenerável (demos não são idempotentes)
python -m compileall -q nucleo
python -m nucleo.quality.pre_pr_gate                # HARD-FAIL (regra de ouro #4): proveniência +
                                                    #   prova independente nos agentes que você tocou
python -m nucleo.quality.forge_check                # DEFINITION OF DONE (ratchet)
python -m nucleo.demo_eval                           # C4 — eval-harness da frota
python -m nucleo.demo_agentshield                    # C8 — sem violação HIGH
python -m unittest discover -s tests                 # suíte completa (NÃO uma lista parcial)
```

> O `pre_pr_gate` é HARD-FAIL e escopado ao que o seu branch mudou vs `origin/main` — ele
> reprova se você fechou capacidade sem proveniência/prova independente. Rode
> `python -m nucleo.quality.pre_pr_gate --fleet` para ver o backlog de retrofit da frota
> (débito atual a zerar; **não** é grandfatherizado). Plano de burn-down em
> [docs/BACKLOG-proveniencia-hermes.md](docs/BACKLOG-proveniencia-hermes.md) — **leia antes** de
> mexer em proveniência (tem regras de integridade que, se violadas, derrubam o `demo_eval`).

- **Ratchet:** o `forge_check` congela o débito atual em `nucleo/quality/forge_baseline.json` e
  reprova só violações NOVAS. Agente novo/alterado tem de bater a barra completa. Se você MELHORAR
  (ex.: converter um genérico em determinístico, ou subir um agente para ≥30 casos), rode
  `python -m nucleo.quality.forge_check --update-baseline` para **travar o ganho** (burn-down) e
  cite no PR. Nunca rode `--update-baseline` para "passar" escondendo uma regressão.

## 4. PR

- Mensagem clara; descreva o que mudou e cole a saída dos gates acima.
- **Não faça merge** — o merge é o gate humano (CEO/founder). Aguarde revisão.
- O norte é **entregar capacidade real e verificável**, não mover um número. As métricas do baseline
  (`handler_generico`, `sem_target_mode`) e o `pre_pr_gate --fleet` são **diagnóstico do humano,
  jamais alvo dado ao agente**: minimizar a métrica sem entregar capacidade é Goodhart (lições
  #30-32 e proveniência #66-80). Melhorar de fato é bem-vindo (genérico→determinístico com prova
  INDEPENDENTE da natureza, `target_mode`, KPIs, casos de domínio); "zerar o baseline" como objetivo
  em si, não. Onde a prova só puder ser auto-declarada pelo próprio agente, **não feche a métrica:
  registre o limite** (regra de ouro #4). Ver [docs/PLANO-AJUSTE-ROTA.md](docs/PLANO-AJUSTE-ROTA.md).
