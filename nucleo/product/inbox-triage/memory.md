# MEMORY — inbox-triage (por tenant)

> Namespaced por cliente (`tenant/{id}/agent/inbox-triage/memory`). Aprende os padrões de mensagem DAQUELE cliente (quem costuma mandar o quê, gatilhos de urgência do negócio dele).

Formato: `§ [confidence:nivel] [YYYY-MM-DD] [run:id] fato acionável`

§ [confidence:local] [2026-05-29] [run:seed] Mensagens com "urgente"/"parado" sobem para urgência alta e vão ao topo da fila.
