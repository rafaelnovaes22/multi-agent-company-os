# CLAUDE.md — NÚCLEO (Company-OS)

> Regras imperativas para qualquer agente. Leia antes de codar. Leia `AGENTS.md` para doutrina completa.

## Comandos (copie-e-cole)

```bash
bin/setup                              # idempotente — instala deps, valida offline
bin/test                               # suíte completa — único comando, parseável
python -m nucleo.quality.pre_pr_gate   # HARD-FAIL proveniência + held-out
python -m nucleo.quality.foundry_check # definition-of-done + baseline ratchet
python -m nucleo.demo                  # end-to-end SHADOW offline (sem LLM)
ai-jail --dry-run --verbose -- python -m nucleo.quality.foundry_check  # inspecionar sandbox
```

## Regras de ouro

1. **Branch de `origin/main`**: `git fetch && git switch -c <branch> origin/main` — nunca clone defasado.
2. **Gate é `foundry_check`**, não `demo_eval` verde.
3. **Traduza `catalogo/G00-G14.md`**, não invente — guardians/tools/KPIs vêm do catálogo.
4. **Proveniência obrigatória**: todo eval-case `provenance ∈ {catalog,human,independent}` + critério held-out (`oracle`) — sem `replay`.
5. **Hermes é auditor**, nunca autor — não materializa agente nem faz merge.

## Estrutura

```
nucleo/{kernel,factory,governance,guilds,quality,learning,company}
catalogo/G00-14.md  # specs dos 169 agentes
tests/              # unittest discover -s tests
docs/               # contratos, planos
demo/live/          # Dockerfile + deploy Railway
```

## Gates

- `pre_pr_gate` escopado ao diff vs `origin/main` — reprova antes de PR.
- `foundry_check` varre 169 agentes vs `nucleo/quality/foundry_baseline.json` (só encolhe).
- LLM offline por padrão (`FakeLLMProvider`); provider real só com `LLM_PROVIDER` setado (C7).

## Anti-padrões

- Handler `spec_driven`/`guardian_check` para agente que promete cálculo → proibido (implemente em `nucleo/kernel/skills_g*.py`).
- `delivered`/`billing_amount` em `expected` sob SHADOW → proibido.
- Crescer `foundry_baseline.json` sem `BASELINE-CHANGE.md` → proibido.
