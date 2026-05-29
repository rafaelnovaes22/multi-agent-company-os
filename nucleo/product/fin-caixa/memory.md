# MEMORY — fin-caixa (por tenant)

> Esta memória é **namespaced por cliente** (`tenant/{id}/agent/fin-caixa/memory`).
> O agente aprende a empresa DAQUELE cliente (sazonalidade, clientes que sempre atrasam, fornecedores críticos) sem vazar para outros.

Formato: `§ [confidence:nivel] [YYYY-MM-DD] [run:id] fato acionável`

§ [confidence:local] [2026-05-29] [run:seed] Caixa projetado = saldo + recebíveis em aberto - pagáveis; negativo = risco a sinalizar já.
