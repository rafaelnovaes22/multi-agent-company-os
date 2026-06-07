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


# ---------------------------------------------------------------------------
# Burn-down handlers — G12: legal/compliance artifacts with deterministic checks.
# ---------------------------------------------------------------------------
@register("dpa_subprocessor_review")
def dpa_subprocessor_review(state, *, llm, store, spec):
    """g12-dpa-manager — validates DPA coverage, subprocessor due diligence,
    RoPA freshness, international-transfer safeguards and PII production blocks."""
    dpa = state["task"].get("dpa", {}) or {}
    processes_pii = bool(dpa.get("processes_pii"))
    dpa_signed = bool(dpa.get("dpa_signed"))
    subprocessor_registered = bool(dpa.get("subprocessor_registered"))
    due_diligence_ok = bool(dpa.get("due_diligence_ok"))
    ropa_updated = bool(dpa.get("ropa_updated"))
    international_transfer = bool(dpa.get("international_transfer"))
    transfer_safeguard = bool(dpa.get("transfer_safeguard"))
    production_enabled = bool(dpa.get("production_enabled"))

    if processes_pii and not dpa_signed:
        status = "blocked_no_dpa" if production_enabled else "dpa_missing_preprod"
    elif not subprocessor_registered:
        status = "subprocessor_unregistered"
    elif not due_diligence_ok:
        status = "privacy_dd_failed"
    elif processes_pii and not ropa_updated:
        status = "ropa_stale"
    elif international_transfer and not transfer_safeguard:
        status = "transfer_safeguard_missing"
    else:
        status = "approved"

    lgpd_ready = status == "approved" and (not processes_pii or dpa_signed)
    requires_human_review = status != "approved" or international_transfer
    return _out(spec, state, {
        "agent_id": spec["id"], "handler_kind": "dpa_subprocessor_review",
        "processes_pii": processes_pii, "dpa_signed": dpa_signed,
        "subprocessor_registered": subprocessor_registered, "due_diligence_ok": due_diligence_ok,
        "ropa_updated": ropa_updated, "international_transfer": international_transfer,
        "transfer_safeguard": transfer_safeguard, "lgpd_ready": lgpd_ready,
        "status": status, "requires_human_review": requires_human_review,
    }, f"Voce e {spec['id']}: DPA status {status}, LGPD ready={lgpd_ready}.", llm)


@register("regulatory_change_assessment")
def regulatory_change_assessment(state, *, llm, store, spec):
    """g12-regulatory-monitor — classifies regulatory changes by source, deadline,
    impact, false-positive history and actionability."""
    change = state["task"].get("regulatory_change", {}) or {}
    source = change.get("source")
    source_trusted = source in {"ANPD", "BACEN", "CVM", "SENACON", "regulador_setorial"}
    applies = bool(change.get("applies_to_company"))
    impact = change.get("impact", "none")
    days = change.get("days_to_deadline")
    action_owner = bool(change.get("action_owner"))
    action_defined = bool(change.get("action"))
    false_positive_count = int(change.get("false_positive_count", 0) or 0)
    impact_assessed = source_trusted and impact in {"none", "low", "medium", "high"}
    actionable = source_trusted and applies and impact in {"medium", "high"} and action_defined and action_owner
    overdue = days is not None and days < 0

    if not source_trusted:
        status = "untrusted_source"
    elif false_positive_count >= 3 and not applies:
        status = "noise_suppressed"
    elif overdue and applies:
        status = "overdue"
    elif not applies or impact == "none":
        status = "monitor_only"
    elif not actionable:
        status = "needs_action_plan"
    else:
        status = "action_required"

    if not source_trusted:
        severity = "low"
    elif status == "overdue" or (impact == "high" and applies):
        severity = "critical"
    elif impact == "medium" and applies:
        severity = "medium"
    else:
        severity = "low"
    creates_task = status == "action_required"
    requires_human_review = status in {"overdue", "needs_action_plan", "action_required"}
    return _out(spec, state, {
        "agent_id": spec["id"], "handler_kind": "regulatory_change_assessment",
        "source_trusted": source_trusted, "applies_to_company": applies,
        "impact": impact, "impact_assessed": impact_assessed,
        "actionable": actionable, "creates_task": creates_task,
        "overdue": overdue, "severity": severity, "status": status,
        "requires_human_review": requires_human_review,
    }, f"Voce e {spec['id']}: mudanca regulatoria {status}, severidade {severity}.", llm)


@register("tos_privacy_doc_review")
def tos_privacy_doc_review(state, *, llm, store, spec):
    """g12-tos-privacy-author — validates legal doc versioning, LGPD legal bases,
    product-dataflow consistency, changelog and re-consent for material changes."""
    doc = state["task"].get("legal_doc", {}) or {}
    dataflows = doc.get("dataflows", []) or []
    bases = doc.get("legal_bases", {}) or {}
    version_bumped = bool(doc.get("version_bumped"))
    changelog_published = bool(doc.get("changelog_published"))
    product_consistent = bool(doc.get("product_consistent"))
    material_change = bool(doc.get("material_change"))
    reconsent_triggered = bool(doc.get("reconsent_triggered"))
    approved_taste_gate = bool(doc.get("approved_taste_gate"))
    published = bool(doc.get("published"))

    missing_legal_bases = sorted([flow for flow in dataflows if not bases.get(flow)])
    if not product_consistent:
        status = "product_mismatch"
    elif missing_legal_bases:
        status = "missing_legal_basis"
    elif not version_bumped or not changelog_published:
        status = "versioning_missing"
    elif material_change and not reconsent_triggered:
        status = "reconsent_missing"
    elif not approved_taste_gate:
        status = "taste_gate_pending"
    elif not published:
        status = "ready_to_publish"
    else:
        status = "published"

    lgpd_compliant = status in {"ready_to_publish", "published"}
    requires_human_review = status != "published" or material_change
    return _out(spec, state, {
        "agent_id": spec["id"], "handler_kind": "tos_privacy_doc_review",
        "dataflow_count": len(dataflows), "missing_legal_bases": missing_legal_bases,
        "product_consistent": product_consistent, "version_bumped": version_bumped,
        "changelog_published": changelog_published, "material_change": material_change,
        "reconsent_triggered": reconsent_triggered, "approved_taste_gate": approved_taste_gate,
        "lgpd_compliant": lgpd_compliant, "status": status,
        "requires_human_review": requires_human_review,
    }, f"Voce e {spec['id']}: documento legal {status}, LGPD={lgpd_compliant}.", llm)
