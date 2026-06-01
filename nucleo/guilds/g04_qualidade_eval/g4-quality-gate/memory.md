# MEMORY — g4-quality-gate

Formato: `§ [confidence:nivel] [YYYY-MM-DD] [run:id] fato acionável`

§ [confidence:local] [2026-05-31] [run:seed] Critérios duros do gate: pass-rate mínimo, cobertura >=80%, E2E verde, sem regressão, SLA ok, prompt-eval ok — qualquer FAIL bloqueia.
§ [confidence:local] [2026-05-31] [run:seed] Lovability é critério de bloqueio: testes verdes não bastam; se o output não encanta, FAIL.
§ [confidence:local] [2026-05-31] [run:seed] Bypass de incidente só com registro auditável no Brain; PILOT+ billable precisa cumprir C3 (custo <=25% do preço) para passar.
