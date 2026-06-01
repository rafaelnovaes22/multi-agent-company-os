"""Handlers determinísticos da G07 Growth & Marketing — o cálculo real (não LLM)
que torna a guilda de growth útil: ROAS/CAC-payback de paid, tamanho de amostra e
significância de experimentos, k-factor/propensity de indicação e atribuição
multitouch reconciliada. Mesmo padrão de skills_finance/skills_custops: campos no
top-level do output, grader genérico de contrato valida `expected` de domínio.

A assinatura é a padrão: handler(state, *, llm, store, spec) -> {output, cost_tokens, citations}.
"""
from __future__ import annotations

import math

from .skills import register, _tokens, _spec_citations


def _out(spec, state, fields, rationale_prompt, llm):
    """Monta o retorno padrão: campos calculados + rationale + by + tenant + citations."""
    rationale = llm.complete(rationale_prompt)
    out = dict(fields)
    out["rationale"] = rationale
    out["by"] = spec["id"]
    out["tenant"] = state.get("task", {}).get("tenant_id")
    return {"output": out, "cost_tokens": _tokens(rationale), "citations": _spec_citations(state, spec)}


@register("paid_roas_cac")
def paid_roas_cac(state, *, llm, store, spec):
    """g7-paid-ads-optimizer — ROAS, CAC, CAC-payback e razão delight/pago.

    Regra de capital do NÚCLEO: gasto pago tem de ser menor que o gasto de delight
    (delight_ratio = paid_spend / delight_spend < 1). Paid só escala se ROAS >= alvo,
    CAC-payback <= limite e a razão delight/pago passar. Criativo fatigado é pausado.
    """
    p = state["task"].get("paid", {}) or {}
    spend = p.get("spend", 0) or 0
    revenue = p.get("revenue", 0) or 0
    conversions = p.get("conversions", 0) or 0
    target_roas = p.get("target_roas", 3.0) or 3.0
    delight_spend = p.get("delight_spend", 0) or 0
    monthly_margin = p.get("monthly_margin_per_customer", 0) or 0
    payback_limit = p.get("payback_limit_months", 12) or 12
    fatigue_ctr_drop = p.get("fatigue_ctr_drop_pct", 0) or 0  # queda de CTR vs baseline

    roas = round(revenue / spend, 2) if spend else 0.0
    cac = round(spend / conversions, 2) if conversions else 0.0
    payback_months = round(cac / monthly_margin, 1) if monthly_margin else 999.0
    delight_ratio = round(spend / delight_spend, 3) if delight_spend else 999.0

    roas_ok = roas >= target_roas
    payback_ok = payback_months <= payback_limit
    delight_ok = delight_ratio < 1.0  # gasto-pago < gasto-delight
    pause_creative = fatigue_ctr_drop >= 30  # >=30% de queda de CTR = fadiga

    if not delight_ok:
        decision = "bloquear_viola_capital"
    elif not roas_ok or not payback_ok:
        decision = "pausar_economics_negativa"
    elif pause_creative:
        decision = "pausar_criativo_fatigado"
    else:
        decision = "escalar"

    status = "escala" if decision == "escalar" else "ajuste"
    return _out(spec, state, {
        "roas": roas, "cac": cac, "cac_payback_months": payback_months,
        "delight_ratio": delight_ratio, "roas_ok": roas_ok, "payback_ok": payback_ok,
        "delight_ok": delight_ok, "pause_creative": pause_creative,
        "decision": decision, "status": status,
    }, f"Voce e {spec['id']}: ROAS {roas} (alvo {target_roas}), CAC-payback {payback_months}m, decisao {decision}.", llm)


@register("ab_sizing_significance")
def ab_sizing_significance(state, *, llm, store, spec):
    """g7-ab-growth-runner — tamanho de amostra (por braço) e significância do teste.

    Desenho válido = amostra mínima definida antes (z-test de duas proporções para
    detectar o MDE com alpha/power dados). Decisão = só promove vencedor se atingiu a
    amostra (sem peeking) E o p-valor cruzou alpha; senão, segue coletando.
    """
    e = state["task"].get("experiment", {}) or {}
    baseline = e.get("baseline_rate", 0) or 0          # conversão do controle (0..1)
    mde = e.get("mde", 0) or 0                          # uplift absoluto detectável (0..1)
    alpha = e.get("alpha", 0.05) or 0.05
    power = e.get("power", 0.8) or 0.8
    # z para teste bicaudal (alpha) e poder (beta)
    z_alpha = {0.05: 1.96, 0.01: 2.576, 0.10: 1.645}.get(round(alpha, 3), 1.96)
    z_beta = {0.8: 0.842, 0.9: 1.282, 0.95: 1.645}.get(round(power, 3), 0.842)

    p1, p2 = baseline, baseline + mde
    pbar = (p1 + p2) / 2
    if mde > 0 and 0 < pbar < 1:
        num = (z_alpha * math.sqrt(2 * pbar * (1 - pbar)) +
               z_beta * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2
        sample_per_arm = math.ceil(num / (mde ** 2))
    else:
        sample_per_arm = 0

    # Leitura do observado (se houver), via z-test de duas proporções
    obs = e.get("observed", {}) or {}
    nc = obs.get("control_n", 0) or 0
    cc = obs.get("control_conv", 0) or 0
    nt = obs.get("treat_n", 0) or 0
    ct = obs.get("treat_conv", 0) or 0
    z_stat, significant, observed_uplift = 0.0, False, 0.0
    if nc > 0 and nt > 0:
        rc = cc / nc
        rt = ct / nt
        observed_uplift = round(rt - rc, 4)
        pooled = (cc + ct) / (nc + nt)
        se = math.sqrt(pooled * (1 - pooled) * (1 / nc + 1 / nt)) if 0 < pooled < 1 else 0.0
        z_stat = round((rt - rc) / se, 3) if se else 0.0
        significant = abs(z_stat) >= z_alpha

    sample_reached = bool(obs) and nc >= sample_per_arm and nt >= sample_per_arm
    if sample_reached and significant:
        decision = "promover_vencedor" if observed_uplift > 0 else "manter_controle"
    elif bool(obs):
        decision = "continuar_coleta"
    else:
        decision = "desenho_pronto"

    return _out(spec, state, {
        "sample_per_arm": sample_per_arm, "z_alpha": z_alpha, "z_beta": z_beta,
        "z_stat": z_stat, "observed_uplift": observed_uplift,
        "significant": significant, "sample_reached": sample_reached, "decision": decision,
    }, f"Voce e {spec['id']}: amostra/braco {sample_per_arm}, z {z_stat}, decisao {decision}.", llm)


@register("referral_kfactor_score")
def referral_kfactor_score(state, *, llm, store, spec):
    """g7-referral-designer — k-factor (coeficiente viral) e Referral Propensity Score.

    k-factor = convites_por_usuario × conversao_do_convite. Viral se k >= 1. Custo de
    delight por indicação convertida tem de caber no orçamento OP. Propensity Score
    (0..100) combina engajamento, NPS e indicações passadas. Fraude sob controle.
    """
    r = state["task"].get("referral", {}) or {}
    users = r.get("users", 0) or 0
    invites = r.get("invites_sent", 0) or 0
    conversions = r.get("invite_conversions", 0) or 0
    delight_cost = r.get("delight_cost", 0) or 0
    op_budget = r.get("op_budget", 0) or 0
    fraud_invites = r.get("fraud_invites", 0) or 0

    invites_per_user = round(invites / users, 3) if users else 0.0
    conv_rate = round(conversions / invites, 4) if invites else 0.0
    k_factor = round(invites_per_user * conv_rate, 4)
    cost_per_conversion = round(delight_cost / conversions, 2) if conversions else 0.0
    budget_ok = delight_cost <= op_budget if op_budget else False
    fraud_rate = round(fraud_invites / invites * 100, 2) if invites else 0.0
    viral = k_factor >= 1.0

    # Referral Propensity Score (0..100) — engajamento/NPS/histórico
    sig = r.get("propensity_signals", {}) or {}
    engagement = sig.get("engagement", 0) or 0      # 0..1
    nps = sig.get("nps", 0) or 0                     # -100..100
    past_referrals = sig.get("past_referrals", 0) or 0
    propensity_score = round(
        min(100.0, max(0.0,
            engagement * 50 + (nps + 100) / 200 * 30 + min(past_referrals, 5) / 5 * 20)), 1)

    if fraud_rate > 5:
        status = "fraude_alta"
    elif not budget_ok:
        status = "estoura_orcamento"
    elif viral:
        status = "viral"
    else:
        status = "abaixo_viral"

    return _out(spec, state, {
        "k_factor": k_factor, "invites_per_user": invites_per_user, "invite_conv_rate": conv_rate,
        "cost_per_conversion": cost_per_conversion, "budget_ok": budget_ok,
        "fraud_rate_pct": fraud_rate, "viral": viral,
        "propensity_score": propensity_score, "status": status,
    }, f"Voce e {spec['id']}: k-factor {k_factor}, propensity {propensity_score}, status {status}.", llm)


@register("attribution_cac_payback")
def attribution_cac_payback(state, *, llm, store, spec):
    """g7-attribution-analyst — atribuição multitouch linear, CAC/payback por canal e
    reconciliação com a fonte de verdade de G6.

    Atribuição linear: cada conversão divide crédito igual entre os touches da jornada.
    CAC por canal = gasto_canal / conversoes_atribuidas. Reconciliação: total atribuído
    tem de fechar com o total de conversões de G6 (tolerância). Double-counting detectado
    quando a soma dos créditos por canal excede o total reconciliado.
    """
    a = state["task"].get("attribution", {}) or {}
    journeys = a.get("journeys", []) or []     # [{"touches": ["paid","social"], "converted": true}]
    spend = a.get("spend", {}) or {}            # {"paid": 1000, ...}
    g6_total = a.get("g6_total_conversions")    # fonte de verdade

    credits = {}
    total_converted = 0.0
    for j in journeys:
        if not j.get("converted"):
            continue
        total_converted += 1
        touches = j.get("touches", []) or []
        if not touches:
            continue
        share = 1.0 / len(touches)
        for t in touches:
            credits[t] = round(credits.get(t, 0) + share, 6)

    attributed_total = round(sum(credits.values()), 4)

    channels = {}
    for ch, cr in credits.items():
        cr_r = round(cr, 4)
        ch_spend = spend.get(ch, 0) or 0
        cac = round(ch_spend / cr_r, 2) if cr_r else 0.0
        channels[ch] = {"credit": cr_r, "spend": ch_spend, "cac": cac}

    # Reconciliação com G6
    if g6_total is not None and g6_total > 0:
        recon_diff_pct = round(abs(attributed_total - g6_total) / g6_total * 100, 2)
        reconciled = recon_diff_pct <= 1.0
    else:
        recon_diff_pct = 0.0
        reconciled = True

    # Double-counting: créditos por canal somam mais que as conversões observadas
    double_counting = round(attributed_total, 4) > round(total_converted, 4) + 1e-6

    # Realocação: maior CAC = candidato a cortar; menor CAC = candidato a reforçar
    ranked = sorted(channels.items(), key=lambda kv: kv[1]["cac"])
    best_channel = ranked[0][0] if ranked else None
    worst_channel = ranked[-1][0] if ranked else None

    return _out(spec, state, {
        "attributed_conversions": attributed_total, "total_converted": round(total_converted, 4),
        "channels": channels, "reconciled": reconciled, "recon_diff_pct": recon_diff_pct,
        "double_counting": double_counting, "best_channel": best_channel,
        "worst_channel": worst_channel, "channel_count": len(channels),
    }, f"Voce e {spec['id']}: {attributed_total} conversoes atribuidas, reconciliado={reconciled}.", llm)


# ---------------------------------------------------------------------------
# Burn-down R2 — C3 runtime enforcement for billable G07 workers
# ---------------------------------------------------------------------------
def _c3_payload(state):
    t = state["task"]
    return t.get("unit_economics") or t.get("economics_check") or t.get("c3") or t


def _c3_out(spec, state, llm, handler_kind, artifact_type, domain_status="ready"):
    econ = _c3_payload(state)
    price = round(float(econ.get("price_brl", econ.get("published_price_brl", 0)) or 0), 2)
    cost = round(float(econ.get("unit_cost_brl", econ.get("delivery_cost_brl", econ.get("inference_cost_brl", 0))) or 0), 2)
    max_ratio = float(econ.get("max_ratio", (spec.get("economics") or {}).get("max_ratio", 0.25)) or 0.25)
    cost_ratio = round(cost / price, 4) if price else 1.0
    c3_ok = cost_ratio <= max_ratio
    min_price = round(cost / max_ratio, 2) if max_ratio else 0.0
    status = "blocked" if not c3_ok else domain_status
    requires_review = bool((not c3_ok) or econ.get("requires_human_review", False))
    return _out(spec, state, {
        "agent_id": spec["id"], "handler_kind": handler_kind, "artifact_type": artifact_type,
        "price_brl": price, "unit_cost_brl": cost, "cost_ratio": cost_ratio,
        "max_ratio": max_ratio, "c3_ok": c3_ok, "min_viable_price_brl": min_price,
        "status": status, "requires_human_review": requires_review,
        "recommended_action": "deliver" if c3_ok else "raise_price_or_reduce_cost",
        "_spec_citations": _spec_citations(state, spec),
    }, f"Voce e {spec['id']}: C3 price={price}, cost={cost}, ratio={cost_ratio}, status={status}.", llm)


@register("copywriter_c3")
def copywriter_c3(state, *, llm, store, spec):
    return _c3_out(spec, state, llm, "copywriter_c3", "copywriter.copy_asset")


@register("lifecycle_crm_c3")
def lifecycle_crm_c3(state, *, llm, store, spec):
    return _c3_out(spec, state, llm, "lifecycle_crm_c3", "lifecycle-crm.campaign")
