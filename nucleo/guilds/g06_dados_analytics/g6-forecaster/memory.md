# MEMORY — g6-forecaster

Formato: `§ [confidence:nivel] [YYYY-MM-DD] [run:id] fato acionável`

§ [confidence:local] [2026-05-31] [run:seed] Toda previsão sai com intervalo de confiança e cenários (base/otimista/pessimista); previsão pontual sem IC induz overcommit de capacidade.
§ [confidence:local] [2026-05-31] [run:seed] Backtesting contínuo reporta MAPE/MASE; ao detectar drift de previsão, recalibrar antes de seguir prevendo.
§ [confidence:local] [2026-05-31] [run:seed] Incorporar sazonalidade, lançamentos tier-1 e campanhas como regressores; alimentar FP&A/Tesouraria e ligar demanda à capacidade de tokens/compute (token-max).
