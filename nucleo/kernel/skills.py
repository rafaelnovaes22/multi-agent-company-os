"""Skills / act-handlers — a lógica do nó `act` de cada agente, plugável por spec.

Cada agente declara `act_handler: <nome>` na sua spec. A Fábrica materializa o
mesmo grafo (load->act->...); só o miolo do `act` muda. Assim 1 template serve
para os ~169 agentes (C8 — variação é configuração, não código novo por agente).

Assinatura de um handler:
    handler(state, *, llm, store, spec) -> {output, cost_tokens, citations}
"""
from __future__ import annotations

from .guardians import validate_outcome_clause
from .loaders import load_icp, load_offerings
from ..product.catalog import recommend as recommend_product_agents

_HANDLERS: dict = {}


def register(name: str):
    def deco(fn):
        _HANDLERS[name] = fn
        return fn
    return deco


def get_handler(name: str):
    return _HANDLERS.get(name) or _HANDLERS["outcome_clause_validator"]


def _tokens(text: str) -> int:
    return max(1, len(text) // 4)


# ---------------------------------------------------------------------------
# G13 — po-guardian: valida a cláusula de outcome (C2) de uma spec-alvo
# ---------------------------------------------------------------------------
@register("outcome_clause_validator")
def outcome_clause_validator(state, *, llm, store, spec):
    verdict = validate_outcome_clause(state["task"].get("target_spec", {}))
    rationale = llm.complete(
        f"Voce e {spec['id']}. verdict={'valid' if verdict['valid'] else 'invalid'}; "
        f"faltando={verdict['missing']}. Escreva um parecer curto e acionavel."
    )
    return {
        "output": {"verdict": verdict, "rationale": rationale, "by": spec["id"]},
        "cost_tokens": _tokens(rationale),
        "citations": ["spec:" + str(state["task"].get("target_spec", {}).get("id", "?"))],
    }


# ---------------------------------------------------------------------------
# G08 — lead-qualifier: pontua um lead contra o ICP L0 (company/icp.md)
# ---------------------------------------------------------------------------
@register("lead_qualifier")
def lead_qualifier(state, *, llm, store, spec):
    icp = load_icp()                       # C5 — carrega o ICP estratégico (cacheado)
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
            "decision": decision, "score": score, "track": track,
            "icp_fit_signals": signals, "reasons": reasons,
            "lead_id": lead.get("id"), "rationale": rationale, "by": spec["id"],
        },
        "cost_tokens": _tokens(rationale),
        "citations": [icp_ref, "lead:" + str(lead.get("id", "?"))],
    }


@register("outbound_sdr")
def outbound_sdr(state, *, llm, store, spec):
    """Monta uma sequência de cold B2B outreach personalizada (Tier 2 do ICP), respeitando consentimento (LGPD)."""
    icp = load_icp()                                   # C5 — ancora a mensagem nas dores do ICP
    lead = state["task"].get("lead", {}) or {}
    qual = state["task"].get("qualification", {}) or {}
    pains = [k for k, v in (qual.get("icp_fit_signals") or {}).items() if v]
    skus = (state["task"].get("diagnostic") or {}).get("sku_candidates", [])   # pitch vindo do diagnóstico
    sequence = [
        {"step": 1, "channel": "email", "angle": "dor: vende bem mas opera no caos / sem processo",
         "subject": f"{lead.get('company', '')}: tirar o caos da operação"},
        {"step": 2, "channel": "email", "angle": "prova social + build-in-public (founder brand)",
         "subject": "como founders R$1-5M escalam sem virar bombeiro"},
        {"step": 3, "channel": "messaging", "angle": "follow-up curto, CTA 15min",
         "subject": "vale 15 min?"},
    ]
    rationale = llm.complete(
        f"Voce e {spec['id']}. Monte cold outreach para {lead.get('company', '?')} "
        f"ancorado nas dores {pains} do ICP. Respeite consentimento/LGPD."
    )
    return {
        "output": {"account_id": lead.get("id"), "sequence": sequence,
                   "consent_required": True, "personalization_signals": pains, "sku_pitch": skus[:2],
                   "rationale": rationale, "by": spec["id"]},
        "cost_tokens": _tokens(rationale),
        "citations": ["icp:/nucleo/company/icp.md", "lead:" + str(lead.get("id", "?"))],
    }


@register("diagnose")
def diagnose(state, *, llm, store, spec):
    """C1 (diagnose-before-build): produz um diagnóstico estruturado e cobrável de um
    cliente — problema, baseline humano, outcome proposto, métrica e candidatos a SKU.
    É o PRIMEIRO entregável cobrável (vende-se o diagnóstico antes de construir)."""
    icp = load_icp()
    offerings = load_offerings()                       # pode não existir ainda (pré-workshop)
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
    proposed_outcome = (f"Automatizar '{proc}' entregando o resultado dentro do SLA, "
                        f"com acurácia >= 95%, reduzindo o custo humano do baseline.")
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
        "client_id": client.get("id"), "fit_icp_score": fit_score, "fit_signals": fit_signals,
        "problem": problem,
        "baseline": {"monthly_volume": vol, "hours_per_unit": hpu, "hourly_cost_brl": cph,
                     "baseline_hours_month": baseline_hours, "baseline_cost_brl_month": baseline_cost},
        "proposed_outcome": proposed_outcome, "success_metric": success_metric,
        "recommended_agents": recommended,
        "recommendation": "go" if go else "no-go (qualificar mais ou recusar)",
        "rationale": rationale, "by": spec["id"],
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
    founder_share = c.get("founder_led_share", 0) or 0          # 0..1
    pain = c.get("process_pain_evidence", 0) or 0               # 0..5
    tier2 = c.get("tier2_sources", []) or []
    reg_risk = c.get("regulatory_risk", 0) or 0                 # 0..5
    icp_pool = int(est * founder_share)
    density = _bucket(icp_pool, [(0, 1), (1_000, 2), (10_000, 3), (50_000, 4), (200_000, 5)])
    hard = {"F1_icp_presente": icp_pool > 0, "F2_dor_processo": pain >= 3, "F4_acessivel_tier2": len(tier2) > 0}
    passes = all(hard.values())
    rationale = llm.complete(
        f"Voce e {spec['id']}. Vertical '{vert}': pool ICP ~{icp_pool}, dor {pain}/5, "
        f"{len(tier2)} fontes Tier2, risco reg {reg_risk}/5. Passa hard-filters={passes}."
    )
    return {"output": {"vertical": vert, "icp_pool_estimate": icp_pool, "density_score": density,
                       "process_pain_0a5": pain, "tier2_sources": tier2, "regulatory_risk_0a5": reg_risk,
                       "hard_filters": hard, "passes_hard_filters": passes,
                       "rationale": rationale, "by": spec["id"]},
            "cost_tokens": _tokens(rationale),
            "citations": ["icp:/nucleo/company/icp.md", "vertical:" + str(vert)]}


@register("opportunity_sizer")
def opportunity_sizer(state, *, llm, store, spec):
    """G01 — TAM/SAM/SOM de um vertical candidato a partir de premissas explícitas."""
    c = state["task"].get("candidate", {}) or {}
    vert = c.get("vertical", "?")
    companies = c.get("icp_pool_estimate") or c.get("est_companies_brazil", 0) or 0
    reach = c.get("reachable_share", 0.0) or 0.0                # 0..1 (alcançável via Tier 2)
    conv = c.get("conversion", 0.0) or 0.0                      # 0..1
    ticket = c.get("avg_ticket_brl_year", 0) or 0
    tam = companies * ticket
    sam = int(companies * reach) * ticket
    som = int(companies * reach * conv) * ticket
    rationale = llm.complete(
        f"Voce e {spec['id']}. Sizing '{vert}': TAM R${tam}, SAM R${sam}, SOM R${som}. "
        f"Premissas: {companies} empresas, reach {reach}, conv {conv}, ticket R${ticket}/ano."
    )
    return {"output": {"vertical": vert, "tam_brl": tam, "sam_brl": sam, "som_brl": som,
                       "assumptions": {"companies": companies, "reachable_share": reach,
                                       "conversion": conv, "avg_ticket_brl_year": ticket},
                       "rationale": rationale, "by": spec["id"]},
            "cost_tokens": _tokens(rationale),
            "citations": ["vertical:" + str(vert)]}


def _bucket(value, thresholds):
    """thresholds: lista (min_value, score) em ordem asc; retorna o maior score cujo min <= value."""
    score = thresholds[0][1]
    for mn, sc in thresholds:
        if value >= mn:
            score = sc
    return score


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


@register("inbox_triage")
def inbox_triage(state, *, llm, store, spec):
    """AGENTE DE PRODUTO (multi-tenant) — triagem da caixa de entrada do cliente.
    Classifica e roteia mensagens/pedidos. Agnóstico de segmento."""
    t = state["task"]
    profile = (state.get("context", {}) or {}).get("tenant_profile", {}) or {}
    msgs = (t.get("inbox", {}) or {}).get("messages", []) or []
    triaged, counts = [], {}
    for m in msgs:
        cat, route = _classify_msg(m.get("text", ""))
        urgent = _is_urgent(m.get("text", ""))
        counts[cat] = counts.get(cat, 0) + 1
        triaged.append({"id": m.get("id"), "from": m.get("from"), "category": cat,
                        "urgency": "alta" if urgent else "normal", "route": route})
    urgent_count = sum(1 for x in triaged if x["urgency"] == "alta")
    rationale = llm.complete(
        f"Voce e {spec['id']} para {profile.get('name', 'o cliente')}: {len(msgs)} mensagens triadas, "
        f"{urgent_count} urgentes. Roteie para o agente/humano certo."
    )
    return {
        "output": {"tenant": t.get("tenant_id"), "total": len(msgs), "triaged": triaged,
                   "counts_by_category": counts, "urgent_count": urgent_count,
                   "rationale": rationale, "by": spec["id"]},
        "cost_tokens": _tokens(rationale),
        "citations": [f"tenant:{t.get('tenant_id')}", "inbox:snapshot"],
    }


def _classify_msg(text: str):
    tl = (text or "").lower()
    if any(k in tl for k in ["orçamento", "orcamento", "preço", "preco", "quero comprar", "cotação", "cotacao", "proposta"]):
        return "comercial", "atendimento"
    if any(k in tl for k in ["boleto", "nota", " nf ", "pagamento", "pagar", "cobrança", "cobranca", "atraso", "fatura"]):
        return "financeiro", "fin-caixa"
    if any(k in tl for k in ["reclamação", "reclamacao", "problema", "não funciona", "nao funciona", "cancelar", "reembolso"]):
        return "suporte", "ops-followup"
    if any(k in tl for k in ["fornecedor", "entrega do pedido", "insumo", "pedido do fornecedor"]):
        return "compras", "ops-followup"
    return "geral", "painel-dono"


def _is_urgent(text: str) -> bool:
    tl = (text or "").lower()
    return any(k in tl for k in ["urgente", "hoje", "agora", "parado", "parada", "imediato", "emergência", "emergencia"])


@register("ops_followup")
def ops_followup(state, *, llm, store, spec):
    """PRODUTO multi-tenant — operações/follow-up: o que está parado, sem dono ou atrasado."""
    t = state["task"]
    profile = (state.get("context", {}) or {}).get("tenant_profile", {}) or {}
    ops = t.get("ops", {}) or {}
    today = ops.get("today", "")
    tasks = ops.get("tasks", []) or []
    stalled = [x for x in tasks if x.get("status") not in ("done", "concluido")
               and ((x.get("due_date", "") and x["due_date"] < today) or x.get("status") in ("parado", "blocked", "bloqueado"))]
    no_owner = [x for x in tasks if not x.get("owner") and x.get("status") not in ("done", "concluido")]
    actions = []
    if stalled:
        actions.append("Destravar: " + ", ".join(x.get("title", "?") for x in sorted(stalled, key=lambda z: z.get("due_date", ""))[:3]))
    if no_owner:
        actions.append("Atribuir dono: " + ", ".join(x.get("title", "?") for x in no_owner[:3]))
    rationale = llm.complete(f"Voce e {spec['id']} para {profile.get('name', 'o cliente')}: {len(stalled)} paradas, {len(no_owner)} sem dono.")
    return {"output": {"tenant": t.get("tenant_id"), "stalled_count": len(stalled), "no_owner_count": len(no_owner),
                       "stalled": [x.get("title") for x in stalled], "recommended_actions": actions,
                       "rationale": rationale, "by": spec["id"]},
            "cost_tokens": _tokens(rationale), "citations": [f"tenant:{t.get('tenant_id')}", "ops:snapshot"]}


@register("atendimento")
def atendimento(state, *, llm, store, spec):
    """PRODUTO multi-tenant — atendimento/comercial: fila de respostas e follow-up de orçamentos."""
    t = state["task"]
    profile = (state.get("context", {}) or {}).get("tenant_profile", {}) or {}
    reqs = (t.get("atendimento", {}) or {}).get("requests", []) or []
    queue = sorted(reqs, key=lambda r: -(r.get("waiting_hours", 0) or 0))
    overdue = [r for r in reqs if (r.get("waiting_hours", 0) or 0) > 24]
    actions = [f"Responder {r.get('customer', '?')} ({r.get('type', '?')}, {r.get('waiting_hours', 0)}h esperando)" for r in queue[:3]]
    rationale = llm.complete(f"Voce e {spec['id']} para {profile.get('name', 'o cliente')}: {len(reqs)} pendentes, {len(overdue)} atrasadas (>24h).")
    return {"output": {"tenant": t.get("tenant_id"), "reply_queue_count": len(reqs), "overdue_replies": len(overdue),
                       "queue": [{"customer": r.get("customer"), "type": r.get("type"), "waiting_hours": r.get("waiting_hours")} for r in queue],
                       "recommended_actions": actions, "rationale": rationale, "by": spec["id"]},
            "cost_tokens": _tokens(rationale), "citations": [f"tenant:{t.get('tenant_id')}", "atendimento:snapshot"]}


@register("painel_dono")
def painel_dono(state, *, llm, store, spec):
    """PRODUTO multi-tenant — painel do dono: 'como estou?' (semáforo + alertas) agregando o fleet."""
    t = state["task"]
    profile = (state.get("context", {}) or {}).get("tenant_profile", {}) or {}
    m = t.get("metrics", {}) or {}
    alerts = []
    if (m.get("projected_cash") or 0) < 0:
        alerts.append("Caixa projetado negativo")
    if (m.get("total_overdue") or 0) > 0:
        alerts.append(f"Inadimplência a cobrar: R$ {m.get('total_overdue')}")
    if m.get("margin_pct") is not None and m["margin_pct"] < 10:
        alerts.append(f"Margem apertada ({m['margin_pct']}%)")
    if (m.get("urgent_msgs") or 0) > 0:
        alerts.append(f"{m['urgent_msgs']} mensagem(ns) urgente(s)")
    if (m.get("stalled_tasks") or 0) > 0:
        alerts.append(f"{m['stalled_tasks']} tarefa(s) parada(s)")
    semaforo = "vermelho" if (m.get("projected_cash") or 0) < 0 else ("amarelo" if alerts else "verde")
    resumo = f"Caixa R$ {m.get('cash_position')}, projetado R$ {m.get('projected_cash')} | {len(alerts)} alerta(s)"
    rationale = llm.complete(f"Voce e {spec['id']} para {profile.get('name', 'o dono')}: semaforo {semaforo}, {len(alerts)} alertas.")
    return {"output": {"tenant": t.get("tenant_id"), "semaforo": semaforo, "alert_count": len(alerts),
                       "top_alerts": alerts, "resumo": resumo, "rationale": rationale, "by": spec["id"]},
            "cost_tokens": _tokens(rationale), "citations": [f"tenant:{t.get('tenant_id')}", "painel:snapshot"]}


def _score_lead_against_icp(lead: dict):
    """Pontua o lead contra o ICP Tier 1: R$1-5M, founder-led, vende bem sem processo, perfil bombeiro."""
    signals, reasons, score = {}, [], 0
    rev = lead.get("revenue_brl_year", 0) or 0

    if 1_000_000 <= rev <= 5_000_000:
        score += 35; signals["faturamento_1a5M"] = True
        reasons.append("Faturamento na faixa R$1-5M (Tier 1)")
    elif 0 < rev < 1_000_000:
        signals["faturamento_1a5M"] = False; reasons.append("Abaixo de R$1M (pre-ICP)")
    elif rev > 5_000_000:
        signals["faturamento_1a5M"] = False; reasons.append("Acima de R$5M (pode ser maduro demais)")

    if lead.get("founder_led"):
        score += 20; signals["founder_led"] = True; reasons.append("Decisao founder-led")
    if lead.get("sells_well"):
        score += 15; signals["vende_bem"] = True; reasons.append("Vende bem (gargalo nao e receita)")
    if lead.get("lacks_process"):
        score += 20; signals["sem_processo"] = True; reasons.append("Sem processos definidos (dor central)")
    if lead.get("firefighter") or lead.get("adhd_traits"):
        score += 10; signals["perfil_bombeiro"] = True; reasons.append("Perfil bombeiro/TDAH")
    if lead.get("ops_mature"):
        score -= 30; signals["ops_madura"] = True; reasons.append("Operacao ja madura (desqualifica)")

    return max(0, min(100, score)), signals, reasons


def _route(score: int) -> str:
    if score >= 75:
        return "assistido (SDR/closer)"
    if score >= 60:
        return "self-serve (ativacao no produto)"
    return "descarte"
