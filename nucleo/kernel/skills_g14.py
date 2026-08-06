"""Handlers determinísticos da G14 Model & AI-Ops — o cálculo real (não LLM) que
mantém o "motor de inteligência" saudável, barato e confiável: roteamento de
modelo por custo×qualidade×latência, scorecard de benchmark com estimativa C3,
qualidade de recuperação (RAG) e economia de inferência (cache/batch/compressão).

Mesmo padrão de skills_finance/skills_custops: handlers puros/determinísticos,
campos no top-level do output, grader genérico valida `expected` de domínio.
A assinatura é a padrão: handler(state, *, llm, store, spec) -> {output, cost_tokens, citations}.
"""

from __future__ import annotations

from .skills import _spec_citations, _tokens, register

# Tiers de modelo: custo relativo por chamada (unidade) e qualidade nominal (0..1).
# Determinístico: tabela explícita, sem rede nem aleatoriedade.
_MODEL_TIERS = {
    "barato": {"cost": 1.0, "quality": 0.80, "latency_ms": 400},
    "medio": {"cost": 3.0, "quality": 0.90, "latency_ms": 700},
    "forte": {"cost": 10.0, "quality": 0.97, "latency_ms": 1500},
}


def _out(spec, state, fields, rationale_prompt, llm):
    """Monta o retorno padrão: campos calculados + rationale (guardians) + by + citations."""
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


@register("model_routing_decision")
def model_routing_decision(state, *, llm, store, spec):
    """g14-model-router — escolhe o modelo mais barato que atende o SLA de qualidade
    da tarefa, aplica fallback se o provider primário caiu e bloqueia/rebaixa chamada
    billable que estouraria o teto C3 (custo máximo por chamada)."""
    r = state["task"].get("routing", {}) or {}
    min_quality = r.get("min_quality", 0.85) or 0.85  # SLA de qualidade da tarefa
    ledger = r.get("ledger", "operating")
    cost_cap = r.get("cost_cap")  # teto C3 (billable)
    primary_down = bool(r.get("primary_down"))

    # Modelos ordenados do mais barato ao mais caro que atende a qualidade mínima.
    candidates = sorted(
        [(name, t) for name, t in _MODEL_TIERS.items() if t["quality"] >= min_quality],
        key=lambda kv: kv[1]["cost"],
    )
    # Decisão base: o mais barato que cumpre o SLA (fallback se primário caiu = próximo).
    selected, fell_back = None, False
    if candidates:
        selected = candidates[0][0]
        if primary_down and len(candidates) > 1:
            selected = candidates[1][0]
            fell_back = True

    cost = _MODEL_TIERS[selected]["cost"] if selected else None
    quality = _MODEL_TIERS[selected]["quality"] if selected else None
    latency = _MODEL_TIERS[selected]["latency_ms"] if selected else None

    # Firewall C3: chamada billable que excede o teto é bloqueada/rebaixada.
    blocked = False
    if selected and ledger == "billable" and cost_cap is not None and cost > cost_cap:
        cheaper = [(n, t) for n, t in candidates if t["cost"] <= cost_cap]
        if cheaper:
            selected = cheaper[0][0]
            cost = _MODEL_TIERS[selected]["cost"]
            quality = _MODEL_TIERS[selected]["quality"]
            latency = _MODEL_TIERS[selected]["latency_ms"]
            fell_back = True
        else:
            blocked = True

    status = "blocked" if blocked else ("fallback" if fell_back else "ok")
    return _out(
        spec,
        state,
        {
            "selected_model": selected,
            "cost": cost,
            "quality": quality,
            "latency_ms": latency,
            "fell_back": fell_back,
            "blocked": blocked,
            "candidate_count": len(candidates),
            "status": status,
        },
        f"Voce e {spec['id']}: modelo '{selected}' (custo {cost}), status {status}.",
        llm,
    )


@register("model_scorecard")
def model_scorecard(state, *, llm, store, spec):
    """g14-model-eval-bench — scorecard comparativo do modelo candidato contra o
    atual (qualidade/custo/latência sobre golden datasets) + estimativa econômica
    C3; recomenda adotar/reverter. Regressão de qualidade => reverter."""
    s = state["task"].get("scorecard", {}) or {}
    cur = s.get("current", {}) or {}
    cand = s.get("candidate", {}) or {}
    cur_q = cur.get("quality", 0) or 0  # 0..1 no golden set
    cand_q = cand.get("quality", 0) or 0
    cur_cost = cur.get("cost", 0) or 0  # custo por outcome
    cand_cost = cand.get("cost", 0) or 0
    tol = s.get("quality_tolerance", 0.02) or 0.02  # tolerância de regressão

    quality_delta = round(cand_q - cur_q, 4)
    cost_delta = round(cand_cost - cur_cost, 4)
    cost_savings_pct = round((cur_cost - cand_cost) / cur_cost * 100, 1) if cur_cost else 0.0
    regression = quality_delta < -tol
    # Economia C3 mensal estimada a partir do volume de chamadas.
    volume = s.get("monthly_calls", 0) or 0
    monthly_savings = round((cur_cost - cand_cost) * volume, 2)

    if regression:
        recommendation, adopt = "reverter", False
    elif cost_delta <= 0 and quality_delta >= -tol:
        recommendation, adopt = "adotar", True
    else:
        recommendation, adopt = "revisar", False  # mais caro sem ganho claro

    return _out(
        spec,
        state,
        {
            "quality_delta": quality_delta,
            "cost_delta": cost_delta,
            "cost_savings_pct": cost_savings_pct,
            "monthly_savings": monthly_savings,
            "regression": regression,
            "recommendation": recommendation,
            "adopt": adopt,
        },
        f"Voce e {spec['id']}: recomendacao '{recommendation}' (dq {quality_delta}, dcusto {cost_delta}).",
        llm,
    )


@register("retrieval_quality_score")
def retrieval_quality_score(state, *, llm, store, spec):
    """g14-rag-knowledge-ops — qualidade da recuperação: precisão/recall/F1 dos
    chunks recuperados contra os relevantes, frescor médio do índice e flag de
    vazamento de Tier (C5). Aprova só se F1 >= limiar e sem leakage."""
    r = state["task"].get("retrieval", {}) or {}
    retrieved = r.get("retrieved", []) or []  # ids recuperados
    relevant = set(r.get("relevant", []) or [])  # ids realmente relevantes
    threshold = r.get("threshold", 0.7) or 0.7  # limiar de F1
    stale_days = r.get("stale_days", 0) or 0  # frescor: dias desde reindex
    max_stale = r.get("max_stale_days", 30) or 30
    tier_leak = bool(r.get("tier_leak"))  # mistura de Tiers (C5)

    ret_set = list(retrieved)
    tp = sum(1 for x in ret_set if x in relevant)
    precision = round(tp / len(ret_set), 3) if ret_set else 0.0
    recall = round(tp / len(relevant), 3) if relevant else 0.0
    f1 = round(2 * precision * recall / (precision + recall), 3) if (precision + recall) else 0.0
    stale = stale_days > max_stale
    passed = (f1 >= threshold) and (not tier_leak) and (not stale)
    status = (
        "tier_leak" if tier_leak else ("stale" if stale else ("ok" if passed else "abaixo_limiar"))
    )
    return _out(
        spec,
        state,
        {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "tier_leak": tier_leak,
            "stale": stale,
            "passed": passed,
            "status": status,
        },
        f"Voce e {spec['id']}: F1 {f1} (limiar {threshold}), status {status}.",
        llm,
    )


@register("inference_cost_savings")
def inference_cost_savings(state, *, llm, store, spec):
    """g14-inference-cost-optimizer — economia de inferência por cache + batching +
    compressão de prompt, validando qualidade >= baseline (tolerância). Só aplica
    se a economia for positiva e a qualidade não regredir além da tolerância."""
    c = state["task"].get("optimization", {}) or {}
    base_cost = c.get("baseline_cost", 0) or 0  # custo por outcome antes
    cache_hit = c.get("cache_hit_rate", 0) or 0  # 0..1 chamadas servidas do cache
    batch_factor = c.get("batch_savings", 0) or 0  # fração economizada por batching
    compression = c.get("prompt_compression", 0) or 0  # fração de tokens cortados
    quality_after = c.get("quality_after", 1.0) or 1.0  # qualidade pós-otimização
    baseline_quality = c.get("baseline_quality", 1.0) or 1.0
    tol = c.get("quality_tolerance", 0.02) or 0.02

    # Custo efetivo: cache zera o custo dos hits; nos misses aplicam-se batch+compressão.
    miss = 1 - cache_hit
    factor = miss * (1 - batch_factor) * (1 - compression)
    optimized_cost = round(base_cost * factor, 4)
    savings = round(base_cost - optimized_cost, 4)
    savings_pct = round(savings / base_cost * 100, 1) if base_cost else 0.0
    quality_regression = round(baseline_quality - quality_after, 4)
    quality_ok = quality_regression <= tol
    applied = quality_ok and savings > 0
    status = "applied" if applied else ("quality_regression" if not quality_ok else "no_savings")
    return _out(
        spec,
        state,
        {
            "optimized_cost": optimized_cost,
            "savings": savings,
            "savings_pct": savings_pct,
            "quality_regression": quality_regression,
            "quality_ok": quality_ok,
            "applied": applied,
            "status": status,
        },
        f"Voce e {spec['id']}: economia {savings_pct}% (de {base_cost} p/ {optimized_cost}), status {status}.",
        llm,
    )


# ---------------------------------------------------------------------------
# Burn-down Track A — g14-prompt-context-registry: registry determinístico.
# ---------------------------------------------------------------------------
@register("prompt_context_registry")
def prompt_context_registry(state, *, llm, store, spec):
    """g14-prompt-context-registry — versiona prompt/contexto, hash, A/B e recalc C3."""
    import hashlib

    p = state["task"].get("prompt_registry", {}) or {}
    prompt_id = p.get("prompt_id")
    content = p.get("content", "") or ""
    previous_hash = p.get("previous_hash")
    prompt_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16] if content else None
    hash_changed = bool(prompt_hash and prompt_hash != previous_hash)
    ab = p.get("ab", {}) or {}
    variants = ab.get("variants", []) or []
    winner = None
    if variants:
        winner = sorted(
            variants,
            key=lambda v: (v.get("quality", 0) or 0, -(v.get("cost", 0) or 0)),
            reverse=True,
        )[0].get("id")
    context_tiers = p.get("context_tiers", []) or []
    max_allowed_tier = p.get("max_allowed_tier", 1) if p.get("max_allowed_tier") is not None else 1
    tier_leak = any((t or 0) > max_allowed_tier for t in context_tiers)
    cacheable = bool(p.get("cacheable", False)) and not tier_leak
    version_registered = bool(prompt_id and prompt_hash and not tier_leak)
    recalc_unit_economics = hash_changed
    status = (
        "blocked_tier_leak" if tier_leak else ("versioned" if version_registered else "invalid")
    )
    return _out(
        spec,
        state,
        {
            "prompt_id": prompt_id,
            "prompt_hash": prompt_hash,
            "hash_changed": hash_changed,
            "version_registered": version_registered,
            "recalc_unit_economics": recalc_unit_economics,
            "variant_count": len(variants),
            "winner_variant": winner,
            "tier_leak": tier_leak,
            "cacheable": cacheable,
            "status": status,
        },
        f"Voce e {spec['id']}: prompt {prompt_id}, status {status}, hash_changed={hash_changed}.",
        llm,
    )
