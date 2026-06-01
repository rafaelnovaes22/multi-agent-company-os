# MEMORY — g6-drift-detector

Formato: `§ [confidence:nivel] [YYYY-MM-DD] [run:id] fato acionável`

§ [confidence:local] [2026-05-31] [run:seed] 4 dimensões de drift: quality (↓≥5pp/mês), cost (↑≥15%/mês), volume (±30%/mês), prompt (prompt_hash muda sem recálculo de economia).
§ [confidence:local] [2026-05-31] [run:seed] Drift confirmado emite sinal de rebaixamento de modo (AUTONOMOUS→ASSISTED) até reauditoria, em conjunto com a Governança; sempre comparar contra baseline de promoção.
§ [confidence:local] [2026-05-31] [run:seed] Drift de prompt_hash sem recálculo de economia (C3/ROI) é violação — bloquear até reauditoria. Distinguir de anomalia pontual (g6-anomaly-detector).
