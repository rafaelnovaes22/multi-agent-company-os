"""skills_sales — handlers G08/G02/G01 (lead, diagnose, market sizing)."""

from __future__ import annotations

from ..product.catalog import recommend as recommend_product_agents
from .loaders import load_icp, load_offerings
from .skills_registry import _tokens, register


@register("lead_qualifier")
def lead_qualifier(state, *, llm, store, spec):
    icp = load_icp()  # C5 — carrega o ICP estratégico (cacheado)
    lead = state["task"].get("lead", {}) or {}
    score, signals, reasons = _score_lead_against_icp(lead)
    decision = "qualified" if score >= 60 else "disqualified"
    track = _route(score)
    rationale = llm.complete(
        f"Voce e {spec['id']}. Lead={lead.get('company', '?')} score={score} "
        f"decisao={decision} trilha={track}. Justifique pelo ICP Tier 1."
    )
    icp_ref = "icp:" + icp.get("path", "").split("Multi-Agentes")[-1].replace("\\", "/")
    return {
        "output": {
            "decision": decision,
            "score": score,
            "track": track,
            "icp_fit_signals": signals,
            "reasons": reasons,
            "lead_id": lead.get("id"),
            "rationale": rationale,
            "by": spec["id"],
        },
        "cost_tokens": _tokens(rationale),
        "citations": [icp_ref, "lead:" + str(lead.get("id", "?"))],
    }


@register("outbound_sdr")
def outbound_sdr(state, *, llm, store, spec):
    """Monta uma sequência de cold B2B outreach personalizada (Tier 2 do ICP), respeitando consentimento (LGPD)."""
    icp = load_icp()  # C5 — ancora a mensagem nas dores do ICP
    lead = state["task"].get("lead", {}) or {}
    qual = state["task"].get("qualification", {}) or {}
    if qual.get("decision") == "disqualified":
        # respeita a qualificação (auditoria 2026-07-03, decisão §6.7): lead desqualificado
        # NÃO recebe sequência de prospecção — bloqueio explícito, nunca outreach silencioso.
        reason = (
            "lead disqualified na qualificação — prospecção bloqueada "
            "(respeita qualification.decision)"
        )
        return {
            "output": {
                "account_id": lead.get("id"),
                "sequence": [],
                "blocked": True,
                "reason": reason,
                "consent_required": True,
                "requires_human_review": True,
                "rationale": reason,
                "by": spec["id"],
            },
            "cost_tokens": 0,
            "citations": ["icp:/nucleo/company/icp.md", "lead:" + str(lead.get("id", "?"))],
        }
    pains = [k for k, v in (qual.get("icp_fit_signals") or {}).items() if v]
    skus = (state["task"].get("diagnostic") or {}).get(
        "sku_candidates", []
    )  # pitch vindo do diagnóstico
    sequence = [
        {
            "step": 1,
            "channel": "email",
            "angle": "dor: vende bem mas opera no caos / sem processo",
            "subject": f"{lead.get('company', '')}: tirar o caos da operação",
        },
        {
            "step": 2,
            "channel": "email",
            "angle": "prova social + build-in-public (founder brand)",
            "subject": "como CEOs R$1-20M e enterprises ~R$100M tiram caos da operação",
        },
        {
            "step": 3,
            "channel": "messaging",
            "angle": "follow-up curto, CTA 15min",
            "subject": "vale 15 min?",
        },
    ]
    rationale = llm.complete(
        f"Voce e {spec['id']}. Monte cold outreach para {lead.get('company', '?')} "
        f"ancorado nas dores {pains} do ICP. Respeite consentimento/LGPD."
    )
    return {
        "output": {
            "account_id": lead.get("id"),
            "sequence": sequence,
            "consent_required": True,
            "personalization_signals": pains,
            "sku_pitch": skus[:2],
            "rationale": rationale,
            "by": spec["id"],
        },
        "cost_tokens": _tokens(rationale),
        "citations": ["icp:/nucleo/company/icp.md", "lead:" + str(lead.get("id", "?"))],
    }


@register("diagnose")
def diagnose(state, *, llm, store, spec):
    """C1 (diagnose-before-build): produz um diagnóstico estruturado e cobrável de um
    cliente — problema, baseline humano, outcome proposto, métrica e candidatos a SKU.
    É o PRIMEIRO entregável cobrável (vende-se o diagnóstico antes de construir)."""
    icp = load_icp()
    offerings = load_offerings()  # pode não existir ainda (pré-workshop)
    client = state["task"].get("client", {}) or {}

    # 1. Fit com o ICP (reusa o scorer)
    fit_score, fit_signals, _ = _score_lead_against_icp(client)

    # 2. Baseline humano (C1): volume x horas/unidade x custo/hora
    vol = client.get("monthly_volume", 0) or 0
    hpu = client.get("hours_per_unit", 0) or 0
    cph = client.get("hourly_cost_brl", 0) or 0
    baseline_hours = round(vol * hpu, 1)
    baseline_cost = round(vol * hpu * cph, 2)

    # 3. Problema, outcome proposto e métrica
    proc = client.get("process", "o processo crítico")
    problem = client.get("pain") or "Vende bem mas opera no caos: sem processo definido."
    proposed_outcome = (
        f"Automatizar '{proc}' entregando o resultado dentro do SLA, "
        f"com acurácia >= 95%, reduzindo o custo humano do baseline."
    )
    success_metric = f"'{proc}' concluído e verificável por evento técnico (DELIVERED)."

    # 4. Quais AGENTES DE PRODUTO ativar para este cliente (mapeado pelo catálogo)
    recommended = recommend_product_agents(client)

    # 5. Recomendação: precisa de fit de ICP E baseline mensurável (senão, não há o que automatizar/cobrar)
    go = fit_score >= 60 and baseline_cost > 0
    rationale = llm.complete(
        f"Voce e {spec['id']}. Diagnostico de {client.get('company', '?')}: fit={fit_score}, "
        f"baseline=R${baseline_cost}/mes. Recomendacao={'go' if go else 'no-go'}. Justifique em 1 frase."
    )

    diagnostic = {
        "client_id": client.get("id"),
        "fit_icp_score": fit_score,
        "fit_signals": fit_signals,
        "problem": problem,
        "baseline": {
            "monthly_volume": vol,
            "hours_per_unit": hpu,
            "hourly_cost_brl": cph,
            "baseline_hours_month": baseline_hours,
            "baseline_cost_brl_month": baseline_cost,
        },
        "proposed_outcome": proposed_outcome,
        "success_metric": success_metric,
        "recommended_agents": recommended,
        "recommendation": "go" if go else "no-go (qualificar mais ou recusar)",
        "rationale": rationale,
        "by": spec["id"],
    }
    cites = ["icp:/nucleo/company/icp.md", "client:" + str(client.get("id", "?"))]
    if offerings.get("present"):
        cites.append("offerings:/nucleo/company/offerings.md")
    return {"output": diagnostic, "cost_tokens": _tokens(rationale), "citations": cites}


def _sku_candidates(process: str, fit_signals: dict) -> list:
    """Candidatos a SKU automatizável (agnósticos de vertical; especializam após o workshop)."""
    out = []
    if fit_signals.get("sem_processo") or fit_signals.get("perfil_bombeiro"):
        out.append(f"Automação do processo '{process}' (do caos para fluxo definido)")
    out.append("Agente de triagem/qualificação do funil de entrada")
    out.append("Painel de outcomes (tornar a operação legível/queryable)")
    return out


@register("market_intel")
def market_intel(state, *, llm, store, spec):
    """G01 — avalia um VERTICAL candidato contra o ICP: estima o pool de ICP, lista
    fontes Tier 2 e aplica os hard-filters do workshop. Organiza inputs de pesquisa
    (não inventa dados de mercado) num assessment estruturado para a decisão."""
    icp = load_icp()
    c = state["task"].get("candidate", {}) or {}
    vert = c.get("vertical", "?")
    est = c.get("est_companies_brazil", 0) or 0
    founder_share = c.get("founder_led_share", 0) or 0  # 0..1
    pain = c.get("process_pain_evidence", 0) or 0  # 0..5
    tier2 = c.get("tier2_sources", []) or []
    reg_risk = c.get("regulatory_risk", 0) or 0  # 0..5
    icp_pool = int(est * founder_share)
    density = _bucket(icp_pool, [(0, 1), (1_000, 2), (10_000, 3), (50_000, 4), (200_000, 5)])
    hard = {
        "F1_icp_presente": icp_pool > 0,
        "F2_dor_processo": pain >= 3,
        "F4_acessivel_tier2": len(tier2) > 0,
    }
    passes = all(hard.values())
    rationale = llm.complete(
        f"Voce e {spec['id']}. Vertical '{vert}': pool ICP ~{icp_pool}, dor {pain}/5, "
        f"{len(tier2)} fontes Tier2, risco reg {reg_risk}/5. Passa hard-filters={passes}."
    )
    return {
        "output": {
            "vertical": vert,
            "icp_pool_estimate": icp_pool,
            "density_score": density,
            "process_pain_0a5": pain,
            "tier2_sources": tier2,
            "regulatory_risk_0a5": reg_risk,
            "hard_filters": hard,
            "passes_hard_filters": passes,
            "rationale": rationale,
            "by": spec["id"],
        },
        "cost_tokens": _tokens(rationale),
        "citations": ["icp:/nucleo/company/icp.md", "vertical:" + str(vert)],
    }


@register("opportunity_sizer")
def opportunity_sizer(state, *, llm, store, spec):
    """G01 — TAM/SAM/SOM de um vertical candidato a partir de premissas explícitas."""
    c = state["task"].get("candidate", {}) or {}
    vert = c.get("vertical", "?")
    companies = c.get("icp_pool_estimate") or c.get("est_companies_brazil", 0) or 0
    reach = c.get("reachable_share", 0.0) or 0.0  # 0..1 (alcançável via Tier 2)
    conv = c.get("conversion", 0.0) or 0.0  # 0..1
    ticket = c.get("avg_ticket_brl_year", 0) or 0
    tam = companies * ticket
    sam = int(companies * reach) * ticket
    som = int(companies * reach * conv) * ticket
    rationale = llm.complete(
        f"Voce e {spec['id']}. Sizing '{vert}': TAM R${tam}, SAM R${sam}, SOM R${som}. "
        f"Premissas: {companies} empresas, reach {reach}, conv {conv}, ticket R${ticket}/ano."
    )
    return {
        "output": {
            "vertical": vert,
            "tam_brl": tam,
            "sam_brl": sam,
            "som_brl": som,
            "assumptions": {
                "companies": companies,
                "reachable_share": reach,
                "conversion": conv,
                "avg_ticket_brl_year": ticket,
            },
            "rationale": rationale,
            "by": spec["id"],
        },
        "cost_tokens": _tokens(rationale),
        "citations": ["vertical:" + str(vert)],
    }


def _bucket(value, thresholds):
    """thresholds: lista (min_value, score) em ordem asc; retorna o maior score cujo min <= value."""
    score = thresholds[0][1]
    for mn, sc in thresholds:
        if value >= mn:
            score = sc
    return score


def _score_lead_against_icp(lead: dict):
    """Pontua o lead contra os TRÊS ICPs do NÚCLEO (ver company/icp.md, faixas 2026-06-10):
    - ICP-1 bombeiro/PAF: R$1-6M/ano, founder-led, vende bem mas opera no caos.
    - ICP-2 enterprise: >R$100M/ano (ou setor público), desorganizada em processos,
      time grande e custo de pessoal alto substituível por agentes Novais Digital.
    - ICP-3 mid-market: R$50-100M/ano que cresceu além do fundador sem profissionalizar —
      a faixa sozinha NÃO qualifica; exige dor evidente (processo/custo de pessoal/gargalo).
    A faixa R$6-50M é DESCONSIDERADA por enquanto (decisão founder 2026-06-10) — não pontua.
    `signals['icp_tier']` indica o perfil avaliado (bombeiro | enterprise | mid_market |
    fora_do_alvo | fora)."""
    signals, reasons, score = {}, [], 0
    rev = lead.get("revenue_brl_year", 0) or 0

    # Roteia por faturamento (setor público entra como enterprise mesmo sem faturamento alto)
    if rev > 100_000_000 or lead.get("public_sector"):
        tier = "enterprise"
    elif 50_000_000 <= rev <= 100_000_000:
        tier = "mid_market"
    elif 1_000_000 <= rev <= 6_000_000:
        tier = "bombeiro"
    elif 6_000_000 < rev < 50_000_000:
        tier = "fora_do_alvo"  # R$6-50M desconsiderada por enquanto — não pontua nem com dor
    else:
        tier = "fora"  # <R$1M ou faturamento não informado — faixa não validada não pontua
    signals["icp_tier"] = tier

    if tier == "bombeiro":
        score += 35
        signals["faturamento_1a6M"] = True
        reasons.append("Faturamento na faixa R$1-6M (ICP-1 bombeiro/PAF)")
        if lead.get("founder_led"):
            score += 20
            signals["founder_led"] = True
            reasons.append("Decisao founder-led")
        if lead.get("sells_well"):
            score += 15
            signals["vende_bem"] = True
            reasons.append("Vende bem (gargalo nao e receita)")
        if lead.get("lacks_process"):
            score += 20
            signals["sem_processo"] = True
            reasons.append("Sem processos definidos (dor central)")
        if lead.get("firefighter") or lead.get("adhd_traits"):
            score += 10
            signals["perfil_bombeiro"] = True
            reasons.append("Perfil bombeiro/TDAH")
        if lead.get("ops_mature"):
            score -= 30
            signals["ops_madura"] = True
            reasons.append("Operacao ja madura (desqualifica)")

    elif tier == "enterprise":
        score += 30
        signals["faturamento_100M+"] = True
        reasons.append("Faturamento >R$100M ou setor publico (ICP-2 enterprise)")
        if lead.get("public_sector"):
            score += 15
            signals["setor_publico"] = True
            reasons.append("Setor publico (alta desorganizacao = alvo)")
        if lead.get("lacks_process") or lead.get("process_disorganized"):
            score += 20
            signals["processos_desorganizados"] = True
            reasons.append("Desorganizada em processos (dor central)")
        if lead.get("large_team") or (lead.get("team_size", 0) or 0) >= 50:
            score += 15
            signals["time_grande"] = True
            reasons.append("Time grande (muitas pessoas)")
        if lead.get("high_personnel_cost"):
            score += 20
            signals["custo_pessoal_alto"] = True
            reasons.append("Custo de pessoal alto substituivel por agentes Novais Digital")

    elif tier == "mid_market":
        score += 30
        signals["faturamento_50a100M"] = True
        reasons.append("Faturamento na faixa R$50-100M (ICP-3 mid-market)")
        if lead.get("lacks_process") or lead.get("process_disorganized"):
            score += 20
            signals["processos_desorganizados"] = True
            reasons.append("Processos nao acompanharam o porte (dor central)")
        if lead.get("high_personnel_cost"):
            score += 20
            signals["custo_pessoal_alto"] = True
            reasons.append("Custo de pessoal alto substituivel por agentes Novais Digital")
        if lead.get("large_team") or (lead.get("team_size", 0) or 0) >= 50:
            score += 15
            signals["time_grande"] = True
            reasons.append("Time grande (muitas pessoas)")
        if lead.get("founder_led") or lead.get("firefighter"):
            score += 10
            signals["fundador_gargalo"] = True
            reasons.append("Fundador ainda e gargalo de decisao")
        if lead.get("ops_mature"):
            score -= 30
            signals["ops_madura"] = True
            reasons.append("Operacao ja madura (desqualifica)")

    elif tier == "fora_do_alvo":
        signals["faturamento"] = False
        reasons.append("Faixa R$6-50M desconsiderada por enquanto (decisao 2026-06-10)")

    else:  # fora (<R$1M ou não informado)
        signals["faturamento"] = False
        reasons.append("Abaixo de R$1M ou faturamento nao informado (pre-ICP)")

    return max(0, min(100, score)), signals, reasons


def _route(score: int) -> str:
    if score >= 75:
        return "assistido (SDR/closer)"
    if score >= 60:
        return "self-serve (ativacao no produto)"
    return "descarte"


# ---------------------------------------------------------------------------
# Handlers determinísticos por guilda (registram-se por side-effect ao importar).
# Mantidos no fim para evitar ciclo: importam register/_tokens/_spec_citations já
# definidos acima. Dão lógica de domínio real aos agentes que a spec marca com um
# act_handler nominal (rice_score, churn_risk_score, secret_scan, ...). C8: a
# variação continua na spec; aqui mora só o cálculo, reusado por todos os tenants.
# ---------------------------------------------------------------------------
from . import (  # noqa: E402,F401  # noqa: E402,F401  # noqa: E402,F401
    skills_custops,  # noqa: E402,F401  (G09)
    skills_exec,  # noqa: E402,F401  (spec_executor — VERIFY-IN-EVAL F0)
    skills_finance,  # noqa: E402,F401  (G10)
    skills_g00,
    skills_g01,
    skills_g02,
    skills_g03,
    skills_g04,
    skills_g05,
    skills_g06,
    skills_g07,
    skills_g08,
    skills_g11,
    skills_g12,
    skills_g13,
    skills_g14,
)
