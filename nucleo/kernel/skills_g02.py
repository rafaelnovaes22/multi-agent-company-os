"""Handlers determinísticos da G02 Produto & Discovery — o cálculo real (não LLM) que
torna a guilda de produto útil: priorização RICE auditável, dimensionamento estatístico
de experimentos e checagem C3 de fit de pricing. Mesmo padrão de skills_finance/custops:
campos no top-level do output, grader genérico valida `expected` de domínio direto.

Registrados via @register de kernel.skills; importado no fim de skills.py.
Assinatura padrão: handler(state, *, llm, store, spec) -> {output, cost_tokens, citations}.
"""
from __future__ import annotations

from .skills import register, _tokens, _spec_citations

# Mapeamento de feature para a camada de pricing de 3 níveis (postura outcome-native).
_TIERS = ("assinatura", "top_up", "outcome_based")
# Teto de C3: custo do outcome <= 25% do preco cobrado em ofertas billable.
_C3_MAX_RATIO = 0.25


def _out(spec, state, fields, rationale_prompt, llm):
    """Monta o retorno padrão: campos calculados + rationale + by + tenant + citations."""
    rationale = llm.complete(rationale_prompt)
    out = dict(fields)
    out["rationale"] = rationale
    out["by"] = spec["id"]
    out["tenant"] = state.get("task", {}).get("tenant_id")
    return {"output": out, "cost_tokens": _tokens(rationale), "citations": _spec_citations(state, spec)}


@register("rice_score")
def rice_score(state, *, llm, store, spec):
    """g2-prioritizer — RICE = (Reach x Impact x Confidence) / Effort, com fonte por fator.

    Confidence vem como fração 0..1. Itens com Confidence < 0.5 sao rebaixados e
    sinalizados para validação em experimento antes de subir no ranking.
    """
    r = state["task"].get("rice", {}) or {}
    reach = r.get("reach", 0) or 0                # alcance (usuarios/periodo)
    impact = r.get("impact", 0) or 0             # 0.25,0.5,1,2,3 (minimo..massivo)
    confidence = r.get("confidence", 0) or 0     # 0..1
    effort = r.get("effort", 0) or 0             # pessoa-mes
    score = round(reach * impact * confidence / effort, 2) if effort > 0 else 0.0
    # Fatores com fonte rastreavel: todo fator declarado tem origem registrada.
    sources = r.get("sources", {}) or {}
    factors = ["reach", "impact", "confidence", "effort"]
    sourced = sum(1 for f in factors if sources.get(f))
    all_sourced = sourced == len(factors)
    low_confidence = confidence < 0.5
    needs_experiment = low_confidence
    status = "rebaixado_experimento" if needs_experiment else ("auditavel" if all_sourced else "sem_fonte")
    return _out(spec, state, {
        "rice_score": score, "reach": reach, "impact": impact, "confidence": confidence,
        "effort": effort, "factors_sourced": sourced, "all_factors_sourced": all_sourced,
        "low_confidence": low_confidence, "needs_experiment": needs_experiment, "status": status,
    }, f"Voce e {spec['id']}: RICE {score} (status {status}, fontes {sourced}/4).", llm)


@register("experiment_sample_size")
def experiment_sample_size(state, *, llm, store, spec):
    """g2-experiment-designer — tamanho de amostra por variante e duração mínima, pré-registrados.

    n por variante para teste de proporcao (z=1.96 a 95%, z=0.84 a 80% poder):
      n = (1.96 + 0.84)^2 * 2 * p(1-p) / mde^2 = 7.84 * 2 * p(1-p) / mde^2.
    Bloqueia start sem metrica guardrail ou se a duracao exceder a janela disponivel.
    """
    e = state["task"].get("experiment", {}) or {}
    p = e.get("baseline_rate", 0) or 0            # taxa base da metrica primaria (0..1)
    mde = e.get("mde", 0) or 0                     # minimo efeito detectavel absoluto (0..1)
    variants = e.get("variants", 2) or 2          # numero de variantes (controle + tratamentos)
    daily = e.get("daily_traffic", 0) or 0        # trafego diario total
    has_guardrail = bool(e.get("guardrail_metric"))
    window = e.get("window_days")                 # janela disponivel (opcional)
    z_sum_sq = (1.96 + 0.84) ** 2                  # = 7.84
    if mde > 0:
        n_per_variant = int(-(-(z_sum_sq * 2 * p * (1 - p)) // (mde ** 2)))  # ceil
    else:
        n_per_variant = 0
    total_n = n_per_variant * variants
    per_variant_daily = daily / variants if variants else 0
    duration_days = int(-(-n_per_variant // per_variant_daily)) if per_variant_daily > 0 else 999
    fits_window = (window is None) or (duration_days <= window)
    can_start = has_guardrail and n_per_variant > 0 and fits_window
    if not has_guardrail:
        decision = "bloqueado_sem_guardrail"
    elif not fits_window:
        decision = "bloqueado_subdimensionado"
    elif can_start:
        decision = "pre_registrado"
    else:
        decision = "bloqueado"
    return _out(spec, state, {
        "sample_size_per_variant": n_per_variant, "total_sample_size": total_n,
        "duration_days": duration_days, "variants": variants, "has_guardrail": has_guardrail,
        "fits_window": fits_window, "can_start": can_start, "decision": decision,
    }, f"Voce e {spec['id']}: n={n_per_variant}/variante, {duration_days}d, decisao {decision}.", llm)


@register("pricing_c3_fit")
def pricing_c3_fit(state, *, llm, store, spec):
    """g2-pricing-product-fit — WTP (Van Westendorp) + checagem C3 (custo <= 25% do preço).

    Preco otimo (OPP) ~ media entre o "caro" e o "barato demais" do Van Westendorp.
    C3: em oferta billable, custo do outcome / preco recomendado deve ser <= 0.25;
    senao a oferta viola C3 e e bloqueada. Mapeia a feature para a camada de pricing.
    """
    pp = state["task"].get("pricing", {}) or {}
    cheap = pp.get("too_cheap", 0) or 0           # preco percebido "barato demais"
    expensive = pp.get("too_expensive", 0) or 0   # preco percebido "caro demais"
    sample = pp.get("sample_size", 0) or 0        # amostra do estudo de WTP
    cost = pp.get("outcome_cost", 0) or 0         # custo do outcome
    billable = bool(pp.get("billable"))
    tier = pp.get("tier", "assinatura")
    if tier not in _TIERS:
        tier = "assinatura"
    recommended_price = round((cheap + expensive) / 2, 2)
    has_wtp = sample > 0 and recommended_price > 0
    c3_ratio = round(cost / recommended_price, 4) if recommended_price > 0 else 1.0
    c3_pass = (not billable) or (c3_ratio <= _C3_MAX_RATIO)
    # Preco minimo para respeitar C3 em oferta billable.
    min_price_c3 = round(cost / _C3_MAX_RATIO, 2) if billable else 0.0
    if not has_wtp:
        status = "sem_wtp"
    elif not c3_pass:
        status = "viola_c3"
    else:
        status = "aprovado"
    blocked = (not has_wtp) or (not c3_pass)
    return _out(spec, state, {
        "recommended_price": recommended_price, "has_wtp": has_wtp, "sample_size": sample,
        "c3_ratio": c3_ratio, "c3_pass": c3_pass, "min_price_c3": min_price_c3,
        "billable": billable, "tier": tier, "blocked": blocked, "status": status,
    }, f"Voce e {spec['id']}: preco {recommended_price}, C3 {c3_ratio} (pass={c3_pass}), {status}.", llm)


# ---------------------------------------------------------------------------
# Burn-down R3 — g2-feedback-router: classificação + roteamento determinístico de feedback.
# Núcleo determinístico (não-LLM): keyword-classify -> guilda-rota -> severidade -> temas.
# ---------------------------------------------------------------------------
_FB_RULES = (
    ("churn_risk", "g1-strategy-supervisor",
     ["cancelar", "cancelamento", "vou sair", "reembolso", "insatisfeito", "decepcion", "piorou", "nunca mais"]),
    ("bug", "g3-eng-supervisor",
     ["erro", "bug", "nao funciona", "não funciona", "quebrou", "travou", "travando", "falha", "crash", "caiu"]),
    ("request", "g2-jobs-to-be-done",
     ["queria", "poderia", "sugest", "gostaria", "adicionar", "faltando", "falta ", "feature", "funcionalidade", "seria bom"]),
    ("elogio", "g7-growth-supervisor",
     ["otimo", "ótimo", "excelente", "adorei", "perfeito", "parabens", "parabéns", "melhor", "incrivel", "incrível", "amei"]),
)


def _classify_feedback(text):
    tl = (text or "").lower()
    for cat, route, kws in _FB_RULES:
        if any(k in tl for k in kws):
            return cat, route
    return "outro", "g2-product-supervisor"


def _fb_severity(cat, text):
    tl = (text or "").lower()
    if cat == "churn_risk":
        return "alta"
    if cat == "bug" and any(k in tl for k in ["critico", "crítico", "todos", "parado", "producao", "produção", "urgente"]):
        return "alta"
    if cat in ("bug", "request"):
        return "media"
    return "baixa"


@register("feedback_route")
def feedback_route(state, *, llm, store, spec):
    t = state["task"]
    fb = t.get("feedback") or {}
    items = fb.get("items", []) or []
    emerging_threshold = int(fb.get("emerging_threshold", 3) or 3)
    routed, by_cat, by_route = [], {}, {}
    for it in items:
        cat, route = _classify_feedback(it.get("text", ""))
        sev = _fb_severity(cat, it.get("text", ""))
        by_cat[cat] = by_cat.get(cat, 0) + 1
        by_route[route] = by_route.get(route, 0) + 1
        routed.append({"id": it.get("id"), "category": cat, "route_guild": route, "severity": sev})
    emerging = sorted([c for c, n in by_cat.items() if n >= emerging_threshold and c != "outro"])
    churn = by_cat.get("churn_risk", 0)
    high_sev = sum(1 for r in routed if r["severity"] == "alta")
    return _out(spec, state, {
        "agent_id": spec["id"], "total": len(items), "routed": routed,
        "counts_by_category": by_cat, "counts_by_route": by_route,
        "emerging_themes": emerging, "churn_risk_count": churn, "high_severity_count": high_sev,
        "requires_human_review": bool(churn or emerging),
    }, f"Voce e {spec['id']}: {len(items)} feedbacks, {churn} churn-risk, emergentes={emerging}.", llm)


# ---------------------------------------------------------------------------
# Burn-down R3-A final - g2-competitor-feature-watch: triagem deterministica de
# sinal competitivo. Rejeita sem fonte publica; dedup; descarta ruido de marketing;
# classifica relevancia (JTBD x ameaca) em recomendacao ignorar/observar/responder e
# roteia. C2: sinal com fonte publica e relevancia classificada (DELIVERED = competitor.signal.committed).
# ---------------------------------------------------------------------------
@register("competitor_signal_triage")
def competitor_signal_triage(state, *, llm, store, spec):
    s = state["task"].get("signal", {}) or {}
    source = s.get("source")
    source_public = bool(s.get("source_public", True)) and bool(source)
    duplicate_of = s.get("duplicate_of")
    substance = bool(s.get("substance", True))
    jtbd = (s.get("jtbd_relevance") or "none").lower()   # core | adjacent | none
    threat = (s.get("threat_level") or "none").lower()   # high | medium | low | none

    if not source_public:
        status, recommendation, routed = "rejeitado_fonte", "ignorar", False
    elif duplicate_of:
        status, recommendation, routed = "duplicado", "ignorar", False
    elif not substance:
        status, recommendation, routed = "ruido", "ignorar", False
    else:
        if threat == "high" or jtbd == "core":
            recommendation = "responder"
        elif threat == "medium" or jtbd == "adjacent":
            recommendation = "observar"
        else:
            recommendation = "ignorar"
        routed = recommendation in ("observar", "responder")
        status = "classificado"

    signal_committed = status == "classificado"
    return _out(spec, state, {
        "agent_id": spec["id"], "source_public": source_public, "is_duplicate": bool(duplicate_of),
        "has_substance": substance, "status": status, "recommendation": recommendation,
        "routed": routed, "signal_committed": signal_committed,
        "requires_human_review": recommendation == "responder",
    }, f"Voce e {spec['id']}: sinal {status} -> {recommendation}.", llm)


@register("jobs_to_be_done")
def jobs_to_be_done(state, *, llm, store, spec):
    """g2-jobs-to-be-done — JTBD com job statement e critérios de switch."""
    jtbd = state["task"].get("jtbd", {}) or {}
    job = jtbd.get("job") or "Quando ... quero ... para ..."
    forces = jtbd.get("forces", {}) or {}
    push = forces.get("push", 0) or 0
    pull = forces.get("pull", 0) or 0
    anxiety = forces.get("anxiety", 0) or 0
    habit = forces.get("habit", 0) or 0
    switch_score = round(push + pull - anxiety - habit, 2)
    will_switch = switch_score > 0
    return _out(spec, state, {
        "job_statement": job, "switch_score": switch_score, "will_switch": will_switch,
        "forces": forces, "artifact_type": state["task"].get("artifact_type") or "jobs-to-be-done.artifact",
        "status": state["task"].get("status") or "ready", "risk": state["task"].get("risk") or "low",
        "requires_human_review": False, "routed_to": state["task"].get("routed_to") or "human-review",
        "handler_kind": "jobs_to_be_done",
    }, f"Voce e {spec['id']}: JTBD switch {switch_score} -> {will_switch}.", llm)


@register("prd_author")
def prd_author(state, *, llm, store, spec):
    """g2-prd-author — PRD com acceptance criteria verificáveis."""
    task = state["task"] or {}
    prd = task.get("prd", {}) or {}
    ac = prd.get("acceptance_criteria", []) or []
    coverage = round(len([c for c in ac if c.get("verifiable")]) / max(1, len(ac)) * 100, 1) if ac else 0.0
    is_complete = coverage == 100.0 and len(ac) >= 3
    return _out(spec, state, {
        "ac_count": len(ac), "verifiable_count": len([c for c in ac if c.get("verifiable")]),
        "coverage": coverage, "is_complete": is_complete,
        "artifact_type": task.get("artifact_type") or "prd.artifact",
        "status": task.get("status") or "ready", "risk": task.get("risk") or "low",
        "requires_human_review": not is_complete, "routed_to": task.get("routed_to") or "human-review",
        "handler_kind": "prd_author",
    }, f"Voce e {spec['id']}: PRD {len(ac)} ACs, coverage {coverage}% -> {is_complete}.", llm)


@register("prototype_builder")
def prototype_builder(state, *, llm, store, spec):
    """g2-prototype-builder — protótipo com escopo e risco técnico."""
    task = state["task"] or {}
    proto = task.get("prototype", {}) or {}
    screens = proto.get("screens", []) or []
    integrations = proto.get("integrations", []) or []
    tech_risk = "high" if len(integrations) > 2 else ("medium" if screens else "low")
    is_buildable = len(screens) > 0 and tech_risk != "high"
    return _out(spec, state, {
        "screen_count": len(screens), "integration_count": len(integrations),
        "tech_risk": tech_risk, "is_buildable": is_buildable,
        "artifact_type": task.get("artifact_type") or "prototype.artifact",
        "status": task.get("status") or "ready", "risk": task.get("risk") or "low",
        "requires_human_review": tech_risk == "high", "routed_to": task.get("routed_to") or "human-review",
        "handler_kind": "prototype_builder",
    }, f"Voce e {spec['id']}: {len(screens)} screens, risco {tech_risk}.", llm)


@register("release_notes")
def release_notes(state, *, llm, store, spec):
    """g2-release-notes — notas de release com lineage de PRs."""
    task = state["task"] or {}
    rel = task.get("release", {}) or {}
    prs = rel.get("prs", []) or []
    with_notes = sum(1 for pr in prs if pr.get("notes"))
    coverage = round(with_notes / max(1, len(prs)) * 100, 1) if prs else 100.0
    is_ready = coverage == 100.0
    return _out(spec, state, {
        "pr_count": len(prs), "with_notes_count": with_notes, "coverage": coverage,
        "is_ready": is_ready,
        "artifact_type": task.get("artifact_type") or "release-notes.artifact",
        "status": task.get("status") or "ready", "risk": task.get("risk") or "low",
        "requires_human_review": not is_ready, "routed_to": task.get("routed_to") or "human-review",
        "handler_kind": "release_notes",
    }, f"Voce e {spec['id']}: {with_notes}/{len(prs)} PRs com notas ({coverage}%).", llm)


@register("roadmap_keeper")
def roadmap_keeper(state, *, llm, store, spec):
    """g2-roadmap-keeper — roadmap com horizonte e OKR alignment."""
    task = state["task"] or {}
    roadmap = task.get("roadmap", {}) or {}
    items = roadmap.get("items", []) or []
    aligned = sum(1 for it in items if it.get("okr_ref"))
    alignment = round(aligned / max(1, len(items)) * 100, 1) if items else 0.0
    horizon_ok = all(it.get("horizon") in ("now", "next", "later") for it in items) if items else True
    return _out(spec, state, {
        "item_count": len(items), "aligned_count": aligned, "alignment": alignment,
        "horizon_ok": horizon_ok,
        "artifact_type": task.get("artifact_type") or "roadmap.artifact",
        "status": task.get("status") or "ready", "risk": task.get("risk") or "low",
        "requires_human_review": not horizon_ok, "routed_to": task.get("routed_to") or "human-review",
        "handler_kind": "roadmap_keeper",
    }, f"Voce e {spec['id']}: {aligned}/{len(items)} alinhados ({alignment}%).", llm)


@register("usability_critic")
def usability_critic(state, *, llm, store, spec):
    """g2-usability-critic — heurísticas de Nielsen com severidade."""
    task = state["task"] or {}
    findings = task.get("findings", []) or []
    critical = sum(1 for f in findings if f.get("severity") == "critical")
    score = round(10 - critical * 2 - len(findings) * 0.5, 1)
    score = max(0.0, min(10.0, score))
    needs_rework = critical > 0 or score < 7
    return _out(spec, state, {
        "finding_count": len(findings), "critical_count": critical, "score": score,
        "needs_rework": needs_rework,
        "artifact_type": task.get("artifact_type") or "usability-critic.artifact",
        "status": task.get("status") or "ready", "risk": task.get("risk") or "low",
        "requires_human_review": needs_rework, "routed_to": task.get("routed_to") or "human-review",
        "handler_kind": "usability_critic",
    }, f"Voce e {spec['id']}: score {score}, critical {critical}.", llm)


@register("interview_synth")
def interview_synth(state, *, llm, store, spec):
    """g2-user-interview-synth — síntese de entrevistas com temas e quotes."""
    task = state["task"] or {}
    interviews = task.get("interviews", []) or []
    themes = {}
    for iv in interviews:
        for t in iv.get("themes", []) or []:
            themes[t] = themes.get(t, 0) + 1
    top_theme = max(themes, key=themes.get) if themes else None
    quote_count = sum(len(iv.get("quotes", []) or []) for iv in interviews)
    return _out(spec, state, {
        "interview_count": len(interviews), "theme_count": len(themes), "top_theme": top_theme,
        "quote_count": quote_count,
        "artifact_type": task.get("artifact_type") or "interview-synth.artifact",
        "status": task.get("status") or "ready", "risk": task.get("risk") or "low",
        "requires_human_review": len(themes) == 0, "routed_to": task.get("routed_to") or "human-review",
        "handler_kind": "interview_synth",
    }, f"Voce e {spec['id']}: {len(interviews)} entrevistas, top {top_theme}.", llm)
