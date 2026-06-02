"""Handlers determinísticos da G05 Segurança & Compliance — o cálculo real (não LLM)
que torna a guilda de segurança útil: priorização de CVEs por exploitabilidade,
pontuação de risco de fraude/abuso e varredura determinística de segredos.

Mesmo padrão de skills_finance/skills_custops: cada handler é puro/determinístico,
calcula a partir de state["task"] e devolve campos no top-level do output (o grader
genérico de contrato valida `expected` de domínio direto). Importado no fim de skills.py.
A assinatura é a padrão: handler(state, *, llm, store, spec) -> {output, cost_tokens, citations}.
"""
from __future__ import annotations

import math

from .skills import register, _tokens, _spec_citations

# SLA de remediação por severidade (dias) — política explícita, sem datas do sistema.
_CVE_SLA_DAYS = {"critica": 2, "alta": 7, "media": 30, "baixa": 90}


def _out(spec, state, fields, rationale_prompt, llm):
    """Monta o retorno padrão: campos calculados + rationale + by + tenant + citations."""
    rationale = llm.complete(rationale_prompt)
    out = dict(fields)
    out["rationale"] = rationale
    out["by"] = spec["id"]
    out["tenant"] = state.get("task", {}).get("tenant_id")
    return {"output": out, "cost_tokens": _tokens(rationale), "citations": _spec_citations(state, spec)}


def _severity_from_cvss(cvss):
    """Faixa de severidade a partir do CVSS base (escala 0-10)."""
    if cvss >= 9.0:
        return "critica"
    if cvss >= 7.0:
        return "alta"
    if cvss >= 4.0:
        return "media"
    return "baixa"


@register("cve_prioritization")
def cve_prioritization(state, *, llm, store, spec):
    """g5-dependency-cve — prioriza CVEs por exploitabilidade real (CVSS × EPSS × exposição
    em caminho ativo), não por CVSS bruto. Define severidade, SLA e o que dispara remediação.

    priority = cvss × epss × (1.5 se in_active_path senão 0.4) — normalizado p/ 0-15.
    """
    c = state["task"].get("cve", {}) or {}
    items = c.get("items", []) or []
    ranked = []
    for it in items:
        cid = it.get("id")
        cvss = it.get("cvss", 0) or 0
        epss = it.get("epss", 0) or 0
        active = bool(it.get("in_active_path"))
        exposure = 1.5 if active else 0.4
        priority = round(cvss * epss * exposure, 3)
        severity = _severity_from_cvss(cvss)
        exploitable = active and (epss >= 0.5 or bool(it.get("exploit_public")))
        ranked.append({
            "id": cid, "severity": severity, "priority": priority,
            "exploitable": exploitable, "sla_days": _CVE_SLA_DAYS[severity],
        })
    ranked.sort(key=lambda x: -x["priority"])
    critical_open = sum(1 for r in ranked if r["severity"] == "critica")
    exploitable_count = sum(1 for r in ranked if r["exploitable"])
    # Dispara remediação se há CVE crítica OU explorável em caminho ativo.
    dispatch = critical_open > 0 or exploitable_count > 0
    delivered_event = "cve.remediation_dispatched" if dispatch else "cve.scan_completed"
    top_id = ranked[0]["id"] if ranked else None
    return _out(spec, state, {
        "cve_count": len(items),
        "ranked": ranked,
        "critical_open": critical_open,
        "exploitable_count": exploitable_count,
        "top_priority_id": top_id,
        "remediation_dispatched": dispatch,
        "delivered_event": delivered_event,
    }, f"Voce e {spec['id']}: {len(items)} CVEs, {critical_open} criticas, "
       f"{exploitable_count} exploraveis; dispatch={dispatch}.", llm)


@register("fraud_score")
def fraud_score(state, *, llm, store, spec):
    """g5-fraud-abuse-detector — pontua risco de fraude/abuso por sinais genéricos
    (velocity, device/fingerprint, comportamento anômalo, coordenação) e decide
    permitir/step-up/bloquear sob política. Livro Misto: C3 só importa quando billable.

    score 0-100 = soma ponderada dos sinais (cada um 0-1). Limiares explícitos.
    """
    f = state["task"].get("fraud", {}) or {}
    velocity = f.get("velocity", 0) or 0           # 0-1 (transações/janela normalizado)
    device_risk = f.get("device_risk", 0) or 0     # 0-1 (device/fingerprint suspeito)
    behavior = f.get("behavior_anomaly", 0) or 0   # 0-1 (desvio comportamental)
    coordination = f.get("coordination", 0) or 0   # 0-1 (padrão multi-conta/anel)
    impossible_travel = bool(f.get("impossible_travel"))  # login impossível -> ATO

    weights = {"velocity": 25, "device": 25, "behavior": 25, "coordination": 25}
    score = round(
        velocity * weights["velocity"] + device_risk * weights["device"]
        + behavior * weights["behavior"] + coordination * weights["coordination"], 1)

    # Login impossível é sinal forte de account takeover: força bloqueio.
    if impossible_travel:
        score = max(score, 80.0)
        ato = True
    else:
        ato = False

    if score >= 70:
        decision = "bloquear"
    elif score >= 40:
        decision = "step-up"
    else:
        decision = "permitir"

    risk_level = "alto" if score >= 70 else ("medio" if score >= 40 else "baixo")
    confirmed = decision == "bloquear"
    delivered_event = "fraud.case_confirmed" if confirmed else "fraud.event_scored"
    return _out(spec, state, {
        "risk_score": score,
        "decision": decision,
        "risk_level": risk_level,
        "account_takeover": ato,
        "case_confirmed": confirmed,
        "delivered_event": delivered_event,
    }, f"Voce e {spec['id']}: score {score}, decisao {decision} (ATO={ato}).", llm)


def _shannon_entropy(s):
    """Entropia de Shannon (bits/char) de uma string — proxy de aleatoriedade de segredo."""
    if not s:
        return 0.0
    freq = {}
    for ch in s:
        freq[ch] = freq.get(ch, 0) + 1
    n = len(s)
    ent = -sum((c / n) * math.log2(c / n) for c in freq.values())
    return round(ent, 3)


# Prefixos/regex de provedores conhecidos (formato de chave) — alta confiança.
_SECRET_PREFIXES = ("AKIA", "sk-", "ghp_", "xoxb-", "AIza", "ASIA", "glpat-")
_ENTROPY_THRESHOLD = 3.5   # bits/char acima do qual o token é candidato a segredo
_MIN_LEN = 16              # comprimento mínimo para considerar entropia


@register("secret_scan")
def secret_scan(state, *, llm, store, spec):
    """g5-secrets-scanner — detecta segredos por entropia alta + regex de provedores,
    respeita allowlist auditada e bloqueia entrada de segredo novo. Confiança por padrão.

    Um candidato é segredo se: casa prefixo de provedor (alta confiança) OU
    (comprimento >= 16 e entropia >= 3.5 bits/char). Allowlist remove falso-positivo.
    """
    s = state["task"].get("scan", {}) or {}
    candidates = s.get("candidates", []) or []
    allowlist = set(s.get("allowlist", []) or [])
    findings = []
    for cand in candidates:
        value = cand.get("value", "") or ""
        location = cand.get("location")
        if value in allowlist:
            continue
        prefix_hit = value.startswith(_SECRET_PREFIXES)
        ent = _shannon_entropy(value)
        entropy_hit = len(value) >= _MIN_LEN and ent >= _ENTROPY_THRESHOLD
        if prefix_hit or entropy_hit:
            confidence = "alta" if prefix_hit else "media"
            findings.append({
                "location": location, "confidence": confidence, "entropy": ent,
            })
    finding_count = len(findings)
    high_confidence = sum(1 for x in findings if x["confidence"] == "alta")
    blocked = finding_count > 0
    delivered_event = "secrets.finding_opened" if blocked else "secrets.scan_completed"
    return _out(spec, state, {
        "scanned_count": len(candidates),
        "finding_count": finding_count,
        "high_confidence_count": high_confidence,
        "findings": findings,
        "blocked": blocked,
        "delivered_event": delivered_event,
    }, f"Voce e {spec['id']}: {len(candidates)} candidatos, {finding_count} segredos "
       f"({high_confidence} alta confianca); blocked={blocked}.", llm)

# ---------------------------------------------------------------------------
# Burn-down Track A — g5-access-auditor: auditoria determinística de IAM.
# ---------------------------------------------------------------------------
@register("access_review")
def access_review(state, *, llm, store, spec):
    """g5-access-auditor — detecta órfãos, over-privilege, credenciais ociosas e SoD."""
    a = state["task"].get("access_review", {}) or {}
    identities = a.get("identities", []) or []
    idle_days = a.get("idle_days", 90) or 90
    findings = []
    revoke_actions = 0
    recertify_actions = 0
    for ident in identities:
        iid = ident.get("id")
        perms = set(ident.get("permissions", []) or [])
        required = set(ident.get("required_permissions", []) or [])
        extra = sorted(perms - required)
        owner_active = bool(ident.get("owner_active", True))
        last_used = ident.get("last_used_days", 0) or 0
        recertified = bool(ident.get("recertified", False))
        sod = ident.get("sod_conflicts", []) or []
        if not owner_active:
            findings.append({"id": iid, "type": "orphan", "severity": "alta"}); revoke_actions += 1
        if extra:
            findings.append({"id": iid, "type": "over_privilege", "severity": "media", "extra_count": len(extra)}); revoke_actions += 1
        if last_used >= idle_days:
            findings.append({"id": iid, "type": "stale_credential", "severity": "media"}); revoke_actions += 1
        if sod:
            findings.append({"id": iid, "type": "sod_violation", "severity": "alta", "conflict_count": len(sod)}); recertify_actions += 1
        if not recertified:
            recertify_actions += 1
    orphan_count = sum(1 for f in findings if f["type"] == "orphan")
    over_privilege_count = sum(1 for f in findings if f["type"] == "over_privilege")
    sod_violation_count = sum(1 for f in findings if f["type"] == "sod_violation")
    least_privilege_pct = round((len(identities) - over_privilege_count) / len(identities) * 100, 1) if identities else 100.0
    status = "remediar" if findings else "ok"
    return _out(spec, state, {
        "identity_count": len(identities), "finding_count": len(findings),
        "orphan_count": orphan_count, "over_privilege_count": over_privilege_count,
        "sod_violation_count": sod_violation_count, "least_privilege_pct": least_privilege_pct,
        "revoke_actions": revoke_actions, "recertify_actions": recertify_actions,
        "status": status,
    }, f"Voce e {spec['id']}: {len(findings)} achados IAM, status {status}.", llm)


# ---------------------------------------------------------------------------
# Burn-down R3-A — g5-agentshield-scanner: varredura determinística da config de UM
# agente contra o baseline AgentShield. Espelha nucleo/security/agentshield.py mas
# opera sobre state["task"]["scan"] (payload do caso) p/ ser autocontido e determinístico.
# Acha: over-privilege (worker com tool de escrita sem justificativa), violação C7
# (SDK de fornecedor citado como tool), exec arbitrário em MCP sem gate, eval/guardians
# ausentes (pré-condição C4), e drift de modo (escalada de autonomia sem aprovação).
# ---------------------------------------------------------------------------
_PRIVILEGED_TOOLS = {"repo.write", "db.migrate", "shell.exec", "infra.apply"}
_VENDOR_SDKS = ("openai", "anthropic", "stripe", "twilio", "whatsapp-web", "boto3", "langchain")
_AUTONOMY_ORDER = {"SHADOW": 0, "PILOT": 1, "ASSISTED": 2, "AUTONOMOUS": 3}


@register("agentshield_scan")
def agentshield_scan(state, *, llm, store, spec):
    sc = state["task"].get("scan", {}) or {}
    role = sc.get("role", "worker")
    tools = sc.get("tools", []) or []
    justified = set(sc.get("justified_tools", []) or [])
    guardians = sc.get("guardians", []) or []
    has_evals = bool(sc.get("has_evals", True))
    mode = sc.get("mode")
    prev_mode = sc.get("prev_mode")
    mode_change_approved = bool(sc.get("mode_change_approved", False))
    mcp_arbitrary_exec = bool(sc.get("mcp_arbitrary_exec", False))

    findings = []  # cada um: (severidade, tipo)
    # over-privilege: worker com tool de escrita não justificada
    over = [t for t in tools if t in _PRIVILEGED_TOOLS and t not in justified]
    if role == "worker" and over:
        findings.append(("high", "over_privilege"))
    # C7: SDK de fornecedor citado como tool
    c7_violations = [t for t in tools if any(v in str(t).lower() for v in _VENDOR_SDKS)]
    if c7_violations:
        findings.append(("high", "c7_vendor_sdk"))
    # MCP com execução arbitrária sem gate humano
    if mcp_arbitrary_exec:
        findings.append(("high", "mcp_arbitrary_exec"))
    # pré-condição de promoção C4
    if not has_evals:
        findings.append(("high", "sem_eval_suite"))
    if not guardians:
        findings.append(("med", "sem_guardians"))
    # drift: escalada de autonomia entre releases sem aprovação cruzada
    drift_detected = bool(
        prev_mode and mode and _AUTONOMY_ORDER.get(mode, 0) > _AUTONOMY_ORDER.get(prev_mode, 0)
        and not mode_change_approved
    )
    if drift_detected:
        findings.append(("high", "config_drift"))

    high_count = sum(1 for sev, _ in findings if sev == "high")
    verdict = "fail" if high_count else ("warn" if findings else "pass")
    return _out(spec, state, {
        "agent_id": spec["id"], "scanned_agent": sc.get("agent_id"),
        "verdict": verdict, "finding_count": len(findings), "high_count": high_count,
        "over_privilege": bool(over) and role == "worker", "c7_violation": bool(c7_violations),
        "drift_detected": drift_detected, "missing_evals": not has_evals,
        "missing_guardians": not guardians, "requires_human_review": verdict == "fail",
    }, f"Voce e {spec['id']}: scan de {sc.get('agent_id')} -> {verdict} ({len(findings)} achados).", llm)
