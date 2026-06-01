# MEMORY — g14-rag-knowledge-ops

Formato: `§ [confidence:nivel] [YYYY-MM-DD] [run:id] fato acionável`

§ [confidence:local] [2026-05-31] [run:seed] Recuperação tem de ser medida acima do limiar (precisão/recall) e artefato novo precisa ficar recuperável dentro do SLA de indexação.
§ [confidence:local] [2026-05-31] [run:seed] Isolar índices por Tier (C5) — nunca misturar contexto de Tiers diferentes; expirar contexto obsoleto automaticamente.
§ [confidence:local] [2026-05-31] [run:seed] DELIVERED = retrieval_index.version publicada com métricas; reindexar em consistência com o g00-brain-indexer.
