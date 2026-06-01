"""Handlers determinísticos da G08 Vendas & Receita — o cálculo real (não LLM) das
faturas em 3 camadas com tributos BR (billing), do score de match de duplicatas
(crm-hygiene), da margem C3 do pricing (custo <= 25% do preço) e das métricas de
receita MRR/ARR/NRR reconciliadas com o audit-log (revenue-reporter).

Mesmo padrão de skills_finance/skills_custops: handlers puros/determinísticos que
medem números do tenant e devolvem campos no top-level do output; o grader genérico
de contrato valida os `expected` de domínio direto. SEM aleatoriedade, SEM datas do
sistema. Registrados via @register; importado no fim de skills.py por outro processo.
"""
from __future__ import annotations

from .skills import register, _tokens, _spec_citations

# Alíquotas efetivas aproximadas por regime tributário BR (configurável por tenant).
_REGIME_RATES = {"simples": 0.06, "presumido": 0.1133, "real": 0.15}

# Trava econômica C3: custo de entrega <= 25% do preço.
_C3_MAX_RATIO = 0.25


def _out(spec, state, fields, rationale_prompt, llm):
    """Monta o retorno padrão: campos calculados + rationale + by + tenant + citations."""
    rationale = llm.complete(rationale_prompt)
    out = dict(fields)
    out["rationale"] = rationale
    out["by"] = spec["id"]
    out["tenant"] = state.get("task", {}).get("tenant_id")
    return {"output": out, "cost_tokens": _tokens(rationale), "citations": _spec_citations(state, spec)}


@register("billing_invoice_calc")
def billing_invoice_calc(state, *, llm, store, spec):
    """g8-billing-agent — soma as 3 camadas (assinatura + top-up + outcome), aplica
    tributos BR pelo regime e checa C3 antes de emitir. Bloqueia fatura que viole a
    trava econômica (custo de entrega > 25% do preço) e exige audit-log (C6)."""
    inv = state["task"].get("invoice", {}) or {}
    subscription = inv.get("subscription", 0) or 0
    topup = inv.get("topup", 0) or 0
    # Cobrança outcome-based só vale para outcomes DELIVERED (C2): soma apenas os entregues.
    outcomes = inv.get("outcomes", []) or []
    outcome_total = round(sum(o.get("amount", 0) or 0 for o in outcomes if o.get("delivered")), 2)
    pending_outcomes = sum(1 for o in outcomes if not o.get("delivered"))

    gross = round(subscription + topup + outcome_total, 2)
    regime = inv.get("regime", "simples")
    rate = inv.get("tax_rate", _REGIME_RATES.get(regime, 0.06))
    tax = round(gross * rate, 2)
    net = round(gross - tax, 2)

    # C3: custo de entrega <= 25% do preço bruto.
    delivery_cost = inv.get("delivery_cost", 0) or 0
    cost_ratio = round(delivery_cost / gross, 4) if gross else 1.0
    c3_ok = cost_ratio <= _C3_MAX_RATIO
    audit_logged = bool(inv.get("audit_log_ref"))
    # Emite só se C3 ok E houver audit-log (C6); caso contrário bloqueia.
    blocked = (not c3_ok) or (not audit_logged)
    status = "emitida" if not blocked else "bloqueada"

    tiers_billed = []
    if subscription:
        tiers_billed.append("assinatura")
    if topup:
        tiers_billed.append("top-up")
    if outcome_total:
        tiers_billed.append("outcome")

    return _out(spec, state, {
        "gross_amount": gross, "tax_amount": tax, "net_amount": net,
        "regime": regime, "tax_rate": rate, "outcome_total": outcome_total,
        "pending_outcomes": pending_outcomes, "tiers_billed": tiers_billed,
        "cost_ratio": cost_ratio, "c3_ok": c3_ok, "audit_logged": audit_logged,
        "blocked": blocked, "status": status,
    }, f"Voce e {spec['id']}: fatura bruta {gross} ({regime}), imposto {tax}, status {status}.", llm)


@register("crm_dedupe_score")
def crm_dedupe_score(state, *, llm, store, spec):
    """g8-crm-hygiene — score de match (0..1) entre dois registros para detectar/mesclar
    duplicatas. Pesos: email 0.5 (sinal forte), telefone 0.25, nome normalizado 0.15,
    domínio da empresa 0.10. >=0.85 -> merge automático; 0.6..0.85 -> revisar; <0.6 -> distinto."""
    d = state["task"].get("dedupe", {}) or {}
    a = d.get("record_a", {}) or {}
    b = d.get("record_b", {}) or {}

    def _norm(s):
        return (s or "").strip().lower()

    weights = {"email": 0.5, "phone": 0.25, "name": 0.15, "company_domain": 0.10}
    score = 0.0
    matched_fields = []
    for field, w in weights.items():
        va, vb = _norm(a.get(field)), _norm(b.get(field))
        if va and vb and va == vb:
            score += w
            matched_fields.append(field)
    score = round(score, 4)

    if score >= 0.85:
        decision, survivor = "merge", a.get("id") if a.get("id") else b.get("id")
    elif score >= 0.6:
        decision, survivor = "review", None
    else:
        decision, survivor = "distinct", None
    is_duplicate = decision == "merge"
    # Regra de sobrevivência (auditável): vence o registro mais completo (mais campos preenchidos).
    if is_duplicate:
        fa = sum(1 for k in weights if _norm(a.get(k)))
        fb = sum(1 for k in weights if _norm(b.get(k)))
        survivor = a.get("id") if fa >= fb else b.get("id")

    return _out(spec, state, {
        "match_score": score, "decision": decision, "is_duplicate": is_duplicate,
        "matched_fields": matched_fields, "survivor_id": survivor,
        "auto_merge": is_duplicate,
    }, f"Voce e {spec['id']}: match {score} entre registros, decisao {decision}.", llm)


@register("pricing_c3_margin")
def pricing_c3_margin(state, *, llm, store, spec):
    """g8-pricing-engine — calcula preço por camada e verifica C3 (custo de entrega <= 25%
    do preço) por camada e no total. Sugere min_price = custo/0.25 para a camada que violar.
    Bloqueia publicação se qualquer camada estourar a trava econômica."""
    p = state["task"].get("pricing", {}) or {}
    tiers = p.get("tiers", []) or []

    tier_results = []
    total_price = 0.0
    total_cost = 0.0
    all_ok = True
    for t in tiers:
        name = t.get("name", "?")
        price = t.get("price", 0) or 0
        cost = t.get("delivery_cost", 0) or 0
        ratio = round(cost / price, 4) if price else 1.0
        ok = ratio <= _C3_MAX_RATIO
        min_price = round(cost / _C3_MAX_RATIO, 2) if cost else 0.0
        margin_pct = round((price - cost) / price * 100, 1) if price else 0.0
        if not ok:
            all_ok = False
        total_price += price
        total_cost += cost
        tier_results.append({"name": name, "price": price, "cost_ratio": ratio,
                             "c3_ok": ok, "min_price": min_price, "margin_pct": margin_pct})

    total_ratio = round(total_cost / total_price, 4) if total_price else 1.0
    total_margin_pct = round((total_price - total_cost) / total_price * 100, 1) if total_price else 0.0
    c3_pass = all_ok and total_ratio <= _C3_MAX_RATIO
    blocked = not c3_pass
    violating_tiers = [t["name"] for t in tier_results if not t["c3_ok"]]

    return _out(spec, state, {
        "total_price": round(total_price, 2), "total_cost": round(total_cost, 2),
        "total_cost_ratio": total_ratio, "total_margin_pct": total_margin_pct,
        "c3_pass": c3_pass, "blocked": blocked, "tier_count": len(tiers),
        "violating_tiers": violating_tiers, "tiers": tier_results,
    }, f"Voce e {spec['id']}: ratio total {total_ratio} (C3={'ok' if c3_pass else 'viola'}), {len(violating_tiers)} camadas fora.", llm)


@register("revenue_metrics_calc")
def revenue_metrics_calc(state, *, llm, store, spec):
    """g8-revenue-reporter — calcula MRR/ARR e NRR (a partir de MRR inicial, expansão,
    contração e churn da coorte) e o delta de reconciliação vs audit-log de billing.
    Sinaliza drift se |delta| > 1% (limiar C2). NRR = (inicial + exp - contr - churn)/inicial."""
    r = state["task"].get("revenue", {}) or {}
    starting_mrr = r.get("starting_mrr", 0) or 0
    expansion = r.get("expansion", 0) or 0
    contraction = r.get("contraction", 0) or 0
    churn = r.get("churn", 0) or 0
    new_mrr = r.get("new_mrr", 0) or 0

    # MRR do período: parte da coorte (inicial +exp -contr -churn) mais receita nova.
    ending_cohort = starting_mrr + expansion - contraction - churn
    mrr = round(ending_cohort + new_mrr, 2)
    arr = round(mrr * 12, 2)
    nrr = round(ending_cohort / starting_mrr * 100, 1) if starting_mrr else 0.0

    # Reconciliação vs audit-log de billing (C6): delta percentual.
    audit_total = r.get("audit_log_total")
    if audit_total:
        delta_pct = round((mrr - audit_total) / audit_total * 100, 2)
    else:
        delta_pct = 0.0
    drift = abs(delta_pct) > 1.0
    reconciled = not drift
    status = "drift" if drift else "reconciliado"

    return _out(spec, state, {
        "mrr": mrr, "arr": arr, "nrr_pct": nrr, "new_mrr": new_mrr,
        "expansion": expansion, "contraction": contraction, "churn": churn,
        "reconciliation_delta_pct": delta_pct, "reconciled": reconciled,
        "drift": drift, "status": status,
    }, f"Voce e {spec['id']}: MRR {mrr}, NRR {nrr}%, delta reconciliacao {delta_pct}% ({status}).", llm)
