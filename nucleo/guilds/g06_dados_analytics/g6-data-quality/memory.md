# MEMORY — g6-data-quality

Formato: `§ [confidence:nivel] [YYYY-MM-DD] [run:id] fato acionável`

§ [confidence:local] [2026-05-31] [run:seed] É o portão de qualidade (C6) que o g6-pipeline-builder precisa passar antes de publicar; dado fora de contrato é BLOQUEADO e vai para quarentena.
§ [confidence:local] [2026-05-31] [run:seed] Testes obrigatórios por load: completude, integridade referencial, duplicatas, distribuição e freshness; duplicata em chave infla a north-star.
§ [confidence:local] [2026-05-31] [run:seed] PII inesperada em trânsito (C1/LGPD) aciona o g5-lgpd-privacy ANTES do load; nunca liberar dataset com freshness fora de SLA sem sinalizar.
