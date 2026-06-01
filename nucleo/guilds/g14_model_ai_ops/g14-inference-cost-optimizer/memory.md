# MEMORY — g14-inference-cost-optimizer

Formato: `§ [confidence:nivel] [YYYY-MM-DD] [run:id] fato acionável`

§ [confidence:local] [2026-05-31] [run:seed] Reduzir custo de inferência por outcome via cache/batch/compressão SEM regressão de qualidade acima da tolerância (alvo de regressões = 0).
§ [confidence:local] [2026-05-31] [run:seed] Cache nunca pode servir resposta obsoleta/errada; tarefa simples pode migrar para modelo menor só com economia comprovada e qualidade mantida.
§ [confidence:local] [2026-05-31] [run:seed] DELIVERED = cost_optimization.applied com economia medida e qualidade ≥ baseline; ratear economia visível por guilda (alimentar g10-token-cost-accountant).
