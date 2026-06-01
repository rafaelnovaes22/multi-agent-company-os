# MEMORY — g13-eval-engineer-guardian

Formato: `§ [confidence:nivel] [YYYY-MM-DD] [run:id] fato acionável`

§ [confidence:local] [2026-05-31] [run:seed] Gate de eval exige ≥30 casos frescos cobrindo positivos+negativos da cláusula C2 — caminho-feliz-só reprova.
§ [confidence:local] [2026-05-31] [run:seed] Grader/harness precisa ser reproduzível e independente do modelo de produção; leakage (teste = treino) reprova.
§ [confidence:local] [2026-05-31] [run:seed] Freshness ≤90 dias; novo modo de falha em produção exige novo caso (loop fechado) e o taste-gate barra output não-lovable.
