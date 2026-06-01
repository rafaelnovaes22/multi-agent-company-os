---
artifact: icp
tier: L0
version: "0.2.0"
status: active
source: "Decisão ICP Rafael/Hermes 2026-06-01: CEO bombeiro R$1-20M/ano + enterprise ~R$100M/ano"
date: 2026-06-01
loaded_by: nucleo.kernel.loaders.load_icp
---

# ICP — Ideal Customer Profile (NÚCLEO)

> **Tier de contexto:** L0 (estratégico). Carregado uma vez por run e cacheado (helper pattern C5).
> **Nota de mercado:** o **vertical/oferta ainda não está definido** — este documento descreve **quem é o cliente** (perfil de comprador), não o setor. Os campos dependentes de vertical estão marcados *(configurável quando o mercado for definido)*.

## Resumo em uma frase

NÚCLEO atende dois segmentos de ICP: **CEOs/fundadores “bombeiro” de empresas que faturam R$ 1–20 milhões/ano** e **empresas enterprise em torno de R$ 100 milhões/ano** que já vendem bem, mas ainda operam com caos, gargalos de processo e conhecimento espalhado — sempre com vertical/oferta configuráveis e sem hardcode nos agentes.

---

## Segmentos ICP ativos

### Segmento A — CEO bombeiro R$ 1–20M/ano

**Firmográfico**
- Faturamento: **R$ 1M a R$ 20M / ano** (já validou venda; não é ideação).
- Estágio: pós-product-market-fit comercial, pré-maturidade operacional.
- Decisor: o **próprio fundador/sócio/CEO** (compra é founder-led).

**Comportamental (o coração do ICP)**
- Perfil **"bombeiro"**: apaga incêndios o dia todo, faz um monte de coisa ao mesmo tempo.
- Traços de **TDAH** / alta dispersão operacional (boa parte do público).
- **Vende bem** — o gargalo não é receita, é operação/processo.

**Situação / dores**
- **Sem processos bem definidos** apesar de vender bem.
- **Sem infraestrutura para escalar** o que funciona → "começa a ficar maluco".
- Conhecimento e operação concentrados na cabeça do fundador (não é legível, não delega).

**Job-to-be-done (hipótese):** *"Tirar o caos da minha cabeça e transformar o que já vende em processo/infra que roda sem mim."* → encaixa na tese AI-native do NÚCLEO (a empresa que vira processos legíveis e closed-loops).

### Segmento B — Enterprise ~R$ 100M/ano

**Firmográfico**
- Faturamento de referência: **~R$ 100M / ano** (faixa operacional inicial para scoring: aproximadamente R$ 80M–R$ 130M).
- Estágio: empresa já grande o suficiente para múltiplas áreas, dados e aprovações, mas ainda com processos críticos manuais/fragmentados.
- Decisor econômico: liderança executiva/board/C-level; usuário operacional pode estar em Ops, Financeiro, CS, Vendas ou BI.

**Comportamental / dores**
- Dor de processo ainda explícita: retrabalho, fila, conciliação manual, handoff quebrado, baixa visibilidade de status.
- Busca governança, auditabilidade e redução de custo/tempo sem perder controle humano.
- Compra pode envolver comitê/procurement; por isso o produto precisa provar valor por diagnóstico, baseline e evidência no Brain.

**Job-to-be-done (hipótese):** *"Transformar operação crítica e dispersa em workflows auditáveis com agentes em SHADOW/ASSISTED antes de ganhar autonomia."*

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

| ✅ Qualifica | ❌ Desqualifica |
|---|---|
| CEO/fundador bombeiro com fatura R$ 1–20M/ano | Pré-receita / ideação |
| Enterprise em torno de R$100M/ano com dor operacional concreta | Enterprise madura sem dor de processo ou sem dono executivo |
| Founder-led ou com sponsor executivo claro | Compra sem sponsor, apenas curiosidade técnica |
| Vende bem mas não escala a operação | Problema é *vender* (não é nosso ICP primário) |
| Quer tirar o caos da cabeça/processo e aceitar SHADOW/ASSISTED | Não sente a dor de processo/infra ou não aceita evidência/gates |

---

## Quem consome este ICP (conexão com a frota)

Este artefato L0 é a **fonte única** do perfil de cliente. Agentes carregam via `load_icp()` (C5) e **não redefinem** o ICP localmente (C8 — config, não duplicação):

| Agente | Como usa o ICP |
|---|---|
| **g8-lead-qualifier** (G08) | Pontua/qualifica cada lead contra os segmentos CEO bombeiro R$1–20M e enterprise ~R$100M; rejeita fora-do-ICP |
| **g8-outbound-sdr** (G08) | Constrói segmentação e mensagem de **cold B2B outreach** a partir do Tier 2, adaptando ângulo por segmento |
| **g1-market-intel** (G01) | Dimensiona e monitora **onde cada segmento ICP se concentra**; alimenta o Tier 2 (fontes de scraping) |
| **g2-jobs-to-be-done / g2-prd-author** (G02) | Ancoram descoberta e PRD no JTBD do segmento ICP |
| **g7-referral-designer / g7-content-writer** (G07) | Mensagem e indicação miram o perfil "bombeiro/TDAH" e a tese enterprise de governança/evidência (doutrina de growth, [../../05-DOUTRINA-GTM-LOVABLE.md](../../05-DOUTRINA-GTM-LOVABLE.md)) |
| **g10-unit-economist** (G10) | Usa as faixas R$1–20M e ~R$100M para sanidade de willingness-to-pay / C3 |

## Conformidade (C-rules)

- **C5:** L0 estratégico — não lê contexto Tier 2/3; é lido por L1/L2.
- **C8:** ICP é **dado** (este arquivo), nunca `if (cliente === 'x')` em código.
- **C6/LGPD:** dados de leads coletados no Tier 2 são PII — tratados pelos agentes de G05 (g5-lgpd-privacy); este documento **não** guarda dados pessoais reais.

## Pendências (para fechar o ICP)

- [ ] Definir o **vertical/oferta** (destrava os campos *(configurável)* do Tier 2).
- [ ] Validar a faixa de ticket e o pricing por segmento (CEO bombeiro R$1–20M vs enterprise ~R$100M) com g2-pricing-product-fit + g10.
- [ ] Listar as **fontes concretas** de scraping assim que o nicho for escolhido.
