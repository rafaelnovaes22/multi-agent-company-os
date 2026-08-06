"""Handlers determinísticos da G03 Engenharia — o cálculo real (não LLM) que dá
lógica de domínio aos agentes da Software Factory que a spec marcou como
`needs_deterministic`. Mesmo padrão de skills_finance/skills_custops: campos no
top-level do output; o grader genérico de contrato valida `expected` direto.
"""

from __future__ import annotations

from .skills import _spec_citations, _tokens, register


def _out(spec, state, fields, rationale_prompt, llm):
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


@register("perf_benchmark_delta")
def perf_benchmark_delta(state, *, llm, store, spec):
    """g3-perf-optimizer — compara métrica antes/depois (p95, throughput, custo) de
    forma determinística e só declara melhoria com evidência de benchmark E correção
    preservada (testes verdes). Sem otimização "no escuro" e sem ganho às custas de
    resultado incorreto (KPIs: melhoria p95/p99, redução de custo, regressões=0).

    Inputs em state['task']['benchmark']:
      before, after          — latência p95 (ms) antes/depois (menor é melhor)
      cost_before, cost_after — custo por operação (menor é melhor; opcional)
      tests_passed           — bool: correção preservada (testes verdes)
      slo_registered         — bool: SLO registrado para travar regressão futura
      profiled               — bool: otimização justificada por profiling (não no escuro)
    """
    b = state["task"].get("benchmark", {}) or {}
    before = b.get("before", 0) or 0
    after = b.get("after", 0) or 0
    cost_before = b.get("cost_before")
    cost_after = b.get("cost_after")
    tests_passed = bool(b.get("tests_passed", False))
    slo_registered = bool(b.get("slo_registered", False))
    profiled = bool(b.get("profiled", False))

    # Delta de latência: positivo = melhora (queda de p95).
    latency_delta_pct = round((before - after) / before * 100, 1) if before else 0.0
    cost_delta_pct = (
        round((cost_before - cost_after) / cost_before * 100, 1) if cost_before else None
    )

    # Melhoria real exige: ganho de latência > 0, profiling que justifique e correção preservada.
    improved = latency_delta_pct > 0 and profiled and tests_passed
    correctness_preserved = tests_passed
    # DELIVERED só com benchmark melhorado, correção preservada e SLO travando regressão.
    delivered = improved and correctness_preserved and slo_registered

    if not profiled:
        status = "no_escuro"  # otimização sem profiling — rejeitada
    elif not tests_passed:
        status = "regressao"  # ganho às custas de correção — rejeitada
    elif latency_delta_pct <= 0:
        status = "sem_ganho"  # não melhorou (ou regrediu) a métrica-alvo
    elif not slo_registered:
        status = "melhorou_sem_slo"  # melhorou mas falta SLO p/ travar regressão
    else:
        status = "melhorou"

    return _out(
        spec,
        state,
        {
            "latency_delta_pct": latency_delta_pct,
            "cost_delta_pct": cost_delta_pct,
            "improved": improved,
            "correctness_preserved": correctness_preserved,
            "delivered": delivered,
            "status": status,
        },
        f"Voce e {spec['id']}: p95 {before}->{after} ({latency_delta_pct}%), status {status}.",
        llm,
    )


# ---------------------------------------------------------------------------
# Burn-down R3 — g3-feature-flagger: decisão determinística de rollout/kill-switch.
# guard-metrics vs thresholds -> rollback/kill; senão ramp progressivo; detecta flag obsoleta.
# ---------------------------------------------------------------------------
@register("feature_flag_rollout")
def feature_flag_rollout(state, *, llm, store, spec):
    t = state["task"]
    flag = t.get("flag", {}) or {}
    rollout = float(flag.get("rollout_pct", 0) or 0)
    step = float(flag.get("ramp_step_pct", 25) or 25)
    gm = flag.get("guard_metrics", {}) or {}
    th = flag.get("thresholds", {}) or {}
    err = float(gm.get("error_rate", 0) or 0)
    lat = float(gm.get("latency_ms", 0) or 0)
    max_err = float(th.get("max_error_rate", 0.02) or 0.02)
    max_lat = float(th.get("max_latency_ms", 800) or 800)
    err_breach = err > max_err
    lat_breach = lat > max_lat
    guard_breached = err_breach or lat_breach
    severe = err > 2 * max_err
    age = float(flag.get("age_days", 0) or 0)
    last_used = float(flag.get("last_used_days", 0) or 0)
    obsolete = age > 90 and last_used > 30
    if guard_breached:
        decision = "kill" if severe else "rollback"
        rollback_triggered, next_pct, requires_review = True, 0.0, True
    elif rollout >= 100:
        decision, rollback_triggered, next_pct, requires_review = "hold", False, 100.0, False
    else:
        decision, rollback_triggered = "proceed_ramp", False
        next_pct, requires_review = min(100.0, rollout + step), False
    return _out(
        spec,
        state,
        {
            "agent_id": spec["id"],
            "flag": flag.get("name"),
            "rollout_pct": rollout,
            "guard_breached": guard_breached,
            "error_breach": err_breach,
            "latency_breach": lat_breach,
            "decision": decision,
            "rollback_triggered": rollback_triggered,
            "next_rollout_pct": next_pct,
            "obsolete": obsolete,
            "requires_human_review": requires_review,
        },
        f"Voce e {spec['id']}: flag {flag.get('name')} rollout {rollout}% -> {decision}.",
        llm,
    )


# ---------------------------------------------------------------------------
# Burn-down R3 — g3-api-contract: detecção determinística de breaking changes (semver).
# ---------------------------------------------------------------------------
@register("api_contract_diff")
def api_contract_diff(state, *, llm, store, spec):
    t = state["task"]
    api = t.get("api", {}) or {}
    old = {
        f"{e['path']}|{e.get('method', 'GET')}": e
        for e in (api.get("old", {}) or {}).get("endpoints", []) or []
    }
    new = {
        f"{e['path']}|{e.get('method', 'GET')}": e
        for e in (api.get("new", {}) or {}).get("endpoints", []) or []
    }
    breaking, non_breaking = [], []
    for key, oe in old.items():
        if key not in new:
            breaking.append({"endpoint": key, "change": "endpoint_removed"})
            continue
        ne = new[key]
        old_req, new_req = set(oe.get("required_params", []) or []), set(
            ne.get("required_params", []) or []
        )
        for p in sorted(new_req - old_req):
            breaking.append({"endpoint": key, "change": "required_param_added", "param": p})
        for p in sorted(old_req - new_req):
            non_breaking.append({"endpoint": key, "change": "required_param_removed", "param": p})
        if oe.get("response_type") != ne.get("response_type"):
            breaking.append({"endpoint": key, "change": "response_type_changed"})
    for key in sorted(new.keys() - old.keys()):
        non_breaking.append({"endpoint": key, "change": "endpoint_added"})
    compatible = not breaking
    bump = "major" if breaking else ("minor" if non_breaking else "patch")
    return _out(
        spec,
        state,
        {
            "agent_id": spec["id"],
            "breaking_count": len(breaking),
            "non_breaking_count": len(non_breaking),
            "breaking_changes": breaking,
            "compatible": compatible,
            "recommended_bump": bump,
            "requires_human_review": not compatible,
        },
        f"Voce e {spec['id']}: {len(breaking)} breaking change(s), bump {bump}.",
        llm,
    )


# ---------------------------------------------------------------------------
# Burn-down R3-A — g3-db-schema: revisão determinística de migração de schema.
# Precedência de bloqueio (do mais grave ao menos): sem rollback -> quebra de
# contrato sem versionamento -> não backward-compatible -> PII não classificada ->
# integridade referencial violada -> ok. C2: migração aplica/reverte sem perda,
# mantém compatibilidade e marca PII (DELIVERED = up_down_validated && pii_map.updated).
# ---------------------------------------------------------------------------
@register("schema_change_review")
def schema_change_review(state, *, llm, store, spec):
    m = state["task"].get("migration", {}) or {}
    has_rollback = bool(m.get("rollback_tested", False))
    backward_compatible = bool(m.get("backward_compatible", True))
    breaks_api_unversioned = bool(m.get("breaks_api_unversioned", False))
    referential_ok = bool(m.get("referential_integrity_ok", True))
    pii_columns = m.get("pii_columns", []) or []
    pii_unclassified = [c.get("name") for c in pii_columns if not c.get("classified", False)]
    pii_map_complete = not pii_unclassified

    if not has_rollback:
        status = "sem_rollback"
    elif breaks_api_unversioned:
        status = "quebra_contrato"
    elif not backward_compatible:
        status = "incompativel"
    elif pii_unclassified:
        status = "pii_nao_classificada"
    elif not referential_ok:
        status = "integridade_violada"
    else:
        status = "ok"

    safe_to_merge = status == "ok"
    # Espelha o trigger DELIVERED do catálogo sem usar a chave proibida 'delivered'.
    up_down_validated = has_rollback and backward_compatible and not breaks_api_unversioned
    return _out(
        spec,
        state,
        {
            "agent_id": spec["id"],
            "has_rollback": has_rollback,
            "backward_compatible": backward_compatible,
            "compatible": not breaks_api_unversioned,
            "pii_unclassified_count": len(pii_unclassified),
            "pii_map_complete": pii_map_complete,
            "referential_integrity_ok": referential_ok,
            "status": status,
            "up_down_validated": up_down_validated,
            "safe_to_merge": safe_to_merge,
            "requires_human_review": not safe_to_merge,
        },
        f"Voce e {spec['id']}: migracao status {status}, merge {'ok' if safe_to_merge else 'bloqueado'}.",
        llm,
    )


# ---------------------------------------------------------------------------
# Burn-down R3-A — g3-dependency-warden: decisão determinística de bump de dependência.
# Política: licença proibida/dep abandonada bloqueia; major exige plano; breaking sem
# código ajustado exige fix; CI vermelho bloqueia; senão aprova (patch/minor = auto).
# C2: deps sem CVE explorável, build verde, licenças compatíveis (DELIVERED = cve_clean && ci.green).
# ---------------------------------------------------------------------------
_LICENCAS_PROIBIDAS = {"AGPL-3.0", "SSPL", "GPL-3.0", "BUSL-1.1", "Commons-Clause"}
_CVE_SLA_DAYS = {"critica": 2, "alta": 7, "media": 30, "baixa": 90}


@register("dependency_bump_review")
def dependency_bump_review(state, *, llm, store, spec):
    d = state["task"].get("dependency", {}) or {}
    cve = d.get("cve_severity")  # None | critica | alta | media | baixa
    bump = (d.get("bump_type") or "patch").lower()  # patch | minor | major
    has_breaking = bool(d.get("has_breaking_changes", False))
    code_adjusted = bool(d.get("code_adjusted", False))
    has_plan = bool(d.get("has_migration_plan", False))
    ci_green = bool(d.get("ci_green", True))
    license_id = d.get("license", "MIT")
    abandoned = bool(d.get("abandoned", False))

    license_ok = license_id not in _LICENCAS_PROIBIDAS
    if not license_ok:
        decision = "block_licenca"
    elif abandoned:
        decision = "block_abandonada"
    elif bump == "major" and not has_plan:
        decision = "needs_plan"
    elif has_breaking and not code_adjusted:
        decision = "needs_code_fix"
    elif not ci_green:
        decision = "ci_vermelho"
    else:
        decision = "approve_bump"

    approved = decision == "approve_bump"
    auto_mergeable = approved and bump in ("patch", "minor")
    cve_addressed = approved and cve is not None  # o bump aprovado limpa a CVE
    requires_review = not auto_mergeable  # major/bloqueio/pendência -> humano
    return _out(
        spec,
        state,
        {
            "agent_id": spec["id"],
            "cve_severity": cve,
            "bump_type": bump,
            "decision": decision,
            "license_ok": license_ok,
            "abandoned": abandoned,
            "auto_mergeable": auto_mergeable,
            "cve_addressed": cve_addressed,
            "exposure_sla_days": _CVE_SLA_DAYS.get(cve),
            "requires_human_review": requires_review,
        },
        f"Voce e {spec['id']}: bump {bump} -> {decision}.",
        llm,
    )


# ---------------------------------------------------------------------------
# Burn-down G03 — g3-docs-lookup: busca determinística em docs com ranking.
# Query vs corpus: score por overlap de palavras; detecta encontrado vs vazio.
# C2: docs consultáveis e resposta rastreável (top doc + score + found).
# ---------------------------------------------------------------------------
@register("docs_lookup")
def docs_lookup(state: dict, *, llm, store, spec: dict) -> dict:
    t = state.get("task", {}) or {}
    query = (t.get("query") or "").strip()
    docs = t.get("docs", []) or []
    q_words = set(query.lower().split()) if query else set()

    def _score(doc: dict) -> int:
        text = (doc.get("text") or "").lower()
        words = set(text.split())
        return len(q_words & words)

    scored = [(d, _score(d)) for d in docs]
    scored.sort(key=lambda x: x[1], reverse=True)
    top = scored[0] if scored else (None, 0)
    top_doc, top_score = top[0], top[1] if scored else 0
    found = bool(query and top_score > 0)
    ranked_ids = [d.get("id") for d, s in scored if s > 0]
    status = "found" if found else ("empty_query" if not query else "not_found")
    return _out(
        spec,
        state,
        {
            "agent_id": spec["id"],
            "query": query,
            "docs_count": len(docs),
            "top_score": top_score,
            "top_doc_id": top_doc.get("id") if top_doc else None,
            "found": found,
            "ranked_ids": ranked_ids,
            "status": status,
        },
        f"Voce e {spec['id']}: query '{query}' -> {status} (top_score={top_score}).",
        llm,
    )


# ---------------------------------------------------------------------------
# Burn-down G03 — g3-planner: cobertura de requisitos e detecção de ciclo.
# requirements vs phases[covers, depends_on]: cobertura 100% e grafo acíclico.
# ---------------------------------------------------------------------------
@register("planner")
def planner(state: dict, *, llm, store, spec: dict) -> dict:
    t = state.get("task", {}) or {}
    reqs = t.get("requirements", []) or []
    phases = t.get("phases", []) or []
    req_ids = [r.get("id") if isinstance(r, dict) else str(r) for r in reqs]
    covered: set[str] = set()
    for p in phases:
        for cid in p.get("covers", []) or []:
            covered.add(str(cid))
    total = len(req_ids)
    covered_count = len([r for r in req_ids if r in covered])
    missing = [r for r in req_ids if r not in covered]
    coverage_pct = round(covered_count / total * 100, 1) if total else 100.0
    # ciclo em depends_on
    graph = {p.get("id"): set(p.get("depends_on", []) or []) for p in phases}
    visiting: set[str] = set()
    visited: set[str] = set()
    has_cycle = False

    def _dfs(n: str) -> bool:
        if n in visiting:
            return True
        if n in visited:
            return False
        visiting.add(n)
        for dep in graph.get(n, set()):
            if _dfs(dep):
                return True
        visiting.remove(n)
        visited.add(n)
        return False

    for nid in graph:
        if _dfs(nid):
            has_cycle = True
            break
    is_valid = not missing and not has_cycle and total > 0
    status = "valid" if is_valid else ("cycle" if has_cycle else "missing_reqs" if missing else "empty")
    return _out(
        spec,
        state,
        {
            "agent_id": spec["id"],
            "total_requirements": total,
            "covered_count": covered_count,
            "coverage_pct": coverage_pct,
            "missing_requirements": missing,
            "has_cycle": has_cycle,
            "is_valid": is_valid,
            "status": status,
        },
        f"Voce e {spec['id']}: coverage {coverage_pct}% status {status}.",
        llm,
    )


# ---------------------------------------------------------------------------
# Burn-down G03 — g3-refactorer: análise de impacto e decisão de merge.
# penaliza complexidade aumentada, falha de testes e impacto não mapeado.
# ---------------------------------------------------------------------------
@register("refactorer")
def refactorer(state: dict, *, llm, store, spec: dict) -> dict:
    t = state.get("task", {}) or {}
    r = t.get("refactor", {}) or {}
    target = r.get("target") or ""
    files = r.get("impact_files", []) or []
    tests_passed = bool(r.get("tests_passed", False))
    before = r.get("complexity_before")
    after = r.get("complexity_after")
    delta = (after - before) if isinstance(before, (int, float)) and isinstance(after, (int, float)) else None
    complexity_increased = delta is not None and delta > 0
    impact_size = len(files)
    if not target:
        decision = "blocked_no_target"
    elif not tests_passed:
        decision = "blocked_tests_red"
    elif complexity_increased:
        decision = "blocked_complexity_up"
    elif impact_size == 0:
        decision = "blocked_no_impact"
    else:
        decision = "approve"
    safe_to_merge = decision == "approve"
    risk = "high" if complexity_increased or not tests_passed else ("medium" if impact_size > 5 else "low")
    return _out(
        spec,
        state,
        {
            "agent_id": spec["id"],
            "target": target,
            "impact_size": impact_size,
            "complexity_delta": delta,
            "complexity_increased": complexity_increased,
            "tests_passed": tests_passed,
            "decision": decision,
            "safe_to_merge": safe_to_merge,
            "risk": risk,
            "requires_human_review": not safe_to_merge,
        },
        f"Voce e {spec['id']}: refactor {target} -> {decision}.",
        llm,
    )


# ---------------------------------------------------------------------------
# Burn-down G03 — g3-integration-builder: conformidade C7 para integrações.
# bloqueia SDK direto; exige interface abstraída e config-over-code.
# ---------------------------------------------------------------------------
@register("integration_builder")
def integration_builder(state: dict, *, llm, store, spec: dict) -> dict:
    t = state.get("task", {}) or {}
    integ = t.get("integration", {}) or {}
    provider = integ.get("provider") or ""
    interface = integ.get("interface") or ""
    direct_sdk = bool(integ.get("direct_sdk_call", False))
    config_ok = bool(integ.get("config_over_code", True))
    uses_abstraction = bool(interface and not direct_sdk)
    c7_compliant = uses_abstraction and config_ok and bool(provider)
    if direct_sdk:
        status = "sdk_direto"
    elif not interface:
        status = "sem_interface"
    elif not config_ok:
        status = "hardcode"
    elif not provider:
        status = "sem_provider"
    else:
        status = "compliant"
    return _out(
        spec,
        state,
        {
            "agent_id": spec["id"],
            "provider": provider,
            "interface": interface,
            "uses_abstraction": uses_abstraction,
            "config_compliant": config_ok,
            "c7_compliant": c7_compliant,
            "status": status,
            "requires_human_review": not c7_compliant,
        },
        f"Voce e {spec['id']}: integration {provider}/{interface} -> {status}.",
        llm,
    )
