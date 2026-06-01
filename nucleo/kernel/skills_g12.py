"""Handlers determinísticos da G12 Jurídico & Risco — o cálculo real (não LLM) que
torna a guilda jurídica acionável: estimativa de provisão de contencioso e score de
risco corporativo. Mesmo padrão de skills_finance/skills_custops: campos no top-level
do output, grader genérico de contrato valida `expected` de domínio direto.

Registrados via @register de kernel.skills; importado no fim de skills.py.
A assinatura é a padrão: handler(state, *, llm, store, spec) -> {output, cost_tokens, citations}.
"""
from __future__ import annotations

from .skills import register, _tokens, _spec_citations


def _out(spec, state, fields, rationale_prompt, llm):
    rationale = llm.complete(rationale_prompt)
    out = dict(fields)
    out["rationale"] = rationale
    out["by"] = spec["id"]
    out["tenant"] = state.get("task", {}).get("tenant_id")
    return {"output": out, "cost_tokens": _tokens(rationale), "citations": _spec_citations(state, spec)}


@register("provision_estimate")
def provision_estimate(state, *, llm, store, spec):
    """g12-litigation-tracker — exposição = valor_causa × probabilidade_perda; monitora
    o prazo de resposta/processual e dispara alerta antes do vencimento.

    Inputs em state["task"]["dispute"]:
      claim_amount        — valor da causa (R$)
      loss_probability    — probabilidade de perda [0..1]
      days_to_deadline    — dias até o prazo (resposta/processual)
      alert_window_days   — janela de alerta (default 5)
      registered          — disputa já registrada no Brain (default True)
    """
    d = state["task"].get("dispute", {}) or {}
    claim = d.get("claim_amount", 0) or 0
    prob = d.get("loss_probability", 0) or 0
    days = d.get("days_to_deadline")
    window = d.get("alert_window_days", 5) or 5
    registered = d.get("registered", True)

    # Provisão = exposição esperada = valor da causa × probabilidade de perda.
    provision = round(claim * prob, 2)

    # Nível de exposição (provisão como % do valor da causa, via probabilidade).
    if prob >= 0.7:
        exposure_level = "provavel"      # provável (CPC art. 818): provisiona integral
    elif prob >= 0.3:
        exposure_level = "possivel"      # possível: divulga, provisiona o esperado
    else:
        exposure_level = "remota"        # remota: não provisiona contabilmente

    # Monitoramento de prazo: alerta quando dentro da janela ou já vencido.
    deadline_alert = days is not None and days <= window
    deadline_status = "no_prazo"
    if days is not None:
        if days < 0:
            deadline_status = "vencido"
        elif days <= window:
            deadline_status = "alerta"

    # delivered_event só é satisfeito com registro + prazos monitorados.
    deadlines_tracked = days is not None
    delivered = bool(registered and deadlines_tracked)

    return _out(spec, state, {
        "claim_amount": claim,
        "loss_probability": prob,
        "provision": provision,
        "exposure_level": exposure_level,
        "deadline_status": deadline_status,
        "deadline_alert": deadline_alert,
        "deadlines_tracked": deadlines_tracked,
        "registered": registered,
        "delivered_event": "dispute.registered && dispute.deadlines_tracked" if delivered else None,
    }, f"Voce e {spec['id']}: provisao R$ {provision} (exposicao {exposure_level}), "
       f"prazo {deadline_status}.", llm)


# Pesos por categoria de risco para ponderar a exposição agregada do heatmap.
_RISK_CATEGORY_WEIGHT = {
    "regulatorio": 1.0, "legal": 1.0, "seguranca": 1.0, "privacidade": 1.0,
    "financeiro": 0.9, "operacional": 0.8, "ia": 1.0,
}


@register("risk_score")
def risk_score(state, *, llm, store, spec):
    """g12-risk-register — score = probabilidade × impacto (escala 1..5 → 1..25);
    deriva nível (verde/amarelo/vermelho), célula do heatmap, exige dono e mitigação.

    Inputs em state["task"]["risk"]:
      probability   — 1..5 (raro..quase certo)
      impact        — 1..5 (insignificante..catastrofico)
      category      — regulatorio|legal|seguranca|privacidade|financeiro|operacional|ia
      owner         — dono atribuído (str|None)
      mitigation    — mitigação definida (str|None)
      prev_level    — nível anterior (para detectar mudança/escalada)
    """
    r = state["task"].get("risk", {}) or {}
    prob = r.get("probability", 0) or 0
    impact = r.get("impact", 0) or 0
    category = r.get("category", "operacional")
    owner = r.get("owner")
    mitigation = r.get("mitigation")
    prev_level = r.get("prev_level")

    # Score bruto (matriz 5×5) e ponderado pela criticidade da categoria.
    score = prob * impact
    weight = _RISK_CATEGORY_WEIGHT.get(category, 0.8)
    weighted_score = round(score * weight, 2)

    # Nível pela matriz padrão de risco (thresholds explícitos sobre 1..25).
    if score >= 15:
        level = "vermelho"
    elif score >= 8:
        level = "amarelo"
    else:
        level = "verde"

    # Célula do heatmap (eixo P×I).
    heatmap_cell = f"P{prob}I{impact}"

    has_owner = bool(owner)
    has_mitigation = bool(mitigation)

    # Vermelho sem dono é um achado bloqueante (negative_example da spec).
    escalate = level == "vermelho" or (prev_level is not None and prev_level != "vermelho" and level == "vermelho")
    alert_board = level == "vermelho"
    blocked = level == "vermelho" and not has_owner

    # delivered_event: registrado && dono atribuído && pontuado.
    delivered = bool(has_owner and score > 0)

    return _out(spec, state, {
        "score": score,
        "weighted_score": weighted_score,
        "level": level,
        "heatmap_cell": heatmap_cell,
        "category": category,
        "has_owner": has_owner,
        "has_mitigation": has_mitigation,
        "escalate": escalate,
        "alert_board": alert_board,
        "blocked": blocked,
        "delivered_event": "risk.registered && risk.owner_assigned && risk.scored" if delivered else None,
    }, f"Voce e {spec['id']}: risco {level} (score {score}, {heatmap_cell}), "
       f"dono={'sim' if has_owner else 'NAO'}.", llm)


# ---------------------------------------------------------------------------
# Burn-down R3 — g12-contract-reviewer: classificação determinística de risco contratual.
# Postura de risco do NÚCLEO: indenização ilimitada / sem cap de responsabilidade / foro
# estrangeiro = bloqueante (vermelho). DPA exigido quando há tratamento de dados pessoais.
# ---------------------------------------------------------------------------
@register("contract_risk_review")
def contract_risk_review(state, *, llm, store, spec):
    t = state["task"]
    cl = (t.get("contract", {}) or {}).get("clauses", {}) or {}
    blocking = []
    if cl.get("indemnity") == "unlimited":
        blocking.append("indemnity_unlimited")
    if not cl.get("liability_cap"):
        blocking.append("no_liability_cap")
    gl = (cl.get("governing_law") or "BR").upper()
    if gl not in ("BR", "BRASIL", "BRAZIL"):
        blocking.append("foreign_governing_law")
    yellow = []
    notice = cl.get("termination_notice_days")
    if notice is not None and notice < 30:
        yellow.append("short_termination_notice")
    if cl.get("sla_pct") is None:
        yellow.append("no_sla")
    requires_dpa = bool(cl.get("data_processing")) and not bool(cl.get("dpa") or cl.get("has_dpa"))
    if requires_dpa:
        yellow.append("dpa_required")
    risk = "vermelho" if blocking else ("amarelo" if yellow else "verde")
    rec = "rejeitar" if blocking else ("negociar" if yellow else "assinar")
    return _out(spec, state, {
        "agent_id": spec["id"], "risk_level": risk, "blocking_clauses": blocking,
        "flagged_clauses": blocking + yellow, "requires_dpa": requires_dpa,
        "recommendation": rec, "requires_human_review": bool(blocking or requires_dpa),
    }, f"Voce e {spec['id']}: risco {risk}, recomendacao {rec}.", llm)
