"""Gate para artifacts JSON do `forge-exec` (VERIFY-IN-EVAL F6).

O `exec_report.json` é a fonte machine-readable para crédito de entrega real. Este
módulo valida um ou mais artifacts e retorna exit code != 0 quando o nightly não
pode creditar delivery com execução de verdade.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class GateResult:
    checked: int
    failures: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failures

    def render(self) -> str:
        if self.ok:
            return f"VERIFY-IN-EVAL artifact gate OK — {self.checked} artifact(s) OK"
        lines = [
            f"VERIFY-IN-EVAL artifact gate FAILED — {len(self.failures)} issue(s) in {self.checked} artifact(s):"
        ]
        lines.extend(f"- {failure}" for failure in self.failures)
        return "\n".join(lines)


def _load_json(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: artifact root must be an object")
    return data


def _agent_label(path: str | Path, data: dict) -> str:
    return f"{Path(path).name} ({data.get('agent_id') or 'unknown-agent'})"


def _artifact_failures(path: str | Path, data: dict) -> list[str]:
    label = _agent_label(path, data)
    failures: list[str] = []
    credit = data.get("execution_credit") or {}
    can_credit = credit.get("can_credit_delivery") is True
    credited = int(credit.get("credited_deliveries") or 0)
    reason = credit.get("reason") or "unknown"
    total = int(data.get("total") or 0)
    executed = int(data.get("executed_count") or 0)
    failed = int(data.get("tests_failed_count") or 0)

    rows = data.get("rows")
    if not isinstance(rows, list):
        failures.append(f"{label}: rows_missing_or_not_list")
        rows = []
    rows_count = len(rows)
    executor = data.get("executor") or {}
    executor_available = executor.get("available") is True

    if total <= 0:
        failures.append(f"{label}: total=0")
    if not executor_available:
        failures.append(f"{label}: executor_unavailable reason={reason}")
    if not can_credit:
        failures.append(f"{label}: can_credit_delivery=false reason={reason}")
    if credited <= 0:
        failures.append(f"{label}: credited_deliveries=0 reason={reason}")
    if total > 0 and credited != total:
        failures.append(f"{label}: credited_deliveries={credited}/{total}")
    if total > 0 and executed != total:
        failures.append(f"{label}: executed_count={executed}/{total} reason={reason}")
    if total > 0 and rows_count != total:
        failures.append(f"{label}: rows_count={rows_count}/{total}")
    if failed > 0:
        failures.append(f"{label}: tests_failed_count={failed}")

    for row in rows:
        status = row.get("execution_credit")
        if status != "credited":
            row_id = row.get("id") or "unknown-row"
            failures.append(f"{label}: row {row_id}: {status or 'missing_execution_credit'}")
    return failures


def evaluate_paths(paths: Iterable[str | Path]) -> GateResult:
    failures: list[str] = []
    checked = 0
    for path in paths:
        checked += 1
        try:
            data = _load_json(path)
            failures.extend(_artifact_failures(path, data))
        except Exception as exc:  # noqa: BLE001 — gate deve reportar artifact ruim sem traceback ruidoso
            failures.append(f"{Path(path).name}: invalid artifact ({exc})")
    return GateResult(checked=checked, failures=failures)


def _parse(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Valida artifacts JSON do VERIFY-IN-EVAL forge-exec.")
    parser.add_argument("artifacts", nargs="+", help="Caminhos dos exec_report*.json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse(argv)
    result = evaluate_paths(args.artifacts)
    print(result.render())
    return 0 if result.ok else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
