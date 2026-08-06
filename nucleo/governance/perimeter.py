"""G-PERÍMETRO — prova de entrega emitida por CREDENCIAL DISTINTA do promotor.

O guardrail (PLANO-AJUSTE-ROTA §5): "autor != provador" não pode ser git-author (forjável);
quem prova tem de ser um processo com identidade própria, e o gate confia no artefato
apenas se veio daquele perímetro. Aqui o perímetro é o job `foundry-exec (nightly)` do
GitHub Actions rodando em `main`: só quem tem merge em main consegue produzir esse
artefato, e a consulta é feita à API do GitHub (via `gh`), não a um arquivo local que o
promotor poderia escrever.

Uso no G7 (promote.py): `req["delivery_proof"]="ci-perimeter"` troca a execução local ao
vivo pelo artefato do último nightly verde. FAIL-CLOSED por construção: qualquer erro
(gh ausente/não autenticado, sem run verde recente, artifact sem o agente) => None, e o
G7 reprova com o motivo. Nunca degrada silenciosamente para prova local.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile

WORKFLOW = "foundry-exec.yml"
MAX_AGE_DAYS = 7
_TRUSTED_EVENTS = {"schedule", "workflow_dispatch"}


def _gh(args, *, timeout=60):
    """Roda `gh` e devolve stdout, ou None (fail-closed) em qualquer erro."""
    try:
        r = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=timeout)
        return r.stdout if r.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def _latest_green_run(runner):
    out = runner(
        [
            "run",
            "list",
            "--workflow",
            WORKFLOW,
            "--branch",
            "main",
            "--status",
            "success",
            "--limit",
            "5",
            "--json",
            "databaseId,headSha,createdAt,event,workflowName",
        ]
    )
    if not out:
        return None
    try:
        runs = json.loads(out)
    except ValueError:
        return None
    for run in runs:
        if run.get("event") in _TRUSTED_EVENTS:
            return run
    return None


def _too_old(created_at: str) -> bool:
    import datetime

    try:
        created = datetime.datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    except ValueError:
        return True  # timestamp ilegível = não confia
    age = datetime.datetime.now(datetime.UTC) - created
    return age.days >= MAX_AGE_DAYS


def fetch_perimeter_summary(agent_id: str, *, generative: bool = False, runner=_gh):
    """Busca o exec_report do `agent_id` no artifact do último nightly VERDE em main.

    Retorna {"summary": <exec_report summary>, "proof": {run_id, commit, created_at,
    workflow, artifact}} ou None (fail-closed). `generative=True` seleciona o relatório
    da fase geradora (red→green) em vez do replay de fixtures.
    """
    run = _latest_green_run(runner)
    if not run or _too_old(run.get("createdAt") or ""):
        return None
    run_id = str(run.get("databaseId") or "")
    if not run_id:
        return None
    with tempfile.TemporaryDirectory(prefix="perimeter-") as td:
        if (
            runner(["run", "download", run_id, "-n", "verify-in-eval-exec-report", "-D", td])
            is None
        ):
            return None
        for name in sorted(os.listdir(td)):
            if not name.endswith(".json"):
                continue
            try:
                data = json.load(open(os.path.join(td, name), encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if data.get("agent_id") != agent_id:
                continue
            if bool(data.get("generative")) != bool(generative):
                continue
            return {
                "summary": data,
                "proof": {
                    "run_id": run_id,
                    "commit": run.get("headSha"),
                    "created_at": run.get("createdAt"),
                    "workflow": WORKFLOW,
                    "artifact": name,
                },
            }
    return None
