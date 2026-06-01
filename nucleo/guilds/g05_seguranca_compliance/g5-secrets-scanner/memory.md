# MEMORY — g5-secrets-scanner

Formato: `§ [confidence:nivel] [YYYY-MM-DD] [run:id] fato acionável`

§ [confidence:local] [2026-05-31] [run:seed] Detecção por entropia alta + regex de provedores conhecidos + formatos de chave; classificar por confiança e bloquear em pre-commit/pre-merge.
§ [confidence:local] [2026-05-31] [run:seed] Segredo só é "remediado" após confirmação de rotação E revogação da credencial exposta — nunca antes.
§ [confidence:local] [2026-05-31] [run:seed] Secrets de runtime vêm de cofre/variável via C7, nunca hardcode; allowlist de falsos-positivos precisa ser auditável.
