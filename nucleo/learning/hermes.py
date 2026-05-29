"""Hermes Learning Loop — fecha o ciclo "evoluir aprendendo" (YC#2 / self-harness).

Roda fora do caminho de execução (cron). Lê os snapshots gravados pelos agentes,
extrai fatos (instincts), avalia novidade contra a MEMORY atual, e persiste os
fatos novos na memória do agente — que a PRÓXIMA execução já carrega.

Pipeline (ver 02-ARQUITETURA.md §4 e 04-IMPLEMENTACAO.md §2.6):
    parse_snapshot -> extract_instincts -> assess_novelty -> decide_persist -> persist (PR de memória)

Confiança do fato sobe com o modo em que foi observado (C4): SHADOW->shadow, etc.
"""
from __future__ import annotations


def mode_to_confidence(mode: str) -> str:
    return {"SHADOW": "shadow", "PILOT": "shadow",
            "ASSISTED": "assisted", "AUTONOMOUS": "autonomous"}.get(mode, "local")


def extract_instincts(snap: dict) -> list:
    """Deriva fatos acionáveis do snapshot (ECC instincts). Determinístico/offline.
    Com LLM real, esta função usaria llm.complete para generalizar padrões."""
    facts = []
    out = snap.get("output") or {}

    # Padrões de um Guardian de outcome (g13-po-guardian)
    if "verdict" in out:
        v = out.get("verdict") or {}
        if not v.get("valid") and v.get("missing"):
            facts.append("Specs reprovadas costumam faltar: " + ", ".join(v["missing"]) + ".")
        elif v.get("valid"):
            facts.append("Spec com statement + 3 positivos + 3 negativos + delivered_event passa na validação C2.")

    # Padrões de um qualificador de leads (g8-lead-qualifier)
    if "decision" in out:
        sig = out.get("icp_fit_signals") or {}
        if out.get("decision") == "disqualified" and sig.get("ops_madura"):
            facts.append("Operação já madura desqualifica o lead mesmo com faturamento na faixa R$1-5M.")
        if out.get("decision") == "disqualified" and not sig.get("faturamento_1a5M"):
            facts.append("Fora da faixa de faturamento R$1-5M é um motivo frequente de descarte.")
        if out.get("decision") == "qualified" and (out.get("score") or 0) >= 75:
            true_sig = [k for k, val in sig.items() if val]
            facts.append(f"Sinais {true_sig} produzem lead high-fit (score>=75 -> trilha assistida).")

    return facts


def assess_novelty(fact: str, existing: list) -> bool:
    """True se o fato ainda não está coberto pela memória atual (dedup simples por texto)."""
    norm = fact.lower().strip()
    return not any(norm in str(e).lower() for e in existing)


def run_hermes(store, brain, agent_ids=None, verbose: bool = True) -> dict:
    if agent_ids is None:
        agent_ids = store.subdirs(("snapshots",))

    summary = {"agents": {}, "total_proposed": 0, "processed_snapshots": 0}

    for aid in agent_ids:
        existing = [str(x) for x in store.search(("agent", aid, "memory"))]
        proposed = []

        for key, snap in list(store.items(("snapshots", aid))):
            if snap.get("processed"):
                continue
            summary["processed_snapshots"] += 1
            conf = mode_to_confidence(snap.get("mode", "SHADOW"))
            for fact in extract_instincts(snap):
                pool = existing + [p["fact"] for p in proposed]
                if assess_novelty(fact, pool):
                    proposed.append({"fact": fact, "confidence": conf,
                                     "run_id": snap.get("run_id"),
                                     "date": (snap.get("ts", "") or "")[:10]})
            snap["processed"] = True               # idempotência: não reprocessa
            store.put(("snapshots", aid), key, snap)

        # "PR de memória": persiste os fatos novos na MEMORY do agente (a próxima run carrega)
        for i, p in enumerate(proposed):
            line = f"§ [confidence:{p['confidence']}] [{p['date']}] [run:{p['run_id']}] {p['fact']}"
            store.put(("agent", aid, "memory"), f"learned-{p['run_id']}-{i}", line)

        brain.emit_event({
            "actor": "hermes-learning-loop", "action": "memory_proposed",
            "target_agent": aid, "facts_count": len(proposed),
            "facts": [p["fact"] for p in proposed],
        })

        summary["agents"][aid] = proposed
        summary["total_proposed"] += len(proposed)
        if verbose:
            print(f"  {aid}: +{len(proposed)} fato(s)")
            for p in proposed:
                print(f"     § [confidence:{p['confidence']}] {p['fact']}")

    return summary
