"""Handlers determinísticos da G13 Governança — o cálculo real (não LLM) que torna
cada Guardian da Constituição C1–C8 útil e auditável. Cada handler é puro/determinístico:
mede números a partir de state["task"], aplica thresholds/fórmulas explícitas e devolve
campos no top-level do output (o grader genérico de contrato valida `expected` de domínio
direto, sem grader específico por agente).

Mesmo padrão de skills_finance/skills_custops: assinatura
handler(state, *, llm, store, spec) -> {output, cost_tokens, citations}.
"""

from __future__ import annotations

from .skills import _spec_citations, _tokens, register


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


@register("c3_cost_ratio")
def c3_cost_ratio(state, *, llm, store, spec):
    """g13-unit-economist-guardian — C3 no gate: para BILLABLE veta se custo/preço > 25%;
    para OPERATING não aplica C3 (libera sob tese ROI-vs-headcount/token-max)."""
    c = state["task"].get("c3", {}) or {}
    ledger = c.get("ledger", "billable")
    inf = c.get("inference_cost", 0) or 0
    price = c.get("price", 0) or 0
    max_ratio = c.get("max_ratio", 0.25) or 0.25
    prompt_changed = bool(c.get("prompt_hash_changed"))
    cost_ratio = round(inf / price, 4) if price else 1.0
    if ledger == "operating":
        # ROI-vs-headcount: a conta de tokens alta é aceita se substitui FTEs.
        fte_replaced = c.get("fte_replaced", 0) or 0
        verdict = "liberado_operating" if fte_replaced >= 1 else "rever_roi"
        valid = fte_replaced >= 1
        blocked = False
    else:
        valid = cost_ratio <= max_ratio
        blocked = not valid
        verdict = "pass" if valid else "veto_economico"
    # Drift de custo: prompt_hash mudou -> exige reauditoria antes de manter o modo.
    needs_recalc = prompt_changed
    return _out(
        spec,
        state,
        {
            "ledger": ledger,
            "cost_ratio": cost_ratio,
            "max_ratio": max_ratio,
            "valid": valid,
            "blocked": blocked,
            "verdict": verdict,
            "needs_recalc": needs_recalc,
        },
        f"Voce e {spec['id']}: C3 {ledger} ratio {cost_ratio} (teto {max_ratio}), verdict={verdict}.",
        llm,
    )


@register("mode_gate_score")
def mode_gate_score(state, *, llm, store, spec):
    """g13-promotion-officer — escada C4: promove só com pass@k >= limiar, janela SHADOW >= 14d,
    todos os Guardians PASS e, no caminho-crítico, cross-approval DRI != founder."""
    g = state["task"].get("gate", {}) or {}
    passk = g.get("pass_at_k", 0) or 0
    passk_threshold = g.get("passk_threshold", 0.9) or 0.9
    shadow_days = g.get("shadow_days", 0) or 0
    min_days = g.get("min_shadow_days", 14) or 14
    guardians_pending = g.get("guardians_pending", 0) or 0
    critical_path = bool(g.get("critical_path"))
    dri = g.get("dri_approver")
    founder = g.get("founder_approver")
    drift_pp = g.get("drift_pp", 0) or 0

    # Rebaixamento automático por drift de acurácia.
    if drift_pp <= -5:
        return _out(
            spec,
            state,
            {
                "decision": "rebaixar",
                "promoted": False,
                "blocked": True,
                "pass_at_k": passk,
                "shadow_days": shadow_days,
                "gates_passed": False,
                "cross_approval_ok": False,
                "reason": "drift",
            },
            f"Voce e {spec['id']}: drift {drift_pp}pp -> rebaixar.",
            llm,
        )

    gates_passed = passk >= passk_threshold and shadow_days >= min_days and guardians_pending == 0
    cross_approval_ok = (not critical_path) or (bool(dri) and bool(founder) and dri != founder)
    promoted = gates_passed and cross_approval_ok
    if promoted:
        decision, reason = "promover", "todos os gates PASS"
    elif not gates_passed:
        if passk < passk_threshold:
            reason = "pass@k abaixo do limiar"
        elif shadow_days < min_days:
            reason = "janela SHADOW insuficiente"
        else:
            reason = "guardian pendente"
        decision = "bloquear"
    else:
        decision, reason = "aguardar_cross_approval", "cross-approval DRI!=founder pendente"
    return _out(
        spec,
        state,
        {
            "decision": decision,
            "promoted": promoted,
            "blocked": decision == "bloquear",
            "pass_at_k": passk,
            "shadow_days": shadow_days,
            "gates_passed": gates_passed,
            "cross_approval_ok": cross_approval_ok,
            "reason": reason,
        },
        f"Voce e {spec['id']}: decision={decision}, gates_passed={gates_passed}.",
        llm,
    )


@register("eval_coverage_score")
def eval_coverage_score(state, *, llm, store, spec):
    """g13-eval-engineer-guardian — eval-suite real: >=30 casos, cobre positivos+negativos da
    cláusula, fresca (<=90d) e sem leakage. 'Se não há eval, não há promoção'."""
    e = state["task"].get("eval", {}) or {}
    case_count = e.get("case_count", 0) or 0
    pos_covered = e.get("positive_covered", 0) or 0
    neg_covered = e.get("negative_covered", 0) or 0
    age_days = e.get("age_days", 0) or 0
    leakage = bool(e.get("leakage"))
    min_cases = 30
    has_min_cases = case_count >= min_cases
    covers_clause = pos_covered >= 3 and neg_covered >= 3
    is_fresh = age_days <= 90
    gaps = []
    if not has_min_cases:
        gaps.append(f"apenas {case_count} casos (<{min_cases})")
    if pos_covered < 3:
        gaps.append("positivos da clausula descobertos")
    if neg_covered < 3:
        gaps.append("negativos da clausula descobertos")
    if not is_fresh:
        gaps.append(f"suite com {age_days}d (>90d)")
    if leakage:
        gaps.append("leakage detectado")
    coverage_pct = round((pos_covered + neg_covered) / 6 * 100, 1)
    if coverage_pct > 100:
        coverage_pct = 100.0
    valid = has_min_cases and covers_clause and is_fresh and not leakage
    status = "PASS" if valid else "FAIL"
    return _out(
        spec,
        state,
        {
            "case_count": case_count,
            "coverage_pct": coverage_pct,
            "covers_clause": covers_clause,
            "is_fresh": is_fresh,
            "leakage": leakage,
            "gap_count": len(gaps),
            "gaps": gaps,
            "valid": valid,
            "status": status,
        },
        f"Voce e {spec['id']}: {case_count} casos, cobertura {coverage_pct}%, status {status}.",
        llm,
    )


@register("tenant_hardcode_lint")
def tenant_hardcode_lint(state, *, llm, store, spec):
    """g13-tenant-context-curator — C8: lint config-over-code. Conta hardcodes de tenant
    (if tenantId===, clients/{nome}/), vertical sem marcador e PII de tenant em memória."""
    t = state["task"].get("lint", {}) or {}
    findings = t.get("findings", []) or []
    hardcode_kinds = {"tenant_conditional", "client_folder", "vertical_assumption"}
    hardcode_count = sum(1 for f in findings if f.get("kind") in hardcode_kinds)
    pii_in_memory = any(f.get("kind") == "tenant_pii_in_memory" for f in findings)
    pii_count = sum(1 for f in findings if f.get("kind") == "tenant_pii_in_memory")
    clean = hardcode_count == 0 and not pii_in_memory
    status = "PASS" if clean else "FAIL"
    block_merge = not clean
    return _out(
        spec,
        state,
        {
            "hardcode_count": hardcode_count,
            "pii_in_memory": pii_in_memory,
            "pii_count": pii_count,
            "clean": clean,
            "status": status,
            "block_merge": block_merge,
        },
        f"Voce e {spec['id']}: {hardcode_count} hardcodes, PII={pii_in_memory}, status {status}.",
        llm,
    )


@register("outcomes_traces_delta")
def outcomes_traces_delta(state, *, llm, store, spec):
    """g13-observability-guardian — C6: desvio outcomes<->traces vs teto de 1%; campos canônicos
    do evento e bifurcação ai_enabled (trace LLM) vs audit-log."""
    o = state["task"].get("telemetry", {}) or {}
    outcomes = o.get("outcomes_delivered", 0) or 0
    traces = o.get("traces", 0) or 0
    ai_enabled = bool(o.get("ai_enabled"))
    has_trace = bool(o.get("has_llm_trace"))
    has_audit = bool(o.get("has_audit_log"))
    canonical_fields = bool(o.get("canonical_fields", True))
    max_delta = 0.01
    base = max(outcomes, traces)
    delta = round(abs(outcomes - traces) / base, 4) if base else 0.0
    delta_pct = round(delta * 100, 2)
    # Bifurcação C6: AI exige trace LLM; não-AI exige audit-log. Sem um dos dois -> FAIL.
    telemetry_ok = has_trace if ai_enabled else has_audit
    within_threshold = delta <= max_delta
    valid = within_threshold and telemetry_ok and canonical_fields
    status = "PASS" if valid else "FAIL"
    return _out(
        spec,
        state,
        {
            "outcomes_traces_delta": delta,
            "delta_pct": delta_pct,
            "within_threshold": within_threshold,
            "telemetry_ok": telemetry_ok,
            "canonical_fields": canonical_fields,
            "valid": valid,
            "status": status,
        },
        f"Voce e {spec['id']}: desvio {delta_pct}% (teto 1%), status {status}.",
        llm,
    )


@register("learning_novelty_score")
def learning_novelty_score(state, *, llm, store, spec):
    """g13-learning-curator — curadoria do loop: assess_novelty + escada de confiança (a
    confiança nunca excede o modo do agente) + vetos C1/C6/C7/C8 (PII, hardcode)."""
    l = state["task"].get("learning", {}) or {}
    novelty = l.get("novelty", 0) or 0
    novelty_threshold = l.get("novelty_threshold", 0.3) or 0.3
    confidence = l.get("confidence", "local") or "local"
    agent_mode = l.get("agent_mode", "SHADOW") or "SHADOW"
    has_pii = bool(l.get("has_pii"))
    has_tenant_hardcode = bool(l.get("has_tenant_hardcode"))
    recurrence = l.get("recurrence", 0) or 0  # nº de agentes onde o instinct recorre
    evolve_threshold = l.get("evolve_threshold", 5) or 5

    # Escada de confiança ligada ao modo: confiança não pode exceder o modo do agente.
    ladder = ["local", "shadow", "assisted", "autonomous"]
    mode_to_conf = {
        "SHADOW": "shadow",
        "PILOT": "shadow",
        "ASSISTED": "assisted",
        "AUTONOMOUS": "autonomous",
    }
    max_conf = mode_to_conf.get(agent_mode, "local")
    conf_rank = ladder.index(confidence) if confidence in ladder else 0
    max_rank = ladder.index(max_conf)
    confidence_ok = conf_rank <= max_rank

    is_novel = novelty >= novelty_threshold
    veto_reasons = []
    if has_pii:
        veto_reasons.append("PII na memoria (C1/C8)")
    if has_tenant_hardcode:
        veto_reasons.append("hardcode de tenant (C8)")
    if not is_novel:
        veto_reasons.append("baixa novidade")
    if not confidence_ok:
        veto_reasons.append("confianca excede o modo")
    persist = len(veto_reasons) == 0
    promote_to_skill = persist and recurrence >= evolve_threshold
    return _out(
        spec,
        state,
        {
            "novelty": round(float(novelty), 4),
            "is_novel": is_novel,
            "confidence_ok": confidence_ok,
            "persist": persist,
            "promote_to_skill": promote_to_skill,
            "veto_count": len(veto_reasons),
            "veto_reasons": veto_reasons,
        },
        f"Voce e {spec['id']}: novidade {novelty}, persist={persist}, skill={promote_to_skill}.",
        llm,
    )


@register("audit_drift_score")
def audit_drift_score(state, *, llm, store, spec):
    """g13-monthly-reviewer — auditoria mensal independente: re-amostra 5-10% dos outcomes e
    sinaliza drift (acurácia <=-5pp WARN, custo >=+15%, volume +-30%)."""
    a = state["task"].get("audit", {}) or {}
    total_outcomes = a.get("total_outcomes", 0) or 0
    sample_size = a.get("sample_size", 0) or 0
    divergences = a.get("divergences", 0) or 0
    accuracy_pp = a.get("accuracy_delta_pp", 0) or 0
    cost_pct = a.get("cost_delta_pct", 0) or 0
    volume_pct = a.get("volume_delta_pct", 0) or 0

    sample_rate = round(sample_size / total_outcomes * 100, 1) if total_outcomes else 0.0
    sample_ok = 5.0 <= sample_rate <= 10.0
    divergence_rate = round(divergences / sample_size * 100, 1) if sample_size else 0.0

    flags = []
    if accuracy_pp <= -5:
        flags.append("drift_acuracia")
    if cost_pct >= 15:
        flags.append("drift_custo")
    if abs(volume_pct) >= 30:
        flags.append("drift_volume")
    drift_detected = len(flags) > 0
    # Severidade: acurácia em queda recomenda rebaixamento (P1); demais WARN.
    if "drift_acuracia" in flags:
        severity = "P1"
    elif drift_detected:
        severity = "P2"
    else:
        severity = "OK"
    recommend_demotion = "drift_acuracia" in flags
    return _out(
        spec,
        state,
        {
            "sample_rate": sample_rate,
            "sample_ok": sample_ok,
            "divergence_rate": divergence_rate,
            "drift_detected": drift_detected,
            "flag_count": len(flags),
            "flags": flags,
            "severity": severity,
            "recommend_demotion": recommend_demotion,
        },
        f"Voce e {spec['id']}: amostra {sample_rate}%, drift={drift_detected}, severidade {severity}.",
        llm,
    )
