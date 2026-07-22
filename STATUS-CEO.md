# NÚCLEO — Posição do projeto (para a CEO — exemplo: Orbita Labs)

> **Documento de exemplo.** Status report que o framework produz para a CEO de uma venture fictícia ("Orbita Labs"). Nenhuma empresa, pessoa ou cliente real é referenciado.

> **Data:** 2026-05-29 · **Status:** protótipo funcional rodando (prova de conceito), pré-piloto.

## O que é (em uma linha)
Um **sistema multi-agente de gestão** que vendemos ao **fundador-bombeiro** (PME faturando R$ 1–20M ou enterprise ~R$100M, que vende bem mas opera no caos) e que **toca a operação da empresa dele — independentemente do segmento**.

## O que já está de pé (provado em código, hoje)
- **A plataforma**: fábrica que cria agentes a partir de uma “receita”, governança com regras auditáveis, segurança automática e aprendizado contínuo. Multi-cliente (cada cliente é isolado).
- **O produto — 5 agentes de gestão funcionando**, todos testados (100% nos testes):
  - **Caixa/Financeiro** — caixa, inadimplência, margem
  - **Triagem da caixa de entrada** — classifica e direciona cada mensagem
  - **Operações** — o que está parado, atrasado ou sem dono
  - **Atendimento** — fila de respostas e follow-up
  - **Painel do dono** — o “como estou?” num semáforo (verde/amarelo/vermelho)
- **Fluxo de venda→ativação ponta a ponta** (demonstrável): um cliente novo entra, o sistema **diagnostica** a empresa dele e **liga o time de agentes** na conta dele. Hoje rodam **16 demonstrações** completas, offline.

## Por que o cliente (cético) vai confiar
Todo agente **nasce “observando”** (modo sombra): ele sugere, **mas não age** — o dono compara. Só ganha autonomia **passando por aprovações**, no ritmo do cliente. É o antídoto para a desconfiança do bombeiro com automação.

## Onde vamos vender (go-to-market)
- **Cliente-alvo:** o fundador-bombeiro R$ 1–20M e enterprise ~R$100M (definidos por você).
- **Praça inicial:** **Estado de SP**. Pesquisa de mercado (dados oficiais IBGE/SEBRAE) feita: há **milhares** desses fundadores em SP, concentrados em serviços e comércio.
- **Atenção legal:** evitar **advocacia** (a OAB proíbe abordagem ativa) e tratar **saúde** com cautela; os demais setores são livres para prospecção.
- O **produto é horizontal** — quem tem “segmento” é o cliente; nós atendemos qualquer um.

## Economia (a lógica de margem)
- O que o cliente **compra** é controlado para custar **≤ 25% do preço** (margem garantida).
- O que usamos **internamente** roda “quente” (substituímos custo de equipe por custo de IA, muito menor).

## O que ainda falta (honesto)
1. **Conectar à vida real:** hoje roda com IA simulada e dados de exemplo. Falta plugar a **IA de verdade** e as **integrações** (puxar os dados do cliente) — é trabalho conhecido, não risco.
2. **Preço/oferta:** ainda é hipótese; valida-se no **primeiro diagnóstico vendido**.
3. **Primeiro cliente real:** ainda não temos — é o próximo passo.

## Decisões que dependem de você
- **Preço** do diagnóstico de entrada e do pacote de agentes.
- **Foco da prospecção** em SP (quais setores atacar primeiro).
- **Sinal verde** para irmos a um **piloto pago** com 1 cliente real.

## Recomendação / próximo passo
**Vender o diagnóstico (pago) para 1 fundador-bombeiro em SP** e rodar os agentes em modo sombra na conta dele. Em ~2 semanas teremos o primeiro sinal real de valor (e de preço) — sem comprometer mais nada antes disso.

---
*Base técnica: plataforma + 5 agentes de produto + funil de venda, tudo rodando e versionado. Detalhe operacional disponível a pedido.*
