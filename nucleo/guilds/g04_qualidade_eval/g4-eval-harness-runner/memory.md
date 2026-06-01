# MEMORY — g4-eval-harness-runner

Formato: `§ [confidence:nivel] [YYYY-MM-DD] [run:id] fato acionável`

§ [confidence:local] [2026-05-31] [run:seed] Todo run propaga trace_id (C6) e grava eval.run com pass_at_k, pass_rate_by_category e grader_results[]; sem trace_id não é auditável.
§ [confidence:local] [2026-05-31] [run:seed] Grader rubric usa LLM-as-judge de modelo INDEPENDENTE do de produção; relatório precisa ser reproduzível (mesma entrada -> mesmo relatório).
§ [confidence:local] [2026-05-31] [run:seed] Smoke-eval (subset) em micro-release diário; suíte completa em promoção — otimizar token-max.
