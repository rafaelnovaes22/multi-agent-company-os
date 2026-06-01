# MEMORY — g6-anomaly-detector

Formato: `§ [confidence:nivel] [YYYY-MM-DD] [run:id] fato acionável`

§ [confidence:local] [2026-05-31] [run:seed] Foco em desvio pontual/agudo de métrica (não degradação lenta — isso é do g6-drift-detector); usar baseline sazonal para suprimir falso alarme.
§ [confidence:local] [2026-05-31] [run:seed] Todo alerta sai com severidade classificada + hipótese de causa-raiz (correlação com deploys/campanhas via Brain); alerta sem isso é inacionável.
§ [confidence:local] [2026-05-31] [run:seed] Rotear alerta à guilda dona da métrica e ao Operator Console; abrir incidente (g3-incident-responder) quando a severidade exigir.
