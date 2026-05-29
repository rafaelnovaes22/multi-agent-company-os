"""Company Brain (Sprint 0) — a empresa queryable (YC#3 / C6).

- `Brain`: event store append-only (JSONL). Toda ação de agente emite um evento aqui.
- `FileStore`: memória longa persistente (SOUL / MEMORY / snapshots), com a mesma
  API get/put/search do store do LangGraph — para trocar por PostgresStore depois (C7).

Em produção: Postgres + pgvector + grafo. Aqui: arquivos locais, para a demo rodar
sem infra. A fronteira (a interface) é a mesma.
"""
from __future__ import annotations
import datetime
import json
import os
import threading


def _now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def _safe(key: str) -> str:
    return "".join(c if (c.isalnum() or c in "-_.") else "_" for c in str(key))[:80]


class Brain:
    def __init__(self, root: str):
        self.root = root
        os.makedirs(root, exist_ok=True)
        self.events_path = os.path.join(root, "events.jsonl")
        self._lock = threading.Lock()

    def emit_event(self, event: dict) -> dict:
        event = {"ts": _now(), **event}
        with self._lock, open(self.events_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
        return event

    def events(self) -> list:
        if not os.path.exists(self.events_path):
            return []
        with open(self.events_path, encoding="utf-8") as f:
            return [json.loads(ln) for ln in f if ln.strip()]


class FileStore:
    """Espelha a API do store do LangGraph (namespaced get/put/search)."""

    def __init__(self, root: str):
        self.root = root
        os.makedirs(root, exist_ok=True)

    def _dir(self, namespace: tuple) -> str:
        d = os.path.join(self.root, *[_safe(n) for n in namespace])
        os.makedirs(d, exist_ok=True)
        return d

    def put(self, namespace: tuple, key: str, value) -> None:
        with open(os.path.join(self._dir(namespace), _safe(key) + ".json"), "w", encoding="utf-8") as f:
            json.dump({"key": key, "value": value}, f, ensure_ascii=False, indent=2)

    def get(self, namespace: tuple, key: str):
        p = os.path.join(self._dir(namespace), _safe(key) + ".json")
        if not os.path.exists(p):
            return None
        with open(p, encoding="utf-8") as f:
            return json.load(f)["value"]

    def search(self, namespace: tuple, query: str = "", limit: int = 20) -> list:
        d = self._dir(namespace)
        out = []
        for fn in sorted(os.listdir(d)):
            if fn.endswith(".json"):
                with open(os.path.join(d, fn), encoding="utf-8") as f:
                    out.append(json.load(f)["value"])
        return out[:limit]

    def items(self, namespace: tuple):
        """Itera (key, value) — necessário p/ o Hermes marcar snapshots como processados."""
        d = self._dir(namespace)
        for fn in sorted(os.listdir(d)):
            if fn.endswith(".json"):
                with open(os.path.join(d, fn), encoding="utf-8") as f:
                    rec = json.load(f)
                yield rec["key"], rec["value"]

    def subdirs(self, namespace: tuple) -> list:
        """Lista subdiretórios (ex.: agentes sob ('snapshots',))."""
        d = self._dir(namespace)
        return sorted(n for n in os.listdir(d) if os.path.isdir(os.path.join(d, n)))
