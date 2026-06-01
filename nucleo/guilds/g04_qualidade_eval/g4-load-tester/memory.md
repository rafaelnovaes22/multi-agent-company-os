# MEMORY — g4-load-tester

Formato: `§ [confidence:nivel] [YYYY-MM-DD] [run:id] fato acionável`

§ [confidence:local] [2026-05-31] [run:seed] Promoção a AUTONOMOUS e lançamento tier-1 exigem teste de carga com SLA validado (p50/p95/p99), throughput e taxa de erro — nunca só média.
§ [confidence:local] [2026-05-31] [run:seed] Custo sob carga é cruzado com C3 (custo <=25% do preço) para outputs BL; estourar C3 bloqueia liberação.
§ [confidence:local] [2026-05-31] [run:seed] Reportar ponto de saturação e gargalo (agente, fila, provider, banco) com evidência; enviar regressão de performance ao g4-regression-watcher.
