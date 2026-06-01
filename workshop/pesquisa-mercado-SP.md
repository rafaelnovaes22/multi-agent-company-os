# Pesquisa de mercado — Estado de SP (rodada 1)

> **Data:** 2026-05-29 · **Método:** deep-research (6 ângulos · 30 fontes · 95 claims → 25 verificados → **21 confirmados / 4 refutados**, verificação adversarial 3-votos).
> **Objetivo:** formar a short-list de verticais (beachhead = estado de SP), ancorada no ICP ([../nucleo/company/icp.md](../nucleo/company/icp.md)).
> **Veredito honesto:** validou a **infraestrutura** (quais fontes oficiais usar) e os **sinais transversais** (dor, maturidade, acessibilidade, regulatório). **NÃO** produziu firmographics por vertical → **ranking rigoroso ainda pendente** (ver §Lacuna).

---

## 1. Achados confirmados (com fonte)

| # | Achado | Conf. | Fonte(s) |
|---|---|---|---|
| 1 | **CEMPRE/IBGE** é a fonte de firmographics por CNAE 2.0 × UF/município (SP incluso). **Não traz faturamento** — só proxy por nº de empregados. Demografia das Empresas cobre só empregadoras. | alta | [SIDRA/CEMPRE](https://sidra.ibge.gov.br/pesquisa/cempre/tabelas), [IBGE Demografia](https://www.ibge.gov.br/estatisticas/economicas/servicos/22649-demografia-das-empresas-e-estatisticas-de-empreendedorismo.html) |
| 2 | SP ~**4,7M pequenos negócios** (~90% dos estabelecimentos); **serviços** é o setor mais concentrado, seguido de comércio. | alta | [Panorama SEBRAE-SP](https://datasebrae.com.br/matriz-panorama-sebrae-sao-paulo/) (base 2020) |
| 3 | **Dor do "bombeiro" comprovada** (centralização no fundador, sem processos, gestão reativa) — mas **transversal aos 12 verticais**. 37% dos donos decidem tudo sozinhos; só 9–10% têm planejamento formal. | alta | ["Cabeça de Dono" Locomotiva/Itaú via Diário do Comércio](https://diariodocomercio.com.br/gestao/confira-cinco-entraves-crescimento-micro-pequenas-empresas/) |
| 4 | **Maturidade digital baixa**: IMD 37/80 (2025); 2/3 das PMEs em nível baixo-médio → espaço para gestão/AI. (nacional) | alta | [SEBRAE IMD 2024](https://sebraepr.com.br/impulsiona/maturidade-digital-dos-pequenos-negocios-no-brasil-2024/), [Exame](https://exame.com/bussola/por-que-99-das-empresas-sao-pmes-mas-maturidade-digital-atinge-apenas-37/) |
| 5 | **Adoção de software subindo**: 47% usam software integrativo (2025); **comércio lidera (53%)** → maior propensão a pagar por software. Reachability digital alta (73–76%). | alta | [SEBRAE digitalização 2025](https://agenciasebrae.com.br/inovacao-e-tecnologia/digitalizacao-recorde-pequenos-negocios-no-brasil-atingem-nivel-historico-em-2025/) |
| 6 | **Tier 2 via JUCESP viável** p/ descoberta: consultas gratuitas; **API Infosimples** filtra por objeto social/município/capital. Atrito: **cap de 15 resultados/consulta** (mitiga-se particionando filtros). | alta | [JUCESP Online](https://www.jucesponline.sp.gov.br/), [Infosimples NIRE](https://infosimples.com/consultas/junta-comercial-sp-nire/) |
| 7 | **Regulatório é o maior diferenciador**: advocacia proíbe captação ativa (cold outreach hostil); saúde tem publicidade rígida; LGPD transversal (legítimo interesse, guia ANPD 2024). | alta | [OAB Prov. 205/2021](https://www.oabsp.org.br/upload/526840268.pdf), [CFM 2.336/2023](https://publicidademedica.cfm.org.br/resolucao/o-que-muda), [ANPD legítimo interesse](https://www.gov.br/anpd/pt-br/centrais-de-conteudo/materiais-educativos-e-publicacoes/guia_orientativo_hipoteses_legais_tratamento_de_dados_pessoais_legitimo_interesse) |

## 2. Matriz regulatória por vertical (aderência a cold outreach)

| Vertical | Aderência a cold outreach | Nota |
|---|---|---|
| Agências, e-commerce/DTC, distribuição/atacado, indústria leve, food service, software houses, prestadores B2B, franqueados | ✅ favorável | sem regulador publicitário restritivo; LGPD legítimo interesse aplicável |
| Serviços profissionais — **contabilidade, arquitetura, engenharia** | ✅ favorável (com etiqueta) | conselhos (CRC/CAU/CREA) sem proibição de captação como a OAB |
| Clínicas/consultórios (**saúde/odonto/estética**) | ⚠️ cautela | CFM 2.336/2023 (publicidade médica), fiscalização CRM-SP |
| Serviços profissionais — **advocacia** | ❌ hostil | OAB Prov. 205/2021 proíbe captação ativa de clientela |

## 3. Acessibilidade Tier 2 — fontes verificadas em SP
- **JUCESP / Infosimples** — descoberta segmentável por objeto social + município + capital (cap 15/consulta). Serve a **qualquer** vertical filtrável por CNAE.
- **ABComm** — diretório público de associados de **e-commerce** ([selos.abcomm.org/associados](https://selos.abcomm.org/associados/)).
- **ABF** — diretório público de associados de **franquias** ([abf.com.br/associados](https://abf.com.br/associados/)).
- **Conselhos (CRC-SP, CREA-SP)** — páginas de consulta existem, mas **scrapeabilidade não confirmada** nesta rodada (fontes não extraíram).

## 4. Firmographics REAIS por vertical (IBGE/CEMPRE, extração 2026-05-29)
Fonte: API SIDRA, **tabela 7528**, UF=SP (35), ano **2023**, var. 2585 (nº de empresas). **Proxy de porte do ICP = faixa 5–49 empregados** ("vende bem, tem equipe"). ⚠️ Faturamento R$1–20M **não é filtrável direto** — CEMPRE usa pessoal ocupado.

| Vertical (CNAE) | **ICP-proxy (5–49)** | Total (todas faixas) | Regulatório (cold outreach) |
|---|---|---|---|
| Varejo (47) \* | 103.510 | 528.236 | ✅ (\*e-commerce é subset não isolável na divisão) |
| Indústria de transformação (C) \* | 49.872 | 158.313 | ✅ (\*"leve" é subset) |
| Prestadores B2B — limpeza+apoio (81+82) | **33.415** | 311.365 | ✅ |
| Food service (56) | **31.998** | 125.998 | ✅ |
| Construção/reforma (41+43) | **20.631** | 145.028 | ✅ |
| Distribuição/atacado (46) | **19.633** | 139.948 | ✅ |
| Clínicas/saúde (86) | 15.838 | 170.167 | ⚠️ CFM 2.336/2023 |
| Educação (85) | 14.272 | 94.433 | ✅ |
| Contabilidade (69.2) | **7.409** | 28.400 | ✅ (ICP clássico) |
| Software houses/TI (62) | 4.322 | 94.006 | ✅ |
| Arquitetura/engenharia (71) | 3.681 | 58.083 | ✅ |
| Advocacia (69.1) | 2.717 | 42.773 | ❌ OAB 205/2021 (corta cold outreach) |
| Agências de marketing (73) | 2.057 | 55.968 | ✅ |

## 5. Short-list por EVIDÊNCIA (densidade × regulatório)
Cortando advocacia (OAB) e marcando saúde (CFM); excluindo supersets não isoláveis na divisão (varejo 47, indústria C). Ordenada por densidade de ICP-proxy com regulatório favorável:
1. **Prestadores B2B** (limpeza+apoio, 81+82) — **33.415**
2. **Food service** (56) — **31.998**
3. **Construção/reforma** (41+43) — **20.631**
4. **Distribuição/atacado** (46) — **19.633**
5. **Contabilidade** (69.2) — **7.409** (ICP clássico: dono-operador, dor de processo aguda)
6. **Software houses/TI** (62) — **4.322** (menor densidade, mas maior WTP e fit-agêntico)

Condicional: **Clínicas/saúde** (15.838 — alta densidade, mas ⚠️ CFM). Fora: **advocacia** (❌ OAB).

**Lacunas remanescentes:** (a) ticket/WTP por vertical — sem fonte confiável (vai à matriz como hipótese); (b) e-commerce e "indústria leve" precisam de nível **classe** (tab. 9418, sem faixas); (c) scrapeabilidade Tier 2 setorial (CRC-SP, ABRASEL, ABComm…) não testada uma a uma.

## 6. Próximos passos (para fechar a short-list)
1. ✅ **FEITO (2026-05-29)** — extração IBGE/CEMPRE (tab. 7528, SP, 2023, faixa 5–49) por vertical concluída (ver §4). Resta isolar e-commerce e "indústria leve" no nível de **classe** (tab. 9418, sem faixas).
2. **Avaliar scrapeabilidade** das fontes Tier 2 **setoriais** uma a uma (ABComm, ABF, CRC-SP, CREA-SP, sindicatos, ABRASEL, feiras) sob LGPD/legítimo interesse.
3. **Buscar fonte primária de WTP** (relatórios SEBRAE de TIC por porte; estudos de SaaS BR) — os de blog foram refutados.

## 7. Refutado (não usar)
- WTP "R$30–70/usuário/mês" e mix "44% ERP / 33% planilhas" → blog Capterra, **reprovados 0-3**.
- "JUCESP não tem API/bulk" → **falso** (Infosimples existe; só tem cap por consulta).

---
*Fontes primárias citadas inline. Vários dados (IMD, adoção, reachability) são **nacionais**, não SP-específicos. Stock SEBRAE-SP é de 2020.*
