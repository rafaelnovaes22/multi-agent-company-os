"""Handlers determinísticos da G10 Finanças — o cálculo real (não LLM) que torna a
guilda financeira útil ao cliente. Cada handler é puro/determinístico: mede números
do tenant e devolve campos no top-level do output (o grader genérico de contrato
valida `expected` de domínio direto, sem grader específico por agente).

Registrados via @register de kernel.skills; importado no fim de skills.py.
A assinatura é a padrão: handler(state, *, llm, store, spec) -> {output, cost_tokens, citations}.
"""
from __future__ import annotations

from .skills import register, _tokens, _spec_citations

# Alíquotas efetivas aproximadas por regime tributário BR (configurável por tenant).
_REGIME_RATES = {"simples": 0.06, "presumido": 0.1133, "real": 0.15}


def _out(spec, state, fields, rationale_prompt, llm):
    """Monta o retorno padrão: campos calculados + rationale (guardians) + by + citations."""
    rationale = llm.complete(rationale_prompt)
    out = dict(fields)
    out["rationale"] = rationale
    out["by"] = spec["id"]
    out["tenant"] = state.get("task", {}).get("tenant_id")
    return {"output": out, "cost_tokens": _tokens(rationale), "citations": _spec_citations(state, spec)}


@register("fin_runway")
def fin_runway(state, *, llm, store, spec):
    """Runway & burn vs plano (g10-burn-monitor): meses de caixa restante e alerta de limiar."""
    b = state["task"].get("burn", {}) or {}
    cash = b.get("cash", 0) or 0
    burn = b.get("monthly_burn", 0) or 0
    plan = b.get("plan_burn")
    runway = round(cash / burn, 1) if burn > 0 else 999.0
    threshold = next((t for t in (6, 9, 12) if runway < t), None)
    alerts = [f"runway abaixo de {threshold} meses"] if threshold else []
    status = "critico" if runway < 6 else ("atencao" if runway < 12 else "saudavel")
    variance_pct = round((burn - plan) / plan * 100, 1) if plan else None
    return _out(spec, state, {
        "runway_months": runway, "burn_rate": burn, "status": status,
        "alerts": alerts, "variance_pct": variance_pct,
    }, f"Voce e {spec['id']}: runway {runway} meses, status {status}.", llm)


@register("fin_forecast")
def fin_forecast(state, *, llm, store, spec):
    """FP&A (g10-fpna): forecast rolante de receita por cenário a partir de premissas explícitas."""
    f = state["task"].get("forecast", {}) or {}
    base = f.get("base_revenue", 0) or 0
    g = f.get("growth_rate", 0) or 0
    months = f.get("months", 3) or 3
    proj = round(base * ((1 + g) ** months), 2)
    scenarios = {
        "base": proj,
        "otimista": round(base * ((1 + g * 1.5) ** months), 2),
        "conservador": round(base * ((1 + g * 0.5) ** months), 2),
    }
    return _out(spec, state, {
        "base_revenue": base, "projected_revenue": proj, "months": months, "scenarios": scenarios,
    }, f"Voce e {spec['id']}: receita projetada {proj} em {months} meses.", llm)


@register("fin_margin_score")
def fin_margin_score(state, *, llm, store, spec):
    """Vigilância de margem (g10-margin-watch): margem do período e alerta de compressão."""
    m = state["task"].get("margin", {}) or {}
    rev = m.get("revenue", 0) or 0
    cost = m.get("cost", 0) or 0
    prev = m.get("prev_margin_pct")
    margin = round((rev - cost) / rev * 100, 1) if rev else 0.0
    alerts, cause = [], None
    if margin < 10:
        alerts.append("margem abaixo de 10%")
    if prev is not None and margin < prev - 5:
        alerts.append(f"compressao de {round(prev - margin, 1)}pp")
        cause = "custo subiu ou preco caiu"
    status = "vermelho" if margin < 10 else ("amarelo" if alerts else "verde")
    return _out(spec, state, {
        "margin_pct": margin, "status": status, "alerts": alerts, "cause": cause,
    }, f"Voce e {spec['id']}: margem {margin}%, status {status}.", llm)


@register("fin_reconcile")
def fin_reconcile(state, *, llm, store, spec):
    """Conciliação (g10-reconciliation): casa ledger x banco por (valor, data) e abre exceções."""
    r = state["task"].get("reconcile", {}) or {}
    ledger = r.get("ledger", []) or []
    bank = r.get("bank", []) or []
    bk = [(x.get("amount"), x.get("date")) for x in bank]
    matched, exceptions = 0, []
    for l in ledger:
        k = (l.get("amount"), l.get("date"))
        if k in bk:
            matched += 1
            bk.remove(k)
        else:
            exceptions.append({"type": "sem_lancamento_no_banco", "amount": l.get("amount")})
    for amount, date in bk:                       # sobrou no banco sem ledger
        exceptions.append({"type": "sem_lancamento_no_ledger", "amount": amount})
    total = len(ledger)
    rate = round(matched / total * 100, 1) if total else 100.0
    return _out(spec, state, {
        "matched_count": matched, "exception_count": len(exceptions),
        "reconciliation_rate": rate, "exceptions": exceptions,
    }, f"Voce e {spec['id']}: {matched}/{total} conciliados ({rate}%), {len(exceptions)} excecoes.", llm)


@register("fin_invoice_tax")
def fin_invoice_tax(state, *, llm, store, spec):
    """Emissão fiscal (g10-invoicing): aplica alíquota do regime e calcula imposto/líquido."""
    inv = state["task"].get("invoice", {}) or {}
    amount = inv.get("amount", 0) or 0
    regime = inv.get("regime", "simples")
    rate = inv.get("tax_rate", _REGIME_RATES.get(regime, 0.06))
    tax = round(amount * rate, 2)
    net = round(amount - tax, 2)
    return _out(spec, state, {
        "gross_amount": amount, "regime": regime, "tax_rate": rate,
        "tax_amount": tax, "net_amount": net,
    }, f"Voce e {spec['id']}: NF de {amount} ({regime}) imposto {tax}.", llm)


@register("fin_tax_assessment")
def fin_tax_assessment(state, *, llm, store, spec):
    """Apuração tributária (g10-tax-compliance): tributos do período pelo regime vigente."""
    tx = state["task"].get("tax", {}) or {}
    revenue = tx.get("revenue", 0) or 0
    regime = tx.get("regime", "simples")
    rate = tx.get("rate", _REGIME_RATES.get(regime, 0.06))
    total = round(revenue * rate, 2)
    return _out(spec, state, {
        "regime": regime, "effective_rate": rate, "total_tax": total,
        "period": tx.get("period"), "revenue": revenue,
    }, f"Voce e {spec['id']}: tributos {total} ({regime}) sobre {revenue}.", llm)


@register("fin_token_cost_allocation")
def fin_token_cost_allocation(state, *, llm, store, spec):
    """Rateio de custo de tokens (g10-token-cost-accountant): atribui cada custo a um actor."""
    tc = state["task"].get("tokens", {}) or {}
    events = tc.get("events", []) or []
    alloc = {}
    unattributed = 0.0
    for e in events:
        actor = e.get("actor")
        cost = e.get("cost", 0) or 0
        if actor:
            alloc[actor] = round(alloc.get(actor, 0) + cost, 4)
        else:
            unattributed += cost
    total = round(sum(alloc.values()) + unattributed, 4)
    return _out(spec, state, {
        "total_cost": total, "allocation": alloc, "agent_count": len(alloc),
        "unattributed_cost": round(unattributed, 4),
    }, f"Voce e {spec['id']}: custo total {total} em {len(alloc)} agentes.", llm)


