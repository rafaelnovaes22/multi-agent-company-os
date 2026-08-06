"""Handlers determinísticos da G11 Pessoas & Conhecimento — o cálculo real (não LLM)
que torna a guilda de pessoas útil. Mesmo padrão de skills_finance/skills_custops:
campos no top-level do output, grader genérico valida `expected` de domínio direto.

A assinatura é a padrão: handler(state, *, llm, store, spec) -> {output, cost_tokens, citations}.
"""

from __future__ import annotations

from .skills import _spec_citations, _tokens, register

# Pesos do Slope Score (somam 1.0) — os 4 sinais de "slope" do catálogo G11:
# autonomia demonstrada, taxa de aprendizado, breadth (generalista), evidência de shipping.
_SLOPE_WEIGHTS = {"autonomy": 0.30, "learning_rate": 0.25, "breadth": 0.20, "shipping": 0.25}
# Limiar de qualificação (0..100): só entra na short-list quem passa.
_QUALIFY_THRESHOLD = 70.0


def _out(spec, state, fields, rationale_prompt, llm):
    """Monta o retorno padrão: campos calculados + rationale + by + tenant + citations."""
    rationale = llm.complete(rationale_prompt)
    out = dict(fields)
    out["rationale"] = rationale
    out["by"] = spec["id"]
    out["tenant"] = state.get("task", {}).get("tenant_id")
    return {
        "output": out,
        "cost_tokens": _tokens(rationale),
        "citations": _spec_citations(state, spec),
    }


def _slope(c):
    """Slope Score puro de um candidato (0..100) a partir dos 4 sinais (cada um 0..100)."""
    score = 0.0
    for sig, w in _SLOPE_WEIGHTS.items():
        v = c.get(sig, 0) or 0
        score += w * v
    return round(score, 1)


@register("slope_score")
def slope_score(state, *, llm, store, spec):
    """g11-recruiter-sourcer — calcula o Slope Score (autonomia, taxa de aprendizado, breadth,
    shipping) de cada candidato, ranqueia a short-list e qualifica quem passa do limiar.
    Penaliza candidato sem citação de fonte (não pode entrar na short-list — exige evidência)
    e respeita o orçamento de sourcing (inbound preferido a pago)."""
    s = state["task"].get("sourcing", {}) or {}
    candidates = s.get("candidates", []) or []
    target = s.get("target", 5) or 5
    threshold = s.get("threshold", _QUALIFY_THRESHOLD) or _QUALIFY_THRESHOLD

    ranked = []
    for c in candidates:
        sc = _slope(c)
        has_source = bool(c.get("source"))  # citação de fonte obrigatória
        inbound = bool(c.get("inbound"))  # via founder brand (sem custo pago)
        qualified = sc >= threshold and has_source
        ranked.append(
            {
                "name": c.get("name"),
                "slope_score": sc,
                "qualified": qualified,
                "has_source": has_source,
                "inbound": inbound,
            }
        )
    ranked.sort(key=lambda x: -x["slope_score"])

    shortlist = [r for r in ranked if r["qualified"]]
    qualified_count = len(shortlist)
    avg_slope = (
        round(sum(r["slope_score"] for r in shortlist) / qualified_count, 1)
        if qualified_count
        else 0.0
    )
    inbound_count = sum(1 for r in shortlist if r["inbound"])
    inbound_ratio = round(inbound_count / qualified_count, 3) if qualified_count else 0.0
    meets_target = qualified_count >= target
    status = "publicavel" if meets_target else ("parcial" if qualified_count else "vazia")

    return _out(
        spec,
        state,
        {
            "candidate_count": len(candidates),
            "qualified_count": qualified_count,
            "target": target,
            "meets_target": meets_target,
            "avg_slope_score": avg_slope,
            "inbound_ratio": inbound_ratio,
            "top_candidate": shortlist[0]["name"] if shortlist else None,
            "status": status,
            "shortlist": shortlist,
        },
        f"Voce e {spec['id']}: {qualified_count}/{len(candidates)} qualificados (alvo {target}), "
        f"slope medio {avg_slope}, status {status}.",
        llm,
    )


# ---------------------------------------------------------------------------
# Burn-down Track A — g11-interview-scheduler: agenda determinística de entrevistas.
# ---------------------------------------------------------------------------
@register("interview_schedule")
def interview_schedule(state, *, llm, store, spec):
    """g11-interview-scheduler — casa slots, recupera no-show e consolida scorecards."""
    s = state["task"].get("interview_schedule", {}) or {}
    candidates = s.get("candidates", []) or []
    interviewers = s.get("interviewers", []) or []
    required_stages = s.get("required_stages", ["screen", "technical", "founder"]) or []
    interviewer_slots = {}
    for iv in interviewers:
        for st in iv.get("stages", []) or []:
            interviewer_slots.setdefault(st, set()).update(iv.get("slots", []) or [])
    scheduled, stalled, recovered = 0, 0, 0
    decisions_ready = 0
    for c in candidates:
        slots = set(c.get("slots", []) or [])
        no_show = bool(c.get("no_show"))
        has_all = True
        for stage in required_stages:
            if not (slots & interviewer_slots.get(stage, set())):
                has_all = False
        if has_all:
            scheduled += 1
            if no_show and c.get("reschedule_slot") in slots:
                recovered += 1
        else:
            stalled += 1
        scorecards = c.get("scorecards", {}) or {}
        if all(scorecards.get(stage) is not None for stage in required_stages):
            decisions_ready += 1
    scheduled_pct = round(scheduled / len(candidates) * 100, 1) if candidates else 100.0
    status = "ok" if stalled == 0 else "stalled"
    return _out(
        spec,
        state,
        {
            "candidate_count": len(candidates),
            "scheduled_count": scheduled,
            "stalled_count": stalled,
            "scheduled_pct": scheduled_pct,
            "no_show_recovered_count": recovered,
            "decision_artifact_count": decisions_ready,
            "scorecards_complete_pct": (
                round(decisions_ready / len(candidates) * 100, 1) if candidates else 100.0
            ),
            "status": status,
        },
        f"Voce e {spec['id']}: {scheduled}/{len(candidates)} candidatos agendados, status {status}.",
        llm,
    )


# ---------------------------------------------------------------------------
# Burn-down R3-A final - g11-km-curator: curadoria deterministica de conhecimento.
# Precedencia de bloqueio: acesso exposto (confidencial sem controle) > nao classificado
# > duplicata nao resolvida > vencido (flag de freshness) > curado. C2: conhecimento
# canonico, classificado, fresco, com governanca de acesso
# (DELIVERED = artifact.classified && dedup_resolved && access_policy.applied).
# ---------------------------------------------------------------------------
@register("knowledge_curation")
def knowledge_curation(state, *, llm, store, spec):
    d = state["task"].get("document", {}) or {}
    category = d.get("category")
    owner = d.get("owner")
    classified = bool(category and owner)
    duplicate_of = d.get("duplicate_of")
    archived = bool(d.get("archived", False))
    dedup_resolved = (duplicate_of is None) or archived
    sensitive = bool(d.get("sensitive", False))
    access_controlled = bool(d.get("access_controlled", False))
    access_applied = (not sensitive) or access_controlled
    age = float(d.get("age_days", 0) or 0)
    review_period = float(d.get("review_period_days", 0) or 0)
    stale = review_period > 0 and age > review_period

    if not access_applied:
        status = "acesso_exposto"
    elif not classified:
        status = "nao_classificado"
    elif not dedup_resolved:
        status = "duplicata_nao_resolvida"
    elif stale:
        status = "vencido"
    else:
        status = "curado"

    indexable = status == "curado"
    return _out(
        spec,
        state,
        {
            "agent_id": spec["id"],
            "classified": classified,
            "dedup_resolved": dedup_resolved,
            "access_applied": access_applied,
            "stale": stale,
            "flag_owner_review": stale,
            "status": status,
            "indexable": indexable,
            "requires_human_review": status in ("acesso_exposto", "duplicata_nao_resolvida"),
        },
        f"Voce e {spec['id']}: documento {status}.",
        llm,
    )
