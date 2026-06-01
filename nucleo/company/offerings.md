---
artifact: offerings
tier: L0
version: "0.0.0"
status: template
loaded_by: nucleo.kernel.loaders.load_offerings
note: "Preencher após o workshop de mercado (06-WORKSHOP-MERCADO.md) — o vertical concretiza as ofertas."
---

# Catálogo de Ofertas (NÚCLEO)

> **Template L0.** Hoje vazio de propósito — as ofertas se concretizam quando o vertical for escolhido.
> **Regra C1 (diagnose-before-build):** a **primeira oferta é SEMPRE um diagnóstico cobrável** (`g2-diagnose`), nunca um produto. Vende-se o diagnóstico, mede-se a dor real, e só então a Fábrica constrói o SKU.

## Oferta 0 — Diagnóstico (porta de entrada) · [C1]
| Campo | Valor (preencher pós-workshop) |
|---|---|
| nome | _(ex.: "Diagnóstico de Operação")_ |
| ICP-alvo | herda de [icp.md](icp.md) — CEO/fundador bombeiro R$ 1–20M e enterprise ~R$100M |
| outcome cobrável | _(relatório com baseline + 3 candidatos a SKU automatizável)_ |
| preço (one-time) | _R$ ___ |
| time-to-value | _N dias úteis_ |
| evento DELIVERED | `diagnostic.published` |

## SKUs (preencher após o 1º diagnóstico real)
| SKU | outcome (cláusula C2) | ledger | preço | lifecycle | modo |
|---|---|---|---|---|---|
| _(a definir)_ | | billable | | discovery | SHADOW |

> Consumido por: `g2-diagnose` (mapeia candidatos a SKU), `g8-pricing-engine`, `g2-product-supervisor`.
