"""Graders do eval-harness — um por act_handler (espelha os "grader types" do ECC).

Cada grader recebe (output_do_agente, expected_do_caso) e devolve True/False.
Registrar um grader novo = suportar avaliar um agente novo. Mercado-agnóstico.
"""

from __future__ import annotations

_GRADERS: dict = {}


def register(name: str):
    def deco(fn):
        _GRADERS[name] = fn
        return fn

    return deco


def get_grader(name: str):
    return _GRADERS.get(name)


def _compatible(got, want) -> bool:
    """Igualdade tolerante: bool exato; números dentro de 1% (ou epsilon p/ zero);
    listas por comprimento+conteúdo; dicts por subset-match; resto por igualdade."""
    if isinstance(want, bool):
        return got == want
    if isinstance(want, (int, float)) and isinstance(got, (int, float)):
        return abs(got - want) <= max(1e-9, abs(want) * 0.01)
    if isinstance(want, list):
        return (
            isinstance(got, list)
            and len(got) == len(want)
            and all(_compatible(g, w) for g, w in zip(got, want))
        )
    if isinstance(want, dict):
        return isinstance(got, dict) and all(
            k in got and _compatible(got[k], v) for k, v in want.items()
        )
    return got == want


def generic_contract_grader(out, exp):
    """Fallback de contrato p/ qualquer agente cujo act_handler não tem grader nominal
    (ex.: os handlers determinísticos por guilda rice_score/churn_risk_score/...). Valida:
    output não-vazio com 'rationale' e 'by'; e — se o caso traz 'expected' — cada chave
    presente no output e compatível (tolerância 1% p/ números). Campos calculados no
    top-level do output são checados direto; citations ficam a cargo dos guardians."""
    if not out or "rationale" not in out or "by" not in out:
        return False
    for k, want in (exp or {}).items():
        if k not in out or not _compatible(out[k], want):
            return False
    return True


@register("outcome_clause_validator")
def _g_ocv(out, exp):
    return bool(out) and (out.get("verdict") or {}).get("valid") == exp.get("valid")


@register("lead_qualifier")
def _g_lq(out, exp):
    if not out:
        return False
    ok = out.get("decision") == exp.get("decision")
    if exp.get("track") is not None:
        ok = ok and out.get("track") == exp.get("track")
    return ok


@register("diagnose")
def _g_dg(out, exp):
    if not out:
        return False
    rec_go = str(out.get("recommendation", "")).startswith("go")
    exp_go = str(exp.get("recommendation", "")).startswith("go")
    ok = rec_go == exp_go
    if exp.get("baseline_gt") is not None:
        ok = (
            ok
            and (out.get("baseline") or {}).get("baseline_cost_brl_month", 0) > exp["baseline_gt"]
        )
    return ok


@register("market_intel")
def _g_mi(out, exp):
    return bool(out) and out.get("passes_hard_filters") == exp.get("passes_hard_filters")


@register("opportunity_sizer")
def _g_os(out, exp):
    if not out:
        return False
    tam, sam, som = out.get("tam_brl", 0), out.get("sam_brl", 0), out.get("som_brl", 0)
    ok = True
    if exp.get("som_le_sam"):
        ok = ok and som <= sam
    if exp.get("sam_le_tam"):
        ok = ok and sam <= tam
    if exp.get("som_gt_0"):
        ok = ok and som > 0
    return ok


@register("outbound_sdr")
def _g_ob(out, exp):
    if not out:
        return False
    seq = out.get("sequence", [])
    ok = True
    if exp.get("blocked"):
        # lead disqualified: bloqueio explícito E zero outreach (auditoria 2026-07-03, §6.7)
        ok = ok and out.get("blocked") is True and not seq
    if exp.get("min_steps"):
        ok = ok and len(seq) >= exp["min_steps"]
    if exp.get("consent_required"):
        ok = ok and out.get("consent_required") is True
    if exp.get("personalized"):
        ok = ok and len(out.get("personalization_signals") or []) > 0
    return ok


def _close_num(actual, expected, tolerance=0.01):
    if expected is None:
        return True
    try:
        a = float(actual)
        e = float(expected)
    except (TypeError, ValueError):
        return actual == expected
    if e == 0:
        return abs(a - e) <= tolerance
    return abs(a - e) / abs(e) <= tolerance


def _check_expected_fields(out, exp, fields):
    if not out:
        return False
    ok = True
    for key in fields:
        if key not in exp:
            continue
        expected = exp[key]
        actual = out.get(key)
        if isinstance(expected, (int, float)) and not isinstance(expected, bool):
            ok = ok and _close_num(actual, expected)
        else:
            ok = ok and actual == expected
    return ok


@register("pricing_engine")
def _g_pricing_engine(out, exp):
    return _check_expected_fields(
        out,
        exp,
        (
            "handler_kind",
            "published_price_brl",
            "delivery_cost_brl",
            "min_viable_price_brl",
            "cost_ratio",
            "max_ratio",
            "c3_margin_check",
            "status",
            "requires_human_review",
        ),
    )


@register("dunning_agent")
def _g_dunning_agent(out, exp):
    return _check_expected_fields(
        out,
        exp,
        (
            "handler_kind",
            "invoice_count",
            "total_overdue_brl",
            "recovered_count",
            "in_progress_count",
            "escalated_count",
            "recovery_status",
            "requires_human_review",
            "status",
        ),
    )


@register("revenue_reporter")
def _g_revenue_reporter(out, exp):
    return _check_expected_fields(
        out,
        exp,
        (
            "handler_kind",
            "mrr_brl",
            "nrr_pct",
            "grr_pct",
            "reconciliation_delta_brl",
            "reconciliation_delta_pct",
            "reconciled",
            "status",
            "requires_human_review",
        ),
    )


@register("reconciliation")
def _g_reconciliation(out, exp):
    return _check_expected_fields(
        out,
        exp,
        (
            "handler_kind",
            "matched_count",
            "exception_count",
            "match_rate",
            "unreconciled_balance_brl",
            "status",
            "requires_human_review",
        ),
    )


@register("unit_economist_c3")
def _g_unit_economist_c3(out, exp):
    return _check_expected_fields(
        out,
        exp,
        (
            "handler_kind",
            "billable",
            "price_brl",
            "inference_cost_brl",
            "cost_ratio",
            "max_ratio",
            "min_viable_price_brl",
            "verdict",
            "blocks_delivery",
            "status",
            "requires_human_review",
        ),
    )


@register("fin_cashflow")
def _g_fin(out, exp):
    if not out:
        return False
    ok = True
    if "total_overdue" in exp:
        ok = ok and out.get("total_overdue") == exp["total_overdue"]
    if "has_actions" in exp:
        ok = ok and (len(out.get("recommended_actions") or []) > 0) == exp["has_actions"]
    return ok


@register("inbox_triage")
def _g_inbox(out, exp):
    if not out:
        return False
    ok = True
    if "total" in exp:
        ok = ok and out.get("total") == exp["total"]
    if "urgent_count" in exp:
        ok = ok and out.get("urgent_count") == exp["urgent_count"]
    if "counts" in exp:
        cb = out.get("counts_by_category", {}) or {}
        ok = ok and all(cb.get(k) == v for k, v in exp["counts"].items())
    return ok


@register("ops_followup")
def _g_ops(out, exp):
    if not out:
        return False
    ok = True
    if "stalled_count" in exp:
        ok = ok and out.get("stalled_count") == exp["stalled_count"]
    if "has_actions" in exp:
        ok = ok and (len(out.get("recommended_actions") or []) > 0) == exp["has_actions"]
    return ok


@register("atendimento")
def _g_atend(out, exp):
    if not out:
        return False
    ok = True
    if "reply_queue_count" in exp:
        ok = ok and out.get("reply_queue_count") == exp["reply_queue_count"]
    if "overdue_replies" in exp:
        ok = ok and out.get("overdue_replies") == exp["overdue_replies"]
    return ok


@register("painel_dono")
def _g_painel(out, exp):
    if not out:
        return False
    ok = True
    if "semaforo" in exp:
        ok = ok and out.get("semaforo") == exp["semaforo"]
    if "alert_count" in exp:
        ok = ok and out.get("alert_count") == exp["alert_count"]
    return ok


def _g_catalog_contract(out, exp):
    if not out:
        return False
    ok = True
    for key in (
        "agent_id",
        "handler_kind",
        "artifact_type",
        "status",
        "risk",
        "requires_human_review",
        "routed_to",
    ):
        if key in exp:
            ok = ok and out.get(key) == exp[key]
    if "capabilities_any" in exp:
        caps = set(out.get("capabilities") or [])
        ok = ok and any(c in caps for c in exp["capabilities_any"])
    return ok


def _eq_or_tol(actual, expected, tol=0.01):
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        return abs(actual - expected) <= max(tol, abs(expected) * tol)
    return actual == expected


def _g_expected_fields(out, exp):
    if not out:
        return False
    ok = True
    for key, val in exp.items():
        if isinstance(val, dict) and isinstance(out.get(key), dict):
            ok = ok and all(_eq_or_tol(out[key].get(k), v) for k, v in val.items())
        else:
            ok = ok and _eq_or_tol(out.get(key), val)
    return ok


register("spec_driven")(_g_catalog_contract)
register("supervisor_route")(_g_catalog_contract)
register("guardian_check")(_g_catalog_contract)

for _name in (
    "pricing_engine",
    "billing_agent",
    "dunning_agent",
    "revenue_reporter",
    "reconciliation",
    "csat_analyst",
    "fulfillment_tracker",
    "burn_monitor",
    "unit_economist_c3",
    "token_cost_accountant",
    "margin_watch",
):
    register(_name)(_g_expected_fields)

# Grader de execução (spec_executor — VERIFY-IN-EVAL F0). Import no fim para registrar via
# side-effect sem ciclo: graders_exec só usa `register`, já definido acima.
from . import graders_exec  # noqa: E402,F401
