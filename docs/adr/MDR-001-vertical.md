# MDR-001 — Vertical do beachhead

> Market Decision Record (workshop de mercado — [../../06-WORKSHOP-MERCADO.md](../../06-WORKSHOP-MERCADO.md) §6).

- **Data:** 2026-05-29
- **Decisor (AI Founder):** CEO
- **Vertical escolhido:** **Prestadores de serviço B2B** — CNAE **81** (serviços para edifícios / limpeza / facilities) **+ 82** (apoio administrativo, call center, cobrança, BPO). Beachhead: **estado de São Paulo**.
- **Tese em 1 frase:** *"Ajudamos donos de empresas de serviços B2B (limpeza/facilities e apoio administrativo) faturando R$ 1–5M em SP, que vendem bem mas operam no caos, a transformar a operação (ordens de serviço, escala de equipes, cobrança recorrente) em processo legível — medido por outcomes operacionais entregues/dia."*

## Por que este (e não o topo da matriz)
- A matriz ([../../workshop/matriz-scoring.md](../../workshop/matriz-scoring.md)) deu **Contabilidade (91)** no topo; B2B ficou em **83**.
- **Convicção do founder (C8)** — fator de peso 2, input exclusivo da CEO — desempatou a favor de B2B.
- Racional da escolha: **maior densidade de ICP verificada** (33.415 empresas 5–49 em SP, IBGE/CEMPRE 2023 — o maior pool da short-list), regulatório favorável (sem conselho que vede cold outreach), dor de processo aguda e operacional. Aposta **density-first** para escalar descoberta + outreach (Tier 2) rápido.

## Riscos assumidos / hipóteses a validar (PMF treadmill)
- **WTP** do segmento é hipótese (dado refutado na pesquisa) — validar no 1º diagnóstico.
- **Fit-agêntico médio** (C4=3): parte da operação é mundo físico (equipes em campo) — focar nos outcomes *digitais* (ordens, agendamento, cobrança, triagem), não na execução física.
- **Scrapeabilidade Tier 2 setorial** (SEAC-SP/FEBRAC, JUCESP por CNAE) ainda não testada uma a uma.

## Kill-criteria / reavaliação
- Revisar em **90 dias** (PMF treadmill). Sinal de pivot: < 1 diagnóstico cobrável vendido OU agreement_rate do `g2-diagnose` em SHADOW abaixo do threshold OU C3 inviável no 1º SKU.

## Disagree-and-commit
- Registrado por: equipe (matriz apontava Contabilidade; comprometida com B2B por decisão da CEO). Contabilidade e Software/TI ficam como **candidatos de fallback** caso o kill-criteria dispare.

## O que isto destrava (Commit)
- ✅ `nucleo/company/dna.md` — propósito + vertical + north-star
- ✅ `nucleo/company/offerings.md` — Oferta 0 (diagnóstico) + candidatos a SKU B2B
- ✅ `nucleo/company/icp.md` — Tier 2 com targeting CNAE 81/82 em SP
- ⏭ Fábrica: especializar `g2-diagnose` → `g8-lead-qualifier` → `g8-outbound-sdr` para o vertical; rodar em SHADOW; promover por gate
- ⏭ `g12-regulatory-monitor`: confirmar ausência de conselho restritivo + LGPD
