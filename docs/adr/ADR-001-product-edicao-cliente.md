# ADR-001 — Product como edição cliente da frota canônica

## Status
Aceito

## Contexto
Os agentes em `nucleo/product/` são a edição cliente multi-tenant do NÚCLEO: a superfície vendida para PMEs, com memória e contexto por tenant. Eles não devem virar uma segunda frota com lógica própria. Pela doutrina do Foundry, especialmente C8 (config-over-code), a variação de cliente/segmento deve morar em spec, contexto de tenant e payloads; a execução deve reutilizar handlers canônicos.

## Decisão
Manter `product/` como camada de empacotamento/comercialização e reconciliar cada agente com seu equivalente de catálogo via `reconciled_with` na spec. O `act_handler` permanece apontando para o handler canônico já usado pela frota; a spec de produto só especializa multi-tenant, ferramentas e outcome clause.

Mapeamento adotado:

- `fin-caixa` → `g10-treasury` (`act_handler: fin_cashflow`)
- `inbox-triage` → `g9-support-triage` (`act_handler: inbox_triage`)
- `atendimento` → `g9-tier1-resolver` (`act_handler: atendimento`)
- `ops-followup` → `g9-support-triage` (`act_handler: ops_followup`)
- `painel-dono` → `g6-dashboard-builder` (`act_handler: painel_dono`)

## Justificativa do mapeamento provisório de `ops-followup`
`ops-followup` trata itens parados, atrasados ou sem dono e gera ações de destravamento. Entre as opções provisórias citadas (G9/G03), `g9-support-triage` é o mais aderente no estado atual porque recebe sinais operacionais vindos de inbox/suporte e roteia problemas para resolução, enquanto G03 tende a ser camada mais processual/orquestração. A reconciliação fica explícita na spec e pode ser migrada para um agente G03 dedicado quando o catálogo materializar esse equivalente.

## Consequências
- Product continua sendo edição cliente multi-tenant, não fork lógico.
- Testes e evals continuam usando os campos top-level produzidos pelos handlers canônicos.
- C2 segue válido: todas as specs reconciliadas têm `outcome_clause` com statement, pelo menos 3 exemplos positivos, pelo menos 3 negativos e `delivered_event`.
- C3 segue válido: todos os agentes billable mantêm `economics.max_ratio: 0.25`.
- C8 segue válido: não há hardcode de tenant, segmento ou alíquota; a variação permanece na spec/payload/contexto.
