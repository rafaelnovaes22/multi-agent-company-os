"""verify_code — oráculo OFFLINE de verificação de artefatos de código (épico VERIFY-IN-EVAL, F0).

Tese (North Star): `delivered` deve ser consequência de um ORÁCULO INDEPENDENTE do agente
avaliado, no caminho de eval — não declaração do agente nem carimbo de gate. O critério
(testes/contratos held-out) vem do EVAL-CASE, autorado por um humano; o agente nunca o vê.
O sinal é FUNÇÃO DO ARTEFATO (inspeção estática: ast/diff/sha contra o oráculo), NUNCA a
leitura de um booleano de sucesso que o próprio caso declara.

Distinção central (provada offline pelo protótipo c:/tmp/proto_verify_code.py):

  NECESSÁRIO (estático, offline, sempre computável, função do artefato):
    artifact_parseable   — o artefato tem o formato {files:{path:content}} (não prosa)
    touches_bug_file     — modificou o arquivo-alvo (bug em red→green; esqueleto em build)
    bug_addressed        — tratou os marcadores do alvo no bug_file (must_remove/must_contain)
    protected_unmodified — NÃO alterou arquivos protegidos (teste-alvo/contrato) — sha256
    heldout_untouched    — NÃO declarou nenhum path de teste held-out (não autora o critério)
    result_parses        — todo .py resultante é sintaticamente válido (ast, sem executar)
    no_test_gaming       — sem burla óbvia (sys.exit/skip/SkipTest)

  SUFICIENTE (executado, só F2 com runner Linux+Docker): tests_pass = post_exit == 0.

DUAS NATUREZAS do mesmo oráculo code-exec (F3 generaliza, sem bifurcação):
  red→green (fix)  — o teste-alvo JÁ está na semente, protegido por sha (protected_files).
  build (held-out) — os testes vêm do EVAL-CASE em `oracle.heldout_files` e NÃO existem na
                     semente: o agente nunca os vê. Na execução eles são INJETADOS por cima
                     do merge (semente+patch) — o critério roda sempre na versão do oráculo,
                     jamais na do artefato; declarar o path de um held-out é reprova estática.

  static_ok    = all(NECESSÁRIOS)                       — já reprova lixo/burla offline
  delivered_ok = static_ok AND tests_pass (executado)   — OFFLINE tests_pass=UNVERIFIED ⇒ False

LIMITE HONESTO: static_ok é NECESSÁRIO, não SUFICIENTE — um fix "plausível mas logicamente
errado" passa o estático e só cairia EXECUTANDO (F2). Por isso o eval reporta DOIS números:
static_pass_rate (F0 move, de 0) e delivered_rate (só F2 move). Zero subprocess; stdlib pura.
"""
from __future__ import annotations
import ast
import hashlib

NECESSARIOS = ["artifact_parseable", "touches_bug_file", "bug_addressed",
               "protected_unmodified", "heldout_untouched", "result_parses", "no_test_gaming"]

# Marcadores de burla de teste (anti-gaming) — escrita defensiva, não exaustiva.
_GAMING_TOKENS = ("sys.exit(0)", "pytest.skip", "raise SkipTest",
                  "@pytest.mark.skip", "@unittest.skip", "unittest.SkipTest")


def sha(s: str) -> str:
    """sha256 curto (12 hex) de uma string utf-8 — usado p/ travar arquivos protegidos."""
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()[:12]


def verify_code(artifact: dict, seed: dict, oracle: dict, executor=None) -> dict:
    """Verifica um artefato de código contra (semente, oráculo). Estático sempre; execução
    SÓ se houver um ExecutionProvider disponível (F2) — senão tests_pass=UNVERIFIED (F0/F1).

    artifact: {"files": {path: content}} produzido pelo agente (o patch).
    seed:     {path: content} repo-semente (build vermelho por construção).
    oracle:   {"bug_file", "protected_files": {path: sha}, "bug_markers": {must_remove, must_contain},
               "heldout_files"?: {path: content} testes held-out (natureza build — F3),
               "test_cmd"?: comando de teste (usado SÓ na execução real — F2)}.
    executor: ExecutionProvider | None. None ⇒ não executa (F1 inerte). A execução real só
              CONFIRMA um sinal já estaticamente válido; nunca lê um booleano do eval-case.

    Retorna: {signals, static_ok, first_fail, tests_pass, delivered_ok}.
    """
    sig: dict = {}
    seed = seed or {}
    oracle = oracle or {}

    # (0) artifact_parseable — formato {files:{path:str}}. Texto-livre (handler antigo) FALHA aqui.
    files = artifact.get("files") if isinstance(artifact, dict) else None
    sig["artifact_parseable"] = isinstance(files, dict) and bool(files) \
        and all(isinstance(k, str) and isinstance(v, str) for k, v in files.items())
    if not sig["artifact_parseable"]:
        return {"signals": sig, "static_ok": False, "first_fail": "artifact_parseable",
                "tests_pass": "UNVERIFIED", "delivered_ok": False}

    # repo DEPOIS do patch do agente
    merged = dict(seed)
    merged.update(files)

    bug_file = oracle.get("bug_file")
    # (1) touches_bug_file — modificou o arquivo do bug?  [função do artefato]
    sig["touches_bug_file"] = bool(bug_file) and bug_file in files \
        and files[bug_file] != seed.get(bug_file)

    # (1b) bug_addressed — marcadores do defeito tratados no bug_file?  [estático]
    markers = oracle.get("bug_markers", {}) or {}
    body = files.get(bug_file, seed.get(bug_file, "")) if bug_file else ""
    sig["bug_addressed"] = (
        all(tok not in body for tok in markers.get("must_remove", []))
        and all(tok in body for tok in markers.get("must_contain", []))
    )

    # (2) protected_unmodified — não alterou nenhum arquivo protegido (teste-alvo/contrato)?  [sha256]
    prot_ok = True
    for path, want_hash in (oracle.get("protected_files") or {}).items():
        if path in files and sha(files[path]) != want_hash:
            prot_ok = False   # tentou reescrever o próprio oráculo
    sig["protected_unmodified"] = prot_ok

    # (2b) heldout_untouched — não declarou nenhum path de teste held-out (natureza build)?
    # O held-out é o CRITÉRIO: o agente que o escreve está autorando a própria prova.
    heldout = oracle.get("heldout_files") or {}
    sig["heldout_untouched"] = not any(path in files for path in heldout)

    # (3) result_parses — todo .py resultante é sintaticamente válido?  [ast, sem executar]
    parses = True
    for path, content in merged.items():
        if path.endswith(".py"):
            try:
                ast.parse(content)
            except SyntaxError:
                parses = False
                break
    sig["result_parses"] = parses

    # (4) no_test_gaming — sem burla óbvia no(s) arquivo(s) que o agente escreveu  [texto]
    sig["no_test_gaming"] = not any(
        tok in content for content in files.values() for tok in _GAMING_TOKENS)

    static_ok = all(sig[k] for k in NECESSARIOS)
    first_fail = next((k for k in NECESSARIOS if not sig[k]), None)

    # SUFICIENTE: tests_pass só é bool vindo de EXECUÇÃO real (F2). Sem executor disponível
    # (F0/F1) ou se o artefato nem passou no estático, fica UNVERIFIED. delivered_ok exige
    # static_ok E tests_pass executado True — nunca verde-por-fixture, nunca verde-offline.
    tests_pass = "UNVERIFIED"
    if static_ok and executor is not None and getattr(executor, "available", False):
        test_cmd = (oracle.get("test_cmd") or "pytest -q")
        # held-out por ÚLTIMO: o critério executado é sempre a versão do oráculo, nunca a do
        # artefato (mesmo que algo escape do sinal estático, a injeção sobrescreve).
        exec_files = dict(merged)
        exec_files.update(heldout)
        try:
            res = executor.run_tests(exec_files, test_cmd=test_cmd)
        except Exception as exc:  # noqa: BLE001 — runner falho ⇒ UNVERIFIED, não crash
            import logging
            logging.getLogger(__name__).warning("executor %s falhou: %s",
                                                 getattr(executor, "name", "?"), exc)
            res = None
        if isinstance(res, bool):
            tests_pass = res
    delivered_ok = tests_pass is True

    return {"signals": sig, "static_ok": static_ok, "first_fail": first_fail,
            "tests_pass": tests_pass, "delivered_ok": delivered_ok}
