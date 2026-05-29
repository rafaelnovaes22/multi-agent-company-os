"""Demo do AgentShield — varre a higiene de toda a frota.

Roda:  python -m nucleo.demo_agentshield
"""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nucleo.security.agentshield import scan_fleet, scan_c8  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))


def main():
    fleet = scan_fleet(os.path.join(ROOT, "guilds"))
    print(f"AgentShield | {len(fleet)} agentes escaneados\n")
    counts = {"high": 0, "med": 0, "low": 0}
    for aid, findings in fleet:
        if not findings:
            print(f"  [LIMPO] {aid}")
            continue
        print(f"  {aid}:")
        for sev, rule, detail in findings:
            counts[sev] = counts.get(sev, 0) + 1
            print(f"      [{sev.upper():<4}] {rule}: {detail}")

    c8 = scan_c8(ROOT)
    print(f"\nC8 (hardcode por tenant no código): {'LIMPO' if not c8 else c8}")
    print(f"\nResumo: high={counts['high']}  med={counts['med']}  low={counts['low']}")
    if counts["high"] == 0:
        print("OK - nenhuma violação HIGH: frota apta a promoção pelo gate de segurança.")
    else:
        print("ATENCAO - violações HIGH bloqueiam promoção (Gate de segurança).")


if __name__ == "__main__":
    main()
