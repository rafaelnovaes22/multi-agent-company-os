# MEMORY — g13-observability-guardian

Formato: `§ [confidence:nivel] [YYYY-MM-DD] [run:id] fato acionável`

§ [confidence:local] [2026-05-31] [run:seed] Desvio outcomes↔traces > 1% reprova ("sem artefato, não conta"); ai_enabled=true exige trace LLM, ai_enabled=false exige audit-log+métricas.
§ [confidence:local] [2026-05-31] [run:seed] Todo evento precisa dos campos canônicos (actor, action, inputs_hash, outputs, cost, latency, trace_id, ts) e citations apontando para artefatos reais.
§ [confidence:local] [2026-05-31] [run:seed] Fluxo que entrega sem emitir evento é shadow process — abrir item e rotear à guilda dona.
