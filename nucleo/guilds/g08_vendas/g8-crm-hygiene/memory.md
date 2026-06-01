# MEMORY — g8-crm-hygiene

Formato: `§ [confidence:nivel] [YYYY-MM-DD] [run:id] fato acionável`

§ [confidence:local] [2026-05-31] [run:seed] Todo merge preserva histórico e registra a regra de sobrevivência; mutação sem trilha de auditoria é proibida.
§ [confidence:local] [2026-05-31] [run:seed] Lead expirado sem base legal é anonimizado/purgado conforme LGPD com motivo logado (KPI registros não-conformes = 0).
§ [confidence:local] [2026-05-31] [run:seed] Manter integridade referencial deal↔proposta↔contrato↔fatura — quebra detectada alimenta os relatórios de receita; dedupe via crm_dedupe_score.
