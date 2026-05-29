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
        ok = ok and (out.get("baseline") or {}).get("baseline_cost_brl_month", 0) > exp["baseline_gt"]
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
    if exp.get("min_steps"):
        ok = ok and len(seq) >= exp["min_steps"]
    if exp.get("consent_required"):
        ok = ok and out.get("consent_required") is True
    if exp.get("personalized"):
        ok = ok and len(out.get("personalization_signals") or []) > 0
    return ok


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
