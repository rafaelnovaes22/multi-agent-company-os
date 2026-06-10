"""Servidor da demo viva Acme Multi-Agentes — serve o front e executa a FROTA REAL.

Zero dependências além do próprio NÚCLEO (stdlib http.server). No startup materializa a
empresa inteira (build_company, 164 agentes); cada POST /api/intent roteia a intenção pelo
CEO-OS real (guilda -> worker -> gate C4 em SHADOW) e devolve o trace honesto.

Rodar:   python front/server.py
Gemini:  set LLM_PROVIDER=vertex (+ vars GOOGLE_*) antes — a frota responde com Gemini real.
Abrir:   http://127.0.0.1:8765
"""
from __future__ import annotations
import json
import os
import sys
import uuid
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from http.cookies import SimpleCookie

FRONT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(FRONT)  # parent directory containing nucleo/
sys.path.insert(0, REPO)

from langgraph.checkpoint.memory import MemorySaver  # noqa: E402
from nucleo.kernel.brain import Brain, FileStore  # noqa: E402
from nucleo.kernel.providers.llm import get_llm  # noqa: E402
from nucleo.kernel.registry import build_company  # noqa: E402

GUILD_NAMES = {
    "G00": "Núcleo", "G01": "Estratégia", "G02": "Produto", "G03": "Engenharia",
    "G04": "Qualidade", "G05": "Segurança", "G06": "Dados", "G07": "Growth",
    "G08": "Vendas", "G09": "Customer Ops", "G10": "Finanças", "G11": "Pessoas",
    "G12": "Jurídico", "G13": "Governança", "G14": "Model & AI-Ops",
}

print("Materializando a empresa-OS (164 agentes)...")
BRAIN_DIR = os.path.join(FRONT, ".brain-web")
brain = Brain(os.path.join(BRAIN_DIR, "events"))
store = FileStore(os.path.join(BRAIN_DIR, "store"))
llm = get_llm("root")
ROOT_GRAPH, GUILD_SUPS, FLEET = build_company(os.path.join(REPO, "nucleo"), llm, brain, store, MemorySaver())
N_AGENTS = sum(len(ws) for ws in FLEET.values())
print(f"pronto: {N_AGENTS} agentes | {len(FLEET)} guildas | LLM={llm.name}")

AGENT_DESCRIPTIONS = {}
for guild_key, workers in FLEET.items():
    for spec, agent in workers:
        aid = spec.get("id")
        desc = spec.get("outcome_clause", {}).get("statement", "")
        if desc:
            desc = " ".join(desc.split())
        AGENT_DESCRIPTIONS[aid] = desc or ""

API_KEY = os.environ.get("API_KEY")
RATE_LIMIT = 10  # reqs/minute
rate_limit_store = {}


def check_rate_limit(ip: str) -> bool:
    now = time.time()
    if ip not in rate_limit_store:
        rate_limit_store[ip] = []
    # Filter out requests older than 60s
    rate_limit_store[ip] = [t for t in rate_limit_store[ip] if now - t < 60]
    if len(rate_limit_store[ip]) >= RATE_LIMIT:
        return False
    rate_limit_store[ip].append(now)
    return True


def _safe(v, depth=0):
    """Output do agente -> JSON enxuto p/ o front (trunca prosa, limita profundidade)."""
    if isinstance(v, str):
        return v if len(v) <= 420 else v[:420] + "…"
    if isinstance(v, (int, float, bool)) or v is None:
        return v
    if depth >= 3:
        return str(v)[:120]
    if isinstance(v, dict):
        return {k: _safe(x, depth + 1) for k, x in list(v.items())[:14]}
    if isinstance(v, (list, tuple)):
        return [_safe(x, depth + 1) for x in list(v)[:8]]
    return str(v)[:120]


def run_intent(intent: str, context: dict) -> dict:
    context = context or {}
    payload: dict = {}

    # contexto do cliente -> lead (formato do ICP real) + perfil multi-tenant no store (C5)
    company = (context.get("company") or "").strip()
    lead = {"id": "demo-" + uuid.uuid4().hex[:6], "company": company or "empresa do visitante",
            "revenue_brl_year": int(context.get("revenue_brl_year") or 0),
            "founder_led": bool(context.get("founder_led")),
            "sells_well": bool(context.get("sells_well")),
            "lacks_process": bool(context.get("lacks_process")),
            "firefighter": bool(context.get("firefighter")),
            "high_personnel_cost": bool(context.get("high_personnel_cost")),
            "large_team": bool(context.get("large_team")),
            "public_sector": bool(context.get("public_sector"))}
    payload["lead"] = lead
    if company:
        tid = "t-" + "".join(c for c in company.lower() if c.isalnum())[:18]
        store.put(("tenant", tid), "profile",
                  {"name": company, "segment": context.get("segment") or "—",
                   "pain": context.get("pain") or "—"})
        payload["tenant_id"] = tid

    out = ROOT_GRAPH.invoke(
        {"intent": intent, "payload": payload, "verbose": False},
        config={"configurable": {"thread_id": "web-" + uuid.uuid4().hex[:6]}})
    res = out.get("result", {}) or {}
    gk = res.get("guild")
    workers = [{"id": wid, "output": _safe(o or {})}
               for wid, o in (res.get("results") or {}).items()]
    return {"intent": intent, "guild": gk, "guild_name": GUILD_NAMES.get(gk, gk),
            "workers": workers, "llm": llm.name, "mode": "SHADOW",
            "tenant": payload.get("tenant_id"),
            "note": "modo sombra: proposta registrada no Brain — nada é entregue sem passar o gate C4"}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=FRONT, **kw)

    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if API_KEY:
            parsed_path = urlparse(self.path)
            query_params = parse_qs(parsed_path.query)
            key_param = query_params.get("key", [None])[0]

            cookie_header = self.headers.get("Cookie", "")
            cookie = SimpleCookie(cookie_header)
            session_key = cookie.get("session_key")

            authorized = False
            set_cookie_needed = False

            if key_param == API_KEY:
                authorized = True
                set_cookie_needed = True
            elif session_key and session_key.value == API_KEY:
                authorized = True

            if not authorized:
                body = b"Acesso nao autorizado. Chave invalida ou ausente."
                self.send_response(401)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            if set_cookie_needed:
                # Redirect to clean the URL query parameter and set HttpOnly Cookie
                self.send_response(302)
                self.send_header("Location", parsed_path.path)
                self.send_header("Set-Cookie", f"session_key={API_KEY}; Path=/; HttpOnly; SameSite=Lax; Max-Age=86400")
                self.end_headers()
                return

        if self.path.startswith("/api/health"):
            return self._json(200, {
                "agents": N_AGENTS,
                "guilds": len(FLEET),
                "llm": llm.name,
                "descriptions": AGENT_DESCRIPTIONS
            })
        if self.path.startswith("/api/brain"):
            parsed_path = urlparse(self.path)
            query_params = parse_qs(parsed_path.query)
            tenant_filter = query_params.get("tenant", [None])[0]
            try:
                evs = brain.events()
                if tenant_filter:
                    evs = [e for e in evs if e.get("tenant_id") == tenant_filter]
                return self._json(200, {"events": evs})
            except Exception as exc:  # noqa: BLE001
                return self._json(500, {"error": str(exc)[:300]})
        return super().do_GET()

    def do_POST(self):
        if API_KEY:
            cookie_header = self.headers.get("Cookie", "")
            cookie = SimpleCookie(cookie_header)
            session_key = cookie.get("session_key")

            parsed_path = urlparse(self.path)
            query_params = parse_qs(parsed_path.query)
            key_param = query_params.get("key", [None])[0]

            if not (key_param == API_KEY or (session_key and session_key.value == API_KEY)):
                return self._json(401, {"error": "chave de acesso invalida ou expirada"})

        if not self.path.startswith("/api/intent"):
            return self._json(404, {"error": "rota desconhecida"})

        # Rate Limit Check
        client_ip = self.headers.get("X-Forwarded-For", self.client_address[0]).split(",")[0].strip()
        if not check_rate_limit(client_ip):
            return self._json(429, {"error": "Limite de requisicoes excedido (max 10 por minuto)"})

        try:
            n = int(self.headers.get("Content-Length") or 0)
            req = json.loads(self.rfile.read(n) or b"{}")
            intent = (req.get("intent") or "").strip()
            if not intent:
                return self._json(400, {"error": "intent vazia"})
            return self._json(200, run_intent(intent, req.get("context") or {}))
        except Exception as exc:  # noqa: BLE001
            return self._json(500, {"error": str(exc)[:300]})

    def log_message(self, fmt, *args):  # silencia o ruído por request
        try:
            path = getattr(self, "path", "")
            if "/api/" in path:
                return
            super().log_message(fmt, *args)
        except Exception:  # noqa: BLE001
            pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8765"))
    print(f"demo viva em http://0.0.0.0:{port}  (Ctrl+C para parar)")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()

