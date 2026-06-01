# 06 — Workshop de Definição de Mercado (Vertical)

> **Objetivo único:** sair com **1 vertical escolhido** + **a tese em 1 frase** + **o que isso desbloqueia** (com dono e prazo).
> **O que NÃO está em jogo:** o **ICP já está definido** ([nucleo/company/icp.md](nucleo/company/icp.md)) — CEO/fundador bombeiro faturando R$ 1–20M e enterprise ~R$100M com dor operacional concreta. **O comprador é fixo; escolhemos ONDE ele dói mais e onde a gente ganha.**

---

## 1. Por que agora (o que está travado)

O NÚCLEO foi construído **agnóstico de vertical** de propósito (vantagem early-stage YC #8). Hoje a Fábrica e ~169 specs esperam só uma coisa para destravar: **o vertical**. Tudo marcado *"(configurável quando o mercado for definido)"* depende desta decisão — fontes de scraping (Tier 2 do ICP), regulador setorial (g12-regulatory-monitor), oferta/SKU (offerings), e a primeira leva de agentes de negócio da Fábrica.

> Decisão deliberadamente **reversível**: escolhemos o 1º vertical para começar a aprender em produção (PMF treadmill). "Construir o avião em pleno voo." Não é casamento; é o primeiro alvo.

---

## 2. Pré-work — o NÚCLEO escolhe o próprio mercado (dogfooding)

Na **semana anterior**, rode os próprios agentes em **SHADOW** para gerar os insumos da decisão (output não vinculante — alimenta o debate humano). Isto é a empresa usando a si mesma:

| Agente | Insumo que entrega ao workshop |
|---|---|
| `g1-market-intel` | Mapa de **verticais onde o ICP se concentra** (onde existem muitos CEOs bombeiro R$ 1–20M e enterprises ~R$100M com dor operacional) + fontes candidatas de scraping (Tier 2) |
| `g1-opportunity-sizer` | TAM/SAM/SOM preliminar por vertical candidato |
| `g2-jobs-to-be-done` / `g2-user-interview-synth` | Dores de processo/caos por vertical (intensidade da dor) |
| `g6-forecaster` | Estimativa grosseira de willingness-to-pay / dinheiro na mesa |
| `g5-lgpd-privacy` + `g12-regulatory-monitor` | Sinalização de risco regulatório por setor |

**Entregável do pré-work:** um *intel digest* com **8–12 verticais candidatos** já pré-classificados (a long list inicial). Distribuir 48h antes.

> **Kit pronto:** a long-list-semente está em [workshop/long-list-candidatos.md](workshop/long-list-candidatos.md), o template de pesquisa em [workshop/data-pack-template.md](workshop/data-pack-template.md), e o pré-work automatizado roda hoje: `python -m nucleo.demo_prework` (g1-market-intel aplica os hard-filters F1/F2/F4; g1-opportunity-sizer estima TAM/SAM/SOM). Os templates L0 que recebem a decisão já existem: [nucleo/company/offerings.md](nucleo/company/offerings.md) e [nucleo/company/dna.md](nucleo/company/dna.md).

---

## 3. Participantes & papéis (3 arquétipos YC)

| Papel | Quem | Função no workshop |
|---|---|---|
| **AI Founder** | fundador(a)/CEO | facilitador-dono da decisão; tie-break final; guarda da convicção |
| **DRIs** | Produto, Growth, Dados, Vendas | trazem evidência da sua lente; pontuam a matriz |
| **ICs / builder-operators** | 2–4 | apresentam o pré-work dos agentes e **protótipos/dados** (não slides) |

Tamanho ideal: **5–8 pessoas**. Mais que isso, dilui a decisão.

---

## 4. Critérios de decisão (a régua)

### 4.1 Filtros eliminatórios (hard filters) — aplicar ANTES de pontuar
Um candidato que falhe **qualquer** um destes sai da lista (não vai a scoring):

- **F1 — ICP presente:** o vertical concentra CEOs bombeiro R$ 1–20M ou enterprises ~R$100M com dor operacional? (sem isso, não é nosso comprador)
- **F2 — Dor de processo/caos:** a dor central é operação/processo (não "vender")?
- **F3 — Outcome verificável por agente:** dá para definir um outcome cobrável que um agente entrega e que se mede (C2)?
- **F4 — Acessível pelo Tier 2:** existem fontes para achar e fazer cold B2B outreach? (nosso GTM depende disso)

### 4.2 Matriz de pontuação (1–5) × peso
Some `Σ(nota × peso)`. Pontue a short list (5–7 candidatos que passaram nos filtros).

| Critério | Peso | O que avaliar |
|---|---|---|
| Densidade do ICP | 3 | quantos CEOs bombeiro R$1-20M e enterprises ~R$100M há ali |
| Intensidade da dor | 3 | quão aguda é a dor de caos/processo |
| Willingness-to-pay | 3 | dinheiro real na mesa por resolver |
| Fit com stack agêntica | 3 | o problema é "domável" por agentes, com outcome verificável |
| Acessibilidade (Tier 2) | 2 | facilidade de scraping + outreach (qualidade das fontes) |
| Velocidade ao 1º $ | 2 | time-to-first-billable-outcome |
| Defensibilidade / fosso | 2 | marca, dados proprietários, distribuição |
| Convicção do founder | 2 | você "sentaria com os agentes" disso por 3 anos? |
| Risco regulatório (inverso) | 1 | quanto MENOR o risco LGPD/setor, maior a nota |
| TAM / headroom | 1 | espaço para crescer além do 1º nicho |

> **Template de matriz** (preencher ao vivo; ilustrativo — A/B/C são placeholders, **não** sugestões):

| Critério | Peso | Vert. A | Vert. B | Vert. C |
|---|---|---|---|---|
| Densidade do ICP | 3 | _ | _ | _ |
| Intensidade da dor | 3 | _ | _ | _ |
| Willingness-to-pay | 3 | _ | _ | _ |
| Fit com stack agêntica | 3 | _ | _ | _ |
| Acessibilidade (Tier 2) | 2 | _ | _ | _ |
| Velocidade ao 1º $ | 2 | _ | _ | _ |
| Defensibilidade | 2 | _ | _ | _ |
| Convicção do founder | 2 | _ | _ | _ |
| Risco regulatório (inv.) | 1 | _ | _ | _ |
| TAM / headroom | 1 | _ | _ | _ |
| **TOTAL ponderado** | | **_** | **_** | **_** |

---

## 5. Agenda (3h30 — uma sessão; pode quebrar em 2)

| Tempo | Bloco | Como |
|---|---|---|
| 0:00–0:15 | **Abertura** (founder) | objetivo, regra de ouro: ICP é fixo; decidimos o vertical; decisão reversível |
| 0:15–0:35 | **Insumos do NÚCLEO** | ICs apresentam o pré-work dos agentes (digest + sizing + dores) |
| 0:35–1:05 | **Divergência** | brainwriting silencioso → long list de candidatos (sem julgar ainda) |
| 1:05–1:25 | **Hard filters** | aplicar F1–F4; cortar para short list de 5–7 |
| 1:25–2:10 | **Scoring** | cada um pontua a matriz individualmente → consolida média |
| 2:10–2:40 | **Red-team dos top 3** | advogado do diabo: "por que isso falha?"; checar Tier 2 e fit agêntico |
| 2:40–3:00 | **Decisão** | founder decide (tie-break por convicção); **disagree-and-commit** |
| 3:00–3:30 | **Commit** | preencher o Decision Record (§6) + lista do que desbloqueia + dono/prazo |

**Materiais:** o digest do pré-work, a matriz (§4.2), o [icp.md](nucleo/company/icp.md), e este doc. **Notetaker:** `g11-meeting-notetaker` grava e resume → Company Brain (a decisão fica queryable).

---

## 6. Saída — Market Decision Record (preencher no fim)

```md
# MDR-001 — Vertical escolhido
- Data:
- Decisor (AI Founder):
- Vertical escolhido:
- Tese em 1 frase: "Ajudamos [ICP] em [vertical] a [outcome] — medido por [métrica]."
- Top 3 avaliados e por que este venceu:
- Riscos assumidos / hipóteses a validar (PMF treadmill):
- Kill-criteria revisão: em [data] reavaliamos; sinal de pivot = [métrica abaixo de X]
- Disagree-and-commit registrado por:
```
> Persistir como `docs/adr/` (ADR no espírito C-rules) **e** no Company Brain via notetaker.

---

## 7. O que a decisão DESBLOQUEIA (checklist pós-workshop)

Com o vertical escolhido, a Fábrica destrava. Donos/prazos no Commit:

- [ ] **`nucleo/company/icp.md` Tier 2** — preencher as **fontes reais de scraping** e canais de outreach do vertical *(dono: DRI Growth + g1-market-intel)*
- [ ] **`nucleo/company/offerings.md`** — criar o **catálogo de oferta** (o loader `load_offerings` já existe) começando pelo **diagnóstico C1** do vertical *(dono: DRI Produto)*
- [ ] **`nucleo/company/dna.md`** — registrar propósito/north-star do vertical *(dono: AI Founder)*
- [ ] **`g12-regulatory-monitor`** — setar o regulador setorial *(dono: DRI Legal)*
- [ ] **Catálogo** — trocar as marcações *"(configurável quando o mercado for definido)"* pelas escolhas reais *(dono: quem mantém o catálogo)*
- [ ] **Fábrica** — fabricar a 1ª guilda de negócio do vertical e o 1º **SKU billable** (nasce em SHADOW; promove por gate) *(dono: DRI Eng)*
- [ ] **North-star** — instanciar o "Daily Active Outcomes" do vertical *(dono: g6-metrics-modeler)*

> Regra C1 (diagnose-before-build): o **primeiro entregável** no vertical é um **diagnóstico cobrável**, não um produto. Vende-se o diagnóstico, aprende-se a dor real, depois a Fábrica constrói o SKU.

---

## 8. Armadilhas a evitar

- ❌ **Escolher por hype** (vertical "quente") ignorando densidade do ICP.
- ❌ **Pular o Tier 2:** vertical lindo mas impossível de achar/abordar = morto no GTM.
- ❌ **Dor de venda, não de processo:** se o cliente precisa *vender mais*, não é nosso ICP.
- ❌ **Outcome não-verificável:** se não dá pra escrever a cláusula C2, a Fábrica não materializa.
- ❌ **Decisão por comitê:** o founder decide; o resto é disagree-and-commit.
- ❌ **Tratar como irreversível:** é o 1º alvo, com kill-criteria e data de reavaliação.

---

## 9. Pós-workshop (primeiras 2 semanas)

1. Executar o checklist §7 (donos/prazos do Commit).
2. Fábrica materializa o **agente de diagnóstico** do vertical → roda em SHADOW.
3. `g1-market-intel` + `g8-outbound-sdr` começam a achar e abordar o ICP no vertical (Tier 2 real).
4. Primeiro **diagnóstico cobrável** vendido = primeiro sinal de PMF → alimenta o learning loop.

> Conecta ao roadmap em [04-IMPLEMENTACAO.md](04-IMPLEMENTACAO.md) (Fase 2→3) e à doutrina em [05-DOUTRINA-GTM-LOVABLE.md](05-DOUTRINA-GTM-LOVABLE.md).
