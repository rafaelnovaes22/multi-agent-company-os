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
