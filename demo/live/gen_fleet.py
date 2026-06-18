"""Gera o array FLEET (com descrição direta de cada agente) a partir dos specs.

Lê todos os `nucleo/guilds/**/spec.yaml`, extrai a cláusula de outcome (C2) como
descrição objetiva e emite JSON pronto para injetar no `index.html`.

    python demo/live/gen_fleet.py            # imprime JSON no stdout
    python demo/live/gen_fleet.py --write    # reescreve o bloco FLEET no index.html
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

import yaml

FRONT = Path(__file__).resolve().parent
REPO = FRONT.parents[1]
GUILDS = REPO / "nucleo" / "guilds"


def short(text: str, limit: int = 160) -> str:
    """Normaliza o statement em uma frase única, enxuta e sem boilerplate."""
    t = " ".join((text or "").split())
    # remove o template "<Título> entrega <slug>.artifact verificável para: <ação>"
    m = re.search(r"verific[áa]vel para:\s*(.+)$", t, flags=re.IGNORECASE)
    if m:
        t = m.group(1)
    t = t[:1].upper() + t[1:] if t else t
    if len(t) > limit:
        cut = t[:limit].rsplit(" ", 1)[0]
        t = cut.rstrip(".,;:") + "…"
    return t


def build() -> list[dict]:
    fleet = []
    for spec_path in GUILDS.glob("*/*/spec.yaml"):
        spec = yaml.safe_load(spec_path.read_text(encoding="utf-8")) or {}
        clause = (spec.get("outcome_clause") or {})
        fleet.append({
            "id": spec.get("id") or spec_path.parent.name,
            "guild": spec.get("guild") or "",
            "tier": spec.get("tier") or "",
            "handler": spec.get("act_handler") or "spec_driven",
            "ledger": spec.get("ledger") or "operating",
            "desc": short(clause.get("statement", "")),
        })
    fleet.sort(key=lambda a: (a["guild"], a["id"]))
    return fleet


def main() -> None:
    fleet = build()
    payload = json.dumps(fleet, ensure_ascii=False)
    if "--write" in sys.argv:
        html_path = FRONT / "index.html"
        html = html_path.read_text(encoding="utf-8")
        new = re.sub(r"const FLEET = \[.*?\];",
                     "const FLEET = " + payload + ";",
                     html, count=1, flags=re.DOTALL)
        if new == html:
            sys.exit("bloco `const FLEET = [...]` não encontrado no index.html")
        html_path.write_text(new, encoding="utf-8")
        print(f"index.html atualizado · {len(fleet)} agentes com descrição")
    else:
        print(payload)


if __name__ == "__main__":
    main()
