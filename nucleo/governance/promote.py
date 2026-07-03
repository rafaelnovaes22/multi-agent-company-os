"""Promotion (C4) — o único caminho para um agente SUBIR de modo.

Aplica os 6 gates + cross-approval (anti-self-approval) e usa o eval-harness como
Gate 4. SHADOW -> PILOT -> ASSISTED -> AUTONOMOUS. Promoção registrada append-only
no Brain + store. É o mecanismo de "evoluir ganhando autonomia". Mercado-agnóstico.

Gates: G1 C2(outcome clause) · G2 C3(economics, billable) · G3 C4(SLA assinado) ·
G4 eval-suite passing (estático+security) · G5 cross-approval (po != promotion_officer) ·
G6 CI/CD · G7 SLA de ENTREGA (delivered_eligible_rate do oráculo executável >= 95%, decisão
CEO 2026-06-30). O denominador do G7 são os casos ELEGÍVEIS (expected.exec_delivered=True — a
suíte é discriminante: negativos-por-design medem o fail-safe, não a entrega); um negativo
que ENTREGA é falso-positivo grave e HARD-FAIL independente da taxa. G7 vale para ->ASSISTED
e ->AUTONOMOUS (os modos que entregam/cobram) e é FAIL-CLOSED em dobro: sem executor real OU
sem casos elegíveis declarados (natureza sem oráculo executável) não promove — a diferença de
G4 (estático, gameável ~100%) para G7 (execução real) é exatamente o ponto da decisão.
AUTONOMOUS exige ainda assinatura do security-privacy-guardian.

DESCER nunca tem gate (resiliência operacional, NIST "sobreviver ao inevitável"):
`demote()` derruba qualquer modo -> SHADOW sem pré-condições, e
`set_fleet_kill_switch()` contém a frota INTEIRA (todo gate runtime passa a se
comportar como SHADOW) sem tocar nos modos persistidos. Ambos auditados
append-only no Brain.
"""
from __future__ import annotations
import datetime
import hashlib
import json

from ..factory.factory import load_spec
from ..kernel.execution import get_executor
from ..kernel.gates import KILL_SWITCH_NS, KILL_SWITCH_KEY
from ..kernel.guardians import validate_outcome_clause
from ..quality import exec_report
from ..quality.eval_harness import run_evals, run_security_evals

MODES = ["SHADOW", "PILOT", "ASSISTED", "AUTONOMOUS"]
REQUIRED = {
    ("SHADOW", "PILOT"): ["G1", "G2", "G4", "G5"],
    ("PILOT", "ASSISTED"): ["G1", "G2", "G3", "G4", "G5", "G7"],
    ("ASSISTED", "AUTONOMOUS"): ["G1", "G2", "G3", "G4", "G5", "G6", "G7"],
}
EVAL_THRESHOLD = 0.9
DELIVERED_THRESHOLD = 0.95   # SLA de entrega (decisão CEO 2026-06-30): >=95% por agente


def _delivered_summary(spec_dir):
    """Resumo do oráculo executável (exec_report) com o delivered_rate REAL.

    Seam de injeção: testes fazem monkeypatch desta função para não rodar Docker.
    Em produção roda o agente pela execução real; sem executor (InertExecutor) o
    delivered_rate volta 0 e o G7 reprova — fail-closed por construção.
    """
    ex = get_executor()
    rep = exec_report.run(spec_dir)
    return exec_report.summarize(rep, executor_name=ex.name, executor_available=ex.available)


def current_mode(store, aid: str) -> str:
    return store.get(("modes", aid), "current") or "SHADOW"


def _spec_hash(spec: dict) -> str:
    blob = json.dumps(spec.get("outcome_clause", {}), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode()).hexdigest()[:12]


def _gate(g, spec, spec_dir, req, deps):
    if g == "G1":  # C2 — cláusula de outcome válida (po-guardian)
        v = validate_outcome_clause(spec)
        return v["valid"], f"C2 outcome_clause valid={v['valid']} missing={v['missing']}"
    if g == "G2":  # C3 — economics (só billable bloqueia)
        if spec.get("ledger") == "billable":
            ec = spec.get("economics") or {}
            ok = bool(ec) and (ec.get("max_ratio", 1) <= 0.25)
            return ok, f"C3 billable max_ratio={ec.get('max_ratio')}"
        return True, "C3 operating (não bloqueia; ROI-vs-headcount)"
    if g == "G3":  # C4 — SLA pré-contratado assinado (observability-guardian)
        return bool(req.get("sla")), f"SLA={'assinado' if req.get('sla') else 'AUSENTE'}"
    if g == "G4":  # eval-suite passing (eval-engineer) + suite security (invariante: 100%)
        rep = run_evals(spec_dir, **deps)
        sec = run_security_evals(spec_dir, **deps)
        sec_ok = sec["total"] == 0 or sec["rate"] >= 1.0  # 0 casos = vácuo (catraca cobra)
        ok = rep["rate"] >= EVAL_THRESHOLD and sec_ok
        return ok, (f"eval {rep['passed']}/{rep['total']} ({rep['rate']*100:.0f}%) "
                    f"thr={EVAL_THRESHOLD*100:.0f}% · security {sec['passed']}/{sec['total']}")
    if g == "G5":  # cross-approval (anti-self-approval)
        po, pr = req.get("approver_po"), req.get("approver_promotion_officer")
        ok = bool(po) and bool(pr) and po != pr
        return ok, f"po={po} promotion_officer={pr} distintos={ok}"
    if g == "G6":  # CI/CD ativo (assisted->autonomous)
        return bool(req.get("cicd_active")), f"cicd_active={bool(req.get('cicd_active'))}"
    if g == "G7":  # SLA de ENTREGA — delivered_eligible_rate do oráculo executável >= 95% (CEO 2026-06-30)
        proof_note = "execução local ao vivo (sem perímetro de credencial)"
        if req.get("delivery_proof") == "ci-perimeter":
            # G-PERÍMETRO: a prova vem do artefato do nightly em main (identidade do CI,
            # distinta do promotor), buscada via API — FAIL-CLOSED se não houver.
            from . import perimeter
            got = perimeter.fetch_perimeter_summary(spec["id"])
            if not got:
                return False, ("SLA entrega: prova de PERÍMETRO indisponível (sem nightly "
                               "forge-exec verde recente em main com este agente). Promoção "
                               "bloqueada (fail-closed) — G-PERÍMETRO não degrada p/ prova local.")
            s = got["summary"]
            p = got["proof"]
            proof_note = (f"perímetro CI: run {p['run_id']} @ {str(p['commit'])[:12]} "
                          f"({p['workflow']}, {p['artifact']})")
        else:
            s = _delivered_summary(spec_dir)
        ex = s.get("executor") or {}
        dr = s.get("delivered_eligible_rate") or {}
        passed, total, pct = dr.get("passed") or 0, dr.get("total") or 0, dr.get("percent") or 0.0
        fp = int(s.get("false_positive_delivery_count") or 0)
        if not ex.get("available"):
            # FAIL-CLOSED: sem execução real não há prova de entrega — não promove.
            return False, (f"SLA entrega: executor '{ex.get('name')}' indisponível — delivered_rate "
                           f"não medível (sem prova executável). Promoção bloqueada (fail-closed).")
        if total <= 0:
            # FAIL-CLOSED: a suíte não declara nenhum caso elegível (expected.exec_delivered=True)
            # — natureza sem oráculo executável de entrega (estrutural/browser) ou suíte
            # não-instrumentada. Sem denominador não há SLA medível, logo não promove.
            return False, ("SLA entrega: 0 casos elegíveis (expected.delivered_ok=True) na suíte — "
                           "entrega não medível para esta natureza. Promoção bloqueada (fail-closed).")
        if fp > 0:
            # HARD-FAIL do fail-safe: um negativo-por-design ENTREGOU = resposta errada
            # silenciosa. Viola o invariante dos <=5% (decisão D3), independe da taxa.
            return False, (f"SLA entrega: {fp} falso-positivo(s) de entrega (negativo-por-design "
                           f"creditado) — fail-safe violado (resposta errada silenciosa). HARD-FAIL.")
        rate = pct / 100.0
        not_delivered = max(total - passed, 0)   # os <=5%: runtime force delivered=False/billing=0
        ok = rate >= DELIVERED_THRESHOLD
        raw = s.get("delivered_rate") or {}
        return ok, (f"SLA entrega: delivered_eligible_rate {passed}/{total} ({pct:.0f}%) "
                    f"thr={DELIVERED_THRESHOLD*100:.0f}% · bruto {raw.get('passed')}/{raw.get('total')} · "
                    f"falso-positivo=0 · {not_delivered} não-entregue(s) caem no "
                    f"fail-safe do runtime (delivered=False/billing=0, sem resposta-errada-silenciosa) "
                    f"· prova: {proof_note}")
    return False, "gate desconhecido"


def promote(spec_dir, to_mode, req, deps, brain, store) -> dict:
    spec = load_spec(spec_dir)
    aid = spec["id"]
    frm = current_mode(store, aid)
    if (frm, to_mode) not in REQUIRED:
        return {"ok": False, "agent": aid, "error": f"transição inválida {frm} -> {to_mode}"}

    checks = []
    for g in REQUIRED[(frm, to_mode)]:
        ok, ev = _gate(g, spec, spec_dir, req, deps)
        checks.append({"gate": g, "ok": ok, "evidence": ev})
    if to_mode == "AUTONOMOUS":  # assinatura extra do security guardian
        sec = bool(req.get("approver_security"))
        checks.append({"gate": "SEC", "ok": sec, "evidence": f"security-privacy-guardian={req.get('approver_security')}"})

    passed = all(c["ok"] for c in checks)
    record = {
        "actor": "promotion-officer", "action": "promotion_attempt", "agent": aid,
        "from": frm, "to": to_mode, "passed": passed, "gates": checks,
        "spec_hash": _spec_hash(spec), "approvals": req,
        "ts": datetime.datetime.now().isoformat(timespec="seconds"),
    }
    brain.emit_event(record)
    if passed:
        store.put(("modes", aid), "current", to_mode)
        log = store.get(("promotions", aid), "log") or []
        log.append({"from": frm, "to": to_mode, "spec_hash": record["spec_hash"], "ts": record["ts"]})
        store.put(("promotions", aid), "log", log)  # append-only
    return {"ok": passed, "agent": aid, "from": frm, "to": to_mode, "gates": checks}


def demote(spec_dir, reason: str, req: dict, brain, store) -> dict:
    """Demoção: qualquer modo -> SHADOW, SEM gates. Conter é sempre permitido —
    o caminho de volta não pode ter fricção. Idempotente (SHADOW -> SHADOW ok)."""
    spec = load_spec(spec_dir)
    aid = spec["id"]
    frm = current_mode(store, aid)
    record = {
        "actor": req.get("actor", "promotion-officer"), "action": "demotion", "agent": aid,
        "from": frm, "to": "SHADOW", "reason": reason,
        "spec_hash": _spec_hash(spec),
        "ts": datetime.datetime.now().isoformat(timespec="seconds"),
    }
    brain.emit_event(record)
    store.put(("modes", aid), "current", "SHADOW")
    log = store.get(("promotions", aid), "log") or []
    log.append({"from": frm, "to": "SHADOW", "action": "demotion", "reason": reason,
                "spec_hash": record["spec_hash"], "ts": record["ts"]})
    store.put(("promotions", aid), "log", log)  # append-only
    return {"ok": True, "agent": aid, "from": frm, "to": "SHADOW", "reason": reason}


def set_fleet_kill_switch(on: bool, reason: str, req: dict, brain, store) -> dict:
    """Liga/desliga a contenção da frota inteira. Com a flag ativa, o gate runtime
    de TODO agente se comporta como SHADOW (sem entrega/cobrança), preservando os
    modos persistidos — soltar o switch devolve a frota ao estado promovido."""
    actor = req.get("actor", "promotion-officer")
    record = {
        "actor": actor, "action": "fleet_kill_switch", "on": on, "reason": reason,
        "ts": datetime.datetime.now().isoformat(timespec="seconds"),
    }
    brain.emit_event(record)
    store.put(KILL_SWITCH_NS, KILL_SWITCH_KEY,
              {"on": on, "reason": reason, "actor": actor, "ts": record["ts"]})
    return {"ok": True, "on": on, "reason": reason}
