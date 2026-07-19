"""ToolBox — least-privilege das capacidades injetadas no handler (NIST PR2).

O `tools:` da spec deixa de ser documentação e vira PERMISSÃO: o nó `act` recebe
`llm`/`store` embrulhados em proxies que validam cada acesso contra a spec antes
de delegar. O teorema do checker (NIST) diz que detecção de intenção sempre tem
bypass; este módulo é o controle ESTRUTURAL — quando um injection passar, o que
ele alcança fica limitado ao que a spec declarou.

Capacidades governadas (as únicas injetadas no handler hoje):
  llm.complete -> exige LLMProvider | llm | llm.complete
  store leitura (get/search/items/subdirs) -> exige brain.query | brain.read | store.read
  store escrita (put) -> exige brain.write | store.write | brain.emit

Rollout em 2 fases (mesmo padrão ratchet do foundry_check):
  - observe (default): violação é AUDITADA no Brain (action=tool_denied,
    enforced=false) mas a chamada prossegue — popula telemetria sem quebrar a frota.
  - enforce (spec `tools_enforce: true`): violação levanta ToolDenied — agentes
    novos nascem assim (catraca `tools_nao_enforcadas` no foundry_check).

Fora do escopo (deliberado): leituras L0 via funções de módulo (load_icp etc.)
são código versionado, não capacidade injetada — entram quando virarem provider.
O kernel (load_context/gate/emit_artifact/snapshot) usa brain/store CRUS: a
permissão governa o handler, não a operação do template.
"""
from __future__ import annotations

import re

ALIASES = {
    "llm.complete": {"llmprovider", "llm", "llm.complete"},
    "brain.query": {"brain.query", "brain.read", "store.read"},
    "brain.write": {"brain.write", "store.write", "brain.emit"},
}


class ToolDenied(PermissionError):
    def __init__(self, agent: str, capability: str):
        self.agent, self.capability = agent, capability
        super().__init__(
            f"{agent}: capacidade '{capability}' negada — não declarada em spec.tools "
            f"(least-privilege; declare a tool ou remova o uso)")


def grants_from_spec(spec: dict) -> set:
    """Normaliza spec['tools'] num conjunto de grants comparável.

    Tolera o vocabulário histórico da frota: anotações entre parênteses
    ("brain.write (audit-log)"), compostos ("brain.query/write",
    "brain.query/brain.write") e caixa ("LLMProvider")."""
    grants = set()
    for raw in spec.get("tools") or []:
        t = re.sub(r"\(.*?\)", "", str(raw)).strip().lower()
        prefix = None
        for part in (p.strip() for p in t.split("/")):
            if not part:
                continue
            if "." in part:
                prefix = part.rsplit(".", 1)[0]
            elif prefix:
                part = f"{prefix}.{part}"
            grants.add(part)
    return grants


class _Guard:
    def __init__(self, spec: dict, brain, run_id):
        self.aid = spec.get("id", "?")
        self.grants = grants_from_spec(spec)
        self.enforce = bool(spec.get("tools_enforce"))
        self.brain = brain
        self.run_id = run_id

    def check(self, capability: str) -> None:
        if self.grants & ALIASES[capability]:
            return
        if self.brain is not None:
            self.brain.emit_event({
                "actor": self.aid, "action": "tool_denied", "capability": capability,
                "enforced": self.enforce, "run_id": self.run_id,
            })
        if self.enforce:
            raise ToolDenied(self.aid, capability)


class GuardedLLM:
    """Proxy de LLMProvider: complete() passa pelo guard; o resto delega."""

    def __init__(self, llm, guard: _Guard):
        self._llm, self._guard = llm, guard

    @property
    def name(self) -> str:
        return self._llm.name

    def complete(self, prompt: str, **kwargs) -> str:
        self._guard.check("llm.complete")
        return self._llm.complete(prompt, **kwargs)

    def __getattr__(self, attr):
        return getattr(self._llm, attr)


class GuardedStore:
    """Proxy de FileStore/LangGraph store: leitura exige brain.query, escrita brain.write."""

    def __init__(self, store, guard: _Guard):
        self._store, self._guard = store, guard

    def get(self, namespace: tuple, key: str):
        self._guard.check("brain.query")
        return self._store.get(namespace, key)

    def search(self, namespace: tuple, query: str = "", limit: int = 20) -> list:
        self._guard.check("brain.query")
        return self._store.search(namespace, query, limit)

    def items(self, namespace: tuple):
        self._guard.check("brain.query")
        return self._store.items(namespace)

    def subdirs(self, namespace: tuple) -> list:
        self._guard.check("brain.query")
        return self._store.subdirs(namespace)

    def put(self, namespace: tuple, key: str, value) -> None:
        self._guard.check("brain.write")
        return self._store.put(namespace, key, value)


def guarded(llm, store, *, spec: dict, brain, run_id=None):
    """Embrulha (llm, store) nos proxies de least-privilege de uma spec/run."""
    guard = _Guard(spec, brain, run_id)
    return GuardedLLM(llm, guard), GuardedStore(store, guard)
