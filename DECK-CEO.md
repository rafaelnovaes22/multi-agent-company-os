# NÚCLEO — Deck para a CEO

> Empresa AI-native (espírito big-techs AI-first + Lovable no **modelo operacional**, mercado nosso, **vertical a definir**). Não é slide: **roda**.

---

## 1. A tese
A Lovable fez **US$400M ARR em 14 meses com 146 PESSOAS** e quase zero mídia paga. O NÚCLEO leva ao próximo nível: **onde a Lovable usou 146 pessoas, operamos com ~169 agentes + uma camada humana fina** (1 AI Founder + ~6 DRIs + ~4 ICs).

## 2. O que construímos (em 3 camadas)
- **Constituição (C1–C8)** — governança auditável (do agent-governance-framework).
- **Frota** — **14 guildas, ~169 agentes** (1 template + ~169 specs; a Fábrica materializa).
- **Runtime LangGraph** — cada agente é um grafo com estado, gate de aprovação humana e telemetria.
- **Aprendizado** — self-harness + instincts (do ECC): os agentes **evoluem ganhando autonomia**.

## 3. Como escala sem caos
`supervisor-raiz → 14 supervisores de guilda → ~12 workers cada`. O "gerente" é um agente (YC #5 — sem middleware humano).

## 4. A economia (resolve token-max × margem)
Dois livros-razão: **OPERATING** (trabalho interno, medido por ROI-vs-headcount — rode quente) e **BILLABLE** (output vendido, travado por C3: custo ≤ 25% do preço).

## 5. Como o agente "evolui aprendendo"
Nasce em **SHADOW** (não entrega/cobra) → prova concordância em gates → **PILOT → ASSISTED → AUTONOMOUS**. Aprender = subir na escada de confiança.

## 6. O cliente (ICP, definido hoje)
- **Segmento A:** CEO/fundador faturando **R$ 1–20M**, perfil "bombeiro"/TDAH, **vende bem mas opera no caos**.
- **Segmento B:** enterprise faturando **~R$100M**, com dor operacional concreta e necessidade de governança/evidência.
- *(vertical/oferta a definir — tudo agnóstico até lá.)*

## 7. Growth (doutrina Lovable adaptada)
Founder brand · beeswarming amplificado por agentes · freemium como verba de marketing · ship diário · "o agente É a ativação" · marca como fosso · **Constituição de Growth GR1–GR10**.

---

## 8. PROVA — está rodando hoje (offline, sem custo)
Cinco comandos provam a tese inteira ponta a ponta:

| Comando | O que prova |
|---|---|
| `python -m nucleo.demo` | Guardian de governança (g13-po-guardian) validando contratos de outcome em SHADOW |
| `python -m nucleo.demo_g8` | Agente de negócio (g8-lead-qualifier) qualificando leads **ancorado no ICP** |
| `python -m nucleo.demo_assisted` | **Human-in-the-loop**: o agente propõe, o DRI aprova/rejeita (interrupt) |
| `python -m nucleo.demo_g08_pipeline` | **Supervisor de guilda**: lead → qualifier → (se qualified) → outbound-sdr |
| `python -m nucleo.demo_hermes` | **Evoluir aprendendo**: snapshots → fatos de memória → o agente lembra |
| `python -m nucleo.demo_evolve` | **/evolve**: o aprendizado de 1 agente vira skill de toda a empresa |

Evidências geradas: eventos no **Company Brain** (`nucleo/.brain/events/events.jsonl`), memória dos agentes crescendo, skills evoluídas em `nucleo/company/skills/`.

## 9. Estado e próximos passos
- **Sprint 0 entregue e rodando:** kernel + Fábrica + 2 guildas-piloto (governança e vendas) + ICP + supervisor + learning loop + /evolve.
- **A seguir:** mais guildas via Fábrica (a partir de specs), Brain em Postgres+pgvector, Operator Console, e promoção dos agentes do caminho-crítico até o **MVP** (roadmap em [04-IMPLEMENTACAO.md](04-IMPLEMENTACAO.md)).

## 10. O pedido
Convicção desenvolve-se **sentando com os agentes** (YC). O próximo marco é definir o **vertical** e deixar a Fábrica fabricar as guildas de negócio rumo ao MVP.

---
*Plano completo: [README.md](README.md) · [02-ARQUITETURA.md](02-ARQUITETURA.md) · [03-CATALOGO-AGENTES.md](03-CATALOGO-AGENTES.md) · [05-DOUTRINA-GTM-LOVABLE.md](05-DOUTRINA-GTM-LOVABLE.md) · código em [nucleo/](nucleo/)*
