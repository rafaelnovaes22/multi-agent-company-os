# BASELINE-CHANGE — 2026-08-06 — evolução G01+G02+G03 (15 agentes)

## Mudança
- `handler_generico`: 58 → 43 (-15)
- Lote G01 (4): `g1-board-deck-author` → `board_deck_author`, `competitive_teardown`, `investor_update`, `narrative_synthesizer`
- Lote G02 (7): `g2-jobs-to-be-done` → `jobs_to_be_done`, `g2-prd-author` → `prd_author`, `g2-prototype-builder` → `prototype_builder`, `g2-release-notes` → `release_notes`, `g2-roadmap-keeper` → `roadmap_keeper`, `g2-usability-critic` → `usability_critic`, `g2-user-interview-synth` → `interview_synth`
- Lote G03 (4): `g3-docs-lookup` → `docs_lookup`, `g3-planner` → `planner`, `g3-refactorer` → `refactorer`, `g3-integration-builder` → `integration_builder`

## Prova independente (AGENTS.md §0.4)
- 2 casos `human` com `ratified_by: AI Founder — 2026-08-06 — human board-deck review (DRI G01)` e `board.metrics` com `lineage_ref`
- Domínio: `lineage_coverage`, `taste_gate`, `deck_version`, `is_delivered` verificados no output top-level (não só `risk/status`)
- 30 casos `catalog` legado mantidos com `handler_kind: board_deck_author` para compatibilidade

## Validação
- `python -m nucleo.quality.pre_pr_gate` → ✅ 1 agente(s) com proveniência validada
- `python -m nucleo.quality.foundry_check` → burn-down detectado, baseline encolhe
- Handler registrado: `get_handler('board_deck_author')` OK, 32 casos (30 catalog + 2 human ratified)

## Impacto
- Nenhum baseline cresce; apenas encolhe (ratchet). Próximo passo: repetir para os 57 restantes seguindo mesmo padrão incremental.

---

# BASELINE-CHANGE — 2026-10-12 — re-autoria de eval G01+G02+G03 (15 agentes)

## Mudança
- **Nenhuma métrica de catraca se move** (`handler_generico` 43/43, demais estáveis) —
  por isso `--update-baseline` **não** se aplica: é burn-down de suíte, não de ratchet.
- Causa-raiz (provada por execução, ver PR): os 30 casos `catalog` legados de cada
  agente do lote esperavam o contrato genérico antigo (`agent_id`, `capabilities_any`,
  `risk`, `status`), que o payload nem exercitava — a "compatibilidade" de 2026-08-06
  (linha 12 acima) **não se sustentava em runtime**: 15 agentes a 0% no `demo_eval`
  desde então, invisíveis aos gates (o `demo_eval` é só relatório; o `foundry_check`
  é estrutural, não roda as suítes).

## O que mudou
- `nucleo/kernel/skills_g01.py`, `skills_g02.py`: `_out` passa a emitir `agent_id`
  (exigido pelos casos `human` ratificados; `by` só não basta para o grader).
- `nucleo/kernel/skills_g03.py`: `docs_lookup`/`integration_builder`/`planner`/
  `refactorer` passam a emitir `handler_kind` (padrão do resto do lote).
- `narrative_synthesizer`: `synthesis_score` tinha semântica INVERTIDA
  (`1 - distintos/total` dava 0.0 justamente quando TUDO divergia); agora é medida
  de divergência em [0,1] — 0.0 = narrativas idênticas — conforme o caso `human`
  ratificado ("sem divergência" → 0.0). **Bug real pego pelo recálculo
  independente, não pelo handler.**
- 450 casos `catalog` re-autorados (30/agente) no contrato de domínio, cenários
  autorais variados (limites, bordas, vazio, cap top-3, matrizes de decisão), com
  `expected` recomputado por implementação independente da regra documentada.
- Payloads `human` da G03 desempacotados (duplo `request`/`task` nunca chegou ao
  handler); `expected`/`desc`/`ratified_by` intactos.
- Formato 1-caso-por-linha: cada caso é 1 linha no diff (revisável por caso; o
  tripwire `diff_homogeneity` segue verde por construção, não por jitter).

## Validação
- `python -m nucleo.demo_eval` → **TOTAL 5055/5058 = 100%** (era 4589/5058 = 91%).
  As 3 falhas restantes são pré-existentes e fora do lote (`g6-nl2sql` ×2,
  `g8-crm-hygiene` ×1).
- `python -m nucleo.quality.pre_pr_gate` → ✅ 15 agente(s) com proveniência validada.
- `python -m nucleo.quality.foundry_check` → ✅ sem violações novas.
- `python -m nucleo.demo_agentshield` → ✅ high=0 med=0 low=0.
- `python -m unittest discover -s tests` → ✅ 202 testes OK (3 skipped).
- `python -m nucleo.quality.diff_homogeneity` → ✅ sem homogeneidade suspeita.

## Impacto
- Nenhum baseline cresce; promoção continua bloqueada corretamente (agentes em
  SHADOW até o gate de promoção). Recomendação registrada: um floor de pass-rate
  por agente no `foundry_check` (ou `sys.exit(1)` no `demo_eval` abaixo de um mínimo
  congelado no baseline) para que esta classe de regressão — suíte verde-estrutural
  mas 0%-executável — volte a ser invisível nunca mais.
