"""Servidor da demo viva Novais Digital Multi-Agentes.

Serve o front estático e executa a frota real do NÚCLEO. No startup materializa
`build_company`; cada POST /api/intent roteia a intenção pelo CEO-OS real
(guilda -> worker -> gate C4 em SHADOW) e devolve um trace honesto.

Local:
    python demo/live/server.py
    abrir http://127.0.0.1:8765

Cloud Run / containers:
    PORT=8080 HOST=0.0.0.0 python demo/live/server.py

LLM real é opt-in via variáveis do NÚCLEO (`LLM_PROVIDER`, `GEMINI_API_KEY`,
`GOOGLE_*`, etc.). Sem provider real, roda offline com FakeLLMProvider.
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import BinaryIO
from urllib.parse import urlsplit

FRONT = Path(__file__).resolve().parent
REPO = FRONT.parents[1]
sys.path.insert(0, str(REPO))

from langgraph.checkpoint.memory import MemorySaver  # noqa: E402

from demo.live.http_contract import MAX_BODY_BYTES, validate_intent_request  # noqa: E402
from nucleo.kernel.brain import Brain, FileStore  # noqa: E402
from nucleo.kernel.providers.llm import get_llm  # noqa: E402
from nucleo.kernel.registry import build_company  # noqa: E402

GUILD_NAMES = {
    "G00": "Núcleo",
    "G01": "Estratégia",
    "G02": "Produto",
    "G03": "Engenharia",
    "G04": "Qualidade",
    "G05": "Segurança",
    "G06": "Dados",
    "G07": "Growth",
    "G08": "Vendas",
    "G09": "Customer Ops",
    "G10": "Finanças",
    "G11": "Pessoas",
    "G12": "Jurídico",
    "G13": "Governança",
    "G14": "Model & AI-Ops",
}


def _bootstrap_gcp_adc() -> None:
    """Railway/containers não têm ADC do gcloud. Se a service account vier como JSON
    inteiro em GOOGLE_CREDENTIALS_JSON, materializa em arquivo e aponta
    GOOGLE_APPLICATION_CREDENTIALS para ele — o google-genai (Vertex) usa daí."""
    raw = os.environ.get("GOOGLE_CREDENTIALS_JSON", "").strip()
    if raw and not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        path = Path(os.environ.get("TMPDIR", "/tmp")) / "gcp-sa.json"
        try:
            path.write_text(raw, encoding="utf-8")
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(path)
            print(f"ADC: credencial Vertex materializada de GOOGLE_CREDENTIALS_JSON -> {path}")
        except OSError as exc:
            print(f"ADC: falha ao materializar credencial ({exc}); seguindo sem ela")


_bootstrap_gcp_adc()

print(json.dumps({"event": "company_bootstrap"}))
BRAIN_DIR = FRONT / ".brain-web"
brain = Brain(str(BRAIN_DIR / "events"))
store = FileStore(str(BRAIN_DIR / "store"))
llm = get_llm("root")
ROOT_GRAPH, GUILD_SUPS, FLEET = build_company(
    str(REPO / "nucleo"), llm, brain, store, MemorySaver()
)
N_AGENTS = sum(len(ws) for ws in FLEET.values())
print(
    json.dumps(
        {"event": "company_ready", "agents": N_AGENTS, "guilds": len(FLEET), "llm": llm.name}
    )
)


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
    lead = {
        "id": "demo-" + uuid.uuid4().hex[:6],
        "company": company or "empresa do visitante",
        "revenue_brl_year": int(context.get("revenue_brl_year") or 0),
        "founder_led": bool(context.get("founder_led")),
        "sells_well": bool(context.get("sells_well")),
        "lacks_process": bool(context.get("lacks_process")),
        "firefighter": bool(context.get("firefighter")),
        "high_personnel_cost": bool(context.get("high_personnel_cost")),
        "large_team": bool(context.get("large_team")),
        "public_sector": bool(context.get("public_sector")),
    }
    payload["lead"] = lead
    if company:
        tid = "t-" + "".join(c for c in company.lower() if c.isalnum())[:18]
        store.put(
            ("tenant", tid),
            "profile",
            {
                "name": company,
                "segment": context.get("segment") or "—",
                "pain": context.get("pain") or "—",
            },
        )
        payload["tenant_id"] = tid

    out = ROOT_GRAPH.invoke(
        {"intent": intent, "payload": payload, "verbose": False},
        config={"configurable": {"thread_id": "web-" + uuid.uuid4().hex[:6]}},
    )
    res = out.get("result", {}) or {}
    gk = res.get("guild")
    workers = [
        {"id": wid, "output": _safe(o or {})} for wid, o in (res.get("results") or {}).items()
    ]
    return {
        "intent": intent,
        "guild": gk,
        "guild_name": GUILD_NAMES.get(gk, gk),
        "workers": workers,
        "llm": llm.name,
        "mode": "SHADOW",
        "tenant": payload.get("tenant_id"),
        "note": "modo sombra: proposta registrada no Brain — nada é entregue sem passar o gate C4",
    }


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(FRONT), **kw)

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

    def do_GET(self) -> None:
        if urlsplit(self.path).path in {"/api/health", "/health"}:
            return self._json(200, {"agents": N_AGENTS, "guilds": len(FLEET), "llm": llm.name})
        return super().do_GET()

    def send_head(self) -> BinaryIO | None:
        # Runtime events and source files share FRONT; only the page is public.
        if urlsplit(self.path).path not in {"/", "/index.html", "/styles.css", "/app.js"}:
            self.send_error(404, "Recurso indisponível")
            return None
        return super().send_head()

    def _read_intent(self) -> tuple[str, dict]:
        n = int(self.headers.get("Content-Length") or 0)
        if not 0 < n <= MAX_BODY_BYTES:
            raise OverflowError("Corpo deve conter de 1 a 16384 bytes.")
        return validate_intent_request(json.loads(self.rfile.read(n)))

    def do_POST(self) -> None:
        if urlsplit(self.path).path != "/api/intent":
            return self._json(404, {"error": "rota desconhecida"})
        try:
            if self.headers.get_content_type() != "application/json":
                return self._json(415, {"error": "Use Content-Type application/json."})
            intent, context = self._read_intent()
            return self._json(200, run_intent(intent, context))
        except OverflowError as exc:
            return self._json(413, {"error": str(exc)})
        except (ValueError, UnicodeDecodeError) as exc:
            return self._json(400, {"error": str(exc)[:200]})
        except Exception as exc:  # noqa: BLE001 — demo: erro vira JSON, não stacktrace na tela
            print(json.dumps({"event": "intent_failed", "exception": type(exc).__name__}))
            return self._json(
                500, {"error": "Não foi possível executar a intenção. Tente novamente."}
            )

    def log_request(self, code: int | str = "-", size: int | str = "-") -> None:
        # Do not log arbitrary URLs, query strings or user-supplied content.
        print(json.dumps({"event": "http_request", "method": self.command, "status": code}))

    def log_message(self, fmt: str, *args: object) -> None:
        # The stdlib error logger also passes integers; keep one structured event per request.
        return None


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8765"))
    host = os.environ.get("HOST", "127.0.0.1")
    print(f"demo viva em http://{host}:{port}  (Ctrl+C para parar)")
    ThreadingHTTPServer((host, port), Handler).serve_forever()
