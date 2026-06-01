---
artifact: icp
tier: L0
version: "0.1.0"
status: draft
source: "Mensagem de voz (WhatsApp PTT) 2026-05-29 — transcrição em C:/tmp/ptt_2026-05-29_transcricao.txt"
date: 2026-05-29
loaded_by: nucleo.kernel.loaders.load_icp
---

# ICP — Ideal Customer Profile (NÚCLEO)

> **Tier de contexto:** L0 (estratégico). Carregado uma vez por run e cacheado (helper pattern C5).
> **Nota de mercado:** o **vertical/oferta ainda não está definido** — este documento descreve **quem é o cliente** (perfil de comprador), não o setor. Os campos dependentes de vertical estão marcados *(configurável quando o mercado for definido)*.

## Resumo em uma frase

São **dois** perfis de comprador: **(ICP-1) fundadores R$ 1–20 milhões/ano** que **vendem bem mas operam no caos** (perfil "bombeiro"/TDAH, sem processo) — canal de distribuição = **PCG** (Programa de Crescimento Guiado da the CEO); e **(ICP-2) organizações enterprise >R$ 100 milhões/ano** (inclui **setor público**), **desorganizadas em processos**, com **time grande e custo de pessoal alto substituível por agentes Acme**.

> A faixa **R$ 20–100M (mid-market)** fica **fora dos dois alvos por enquanto** (decisão CEO 2026-05-30: atacar os dois extremos primeiro). O produto é o mesmo; o **pitch e o motion de venda mudam** (PCG = canal quente, ciclo curto; enterprise/público = procurement/licitação, ciclo longo, narrativa de substituição de custo).

---

## Tier 1 (ICP-1) — Bombeiro / PCG (quem compra)

**Firmográfico**
- Faturamento: **R$ 1M a R$ 20M / ano** (já validou venda; não é ideação).
- Estágio: pós-product-market-fit comercial, pré-maturidade operacional.
- Decisor: o **próprio fundador/sócio** (compra é founder-led).
- **Canal:** mentorados do **PCG** (audiência quente, pré-qualificada) — dispensa prospecção fria. Tese: *"PCG ensina o que fazer; Acme é o headcount que executa."*

**Comportamental (o coração do ICP)**
- Perfil **"bombeiro"**: apaga incêndios o dia todo, faz um monte de coisa ao mesmo tempo.
- Traços de **TDAH** / alta dispersão operacional (boa parte do público).
- **Vende bem** — o gargalo não é receita, é operação/processo.

**Situação / dores**
- **Sem processos bem definidos** apesar de vender bem.
- **Sem infraestrutura para escalar** o que funciona → "começa a ficar maluco".
- Conhecimento e operação concentrados na cabeça do fundador (não é legível, não delega).

**Job-to-be-done (hipótese):** *"Tirar o caos da minha cabeça e transformar o que já vende em processo/infra que roda sem mim."* → encaixa na tese AI-native do NÚCLEO (a empresa que vira processos legíveis e closed-loops).

---

## Tier 1-B (ICP-2) — Enterprise / Setor público (quem compra)

**Firmográfico**
- Faturamento: **> R$ 100M / ano** (ou **órgão público**, independente de faturamento).
- **Time grande** (muitas pessoas) e **custo de pessoal alto**.
- Decisor: comitê / procurement (enterprise) ou **licitação** (setor público) — ciclo longo.

**Situação / dores**
- **Desorganizada em processos** apesar do porte.
- Funções caras e repetitivas **substituíveis por soluções Acme** (redução de headcount/custo).
- Setor público: desorganização estrutural = alvo de alto potencial.

**Job-to-be-done (hipótese):** *"Cortar custo de folha e organizar processos sem um projeto de transformação de anos."* → narrativa de **substituição de custo** (não "dar braços", como no ICP-1).

> **Motion distinto:** compliance pesado, procurement/licitação, ciclo de meses. O time e o material de venda **não** são os mesmos do PCG. Sequência recomendada: **PCG primeiro** (valida rápido e barato), **enterprise como segunda frente**.

---

## Tier 2 — Onde encontrá-los (descoberta / sourcing)

> "É a gente entender **onde estão essas pessoas**, onde a gente faz o *scraping*, de onde estão, e como conectar — fazer um **cold B2B outreach** para achá-las."

- **Mapear onde o ICP se concentra** *(configurável quando o mercado for definido)*: comunidades, eventos, plataformas, marketplaces, redes do nicho.
- **Scraping / enriquecimento** de listas a partir dessas fontes (sinais firmográficos + comportamentais).
- **Cold B2B outreach** segmentado por sinal de dor (caos operacional, crescimento sem processo).

### Fontes verificadas — SP (pesquisa 2026-05-29, ver [../../workshop/pesquisa-mercado-SP.md](../../workshop/pesquisa-mercado-SP.md))
- **JUCESP / API Infosimples** — descoberta de fundadores em SP filtrável por objeto social + município + capital (consultas gratuitas; cap de 15 resultados/consulta → particionar filtros).
- **Diretórios setoriais públicos:** ABComm (e-commerce), ABF (franquias). Conselhos (CRC-SP/CREA-SP/CRM-SP) com scrapeabilidade ainda não confirmada.
- **Base legal do outreach (LGPD):** legítimo interesse (Art. 7, IX) com teste de balanceamento — guia ANPD (2024). Não usar dados sensíveis.
- **Atenção regulatória por setor:** advocacia veda captação ativa (OAB 205/2021); saúde tem publicidade restrita (CFM 2.336/2023).

---

## Sinais de qualificação / desqualificação

**ICP-1 (bombeiro / PCG)**

| ✅ Qualifica | ❌ Desqualifica |
|---|---|
| Fatura R$ 1–20M/ano | Pré-receita / ideação (<R$1M) |
| Fundador "bombeiro", sem processo | Operação já madura, time de ops estruturado |
| Vende bem mas não escala a operação | Problema é *vender* (não é nosso ICP) |
| Decisão founder-led | Faixa R$ 20–100M (mid-market, fora do alvo) |
| Quer tirar o caos da cabeça | Não sente a dor de processo/infra |

**ICP-2 (enterprise / setor público)**

| ✅ Qualifica | ❌ Desqualifica |
|---|---|
| Fatura > R$ 100M/ano ou órgão público | Faixa R$ 20–100M (mid-market, fora do alvo) |
| Desorganizada em processos | Processos já maduros/automatizados |
| Time grande, custo de pessoal alto | Custo de folha baixo (pouco a substituir) |
| Aceita ciclo de procurement/licitação | — |

---

## Quem consome este ICP (conexão com a frota)

Este artefato L0 é a **fonte única** do perfil de cliente. Agentes carregam via `load_icp()` (C5) e **não redefinem** o ICP localmente (C8 — config, não duplicação):

| Agente | Como usa o ICP |
|---|---|
| **g8-lead-qualifier** (G08) | Pontua/qualifica cada lead contra os sinais ✅/❌ deste documento; rejeita fora-do-ICP |
| **g8-outbound-sdr** (G08) | Constrói segmentação e mensagem de **cold B2B outreach** a partir do Tier 2 e das dores |
| **g1-market-intel** (G01) | Dimensiona e monitora **onde o ICP se concentra**; alimenta o Tier 2 (fontes de scraping) |
| **g2-jobs-to-be-done / g2-prd-author** (G02) | Ancoram descoberta e PRD no JTBD do ICP |
| **g7-referral-designer / g7-content-writer** (G07) | Mensagem e indicação miram o perfil "bombeiro/TDAH" (doutrina de growth, [../../05-DOUTRINA-GTM-LOVABLE.md](../../05-DOUTRINA-GTM-LOVABLE.md)) |
| **g10-unit-economist** (G10) | Usa as faixas R$ 1–20M (ICP-1) / >R$ 100M (ICP-2) para sanidade de willingness-to-pay / C3 |

## Conformidade (C-rules)

- **C5:** L0 estratégico — não lê contexto Tier 2/3; é lido por L1/L2.
- **C8:** ICP é **dado** (este arquivo), nunca `if (cliente === 'x')` em código.
- **C6/LGPD:** dados de leads coletados no Tier 2 são PII — tratados pelos agentes de G05 (g5-lgpd-privacy); este documento **não** guarda dados pessoais reais.

## Pendências (para fechar o ICP)

- [ ] Definir o **vertical/oferta** (destrava os campos *(configurável)* do Tier 2).
- [ ] Validar a faixa de ticket e o pricing contra a faixa R$ 1–5M (g2-pricing-product-fit + g10).
- [ ] Listar as **fontes concretas** de scraping assim que o nicho for escolhido.
