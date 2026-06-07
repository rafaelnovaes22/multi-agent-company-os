"""Handlers determinísticos da G11 Pessoas & Conhecimento — o cálculo real (não LLM)
que torna a guilda de pessoas útil. Mesmo padrão de skills_finance/skills_custops:
campos no top-level do output, grader genérico valida `expected` de domínio direto.

A assinatura é a padrão: handler(state, *, llm, store, spec) -> {output, cost_tokens, citations}.
"""
from __future__ import annotations

from .skills import register, _tokens, _spec_citations

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
    return {"output": out, "cost_tokens": _tokens(rationale), "citations": _spec_citations(state, spec)}


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
        has_source = bool(c.get("source"))                 # citação de fonte obrigatória
        inbound = bool(c.get("inbound"))                   # via founder brand (sem custo pago)
        qualified = sc >= threshold and has_source
        ranked.append({
            "name": c.get("name"),
            "slope_score": sc,
            "qualified": qualified,
            "has_source": has_source,
            "inbound": inbound,
        })
    ranked.sort(key=lambda x: -x["slope_score"])

    shortlist = [r for r in ranked if r["qualified"]]
    qualified_count = len(shortlist)
    avg_slope = round(sum(r["slope_score"] for r in shortlist) / qualified_count, 1) if qualified_count else 0.0
    inbound_count = sum(1 for r in shortlist if r["inbound"])
    inbound_ratio = round(inbound_count / qualified_count, 3) if qualified_count else 0.0
    meets_target = qualified_count >= target
    status = "publicavel" if meets_target else ("parcial" if qualified_count else "vazia")

    return _out(spec, state, {
        "candidate_count": len(candidates),
        "qualified_count": qualified_count,
        "target": target,
        "meets_target": meets_target,
        "avg_slope_score": avg_slope,
        "inbound_ratio": inbound_ratio,
        "top_candidate": shortlist[0]["name"] if shortlist else None,
        "status": status,
        "shortlist": shortlist,
    }, f"Voce e {spec['id']}: {qualified_count}/{len(candidates)} qualificados (alvo {target}), "
       f"slope medio {avg_slope}, status {status}.", llm)

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
    return _out(spec, state, {
        "candidate_count": len(candidates), "scheduled_count": scheduled,
        "stalled_count": stalled, "scheduled_pct": scheduled_pct,
        "no_show_recovered_count": recovered, "decision_artifact_count": decisions_ready,
        "scorecards_complete_pct": round(decisions_ready / len(candidates) * 100, 1) if candidates else 100.0,
        "status": status,
    }, f"Voce e {spec['id']}: {scheduled}/{len(candidates)} candidatos agendados, status {status}.", llm)


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
    return _out(spec, state, {
        "agent_id": spec["id"], "classified": classified, "dedup_resolved": dedup_resolved,
        "access_applied": access_applied, "stale": stale, "flag_owner_review": stale,
        "status": status, "indexable": indexable,
        "requires_human_review": status in ("acesso_exposto", "duplicata_nao_resolvida"),
    }, f"Voce e {spec['id']}: documento {status}.", llm)


# ---------------------------------------------------------------------------
# Burn-down handlers — G11: artefatos de conhecimento/pessoas com lógica de domínio.
# ---------------------------------------------------------------------------
@register("meeting_notes_artifact")
def meeting_notes_artifact(state, *, llm, store, spec):
    """g11-meeting-notetaker — valida consentimento, estrutura decisões/action-items,
    restringe PII e determina se o resumo pode ser indexado no Brain."""
    meeting = state["task"].get("meeting", {}) or {}
    participants = meeting.get("participants", []) or []
    transcript = meeting.get("transcript", []) or []
    decisions = meeting.get("decisions", []) or []
    actions = meeting.get("action_items", []) or []

    consent_ok = all(p.get("consented", False) for p in participants) if participants else False
    pii_detected = bool(meeting.get("pii_detected")) or any(t.get("pii", False) for t in transcript)
    access_restricted = (not pii_detected) or bool(meeting.get("access_restricted"))
    summary_structured = bool(transcript) and (bool(decisions) or bool(actions))
    action_items_routed = all(a.get("owner") and a.get("due") for a in actions) if actions else False
    decisions_count = len(decisions)
    action_item_count = len(actions)

    if not consent_ok:
        status = "blocked_no_consent"
    elif not access_restricted:
        status = "pii_exposed"
    elif actions and not action_items_routed:
        status = "actions_unrouted"
    elif summary_structured:
        status = "indexed"
    else:
        status = "draft"

    indexable = status == "indexed"
    requires_human_review = status != "indexed" or pii_detected or meeting.get("risk") in ("high", "critical")
    return _out(spec, state, {
        "agent_id": spec["id"], "handler_kind": "meeting_notes_artifact",
        "consent_ok": consent_ok, "summary_structured": summary_structured,
        "decisions_count": decisions_count, "action_item_count": action_item_count,
        "action_items_routed": action_items_routed, "pii_detected": pii_detected,
        "access_restricted": access_restricted, "indexable": indexable,
        "status": status, "requires_human_review": requires_human_review,
    }, f"Voce e {spec['id']}: reuniao status {status}, decisoes={decisions_count}, "
       f"acoes={action_item_count}, indexable={indexable}.", llm)


@register("internal_policy_author")
def internal_policy_author(state, *, llm, store, spec):
    """g11-policy-author — checa governança mínima de uma política interna:
    owner/revisão, versionamento, alinhamento à Constituição, jurisdição BR, gate legal
    e guardrail quando a política restringe agentes/dados."""
    policy = state["task"].get("policy", {}) or {}
    refs = set(policy.get("constitution_refs", []) or [])
    topic = str(policy.get("topic", "")).lower()
    topic_tokens = {tok.strip(".,;:!?()[]{}") for tok in topic.replace("/", " ").replace("-", " ").split()}
    owner_set = bool(policy.get("owner") and policy.get("review_date"))
    versioned = bool(policy.get("version"))
    allowed_refs = {"C4", "C5", "C6", "C7", "C8", "LGPD"}
    constitution_aligned = bool(refs) and refs.issubset(allowed_refs)
    br_jurisdiction = policy.get("jurisdiction") == "BR"
    legal_gate_passed = bool(policy.get("legal_review_passed"))
    sensitive_tokens = {"agente", "agentes", "ia", "ai", "dado", "dados", "privacidade", "segurança", "seguranca"}
    needs_guardrail = bool(topic_tokens & sensitive_tokens)
    guardrail_proposed = (not needs_guardrail) or bool(policy.get("guardrail_proposed"))

    if not owner_set:
        status = "owner_review_missing"
    elif not versioned:
        status = "unversioned"
    elif not constitution_aligned:
        status = "constitution_gap"
    elif not br_jurisdiction or not legal_gate_passed:
        status = "legal_gate_blocked"
    elif not guardrail_proposed:
        status = "guardrail_missing"
    else:
        status = "publishable"

    publishable = status == "publishable"
    return _out(spec, state, {
        "agent_id": spec["id"], "handler_kind": "internal_policy_author",
        "owner_and_review_date_set": owner_set, "versioned": versioned,
        "constitution_aligned": constitution_aligned, "br_jurisdiction": br_jurisdiction,
        "legal_gate_passed": legal_gate_passed, "guardrail_proposed": guardrail_proposed,
        "publishable": publishable, "status": status,
        "requires_human_review": not publishable,
    }, f"Voce e {spec['id']}: politica {policy.get('topic', '?')} status {status}.", llm)


@register("job_description_author")
def job_description_author(state, *, llm, store, spec):
    """g11-jd-author — enquadra uma vaga nos 3 arquétipos YC e valida rubrica de slope,
    ownership de outcome, protótipo para IC e bloqueios trabalhistas/anti-discriminação."""
    jd = state["task"].get("job_description", {}) or {}
    archetype = jd.get("archetype")
    valid_archetypes = {"AI Founder", "DRI", "IC/builder-operator"}
    archetype_assigned = archetype in valid_archetypes
    outcomes = jd.get("ownership_outcomes", []) or []
    slope = jd.get("slope_criteria", []) or []
    restricted_terms = jd.get("restricted_terms", []) or []
    rubric_attached = len(slope) >= 3
    ownership_defined = len(outcomes) >= 1
    prototype_required = bool(jd.get("prototype_required")) if archetype == "IC/builder-operator" else True
    compliant_language = len(restricted_terms) == 0
    founder_brand_ready = bool(jd.get("short_post")) and archetype_assigned and compliant_language

    if not archetype_assigned:
        status = "missing_archetype"
    elif not ownership_defined:
        status = "missing_outcome_ownership"
    elif not rubric_attached:
        status = "missing_slope_rubric"
    elif not prototype_required:
        status = "missing_prototype_gate"
    elif not compliant_language:
        status = "compliance_blocked"
    else:
        status = "versioned"

    return _out(spec, state, {
        "agent_id": spec["id"], "handler_kind": "job_description_author",
        "archetype_assigned": archetype_assigned, "archetype": archetype,
        "ownership_defined": ownership_defined, "slope_criteria_count": len(slope),
        "rubric_attached": rubric_attached, "prototype_required": prototype_required,
        "compliant_language": compliant_language, "founder_brand_ready": founder_brand_ready,
        "status": status, "requires_human_review": status != "versioned",
    }, f"Voce e {spec['id']}: JD {jd.get('title', '?')} arquétipo={archetype}, status {status}.", llm)
