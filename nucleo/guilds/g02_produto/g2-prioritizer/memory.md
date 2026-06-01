# MEMORY — g2-prioritizer

Formato: `§ [confidence:nivel] [YYYY-MM-DD] [run:id] fato acionável`

§ [confidence:local] [2026-05-31] [run:seed] Cada fator RICE (Reach, Impact, Confidence, Effort) tem fonte rastreável no Brain; score sem fonte é proibido. KPI: % de itens com todos os fatores com fonte.
§ [confidence:local] [2026-05-31] [run:seed] Item de baixa Confidence é rebaixado e enviado ao g2-experiment-designer antes de subir no ranking.
§ [confidence:local] [2026-05-31] [run:seed] Backlog é vivo: re-rank disparado quando novo experimento/sinal muda Reach/Impact/Confidence; ranking estático é violação.
