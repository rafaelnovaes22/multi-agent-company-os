# MEMORY — brain-indexer

Formato: `§ [confidence:nivel] [YYYY-MM-DD] [run:id] fato acionável`

§ [confidence:local] [2026-05-31] [run:seed] Schema canônico obrigatório no event store: actor, action, inputs_hash, outputs, cost, latency, trace_id, ts — sem trace_id/inputs_hash o artefato não conta (C6).
§ [confidence:local] [2026-05-31] [run:seed] Event store é append-only: nunca editar/sobrescrever um evento já gravado; correção é novo evento referenciando o anterior.
§ [confidence:local] [2026-05-31] [run:seed] Reconciliação outcomes↔traces tem alvo desvio ≤ 1%; desvio > 1% é FAIL no gate C6.
