# MEMORY — g13-monthly-reviewer

Formato: `§ [confidence:nivel] [YYYY-MM-DD] [run:id] fato acionável`

§ [confidence:local] [2026-05-31] [run:seed] Auditoria mensal usa modelo independente (não-Claude) e re-amostra 5–10% dos outcomes contra os traces — independência é contrato.
§ [confidence:local] [2026-05-31] [run:seed] Drift: acurácia ≥5pp/mês = WARN, custo ≥+15%/mês, volume ±30%/mês, prompt_hash mudado sem recálculo de economia.
§ [confidence:local] [2026-05-31] [run:seed] Relatório (md+JSON) vai para docs/foundry/audits/ via PR; nunca editar artefato de produção nem comitar direto na main.
