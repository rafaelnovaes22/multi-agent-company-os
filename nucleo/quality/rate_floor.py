"""rate_floor — piso de pass-rate do eval-harness (ratchet executável).

Por que existe: o `demo_eval` era só relatório (nunca saía != 0) e o `foundry_check`
é estrutural — não roda as suítes. Com isso, 15 agentes a 0% (lote G01–G03,
2026-08/10) ficaram invisíveis a todos os gates verdes. Este módulo congela o
pass-rate medido por agente em `eval_rate_floor.json` e reprova qualquer run que
fique abaixo do piso — fechar capacidade sem entregar volta a ser visível.

Semântica de ratchet (igual ao `foundry_baseline.json`):
- o piso nunca desce; só se move para cima via `demo_eval --update-floor`,
  e só após melhora genuína (nunca para "passar" escondendo regressão);
- agente novo (sem entrada no piso) reprova até ser congelado — regressão
  desconhecida não entra silenciosa.

Comparação com tolerância EPS do lado de quem passa (poeira de float não reprova).
"""

from __future__ import annotations

import json
import os

FLOOR_FILENAME = "eval_rate_floor.json"
FLOOR_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), FLOOR_FILENAME)

# Poeira de float (round-trip JSON de doubles é exato; a folga é só defesa).
EPS = 1e-9


def _rate(passed: int, total: int) -> float:
    return (passed / total) if total else 0.0


def load_floor(path: str = FLOOR_PATH):
    """Devolve o piso congelado, ou None se o arquivo não existir/estiver ilegível."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or not isinstance(data.get("agents"), dict):
        return None
    return data


def build_floor(reports) -> dict:
    """Congela o estado medido: 1 entrada por agente + TOTAL. reports: [{id, passed, total}]."""
    agents = {}
    tot_p = tot_t = 0
    for r in reports:
        p, t = int(r["passed"]), int(r["total"])
        agents[str(r["id"])] = {"passed": p, "total": t, "rate": _rate(p, t)}
        tot_p += p
        tot_t += t
    return {
        "version": 1,
        "agents": dict(sorted(agents.items())),
        "total": {"passed": tot_p, "total": tot_t, "rate": _rate(tot_p, tot_t)},
    }


def write_floor(path: str, floor: dict) -> None:
    """Serialização determinística (chaves ordenadas): diff revisável, byte-estável."""
    ordered = {
        "version": floor.get("version", 1),
        "agents": dict(sorted(floor["agents"].items())),
        "total": floor["total"],
    }
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(ordered, f, indent=2, ensure_ascii=False)
        f.write("\n")


def check_floor(reports, floor: dict):
    """Compara o medido contra o piso. Devolve (ok, violations: [str])."""
    violations = []
    seen = set()
    for r in reports:
        aid = str(r["id"])
        seen.add(aid)
        p, t = int(r["passed"]), int(r["total"])
        entry = (floor.get("agents") or {}).get(aid)
        if entry is None:
            violations.append(
                f"{aid}: sem piso congelado ({p}/{t}) — agente novo: revise e rode --update-floor"
            )
            continue
        if t == 0:
            violations.append(f"{aid}: sem casos executados — nada a comparar com o piso")
            continue
        if _rate(p, t) + EPS < float(entry["rate"]):
            violations.append(
                f"{aid}: {p}/{t} ({_rate(p, t):.1%}) abaixo do piso "
                f"({entry['passed']}/{entry['total']} = {float(entry['rate']):.1%})"
            )
    tot = floor.get("total") or {}
    tot_p = sum(int(r["passed"]) for r in reports)
    tot_t = sum(int(r["total"]) for r in reports)
    if tot and _rate(tot_p, tot_t) + EPS < float(tot["rate"]):
        violations.append(
            f"TOTAL: {tot_p}/{tot_t} ({_rate(tot_p, tot_t):.1%}) abaixo do piso "
            f"({tot.get('passed')}/{tot.get('total')} = {float(tot['rate']):.1%})"
        )
    return (not violations), violations
