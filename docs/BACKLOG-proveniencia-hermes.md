# Backlog do Hermes — proveniência dos eval-cases (burn-down do `pre_pr_gate`)

> Tarefa para o **hermes-agent** (loop normal: ramifica de `origin/main`, abre PR, **não** mergeia).
> Origem: o `pre_pr_gate` (regra de ouro #4 do [AGENTS.md](../AGENTS.md)) passou a exigir
> proveniência + prova independente. A frota nasceu sem isso → há um backlog a queimar **PR a PR**.

## Objetivo

Zerar o `python -m nucleo.quality.pre_pr_gate --fleet` (hoje: **111 handlers determinísticos**
sem `provenance`; 99 calc, 7 build c/ oracle, 5 build s/ oracle). Cada agente, quando regularizado,
sai da lista. **Trabalhe por guilda, em PRs pequenos** (1 guilda ou poucos agentes por PR).

## O que fazer em cada agente determinístico

1. **Recompute independente.** Leia `spec.yaml` (outcome_clause, KPIs, regras de domínio),
   `soul.md` e as **entradas** dos casos. **NÃO leia o handler** (`nucleo/kernel/skills_*.py`) —
   o ponto é autorar a prova de fora, não copiar o handler.
2. **Rotule `provenance` em CADA caso** (chave no nível do caso, irmã de `expected`):
   - recomputação bate com o `expected` atual → `"provenance": "independent"`;
   - `expected` é decisão/rótulo derivável do spec mas não numericamente recomputável → `"provenance": "catalog"`;
   - recomputação **diverge** → `"provenance": "catalog"` **e registre o bug** (ver §Bugs), **sem alterar o `expected`**.
3. **Garanta ≥1 caso `independent`** por agente **calc** (é o que o gate exige como prova independente).
4. **Build (guilda G03 / agentes com `oracle`):** a prova independente é o **critério held-out** em
   `oracle` (`heldout_files`/`structure`/`browser`/`bug_markers`), que o agente nunca vê. Os 7 que já
   têm `oracle` só precisam de `provenance`. Os **5 sem** (`g3-api-contract`, `g3-db-schema`,
   `g3-dependency-warden`, `g3-feature-flagger`, `g3-perf-optimizer`) precisam de held-out **autorado
   com cuidado** — trate-os à parte, um PR dedicado por agente.

## Regras de integridade (NÃO viole — lições de uma tentativa que regrediu)

- **A ÚNICA mudança permitida no `cases.json` é ADICIONAR `provenance`** (e, só em build, `oracle`).
  **Nunca** altere `expected`, entradas, `desc`, ordem ou quantidade de casos.
- **NUNCA adicione `oracle` a agente calc (não-G03).** O gate reclassifica qualquer agente com
  `oracle` como "build" e passa a exigir held-out — além de o `demo_eval` tentar verificar o held-out
  e **falhar**. `oracle` é exclusivo de agentes build.
- `provenance` é chave do **caso**, nunca dentro de `expected`.
- Edite preservando o conteúdo exatamente; mantenha JSON válido.

## Definition of Done (por PR)

Tudo verde, na ordem do [AGENTS.md §3](../AGENTS.md):

```bash
python -m nucleo.quality.pre_pr_gate     # escopado ao diff — os agentes do PR devem passar
python -m nucleo.quality.forge_check     # ratchet intacto
rm -rf nucleo/.brain* .brain* && python -m nucleo.demo_eval   # DEVE seguir 5042/5042 (100%)
python -m unittest discover -s tests
```

Se o `demo_eval` cair de 100%, **algo não-aditivo vazou** (provavelmente `oracle` em calc, ou
`expected` alterado) — reverta e refaça aditivo.

## Bugs candidatos já encontrados (recompute independente) — investigar à PARTE

Estes vieram de um passe de recomputação; **não foram corrigidos** (a regra é não alterar `expected`).
Cada um merece análise própria (corrigir o handler **ou** o `expected`, com caso held-out):

| Agente | Caso | Divergência | Leitura |
|---|---|---|---|
| `g8-outbound-sdr` | ob-05/10/15/20 | lead `disqualified` mas `expected` pede sequência completa | **bug provável** — contraria o soul (não prospectar fora do ICP) |
| `g5-threat-modeler` | domain-10 | `risk_score` 65 vs 75 (off-by-10) | bug de dado provável; level/downstream batem |
| `g1-scenario-planner` | sp-03 | `spread_pct` 53.3 vs 50.0 | 53.3 não deriva de fórmula limpa — revisar |
| `g2-pricing-product-fit` | wtp-20 | `c3_pass` em preço=0 | decisão de domínio defensável — confirmar regra |
| `g4-load-tester` | lt-01/05/08/10/16/24/30 | convenção de percentil p50/p95 (nearest-rank) | inconsistência de convenção; veredito final bate |

Não são bugs: `g2-experiment-designer` exp-07 e `g7-attribution-analyst` aa-23 (apenas arredondamento de float).

## Por que assim (e não em massa)

Carimbar `provenance: catalog` em massa para o gate ficar verde **é o eval-theater que o gate existe
para impedir**. O valor está no recompute honesto: o rótulo `independent` só vale quando alguém
reproduziu o resultado **fora** do handler. Por isso é trabalho por agente, gated, PR a PR.
