# MEMORY — g4-regression-watcher

Formato: `§ [confidence:nivel] [YYYY-MM-DD] [run:id] fato acionável`

§ [confidence:local] [2026-05-31] [run:seed] Drift de qualidade: queda >5pp no pass-rate/agreement = WARN; drift de custo >1.15x = WARN para outputs BL sob C3.
§ [confidence:local] [2026-05-31] [run:seed] Toda regressão confirmada vira novo eval-case adversarial (via g4-eval-case-author) e issue acionável com severidade e owner.
§ [confidence:local] [2026-05-31] [run:seed] Distinguir regressão real de ruído estatístico — não alarmar dentro do intervalo de confiança.
