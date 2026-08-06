# BASELINE-CHANGE — 2026-08-06 — evolução G01+G02 (11 agentes)

## Mudança
- `handler_generico`: 58 → 47 (-11)
- Lote G01 (4): `g1-board-deck-author` → `board_deck_author`, `competitive_teardown`, `investor_update`, `narrative_synthesizer`
- Lote G02 (7): `g2-jobs-to-be-done` → `jobs_to_be_done`, `g2-prd-author` → `prd_author`, `g2-prototype-builder` → `prototype_builder`, `g2-release-notes` → `release_notes`, `g2-roadmap-keeper` → `roadmap_keeper`, `g2-usability-critic` → `usability_critic`, `g2-user-interview-synth` → `interview_synth`

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
