"""Rodada AO VIVO do turno — saúde real dos projetos Vercel da Novais Digital.

Roda:  python -m nucleo.rodada_live

Substitui o payload de exemplo do demo_fase0 pela fonte viva: lista os projetos
do team novaisdigital na API da Vercel, verifica o último deploy de produção de
cada um e o link de Git, e alimenta o agente `turno` (SHADOW) que produz o
relatório da rodada com as ações do dia. Read-only: só requests GET.

Token resolvido em ordem: env VERCEL_TOKEN -> auth.json do CLI Vercel.
Salva o snapshot em relatorios/rodada-turno-YYYY-MM-DD.json.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langgraph.checkpoint.memory import MemorySaver  # noqa: E402

from nucleo.factory.factory import build_from_spec  # noqa: E402
from nucleo.kernel.brain import Brain, FileStore  # noqa: E402
from nucleo.kernel.providers.llm import get_llm  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
TEAM_SLUG = os.environ.get("VERCEL_TEAM_SLUG", "novaisdigital")
AUTH_CANDIDATES = [
    os.path.expandvars(r"%APPDATA%\com.vercel.cli\Data\auth.json"),
    os.path.expanduser("~/.vercel/auth.json"),
    os.path.expanduser("~/.local/share/com.vercel.cli/auth.json"),
]
API = "https://api.vercel.com"
_TEAM = [None]  # teamId corrente (usado pelo fallback do deploy_state)


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


def _get(path: str, token: str, **params) -> dict:
    qs = "&".join(f"{k}={v}" for k, v in params.items() if v is not None)
    url = f"{API}{path}" + (f"?{qs}" if qs else "")
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def resolve_team(token: str) -> str | None:
    """Devolve o teamId do team-alvo, ou None para o escopo pessoal."""
    data = _get("/v2/teams", token, limit=100)
    for t in data.get("teams", []):
        if t.get("slug") == TEAM_SLUG:
            return t.get("id")
    print(f"team '{TEAM_SLUG}' não encontrado; usando escopo pessoal.")
    return None


def list_projects(token: str, team_id: str | None) -> list[dict]:
    projects, until = [], None
    while True:
        data = _get(
            "/v9/projects", token, teamId=team_id, limit=100, until=until
        )
        projects += data.get("projects", [])
        until = data.get("pagination", {}).get("next")
        if not until:
            return projects


def deploy_state(p: dict) -> str:
    """Estado do último deploy de produção, direto do list (v9 projects já
    embute latestDeployments — 1 request total). Fallback: v6/deployments."""
    deps = p.get("latestDeployments") or []
    if not deps:
        try:
            deps = _get(
                "/v6/deployments", _token(), teamId=_TEAM[0],
                project=p.get("name"), limit=5,
            ).get("deployments", [])
        except Exception:
            deps = []
    prod = [d for d in deps if d.get("target") == "production"] or deps
    if not prod:
        return "NEVER_DEPLOYED"
    latest = max(prod, key=lambda d: d.get("createdAt") or 0)
    state = latest.get("readyState") or latest.get("state") or "UNKNOWN"
    if state in ("BUILDING", "QUEUED", "INITIALIZING"):
        return "BUILDING"
    return state


def main() -> int:
    token = _token()
    team_id = resolve_team(token)
    _TEAM[0] = team_id
    t0 = datetime.now(timezone.utc)

    projects = list_projects(token, team_id)
    print(f"Turno — rodada ao vivo | team '{TEAM_SLUG}' | {len(projects)} projetos Vercel\n")

    payload = []
    for p in projects:
        payload.append(
            {
                "name": p["name"],
                "deploy_status": deploy_state(p),
                "repo_ok": p.get("link") is not None,
            }
        )

    llm = get_llm("worker")
    brain = Brain(os.path.join(ROOT, ".brain-fase0", "events"))
    store = FileStore(os.path.join(ROOT, ".brain-fase0", "store"))
    spec, agent, gate = build_from_spec(
        os.path.join(ROOT, "company", "fleet", "turno"), llm, brain, store, MemorySaver()
    )
    if not gate["ok"]:
        print(f"FAIL gate da fábrica: {gate['problems']}")
        return 1

    out = agent.invoke(
        {"task": {"projects": payload}, "mode": "SHADOW", "ledger": spec["ledger"],
         "run_id": "live-" + t0.strftime("%Y%m%d%H%M%S"), "verbose": False},
        config={"configurable": {"thread_id": "rodada-live"}},
    ).get("output") or {}

    print(f"  verdes: {out.get('green_count')}/{out.get('total_projects')} "
          f"({out.get('health_pct')}%)  | erros: {out.get('error_count')}  "
          f"| em build: {out.get('building_count')}  | órfãos (sem Git): {out.get('orphan_count')}\n")
    errors = [e for e in out.get("recommended_actions", []) if "ERROR" in e]
    for a in errors[:5]:
        print(f"  acao: {a}")
    if out.get("orphan_count"):
        print(f"  higiene: {out['orphan_count']} projeto(s) sem Git integrado no Vercel "
              "(deploy via CLI) — adotar repo em lote, não é urgência")

    # Alerta compacto (formato WhatsApp — o "passo 2" do plano, versão copiar/colar)
    err_names = [p["name"] for p in payload if p["deploy_status"] == "ERROR"]
    alert = (
        f"[TURNO {t0.strftime('%d/%m %H:%M')}] Vercel '{TEAM_SLUG}': "
        f"{out.get('total_projects')} projetos | "
        f"{out.get('error_count')} deploy(s) em ERROR"
        + (f" ({', '.join(err_names[:3])})" if err_names else "")
        + f" | {out.get('orphan_count')} sem Git integrado | "
        f"saudável pelo critério READY+Git: {out.get('health_pct')}%"
    )
    print(f"\nALERTA (copiar/colar):\n{alert}")

    # Snapshot com fonte (prova do painel) — tudo que o Prefeito precisa citar
    stamp = t0.strftime("%Y-%m-%d")
    rel_dir = os.path.join(os.path.dirname(ROOT), "relatorios")
    os.makedirs(rel_dir, exist_ok=True)
    rel_path = os.path.join(rel_dir, f"rodada-turno-{stamp}.json")
    with open(rel_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "date": t0.isoformat(),
                "team": TEAM_SLUG,
                "source": "vercel api v9/v9 (read-only)",
                "summary": {k: out.get(k) for k in
                            ("total_projects", "green_count", "error_count",
                             "building_count", "orphan_count", "health_pct")},
                "whatsapp_alert": alert,
                "projects": payload,
            },
            f, ensure_ascii=False, indent=2,
        )
    print(f"\nSnapshot salvo em {rel_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
