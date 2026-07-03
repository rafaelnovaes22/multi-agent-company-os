# Backlog do Hermes — proveniência dos eval-cases (burn-down do `pre_pr_gate`)

> **STATUS (2026-07-03): RETROFIT EXECUTADO — backlog ENCERRADO.** Os **380** casos
> `independent` sem lastro (carimbados nos PRs #66-80, **declarados sem-lastro
> retroativamente** — decisão CEO §6.6) foram rebaixados a `catalog`. O `pre_pr_gate`
> mudou de desenho: **não exige mais** `>=1 independent|human` p/ cálculo (a exigência era
> o combustível do carimbo) e passou a **VALIDAR alegações** (P1c: `independent` exige
> `source` externo OU held-out executável; `human` exige `ratified_by`). Ficam `independent`
> só os 150 exec-backed (5 agentes com oráculo executável validado por execução real).
> Este backlog não deve ser reaberto por rótulo: prova nova = fonte externa ou ratificação.

> **STATUS anterior (2026-06-26): CONGELADO** pelo [PLANO-AJUSTE-ROTA.md](PLANO-AJUSTE-ROTA.md) (§3, "Parar").
> A burn-down de proveniência por **rótulo auto-declarado está SUSPENSA**: `provenance:"independent"`
> escrito pelo próprio Hermes não é prova (o `pre_pr_gate` só confere a string; um caso com
> `rice_score=999999` rotulado `independent` passa). NÃO acionar o Hermes para carimbar `provenance`
> em massa. Prova válida = held-out build/ops/browser (oráculo de fora) OU ratificação humana com
> assinatura/credencial distinta do agente. O `--fleet` é **diagnóstico do humano, não alvo**.
> Retrofit pendente: rebaixar a `catalog` os 380 `independent` não-recomputáveis de fonte externa.

> Tarefa para o **hermes-agent** (loop normal: ramifica de `origin/main`, abre PR, **não** mergeia).
> Origem: o `pre_pr_gate` (regra de ouro #4 do [AGENTS.md](../AGENTS.md)) passou a exigir
> proveniência + prova independente. A frota nasceu sem isso → há um backlog a queimar **PR a PR**.

## Objetivo (revisado — ver STATUS acima)

O objetivo **não** é "zerar o `pre_pr_gate --fleet`" (isso é Goodhart: o gate só checa a string
`provenance`, então zerar o número não prova capacidade). O objetivo é **dar prova INDEPENDENTE real**
onde ela é possível: held-out para build/ops/browser; ratificação humana para os agentes calc de alto
risco (`g8-outbound-sdr`, `g5-threat-modeler`, `g1-scenario-planner`). Onde a prova só puder ser
auto-declarada pelo agente, o caso fica `catalog` (replay honesto) ou a tarefa não vai ao Hermes.
O `--fleet` permanece como diagnóstico do humano. O método abaixo é mantido para referência.

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
