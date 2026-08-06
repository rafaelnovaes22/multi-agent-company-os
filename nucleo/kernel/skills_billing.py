"""skills_billing — handlers financeiros e ops (G10/G09) extraídos de skills.py."""
from __future__ import annotations

from .skills_registry import register, _tokens, _spec_citations

def _ratio(numerator, denominator):
    return round((numerator / denominator), 4) if denominator else None


def _pct(numerator, denominator):
    return round((numerator / denominator) * 100, 2) if denominator else 0.0


def _money(value):
    return round(float(value or 0), 2)


def _max_ratio(spec, task, default=0.25):
    economics = (spec.get("economics") or {}) | ((task.get("economics") or {}) if isinstance(task.get("economics"), dict) else {})
    return float(economics.get("max_ratio", default) or default)


# ---------------------------------------------------------------------------
# Fase 3 — handlers determinísticos para agentes críticos de negócio.
# Variações de mercado/tenant/imposto entram no payload/spec (C8).
# ---------------------------------------------------------------------------
@register("pricing_engine")
def pricing_engine(state, *, llm, store, spec):
    t = state["task"]
    pricing = t.get("pricing", {}) or {}
    max_ratio = _max_ratio(spec, t)
    outcome_price = _money(pricing.get("outcome_price_brl", pricing.get("proposed_price_brl")))
    unit_cost = _money(pricing.get("unit_cost_brl", pricing.get("delivery_cost_brl")))
    subscription = _money(pricing.get("subscription_brl"))
    topup = _money(pricing.get("topup_unit_price_brl"))
    ratio = _ratio(unit_cost, outcome_price)
    min_outcome_price = _money(unit_cost / max_ratio) if max_ratio else 0.0
    c3_ok = bool(outcome_price and ratio is not None and ratio <= max_ratio)
    version = pricing.get("price_book_version") or t.get("price_book_version") or "draft"
    requires_review = bool(pricing.get("risk") in ("high", "critical") or not c3_ok or t.get("blocked"))
    status = "approved" if c3_ok and not t.get("blocked") else "blocked"
    tiers = {"subscription_brl": subscription, "topup_unit_price_brl": topup, "outcome_price_brl": outcome_price}
    rationale = llm.complete(f"Voce e {spec['id']}. Pricing {version}: C3 ratio={ratio}, max={max_ratio}, status={status}.")
    return {"output": {"agent_id": spec["id"], "handler_kind": "pricing_engine", "price_book_version": version, "tiers": tiers,
                       "published_price_brl": outcome_price, "delivery_cost_brl": unit_cost,
                       "unit_cost_brl": unit_cost, "cost_ratio": ratio, "c3_ratio": ratio, "max_ratio": max_ratio,
                       "c3_margin_check": c3_ok, "c3_ok": c3_ok, "min_viable_price_brl": min_outcome_price,
                       "min_outcome_price_brl": min_outcome_price, "requires_human_review": requires_review,
                       "status": status, "recommended_action": "publish" if status == "approved" else "raise_price_or_reduce_cost",
                       "rationale": rationale, "by": spec["id"]},
            "cost_tokens": _tokens(rationale), "citations": ["pricing:payload", "economics:C3"]}


@register("billing_agent")
def billing_agent(state, *, llm, store, spec):
    t = state["task"]
    billing = t.get("billing", {}) or {}
    tax_policy = billing.get("tax_policy") or t.get("tax_policy") or spec.get("tax_policy") or {}
    tax_rate = float(tax_policy.get("tax_rate", 0.0) or 0.0)
    charges = billing.get("charges", []) or []
    billable = [c for c in charges if c.get("billable", True) and (c.get("delivered", True) or c.get("tier") != "outcome")]
    blocked_undelivered = [c.get("id") for c in charges if c.get("tier") == "outcome" and c.get("billable", True) and not c.get("delivered", False)]
    subtotal = _money(sum(float(c.get("amount_brl", 0) or 0) for c in billable))
    tax = _money(subtotal * tax_rate)
    total = _money(subtotal + tax)
    invoice_id = billing.get("invoice_id") or f"inv-{t.get('account_id', spec['id'])}"
    status = "blocked" if blocked_undelivered else "issued"
    rationale = llm.complete(f"Voce e {spec['id']}. Invoice {invoice_id}: subtotal={subtotal}, tax_rate={tax_rate}, status={status}.")
    return {"output": {"agent_id": spec["id"], "invoice_id": invoice_id, "status": status,
                       "billable_charge_count": len(billable), "blocked_undelivered_count": len(blocked_undelivered),
                       "subtotal_brl": subtotal, "tax_rate": tax_rate, "tax_brl": tax, "total_brl": total,
                       "tiers_billed": sorted({c.get("tier", "other") for c in billable}),
                       "audit_log_required": True, "rationale": rationale, "by": spec["id"]},
            "cost_tokens": _tokens(rationale), "citations": ["billing:payload", "tax_policy:configured"]}


@register("dunning_agent")
def dunning_agent(state, *, llm, store, spec):
    t = state["task"]
    policy = (t.get("dunning_policy") or t.get("policy") or {})
    invoices = (t.get("dunning", {}) or {}).get("invoices", []) or []
    threshold = float(policy.get("legal_review_amount_brl", policy.get("escalation_amount_brl", 5000)) or 5000)
    escalation_days = float(policy.get("escalation_days", 60) or 60)
    overdue = [i for i in invoices if i.get("status") not in ("paid", "recovered") and (i.get("overdue_days", i.get("days_overdue", 0)) or 0) > 0]
    attempts = []
    recovery_amount = _money(sum(float(i.get("amount_brl", 0) or 0) for i in overdue))
    max_days = max([i.get("overdue_days", i.get("days_overdue", 0)) or 0 for i in overdue] or [0])
    recovered_count = sum(1 for i in invoices if i.get("status") == "recovered")
    escalated_count = 0
    for inv in overdue:
        days = inv.get("overdue_days", inv.get("days_overdue", 0)) or 0
        stage = "friendly_reminder" if days <= 7 else ("firm_reminder" if days <= 30 else ("renegotiate" if days <= 60 else "legal_review"))
        if days >= escalation_days or float(inv.get("amount_brl", 0) or 0) >= threshold:
            escalated_count += 1
        attempts.append({"invoice_id": inv.get("id"), "stage": stage, "amount_brl": _money(inv.get("amount_brl"))})
    in_progress_count = max(0, len(overdue) - escalated_count)
    requires_human_review = bool(escalated_count)
    recovery_status = "recovered" if recovered_count and not overdue else ("escalated" if escalated_count else ("in_progress" if overdue else "current"))
    status = "escalate" if requires_human_review else ("run_cycle" if attempts else "no_overdue")
    rationale = llm.complete(f"Voce e {spec['id']}. Dunning: {len(overdue)} overdue, amount={recovery_amount}, status={status}.")
    return {"output": {"agent_id": spec["id"], "handler_kind": "dunning_agent", "invoice_count": len(invoices),
                       "total_overdue_brl": recovery_amount, "recovered_count": recovered_count,
                       "in_progress_count": in_progress_count, "escalated_count": escalated_count,
                       "recovery_status": recovery_status, "overdue_count": len(overdue), "attempt_count": len(attempts),
                       "recovery_amount_brl": recovery_amount, "max_overdue_days": max_days,
                       "requires_human_review": requires_human_review, "status": status, "attempts": attempts,
                       "rationale": rationale, "by": spec["id"]},
            "cost_tokens": _tokens(rationale), "citations": ["dunning:payload", "policy:configured"]}


@register("revenue_reporter")
def revenue_reporter(state, *, llm, store, spec):
    t = state["task"]
    rev = t.get("revenue", {}) or {}
    starting = _money(rev.get("starting_mrr_brl", rev.get("prior_mrr_brl")))
    new_mrr = _money(rev.get("new_mrr_brl"))
    expansion = _money(rev.get("expansion_mrr_brl", rev.get("expansion_brl")))
    contraction = _money(rev.get("contraction_mrr_brl", rev.get("contraction_brl")))
    churn = _money(rev.get("churned_mrr_brl", rev.get("churn_brl")))
    ending = _money(starting + new_mrr + expansion - contraction - churn)
    nrr = _pct(starting + expansion - contraction - churn, starting) if starting else 0.0
    grr = _pct(starting - contraction - churn, starting) if starting else 0.0
    billing_total = _money(rev.get("billing_audit_total_brl", rev.get("audit_log_mrr_brl")))
    recognized = _money(rev.get("recognized_revenue_brl", ending))
    reconciliation_delta = _money(ending - billing_total if "audit_log_mrr_brl" in rev else recognized - billing_total)
    reconciliation_delta_pct = _pct(abs(reconciliation_delta), billing_total) if billing_total else 0.0
    reconciled = reconciliation_delta_pct <= float(rev.get("max_reconciliation_delta_pct", 1.0) or 1.0)
    status = "published" if reconciled else "needs_reconciliation"
    rationale = llm.complete(f"Voce e {spec['id']}. Revenue period={rev.get('period')}: ending_mrr={ending}, nrr={nrr}, reconciled={reconciled}.")
    return {"output": {"agent_id": spec["id"], "handler_kind": "revenue_reporter", "period": rev.get("period"),
                       "mrr_brl": ending, "ending_mrr_brl": ending, "nrr_pct": nrr, "grr_pct": grr,
                       "reconciliation_delta_brl": reconciliation_delta,
                       "reconciliation_delta_pct": reconciliation_delta_pct, "reconciled": reconciled,
                       "status": status, "requires_human_review": not reconciled,
                       "rationale": rationale, "by": spec["id"]},
            "cost_tokens": _tokens(rationale), "citations": ["revenue:payload", "billing:audit-log"]}


@register("reconciliation")
def reconciliation(state, *, llm, store, spec):
    t = state["task"]
    recon = t.get("reconciliation", {}) or {}
    ledger = recon.get("ledger_transactions", []) or []
    bank = recon.get("bank_entries", []) or []
    unmatched_bank = list(bank)
    matched, exceptions = [], []
    for tx in ledger:
        ref = tx.get("external_id") or tx.get("ref")
        amount = _money(tx.get("amount_brl"))
        idx = next((i for i, b in enumerate(unmatched_bank)
                    if (b.get("external_id") or b.get("ref")) == ref and _money(b.get("amount_brl")) == amount), None)
        if idx is None:
            exceptions.append({"ledger_id": tx.get("id"), "external_id": ref, "amount_brl": amount, "reason": "missing_bank_match"})
        else:
            b = unmatched_bank.pop(idx)
            matched.append({"ledger_id": tx.get("id"), "bank_id": b.get("id"), "external_id": ref})
    for b in unmatched_bank:
        exceptions.append({"bank_id": b.get("id"), "external_id": b.get("external_id") or b.get("ref"),
                           "amount_brl": _money(b.get("amount_brl")), "reason": "missing_ledger_match"})
    total_ledger = _money(sum(float(x.get("amount_brl", 0) or 0) for x in ledger))
    total_bank = _money(sum(float(x.get("amount_brl", 0) or 0) for x in bank))
    match_rate = round(len(matched) / len(ledger), 4) if ledger else 1.0
    unreconciled_balance = _money(total_ledger - total_bank)
    status = "reconciled" if match_rate >= 0.98 and not exceptions and unreconciled_balance == 0 else "exceptions_opened"
    rationale = llm.complete(f"Voce e {spec['id']}. Reconciliation: match_rate={match_rate}, exceptions={len(exceptions)}, balance={unreconciled_balance}.")
    return {"output": {"agent_id": spec["id"], "handler_kind": "reconciliation", "period": recon.get("period"), "matched_count": len(matched),
                       "exception_count": len(exceptions), "match_rate": match_rate,
                       "unreconciled_balance_brl": unreconciled_balance, "status": status,
                       "requires_human_review": bool(exceptions) or unreconciled_balance != 0,
                       "exceptions": exceptions, "rationale": rationale, "by": spec["id"]},
            "cost_tokens": _tokens(rationale), "citations": ["reconciliation:payload", "ledger:bank-statement"]}


@register("csat_analyst")
def csat_analyst(state, *, llm, store, spec):
    t = state["task"]
    survey = t.get("survey", {}) or {}
    responses = survey.get("responses", []) or []
    csat_scores = [r.get("csat") for r in responses if r.get("csat") is not None]
    nps_scores = [r.get("nps") for r in responses if r.get("nps") is not None]
    csat_pct = _pct(sum(1 for s in csat_scores if s >= 4), len(csat_scores)) if csat_scores else 0.0
    avg_csat = round(sum(csat_scores) / len(csat_scores), 2) if csat_scores else 0.0
    promoters = sum(1 for s in nps_scores if s >= 9)
    detractors = sum(1 for s in nps_scores if s <= 6)
    nps = round(((promoters - detractors) / len(nps_scores)) * 100, 2) if nps_scores else 0.0
    drivers = {}
    for r in responses:
        for tag in r.get("tags", []) or []:
            drivers[tag] = drivers.get(tag, 0) + 1
    top_driver = sorted(drivers.items(), key=lambda kv: (-kv[1], kv[0]))[0][0] if drivers else None
    health = "red" if csat_pct < 70 or nps < 0 else ("yellow" if csat_pct < 85 or nps < 30 else "green")
    rationale = llm.complete(f"Voce e {spec['id']}. CSAT={csat_pct}%, NPS={nps}, health={health}.")
    return {"output": {"agent_id": spec["id"], "response_count": len(responses), "avg_csat": avg_csat,
                       "csat_pct": csat_pct, "nps": nps, "promoters": promoters, "detractors": detractors,
                       "top_driver": top_driver, "health": health, "rationale": rationale, "by": spec["id"]},
            "cost_tokens": _tokens(rationale), "citations": ["survey:payload"]}


@register("fulfillment_tracker")
def fulfillment_tracker(state, *, llm, store, spec):
    t = state["task"]
    outcomes = (t.get("fulfillment", {}) or {}).get("outcomes", []) or []
    delivered = [o for o in outcomes if o.get("delivered_event") and o.get("evidence_ref") and o.get("sla_met", True)]
    deviations = [o for o in outcomes if o.get("blocked") or not o.get("sla_met", True)]
    premature_billing = [o.get("id") for o in outcomes if o.get("billing_attempted") and o not in delivered]
    completion_rate = _pct(len(delivered), len(outcomes)) if outcomes else 0.0
    status = "blocked" if premature_billing else ("deviation_flagged" if deviations else "outcome_delivered")
    rationale = llm.complete(f"Voce e {spec['id']}. Fulfillment: delivered={len(delivered)}, deviations={len(deviations)}, status={status}.")
    return {"output": {"agent_id": spec["id"], "outcome_count": len(outcomes), "delivered_count": len(delivered),
                       "deviation_count": len(deviations), "premature_billing_count": len(premature_billing),
                       "completion_rate_pct": completion_rate, "billable_event_ids": [o.get("id") for o in delivered],
                       "status": status, "rationale": rationale, "by": spec["id"]},
            "cost_tokens": _tokens(rationale), "citations": ["fulfillment:payload", "billing:C3"]}


@register("burn_monitor")
def burn_monitor(state, *, llm, store, spec):
    t = state["task"]
    burn = t.get("burn", {}) or {}
    cash = _money(burn.get("cash_balance_brl"))
    planned = _money(burn.get("planned_burn_brl"))
    gross_burn = _money(burn.get("gross_burn_brl"))
    revenue = _money(burn.get("monthly_revenue_brl"))
    net_burn = _money(max(0, gross_burn - revenue))
    runway = round(cash / net_burn, 2) if net_burn else 999.0
    variance_pct = _pct(gross_burn - planned, planned) if planned else 0.0
    thresholds = burn.get("thresholds") or {}
    warn = float(thresholds.get("warning_runway_months", 9) or 9)
    crit = float(thresholds.get("critical_runway_months", 6) or 6)
    severity = "critical" if runway < crit else ("warning" if runway < warn or variance_pct > 10 else "ok")
    rationale = llm.complete(f"Voce e {spec['id']}. Runway={runway}m, variance={variance_pct}%, severity={severity}.")
    return {"output": {"agent_id": spec["id"], "net_burn_brl": net_burn, "runway_months": runway,
                       "burn_vs_plan_variance_pct": variance_pct, "severity": severity,
                       "alert": severity != "ok", "rationale": rationale, "by": spec["id"]},
            "cost_tokens": _tokens(rationale), "citations": ["burn:payload", "treasury:cash-position"]}


@register("unit_economist_c3")
def unit_economist_c3(state, *, llm, store, spec):
    t = state["task"]
    econ = t.get("unit_economics", t.get("economics_check", {})) or {}
    price = _money(econ.get("price_brl"))
    cost = _money(econ.get("unit_cost_brl", econ.get("inference_cost_brl")))
    max_ratio = float(econ.get("max_ratio", _max_ratio(spec, t)) or _max_ratio(spec, t))
    ratio = _ratio(cost, price)
    viable = bool(price and ratio is not None and ratio <= max_ratio)
    min_price = _money(cost / max_ratio) if max_ratio else 0.0
    signature_hash = econ.get("signature_hash") or f"c3:{spec['id']}:{price}:{cost}:{max_ratio}"
    billable = bool(econ.get("billable", True))
    verdict = "viable" if (viable or not billable) else "blocked"
    blocks_delivery = bool(billable and not viable)
    status = "blocked" if blocks_delivery else "ready"
    rationale = llm.complete(f"Voce e {spec['id']}. C3 price={price}, cost={cost}, ratio={ratio}, viable={viable}.")
    return {"output": {"agent_id": spec["id"], "handler_kind": "unit_economist_c3", "billable": billable,
                       "price_brl": price, "inference_cost_brl": cost, "unit_cost_brl": cost, "cost_ratio": ratio,
                       "max_ratio": max_ratio, "viable": viable, "min_viable_price_brl": min_price,
                       "min_price_brl": min_price, "verdict": verdict, "blocks_delivery": blocks_delivery,
                       "status": status, "requires_human_review": blocks_delivery,
                       "gate2_unlocked": viable, "signature_hash": signature_hash, "rationale": rationale, "by": spec["id"]},
            "cost_tokens": _tokens(rationale), "citations": ["economics:payload", "foundry:C3"]}


@register("token_cost_accountant")
def token_cost_accountant(state, *, llm, store, spec):
    t = state["task"]
    usage = (t.get("token_costs", {}) or {}).get("usage", []) or []
    budgets = (t.get("token_costs", {}) or {}).get("budgets_brl", {}) or {}
    by_guild = {}
    unattributed = 0.0
    for row in usage:
        cost = float(row.get("cost_brl", 0) or 0)
        guild = row.get("guild")
        if not guild:
            unattributed += cost
            continue
        by_guild[guild] = _money(by_guild.get(guild, 0) + cost)
    over = sorted([g for g, cost in by_guild.items() if cost > float(budgets.get(g, float("inf")))])
    total = _money(sum(by_guild.values()) + unattributed)
    rationale = llm.complete(f"Voce e {spec['id']}. Token cost total={total}, unattributed={unattributed}, over={over}.")
    return {"output": {"agent_id": spec["id"], "total_cost_brl": total, "allocated_cost_brl": _money(sum(by_guild.values())),
                       "unattributed_cost_brl": _money(unattributed), "guild_costs_brl": by_guild,
                       "over_budget_guilds": over, "throttle_required": bool(over),
                       "allocation_complete": _money(unattributed) == 0, "rationale": rationale, "by": spec["id"]},
            "cost_tokens": _tokens(rationale), "citations": ["token_costs:payload", "ledger:OP"]}


@register("margin_watch")
def margin_watch(state, *, llm, store, spec):
    t = state["task"]
    m = t.get("margin", {}) or {}
    revenue = _money(m.get("revenue_brl"))
    cogs = _money(m.get("cogs_brl"))
    delivery = _money(m.get("delivery_cost_brl"))
    current = round(((revenue - cogs - delivery) / revenue) * 100, 2) if revenue else 0.0
    previous = m.get("previous_margin_pct")
    compression = round(float(previous) - current, 2) if previous is not None else 0.0
    target = float(m.get("target_margin_pct", 60) or 60)
    threshold = float(m.get("compression_threshold_pp", 5) or 5)
    cause = m.get("cause") or ("token_cost" if delivery > cogs else "cogs")
    severity = "critical" if current < target - 10 else ("warning" if current < target or compression >= threshold else "ok")
    rationale = llm.complete(f"Voce e {spec['id']}. Margin={current}%, compression={compression}pp, severity={severity}.")
    return {"output": {"agent_id": spec["id"], "gross_margin_pct": current, "compression_pp": compression,
                       "target_margin_pct": target, "severity": severity, "cause": cause,
                       "recalc_required": severity != "ok", "rationale": rationale, "by": spec["id"]},
            "cost_tokens": _tokens(rationale), "citations": ["margin:payload", "economics:C3"]}


@register("fin_cashflow")
def fin_cashflow(state, *, llm, store, spec):
    """AGENTE DE PRODUTO (multi-tenant) — gestão de caixa da empresa DO CLIENTE.
    Agnóstico de segmento: toda PME tem entradas/saídas. Configurado pelo perfil do tenant."""
    t = state["task"]
    fin = t.get("finance", {}) or {}
    profile = (state.get("context", {}) or {}).get("tenant_profile", {}) or {}
    cur = profile.get("currency", "BRL")
    today = fin.get("today", "")                          # ISO yyyy-mm-dd (passado p/ determinismo)
    balance = fin.get("balance", 0) or 0
    recv = fin.get("receivables", []) or []
    pay = fin.get("payables", []) or []

    overdue = [r for r in recv if r.get("status") != "paid" and r.get("due_date", "") and r["due_date"] < today]
    total_overdue = sum(r.get("amount", 0) for r in overdue)
    expected_recv = sum(r.get("amount", 0) for r in recv if r.get("status") != "paid")
    total_pay = sum(p.get("amount", 0) for p in pay)
    projected = balance + expected_recv - total_pay

    actions = []
    if overdue:
        top = sorted(overdue, key=lambda r: -r.get("amount", 0))[:3]
        actions.append("Cobrar inadimplentes: " + ", ".join(f"{r.get('customer', '?')} ({cur} {r.get('amount', 0)})" for r in top))
    if projected < 0:
        actions.append(f"ALERTA: caixa projetado negativo ({cur} {projected}). Antecipar recebíveis ou renegociar pagamentos.")
    rev, cost = fin.get("revenue_month"), fin.get("cost_month")
    margin = None
    if rev and cost is not None:
        margin = round((rev - cost) / rev * 100, 1)
        if margin < 10:
            actions.append(f"Margem apertada ({margin}%): revisar custos/preços.")

    rationale = llm.complete(
        f"Voce e {spec['id']} para {profile.get('name', 'o cliente')} ({profile.get('segment', 'segmento?')}). "
        f"Caixa {cur} {balance}, vencidos a cobrar {cur} {total_overdue}, caixa projetado {cur} {projected}."
    )
    return {
        "output": {"tenant": t.get("tenant_id"), "segment": profile.get("segment"),
                   "cash_position": balance, "projected_cash": projected,
                   "total_overdue": total_overdue, "overdue_count": len(overdue),
                   "upcoming_payables": total_pay, "margin_pct": margin,
                   "recommended_actions": actions, "rationale": rationale, "by": spec["id"]},
        "cost_tokens": _tokens(rationale),
        "citations": [f"tenant:{t.get('tenant_id')}", "finance:snapshot"],
    }


