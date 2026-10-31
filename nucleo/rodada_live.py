"""Rodada AO VIVO da Fase 0.5 — turno (deploys Vercel) + ponte (canais de entrada).

Roda:  python -m nucleo.rodada_live [--notify]

Substitui os payloads de exemplo do demo_fase0 por fontes vivas e alimenta os
agentes `turno` e `ponte` (SHADOW) do plano de times:
- turno: projetos do team novaisdigital via API Vercel (v9 projects, 1 request;
  latestDeployments embutido dá estado + data do último deploy de produção);
- ponte: probes HTTP nos /health dos canais de entrada da Novais (latência medida
  = o que um cliente de primeira viagem experimenta, inclusive cold start).

Read-only (só GET). Alerta compacto copiar/colar; snapshot com fonte em
relatorios/rodada-turno-YYYY-MM-DD.json. Com --notify, envia por Telegram se
TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID estiverem no ambiente (ainda sem canal:
avisa e segue).
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langgraph.checkpoint.memory import MemorySaver  # noqa: E402

from nucleo.factory.factory import build_from_spec  # noqa: E402
from nucleo.kernel.brain import Brain, FileStore  # noqa: E402
from nucleo.kernel.providers.llm import get_llm  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
TEAM_SLUG = os.environ.get("VERCEL_TEAM_SLUG", "novaisdigital")
BRAIN_DIR = os.path.join(ROOT, ".brain-fase0")
SECRETS_PATH = os.path.join(BRAIN_DIR, "secrets-novais.json")
FILA_STATE_PATH = os.path.join(BRAIN_DIR, "fila-state.json")
AUTH_CANDIDATES = [
    os.path.expandvars(r"%APPDATA%\com.vercel.cli\Data\auth.json"),
    os.path.expanduser("~/.vercel/auth.json"),
    os.path.expanduser("~/.local/share/com.vercel.cli/auth.json"),
]
API = "https://api.vercel.com"

# Mesmo limiar do handler nv_channel_health (kernel/skills_novais.py)
_LATENCY_DEGRADED_MS = 2000

# Canais de entrada da Novais (o que um cliente toca antes de falar com a gente)
CHANNELS = [
    ("novais-site", "https://inovais.tech/health"),
    ("carinsight-bot", "https://carinsight-sandbox.vercel.app/health"),
    ("claria", "https://claria.inovais.tech/api/health"),
    ("geraboleto", "https://geraboleto-novaisdigital.vercel.app/api/health"),
]


def _token() -> str:
    tok = os.environ.get("VERCEL_TOKEN")
    if tok:
        return tok
    for p in AUTH_CANDIDATES:
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                d = json.load(f)
            tok = d.get("token")
            if tok:
                return tok
    print("Token Vercel não encontrado: exporte VERCEL_TOKEN ou autentique o CLI (vercel login).")
    sys.exit(1)


def _get(url: str, token: str) -> dict:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def resolve_team(token: str) -> str | None:
    data = _get(f"{API}/v2/teams?limit=100", token)
    for t in data.get("teams", []):
        if t.get("slug") == TEAM_SLUG:
            return t.get("id")
    print(f"team '{TEAM_SLUG}' não encontrado; usando escopo pessoal.")
    return None


def _build_agent(name: str, llm, brain, store, cp):
    spec, agent, gate = build_from_spec(
        os.path.join(ROOT, "company", "fleet", name), llm, brain, store, cp
    )
    if not gate["ok"]:
        print(f"FAIL gate da fábrica em {name}: {gate['problems']}")
        sys.exit(1)
    return spec, agent


def _invoke(agent, task, ledger):
    return agent.invoke(
        {"task": task, "mode": "SHADOW", "ledger": ledger, "run_id": "live",
         "verbose": False},
        config={"configurable": {"thread_id": "rodada-live"}},
    ).get("output") or {}


def coletar_projetos(token: str, team_id: str | None) -> list[dict]:
    """Lista projetos com estado+data do último deploy de produção e link de Git."""
    projects, until = [], None
    while True:
        qs = f"teamId={team_id}&limit=100" + (f"&until={until}" if until else "")
        data = _get(f"{API}/v9/projects?{qs}", token)
        projects += data.get("projects", [])
        until = data.get("pagination", {}).get("next")
        if not until:
            break

    payload = []
    now_ms = datetime.now(timezone.utc).timestamp() * 1000
    for p in projects:
        deps = p.get("latestDeployments") or []
        prod = [d for d in deps if d.get("target") == "production"] or deps
        status, age_days = "NEVER_DEPLOYED", None
        if prod:
            latest = max(prod, key=lambda d: d.get("createdAt") or 0)
            state = latest.get("readyState") or latest.get("state") or "UNKNOWN"
            status = (
                "BUILDING" if state in ("BUILDING", "QUEUED", "INITIALIZING") else state
            )
            if status == "ERROR":
                created = latest.get("createdAt") or 0
                if created:
                    age_days = int((now_ms - created) // 86_400_000)
        payload.append(
            {
                "name": p["name"],
                "deploy_status": status,
                "repo_ok": p.get("link") is not None,
                "age_days": age_days,
            }
        )
    return payload


def _probe_once(url: str) -> tuple[int, int]:
    """Um GET de saúde: (status_code, latência_ms). 0 = inalcançável/timeout."""
    t0 = datetime.now(timezone.utc)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "nucleo-ponte/0.1"})
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, int((datetime.now(timezone.utc) - t0).total_seconds() * 1000)
    except urllib.error.HTTPError as e:
        return e.code, int((datetime.now(timezone.utc) - t0).total_seconds() * 1000)
    except Exception:
        return 0, int((datetime.now(timezone.utc) - t0).total_seconds() * 1000)


def coletar_inbound() -> tuple[list[dict], int]:
    """Inbound novo do site (formulários) desde a última rodada.

    Retorna (pendentes, total_no_store). total -1 = fonte indisponível (sem
    secrets). Na PRIMEIRA rodada com histórico existente, marca baseline e
    não dispara fila velha — o SLA conta só para o que chegar a partir de agora.
    Estado de receipts vistos em .brain-fase0/fila-state.json."""
    if not os.path.exists(SECRETS_PATH):
        return [], -1
    cfg = json.load(open(SECRETS_PATH, encoding="utf-8"))
    if not cfg.get("app_origin") or not cfg.get("admin_token_prod"):
        return [], -1
    try:
        req = urllib.request.Request(
            f"{cfg['app_origin']}/api/submissions",
            headers={
                "Authorization": f"Bearer {cfg['admin_token_prod']}",
                "User-Agent": "nucleo-fila/0.1",
            },
        )
        subs = json.load(urllib.request.urlopen(req, timeout=20)).get("submissions", [])
    except Exception as e:
        print(f"  (fila: fonte indisponível: {type(e).__name__})")
        return [], -1

    seen: set[str] = set()
    if os.path.exists(FILA_STATE_PATH):
        seen = set(json.load(open(FILA_STATE_PATH, encoding="utf-8")))
    baseline = not seen and bool(subs)
    novos = [s for s in subs if s.get("receipt") not in seen]
    os.makedirs(BRAIN_DIR, exist_ok=True)
    with open(FILA_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(sorted({s["receipt"] for s in subs}), f)

    if baseline:
        return [], len(subs)
    inbound = [
        {
            "id": (s.get("receipt") or "?")[:8],
            "channel": "site-form",
            "subject": (s.get("payload") or {}).get("name", "lead sem nome"),
            "arrived_at": s.get("createdAt", ""),
            "sla_min": 15,
            "status": "waiting",
        }
        for s in novos
    ]
    return inbound, len(subs)


def probe_canais() -> list[dict]:
    """Um GET por canal: código + latência. Latência = experiência do primeiro
    contato do cliente (cold start incluído — é o sinal, não ruído).

    Warm-retry (26/10): canal degradado/down no 1º probe ganha até 2 remedições
    (10s e 20s). Se aquecer, o status/latência canônicos passam a ser os QUENTES
    e a entrada carrega cold_start=True com o 1º probe preservado como fonte —
    cold start é anotado, não vira falso alerta de manhã."""
    out = []
    for name, url in CHANNELS:
        code, ms = _probe_once(url)
        cold, first_ms = False, ms
        for wait_s in (10, 20):
            if code == 200 and ms < _LATENCY_DEGRADED_MS:
                break
            time.sleep(wait_s)
            code2, ms2 = _probe_once(url)
            if code2 == 200 and ms2 < _LATENCY_DEGRADED_MS:
                cold, code, ms = True, code2, ms2
                break
        out.append(
            {
                "name": name,
                "status_code": code,
                "latency_ms": ms,
                "cold_start": cold,
                "first_probe_ms": first_ms,
            }
        )
    return out


def _notify_telegram(text: str) -> bool:
    tok = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    if not (tok and chat):
        return False
    import urllib.parse

    url = (
        f"https://api.telegram.org/bot{tok}/sendMessage"
        f"?chat_id={urllib.parse.quote(chat)}&text={urllib.parse.quote(text)}"
    )
    try:
        urllib.request.urlopen(url, timeout=15)
        return True
    except Exception as e:
        print(f"  notify falhou: {e}")
        return False


def main() -> int:
    notify = "--notify" in sys.argv
    token = _token()
    team_id = resolve_team(token)
    t0 = datetime.now(timezone.utc)

    llm = get_llm("worker")
    brain = Brain(os.path.join(ROOT, ".brain-fase0", "events"))
    store = FileStore(os.path.join(ROOT, ".brain-fase0", "store"))
    cp = MemorySaver()

    # --- turno: deploys Vercel -------------------------------------------------
    payload = coletar_projetos(token, team_id)
    spec_t, turno = _build_agent("turno", llm, brain, store, cp)
    out_t = _invoke(turno, {"projects": payload}, spec_t["ledger"])

    # --- ponte: canais de entrada ---------------------------------------------
    canais = probe_canais()
    spec_p, ponte = _build_agent("ponte", llm, brain, store, cp)
    out_p = _invoke(ponte, {"channels": canais}, spec_p["ledger"])

    # --- fila: inbound novo do site (formulários) -------------------------------
    inbound, total_inbound = coletar_inbound()
    out_f = None
    if total_inbound >= 0:
        spec_f, fila = _build_agent("fila", llm, brain, store, cp)
        out_f = _invoke(fila, {"inbound": inbound, "now": t0.isoformat()}, spec_f["ledger"])

    # --- relatório -------------------------------------------------------------
    print(
        f"Turno — rodada ao vivo | team '{TEAM_SLUG}' | {out_t.get('total_projects')} projetos\n"
    )
    print(
        f"  verdes: {out_t.get('green_count')}/{out_t.get('total_projects')} "
        f"({out_t.get('health_pct')}%)  | erros: {out_t.get('error_count')}  "
        f"| órfãos (sem Git): {out_t.get('orphan_count')}"
    )
    for a in out_t.get("recommended_actions", [])[:5]:
        print(f"  acao: {a}")
    if out_t.get("orphan_count"):
        print(
            f"  higiene: {out_t['orphan_count']} projeto(s) sem Git integrado no Vercel "
            "(deploy via CLI) — dívida, não urgência"
        )

    print(
        f"\nPonte — canais de entrada: {out_p.get('green_count')} verdes, "
        f"{out_p.get('degraded_count')} degradados, {out_p.get('down_count')} down"
    )
    raw_by_name = {c["name"]: c for c in canais}
    for c in out_p.get("channels", []):
        r = raw_by_name.get(c["name"], {})
        cold = " [frio -> quente]" if r.get("cold_start") else ""
        print(f"  {c['name']:<16} {c['status']:<9} {c['latency_ms']} ms{cold}")
    for a in out_p.get("recommended_actions", [])[:3]:
        print(f"  acao: {a}")

    if out_f is not None:
        base_note = (
            f" (baseline: {total_inbound} no histórico)"
            if not inbound and total_inbound > 0
            else ""
        )
        print(
            f"\nFila — inbound do site: {out_f.get('pending_count')} pendente(s), "
            f"{out_f.get('overdue_count')} com SLA estourado{base_note}"
        )
        for m in out_f.get("queue", [])[:3]:
            print(f"  {m.get('id')} | {m.get('channel')} | esperando {m.get('wait_min')} min")
        for a in out_f.get("recommended_actions", [])[:3]:
            print(f"  acao: {a}")

    # --- alerta compacto (copiar/colar ou Telegram) ----------------------------
    fire, debt = [], []
    for p in payload:
        if p["deploy_status"] == "ERROR":
            dias = p.get("age_days")
            tag = p["name"] + (f" há {int(dias)}d" if dias is not None else "")
            (fire if (dias is not None and dias <= 2) else debt).append(tag)

    # Anotação de cold start: canal degradado no output do agente + aquecido no
    # retry vira "(nome frio Xms -> quente Yms)"; canal ainda degradado é real.
    cold_notes, real_bad = [], []
    raw = {c["name"]: c for c in canais}
    for c in out_p["channels"]:
        if c["status"] == "green":
            if raw.get(c["name"], {}).get("cold_start"):
                cold_notes.append(
                    f"{c['name']} frio {raw[c['name']]['first_probe_ms']}ms -> "
                    f"quente {c['latency_ms']}ms"
                )
            continue
        r = raw.get(c["name"], {})
        cold_notes.append(
            f"{c['name']} {c['status'].upper()} "
            f"{r.get('first_probe_ms', c['latency_ms'])}ms -> {c['latency_ms']}ms"
        )
        real_bad.append(c)

    alert = (
        f"[FROTA {t0.strftime('%d/%m %H:%M')}] Novais | "
        + (f"INCÊNDIO: {', '.join(fire)} | " if fire else "")
        + (
            f"Vercel: {out_t['error_count']} em ERROR há tempo ({', '.join(debt[:3])})"
            if debt
            else "Vercel: deploys ok"
        )
        + f" | {out_t['orphan_count']} sem Git | "
        + f"Ponte: {out_p['green_count']}/{out_p['total']} canais verdes"
    )
    if cold_notes:
        alert += f" | {', '.join(cold_notes)}"
    if real_bad:
        alert += " | ATENÇÃO: canal não aqueceu no retry"
    if out_f is not None:
        if (out_f.get("pending_count") or 0) > 0:
            alert += (
                f" | FILA: {out_f['pending_count']} inbound novo(s) do site, "
                f"mais antigo há {out_f.get('oldest_wait_min', 0)} min"
            )
        elif out_f.get("overdue_count") == 0 and total_inbound == 0:
            alert += " | Fila: vazia (sem histórico)"
    print(f"\nALERTA:\n{alert}")

    if notify:
        if _notify_telegram(alert):
            print("(alerta enviado por Telegram)")
        else:
            print(
                "(--notify sem TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID no ambiente; "
                "alerta apenas impresso/salvo)"
            )

    # --- snapshot com fonte -----------------------------------------------------
    rel_dir = os.path.join(os.path.dirname(ROOT), "relatorios")
    os.makedirs(rel_dir, exist_ok=True)
    rel_path = os.path.join(rel_dir, f"rodada-turno-{t0.strftime('%Y-%m-%d')}.json")
    with open(rel_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "date": t0.isoformat(),
                "team": TEAM_SLUG,
                "sources": {
                    "deploys": "vercel api v9/projects (latestDeployments, read-only)",
                    "canais": "probes HTTP /health (nucleo.rodada_live.CHANNELS)",
                    "inbound": "GET /api/submissions do site (admin, receipts em fila-state.json)",
                },
                "turno": {k: out_t.get(k) for k in
                          ("total_projects", "green_count", "error_count",
                           "orphan_count", "health_pct")},
                "ponte": {k: out_p.get(k) for k in
                          ("total", "green_count", "degraded_count", "down_count")},
                "fila": (
                    {k: out_f.get(k) for k in
                     ("pending_count", "overdue_count", "oldest_wait_min")}
                    if out_f is not None else None
                ),
                "whatsapp_alert": alert,
                "projects": payload,
                "channels": canais,
            },
            f, ensure_ascii=False, indent=2,
        )
    print(f"\nSnapshot salvo em {rel_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
