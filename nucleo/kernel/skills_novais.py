"""skills_novais — handlers da frota INTERNA de gestão da Novais Digital (Fase 0).

Frota `novais` (nucleo/company/fleet/): fila, ponte, turno, ciclo e prefeito.
Diferente da frota de produto (vendida ao cliente), esta opera a PRÓPRIA Novais:
ledger operating, single-tenant, SHADOW. Determinística e offline (FakeLLM).
Regras do PLANO-TIMES-AGENTES-NOVAIS codificadas aqui:
- número nunca se fecha na conversa (banda pro Rafael, por escrito);
- todo número do painel com fonte; métrica sem fonte reprova o painel;
- HTTP 200 não é prova: canal se mede por endpoint+latência, deploy por status+repo.
"""

from __future__ import annotations

from datetime import datetime

from .skills_registry import _tokens, register

# Limiar de latência (ms) do endpoint de saúde acima do qual o canal degrada
# (lesson do sandbox CarInsight: cold start do Neon percebido como "bot morto").
_LATENCY_DEGRADED_MS = 2000
_SLA_DEFAULT_MIN = 15


def _minutes_between(start_iso: str, end_iso: str) -> int:
    try:
        start = datetime.fromisoformat(start_iso)
        end = datetime.fromisoformat(end_iso)
        return int((end - start).total_seconds() // 60)
    except (TypeError, ValueError):
        return -1  # idade desconhecida = fila cega (reprovável)


@register("nv_inbound_queue")
def nv_inbound_queue(state, *, llm, store, spec):
    """Fila (gerente de Atendimento): prioriza o inbound da Novais por tempo de
    espera, marca SLA estourado (15 min padrão) e devolve as 3 ações urgentes."""
    t = state["task"]
    inbound = t.get("inbound", []) or []
    now = t.get("now", "")

    pending = []
    for m in inbound:
        if m.get("status") == "answered":
            continue
        wait = _minutes_between(m.get("arrived_at", ""), now)
        sla = int(m.get("sla_min", _SLA_DEFAULT_MIN) or _SLA_DEFAULT_MIN)
        pending.append(
            {
                "id": m.get("id"),
                "channel": m.get("channel"),
                "wait_min": wait,
                "sla_min": sla,
                "overdue": wait > sla,
            }
        )
    pending.sort(key=lambda e: -e["wait_min"])
    overdue = [e for e in pending if e["overdue"]]
    top = [e["id"] for e in pending[:3]]

    actions = [
        f"Responder {e['id']} ({e['channel']}): esperando {e['wait_min']} min, SLA {e['sla_min']} min"
        for e in overdue[:3]
    ]
    if pending and not overdue:
        actions.append(
            f"Fila sob controle: {len(pending)} pendente(s), o mais antigo há "
            f"{pending[0]['wait_min']} min (dentro do SLA)."
        )

    rationale = llm.complete(
        f"Voce e {spec['id']} (gerente de Atendimento da Novais). "
        f"{len(pending)} pendente(s), {len(overdue)} com SLA estourado; mais antigo há "
        f"{pending[0]['wait_min'] if pending else 0} min."
    )
    return {
        "output": {
            "pending_count": len(pending),
            "overdue_count": len(overdue),
            "oldest_wait_min": pending[0]["wait_min"] if pending else 0,
            "queue": pending[:5],
            "top_urgent": top,
            "recommended_actions": actions,
            "rationale": rationale,
            "by": spec["id"],
        },
        "cost_tokens": _tokens(rationale),
        "citations": ["inbound:snapshot", "sla:plano-fase0"],
    }


@register("nv_channel_health")
def nv_channel_health(state, *, llm, store, spec):
    """Ponte (dev de Atendimento): saúde por canal (bot WhatsApp, formulário,
    webhook): verde / degradado (latência >= 2s, suspeita de cold start) / down."""
    t = state["task"]
    channels = t.get("channels", []) or []

    statuses = []
    for c in channels:
        code = c.get("status_code")
        latency = c.get("latency_ms") or 0
        if code != 200:
            status = "down"
        elif latency >= _LATENCY_DEGRADED_MS:
            status = "degraded"
        else:
            status = "green"
        statuses.append({"name": c.get("name"), "status": status, "latency_ms": latency})

    green = [s for s in statuses if s["status"] == "green"]
    degraded = [s for s in statuses if s["status"] == "degraded"]
    down = [s for s in statuses if s["status"] == "down"]

    actions = []
    for s in down:
        actions.append(
            f"Restaurar {s['name']} (fora do ar) e conferir a fila serial acumulada"
        )
    for s in degraded:
        actions.append(
            f"Keep-alive /health em {s['name']} (latência {s['latency_ms']} ms: suspeita de cold start)"
        )

    rationale = llm.complete(
        f"Voce e {spec['id']} (dev de Atendimento da Novais). "
        f"{len(green)} verde(s), {len(degraded)} degradado(s), {len(down)} down."
    )
    return {
        "output": {
            "total": len(statuses),
            "green_count": len(green),
            "degraded_count": len(degraded),
            "down_count": len(down),
            "all_green": not degraded and not down,
            "channels": statuses,
            "recommended_actions": actions,
            "rationale": rationale,
            "by": spec["id"],
        },
        "cost_tokens": _tokens(rationale),
        "citations": ["health:snapshot", "licao:carinsight-coldstart"],
    }


@register("nv_ops_round")
def nv_ops_round(state, *, llm, store, spec):
    """Turno (gerente de Operações): rodada diária dos projetos da Novais:
    deploys verdes, erros e órfãos (deploy sem repo) com as correções do dia."""
    t = state["task"]
    projects = t.get("projects", []) or []

    # Órfão (sem repo) nunca é verde: deploy vivo sem fonte não é ativo controlado
    green = [p for p in projects if p.get("deploy_status") == "READY" and p.get("repo_ok")]
    errors = [p for p in projects if p.get("deploy_status") == "ERROR"]
    building = [p for p in projects if p.get("deploy_status") == "BUILDING"]
    orphans = [p for p in projects if not p.get("repo_ok")]
    health_pct = round(len(green) / len(projects) * 100, 1) if projects else 0.0

    actions = [f"Redeploy/rollback de {p.get('name')} (deploy em ERROR)" for p in errors]
    actions += [
        f"Adotar repo de {p.get('name')} (deploy Vercel órfão: sem fonte sob controle)"
        for p in orphans
    ]

    rationale = llm.complete(
        f"Voce e {spec['id']} (gerente de Operações da Novais). "
        f"{len(green)}/{len(projects)} verdes ({health_pct}%), {len(errors)} erro(s), "
        f"{len(orphans)} órfão(s)."
    )
    return {
        "output": {
            "total_projects": len(projects),
            "green_count": len(green),
            "error_count": len(errors),
            "building_count": len(building),
            "orphan_count": len(orphans),
            "health_pct": health_pct,
            "recommended_actions": actions,
            "rationale": rationale,
            "by": spec["id"],
        },
        "cost_tokens": _tokens(rationale),
        "citations": [f"deploys:{len(green)}/{len(projects)}", "criterio:inventario-pronto"],
    }


@register("nv_billing_cycle")
def nv_billing_cycle(state, *, llm, store, spec):
    """Ciclo (gerente de Financeiro): MRR das recorrências da Novais, inadimplência
    e churn risk, com a régua (lembrete dia 5, firme dia 10). Nunca confirma
    número com cliente: banda pro Rafael, por escrito."""
    t = state["task"]
    subs = t.get("subscriptions", []) or []

    paying = [s for s in subs if s.get("status") in ("active", "overdue")]
    overdue = [s for s in subs if s.get("status") == "overdue"]
    mrr = sum(s.get("amount_monthly", 0) for s in paying)
    overdue_total = sum(s.get("amount_monthly", 0) for s in overdue)
    churn = [s.get("client") for s in overdue if (s.get("cycles_overdue") or 0) >= 1]

    actions = []
    for s in overdue:
        cycles = s.get("cycles_overdue") or 1
        stage = "conversa de retenção" if cycles >= 2 else "lembrete leve (dia 5)"
        actions.append(
            f"Cobrar {s.get('client')} (R$ {s.get('amount_monthly')}/mês, {cycles} ciclo(s) "
            f"em atraso): {stage}, no tom de voz"
        )
    if overdue:
        actions.append(
            "Reajuste, acordo e número: nunca na conversa — banda pro Rafael responder por escrito"
        )

    rationale = llm.complete(
        f"Voce e {spec['id']} (gerente de Financeiro da Novais). "
        f"MRR R$ {mrr} com {len(paying)} pagante(s); inadimplência R$ {overdue_total} "
        f"em {len(overdue)} cliente(s)."
    )
    return {
        "output": {
            "mrr": mrr,
            "paying_count": len(paying),
            "overdue_count": len(overdue),
            "overdue_total": overdue_total,
            "churn_risk": churn,
            "recommended_actions": actions,
            "rationale": rationale,
            "by": spec["id"],
        },
        "cost_tokens": _tokens(rationale),
        "citations": [f"mrr:{len(paying)} assinaturas", "rega:dia1-dia5-dia10"],
    }


def _metric(label, entry, fallback_source=""):
    """Normaliza uma entrada de métrica em {label, value, source}.

    Métrica sem fonte é inaceitável (regra do painel): devolve source vazia para o
    prefeito reprovar o painel inteiro — nunca inventa fonte."""
    if isinstance(entry, dict):
        return {
            "label": label,
            "value": entry.get("value"),
            "source": entry.get("source") or "",
        }
    return {"label": label, "value": entry, "source": fallback_source}


@register("nv_prefeito_panel")
def nv_prefeito_panel(state, *, llm, store, spec):
    """Prefeito (chief-of-staff): painel 08h/18h da Novais com 10 números, CADA UM
    COM FONTE, e semáforo justificado. Métrica sem fonte => painel reprovado (red)."""
    t = state["task"]
    fila = t.get("fila_out", {}) or {}
    ponte = t.get("ponte_out", {}) or {}
    turno = t.get("turno_out", {}) or {}
    ciclo = t.get("ciclo_out", {}) or {}
    funnel = t.get("funnel", {}) or {}

    pendencias = (fila.get("overdue_count") or 0) + (turno.get("error_count") or 0)

    metrics = [
        _metric("Toques no dia", funnel.get("touches", {})),
        _metric("Conversas", funnel.get("conversations", {})),
        _metric("Diagnósticos pagos", funnel.get("diagnoses", {})),
        _metric("Produtos no ar", funnel.get("sites_live", {})),
        _metric(
            "Deploys verdes (%)",
            {
                "value": turno.get("health_pct", 0),
                "source": f"turno: {turno.get('green_count', 0)}/{turno.get('total_projects', 0)} projetos",
            },
        ),
        _metric(
            "Canais verdes",
            {
                "value": ponte.get("green_count", 0),
                "source": f"ponte: {ponte.get('green_count', 0)}/{ponte.get('total', 0)} canais",
            },
        ),
        _metric(
            "MRR (R$/mês)",
            {
                "value": ciclo.get("mrr", 0),
                "source": f"ciclo: {ciclo.get('paying_count', 0)} assinatura(s) pagante(s)",
            },
        ),
        _metric(
            "Inadimplência (R$)",
            {
                "value": ciclo.get("overdue_total", 0),
                "source": f"ciclo: {ciclo.get('overdue_count', 0)} cliente(s) em atraso",
            },
        ),
        _metric("Custo de API no mês (R$)", t.get("api_cost_month_brl", {})),
        _metric(
            "Pendências queimando",
            {
                "value": pendencias,
                "source": (
                    f"fila: {fila.get('overdue_count', 0)} SLA estourado + "
                    f"turno: {turno.get('error_count', 0)} deploy(s) em ERROR"
                ),
            },
        ),
    ]
    all_sourced = all(m["source"] for m in metrics)

    alerts = []
    if (fila.get("overdue_count") or 0) > 0:
        alerts.append(f"Inbound com SLA estourado: {fila['overdue_count']} mensagem(ns)")
    if (turno.get("error_count") or 0) > 0:
        alerts.append(f"Deploy(s) em ERROR: {turno['error_count']}")
    if (ponte.get("down_count") or 0) > 0:
        alerts.append(f"Canal(is) down: {ponte['down_count']}")
    if (ciclo.get("overdue_total") or 0) > 0:
        alerts.append(f"Inadimplência: R$ {ciclo['overdue_total']}")
    if (ponte.get("degraded_count") or 0) > 0:
        alerts.append(f"Canal(is) degradado(s): {ponte['degraded_count']}")
    if (turno.get("orphan_count") or 0) > 0:
        alerts.append(f"Órfãos no inventário: {turno['orphan_count']} (higiene)")

    red = (
        (fila.get("overdue_count") or 0) > 0
        or (turno.get("error_count") or 0) > 0
        or (ponte.get("down_count") or 0) > 0
    )
    semaforo = "red" if (red or not all_sourced) else ("yellow" if alerts else "green")
    if not all_sourced:
        unsourced = [m["label"] for m in metrics if not m["source"]]
        alerts.insert(0, f"PAINEL REPROVADO: métrica sem fonte ({', '.join(unsourced)})")

    rationale = llm.complete(
        f"Voce e {spec['id']} (chief-of-staff da Novais). Painel 08h: 10 números, "
        f"{sum(1 for m in metrics if m['source'])}/10 com fonte, semáforo {semaforo} "
        f"com {len(alerts)} alerta(s)."
    )
    return {
        "output": {
            "metrics_count": len(metrics),
            "metrics": metrics,
            "all_sourced": all_sourced,
            "semaforo": semaforo,
            "top_alerts": alerts,
            "recommended_actions": alerts,
            "rationale": rationale,
            "by": spec["id"],
        },
        "cost_tokens": _tokens(rationale),
        "citations": ["frota:fila|ponte|turno|ciclo", "regra:numero-com-fonte"],
    }
