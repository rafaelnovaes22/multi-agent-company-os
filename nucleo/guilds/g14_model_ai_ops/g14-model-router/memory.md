# MEMORY — g14-model-router

Formato: `§ [confidence:nivel] [YYYY-MM-DD] [run:id] fato acionável`

§ [confidence:local] [2026-05-31] [run:seed] Escolher o modelo mais barato que ainda atende o SLA de qualidade da tarefa; tarefa simples vai a modelo barato, tarefa crítica ao forte.
§ [confidence:local] [2026-05-31] [run:seed] Fallback entre providers é obrigatório e deve ser transparente (sem mudança de código, C8); chamada billable que estouraria C3 é bloqueada/rebaixada.
§ [confidence:local] [2026-05-31] [run:seed] DELIVERED só com model_id + cost registrados no Brain (C6) — toda chamada gera telemetria de uso por modelo.
