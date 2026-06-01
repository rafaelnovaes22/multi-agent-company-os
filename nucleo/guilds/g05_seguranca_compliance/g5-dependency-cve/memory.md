# MEMORY — g5-dependency-cve

Formato: `§ [confidence:nivel] [YYYY-MM-DD] [run:id] fato acionável`

§ [confidence:local] [2026-05-31] [run:seed] Priorizar por exploitabilidade real (exposição + EPSS + caminho ativo), não só CVSS bruto — evita ruído de remediação em G3.
§ [confidence:local] [2026-05-31] [run:seed] Manter embargo: build que reintroduz versão vulnerável conhecida é bloqueado; versão-alvo sempre com verificação de regressão.
§ [confidence:local] [2026-05-31] [run:seed] Detectar typosquatting/pacote malicioso e barrar entrada no lockfile; CVE crítica exposta escala como incidente.
