---
type: project
description: Checkpoint evolução
---

# Checkpoint — multi-agent-company-os — 2026-08-06 20:30 UTC

Onde paramos:
- Repo rafaelnovaes22/multi-agent-company-os, branch main, HEAD 0d90be8, working tree limpo
- 15 commits evolução G01+G02+G03 (58→43, -15): G01(4) + G02(7) + G03(4: docs_lookup, planner, refactorer, integration_builder) — handler real + 1 human ratified_by + BASELINE-CHANGE.md
- T1: bin/test usa .venv-uv com fallback, bin/setup PRE_COMMIT_HOME=/tmp/pre-commit — bin/test 196 OK, bin/setup 2x OK
- T2: .agents/ ignorado (.gitignore), 380KB untracked limpo
- T3: ruff --fix + black lote isolado (120 fix, 100 reformat, skills.py circular fix)
- G03 handlers em skills_g03.py (docs_lookup, planner, refactorer, integration_builder) + specs + cases 30+1

Medido agora (não estimado):
- .venv-uv/bin/python -m unittest discover -s tests -> 196 OK, 3 skipped
- bash bin/test -> 196 OK (PY=.venv-uv/bin/python)
- pre_pr_gate OK (4 agentes G03); foundry_check OK 43/43 (baseline encolheu 47→43)
- mypy nucleo --ignore-missing-imports -> 83 erros em 20 arquivos (era 79)
- ruff check . -> 150 erros (137 em nucleo, 133 E501); ruff check nucleo -> 137
- black --check . -> 2 arquivos a reformatar (skills.py, skills_g03.py); era 107 antes do lote
- 15 supervisors grandfathered (não evoluir), tools_nao_enforcadas 169, sem_security_cases 81

Próximo:
- Continuar burn-down 43→0: G03 restantes (3 code-reviewers + build-error etc) + G04/G05/G07/G11/G12/G14 + gateways lote a lote
- ruff E501 manual, mypy 83, black 2 pendentes para lote isolado futuro
- PRE_COMMIT_HOME=/tmp/pre-commit já ativo
