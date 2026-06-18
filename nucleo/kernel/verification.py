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
import json

NECESSARIOS = ["artifact_parseable", "touches_bug_file", "bug_addressed",
               "protected_unmodified", "heldout_untouched", "result_parses", "no_test_gaming"]

# Natureza ESTRUTURAL/dry-run (F4b — incident-responder): o artefato é um documento (postmortem
# JSON), não código executável. O oráculo é a COMPLETUDE/CONSISTÊNCIA estrutural — função do
# artefato, autorada no eval-case (oracle.structure), nunca auto-declarada. NÃO há execução:
# delivered_ok é SEMPRE False (ASSISTED, garantia PARCIAL) — estrutura é NECESSÁRIA-não-suficiente
# (um postmortem bem-formado pode ter conteúdo logicamente errado; "mitigated" é estado do mundo,
# não do artefato, e por isso fica FORA do predicado).
STRUCT_NECESSARIOS = ["artifact_parseable", "target_present", "doc_parses", "fields_complete",
                      "timeline_ordered", "durations_valid", "rollback_documented",
                      "followups_actionable", "no_placeholder_gaming"]

# Natureza BROWSER/E2E (F4c — g4-e2e-playwright): o artefato é uma suíte Playwright. Neste
# slice o oráculo checa apenas os necessários estáticos que tornam a suíte auditável: teste alvo,
# uso explícito de Playwright, cobertura de rotas/assertions held-out e evidência configurada
# (trace/screenshot/video). SEM browser real no gate offline: delivered_ok sempre False.
BROWSER_NECESSARIOS = ["artifact_parseable", "target_present", "uses_playwright",
                       "routes_covered", "assertions_present", "evidence_configured",
                       "no_browser_gaming"]

# Placeholders que delatam preenchimento formal vazio (anti-gaming estrutural).
_PLACEHOLDER_TOKENS = ("TODO", "TBD", "FIXME", "XXX", "PLACEHOLDER", "PREENCHER", "LOREM", "<INSIRA")

_BROWSER_GAMING_TOKENS = ("test.skip(", "test.only(", "describe.skip(", "describe.only(",
                          "page.route(", "browser.route(", "route.fulfill(")

# Marcadores de burla de teste (anti-gaming) — escrita defensiva, não exaustiva.
# Python (pytest/unittest) + JS/TS (vitest/jest): a natureza build do frontend (F3) executa
# vitest, então as burlas análogas (skip de suíte / matar o runner verde) também são vetadas.
_GAMING_TOKENS = ("sys.exit(0)", "pytest.skip", "raise SkipTest",
                  "@pytest.mark.skip", "@unittest.skip", "unittest.SkipTest",
                  "process.exit(0)", "it.skip(", "test.skip(", "describe.skip(",
                  # terraform test (F4a): falsear o veredito via mock/override do held-out.
                  "mock_provider", "override_resource", "override_data", "override_module")

# Extensões cujo conteúdo é checado estruturalmente (JS/TS) — não há AST de TS em Python stdlib.
_JS_EXTS = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")

# Extensões HCL (terraform, natureza ops/dry-run F4a) — idem: sem parser de HCL no stdlib,
# checagem estrutural necessário-não-suficiente; a sintaxe/semântica real cai no `terraform
# validate`/`test` (F2). Inclui .tftest.hcl (held-out, só presente na execução).
_TF_EXTS = (".tf", ".tfvars", ".hcl")


def sha(s: str) -> str:
    """sha256 curto (12 hex) de uma string utf-8 — usado p/ travar arquivos protegidos."""
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()[:12]


def _js_structurally_valid(src: str) -> bool:
    """Sanidade estrutural OFFLINE de JS/TS (stdlib pura — Python não tem AST de TypeScript).

    NÃO é um parser de verdade: remove comentários (// e /* */) e literais de string/template
    (', ", `) e exige delimitadores balanceados (){}[]. É NECESSÁRIO-não-suficiente, igual ao
    ast.parse do lado Python — rejeita truncamento/lixo óbvio (chave/parêntese não fechado,
    artefato vazio), mas a validação REAL de sintaxe/semântica é a EXECUÇÃO (vitest, F2).
    """
    if not src or not src.strip():
        return False
    pairs = {")": "(", "]": "[", "}": "{"}
    opens = set(pairs.values())
    stack = []
    quote = None  # ' " ` — dentro de literal, ignora delimitadores
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        if quote is not None:
            if c == "\\":          # escape — pula o próximo char
                i += 2
                continue
            if c == quote:
                quote = None
            i += 1
            continue
        if c == "/" and i + 1 < n and src[i + 1] == "/":   # comentário de linha
            nl = src.find("\n", i)
            i = n if nl == -1 else nl
            continue
        if c == "/" and i + 1 < n and src[i + 1] == "*":   # comentário de bloco
            end = src.find("*/", i + 2)
            if end == -1:
                return False        # bloco não fechado
            i = end + 2
            continue
        if c in ("'", '"', "`"):
            quote = c
        elif c in opens:
            stack.append(c)
        elif c in pairs:
            if not stack or stack.pop() != pairs[c]:
                return False
        i += 1
    return quote is None and not stack


def _hcl_structurally_valid(src: str) -> bool:
    """Sanidade estrutural OFFLINE de HCL/terraform (stdlib pura — sem parser de HCL).

    Espelha _js_structurally_valid: ignora comentários (#, //, /* */), literais "..." (com
    escape) e blocos heredoc (<<TAG / <<-TAG … TAG) e exige delimitadores (){}[] balanceados.
    NECESSÁRIO-não-suficiente: rejeita truncamento/lixo óbvio (bloco não fechado, vazio); a
    validação real de sintaxe/semântica é a EXECUÇÃO (`terraform validate`/`test`, F2).
    """
    if not src or not src.strip():
        return False
    pairs = {")": "(", "]": "[", "}": "{"}
    opens = set(pairs.values())
    stack = []
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        # heredoc: <<TAG ou <<-TAG → pula até a linha que contém só TAG (delimitadores internos
        # do corpo não contam, igual a um literal de string multilinha).
        if c == "<" and i + 1 < n and src[i + 1] == "<":
            j = i + 2
            if j < n and src[j] == "-":
                j += 1
            start = j
            while j < n and (src[j].isalnum() or src[j] == "_"):
                j += 1
            tag = src[start:j]
            if tag:
                end = src.find(tag, j)
                while end != -1:
                    ls = src.rfind("\n", 0, end) + 1
                    if src[ls:end].strip() == "":     # TAG sozinha na linha = fecha o heredoc
                        break
                    end = src.find(tag, end + len(tag))
                if end == -1:
                    return False                       # heredoc não fechado
                i = end + len(tag)
                continue
        if c == '"':                                   # literal de string (com escape \")
            i += 1
            while i < n and src[i] != '"':
                i += 2 if src[i] == "\\" else 1
            if i >= n:
                return False                           # string não fechada
            i += 1
            continue
        if c == "#" or (c == "/" and i + 1 < n and src[i + 1] == "/"):   # comentário de linha
            nl = src.find("\n", i)
            i = n if nl == -1 else nl
            continue
        if c == "/" and i + 1 < n and src[i + 1] == "*":                 # comentário de bloco
            end = src.find("*/", i + 2)
            if end == -1:
                return False
            i = end + 2
            continue
        if c in opens:
            stack.append(c)
        elif c in pairs:
            if not stack or stack.pop() != pairs[c]:
                return False
        i += 1
    return not stack


def verify_code(artifact: dict, seed: dict, oracle: dict, executor=None) -> dict:
    """Verifica um artefato de código contra (semente, oráculo). Estático sempre; execução
    SÓ se houver um ExecutionProvider disponível (F2) — senão tests_pass=UNVERIFIED (F0/F1).

    artifact: {"files": {path: content}} produzido pelo agente (o patch).
    seed:     {path: content} repo-semente (build vermelho por construção).
    oracle:   {"bug_file", "protected_files": {path: sha}, "bug_markers": {must_remove, must_contain},
               "heldout_files"?: {path: content} testes held-out (natureza build — F3),
               "runtime"?: "python"|"node"|"terraform" (default python; node=vitest do frontend; terraform=terraform test),
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

    # (3) result_parses — todo arquivo de código resultante é sintaticamente válido?
    # .py: ast.parse (sem executar). .ts/.tsx/.js/...: checagem estrutural (sem AST de TS no
    # stdlib). Ambos NECESSÁRIOS-não-suficientes; a sintaxe real do JS só cai EXECUTANDO (F2).
    parses = True
    for path, content in merged.items():
        if path.endswith(".py"):
            try:
                ast.parse(content)
            except SyntaxError:
                parses = False
                break
        elif path.endswith(_JS_EXTS):
            if not _js_structurally_valid(content):
                parses = False
                break
        elif path.endswith(_TF_EXTS):
            if not _hcl_structurally_valid(content):
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
        runtime = oracle.get("runtime") or "python"
        try:
            res = executor.run_tests(exec_files, test_cmd=test_cmd, runtime=runtime)
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


def _walk_strings(obj):
    """Itera recursivamente todas as strings de um objeto JSON (valores e chaves)."""
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _walk_strings(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _walk_strings(v)


def _nonempty(v) -> bool:
    """Campo 'preenchido': string não-vazia, número, bool, ou coleção não-vazia."""
    if isinstance(v, str):
        return bool(v.strip())
    if isinstance(v, (list, dict)):
        return bool(v)
    return v is not None


def verify_browser(artifact: dict, oracle: dict) -> dict:
    """Oráculo OFFLINE de suíte BROWSER/E2E (F4c — g4-e2e-playwright).

    O critério fica em `oracle["browser"]` e é held-out ao agente:
      target              — arquivo de teste Playwright esperado (ex.: tests/onboarding.spec.ts)
      required_routes     — rotas/URLs que precisam aparecer em `page.goto(...)`
      required_assertions — textos ou seletores que precisam ser assertados com `expect(...)`
      evidence            — evidências exigidas: trace/screenshot/video

    Este é um predicado NECESSÁRIO-não-suficiente: uma suíte bem formada ainda precisa rodar em
    browser real para provar produto funcionando. Por isso `tests_pass="N/A"` e
    `delivered_ok=False` neste slice offline.
    """
    br = (oracle or {}).get("browser") or {}
    sig = {k: False for k in BROWSER_NECESSARIOS}

    files = artifact.get("files") if isinstance(artifact, dict) else None
    sig["artifact_parseable"] = isinstance(files, dict) and bool(files) \
        and all(isinstance(k, str) and isinstance(v, str) for k, v in files.items())

    target = br.get("target")
    body = ""
    if sig["artifact_parseable"]:
        sig["target_present"] = bool(target) and target in files
        if sig["target_present"]:
            body = files[target]

    if body:
        sig["uses_playwright"] = "@playwright/test" in body and "test(" in body and "expect(" in body
        sig["routes_covered"] = all(str(route) in body for route in (br.get("required_routes") or []))
        sig["assertions_present"] = all(str(assertion) in body for assertion in (br.get("required_assertions") or []))

        all_text = "\n".join(files.values())
        evidence = br.get("evidence") or []
        ev_ok = True
        for ev in evidence:
            ev = str(ev).lower()
            lower = all_text.lower()
            if ev == "trace":
                ev_ok = ev_ok and ("trace:" in lower and "trace: 'off'" not in lower
                                   and 'trace: "off"' not in lower)
            elif ev == "screenshot":
                ev_ok = ev_ok and ("page.screenshot" in all_text or
                                   (("screenshot:" in lower) and "screenshot: 'off'" not in lower
                                    and 'screenshot: "off"' not in lower))
            elif ev == "video":
                ev_ok = ev_ok and ("video:" in lower and "video: 'off'" not in lower
                                   and 'video: "off"' not in lower)
            else:
                ev_ok = False
        sig["evidence_configured"] = bool(evidence) and ev_ok

        upper = [s.upper() for s in _walk_strings(files)]
        sig["no_browser_gaming"] = not any(tok in body for tok in _BROWSER_GAMING_TOKENS) \
            and not any(tok in s for s in upper for tok in _PLACEHOLDER_TOKENS)

    static_ok = all(sig[k] for k in BROWSER_NECESSARIOS)
    first_fail = next((k for k in BROWSER_NECESSARIOS if not sig[k]), None)
    return {"signals": sig, "static_ok": static_ok, "first_fail": first_fail,
            "tests_pass": "N/A", "delivered_ok": False}


def verify_structure(artifact: dict, oracle: dict) -> dict:
    """Oráculo OFFLINE de COMPLETUDE/CONSISTÊNCIA estrutural (F4b — natureza ops/dry-run).

    Para artefatos que são DOCUMENTOS (postmortem/runbook), não código executável. O critério é
    o schema autorado em `oracle["structure"]` (held-out: o agente nunca o vê):
      target            — nome do arquivo-documento dentro de artifact.files (ex "postmortem.json")
      required_fields   — chaves de topo obrigatórias (presentes e NÃO-vazias)
      severity_field/valid_severities — severidade declarada deve estar no conjunto válido
      timeline_field    — lista de {ts, ...} com timestamps ISO MONOTÔNICOS crescentes
      duration_fields   — métricas numéricas > 0 (ex mtta/mttr); se 2, a 1ª <= a 2ª
      rollback_field    — objeto com documented==true e steps (lista não-vazia)
      followups_field   — lista não-vazia, cada item com action e owner não-vazios

    NÃO há execução: tests_pass="N/A", delivered_ok=SEMPRE False (ASSISTED, garantia parcial —
    estrutura é necessária-não-suficiente; "mitigated" é estado do mundo, fora do predicado).
    Retorna o MESMO contrato de verify_code (signals/static_ok/first_fail/tests_pass/delivered_ok).
    """
    st = (oracle or {}).get("structure") or {}
    sig = {k: False for k in STRUCT_NECESSARIOS}

    files = artifact.get("files") if isinstance(artifact, dict) else None
    sig["artifact_parseable"] = isinstance(files, dict) and bool(files) \
        and all(isinstance(k, str) and isinstance(v, str) for k, v in files.items())

    target = st.get("target")
    doc = None
    if sig["artifact_parseable"]:
        sig["target_present"] = bool(target) and target in files
        if sig["target_present"]:
            try:
                doc = json.loads(files[target])
                sig["doc_parses"] = isinstance(doc, dict)
            except (ValueError, TypeError):
                sig["doc_parses"] = False

    if sig["doc_parses"]:
        # (4) campos obrigatórios presentes/não-vazios + severidade válida
        req = st.get("required_fields", [])
        fields_ok = all(k in doc and _nonempty(doc[k]) for k in req)
        sev_field = st.get("severity_field")
        valid_sev = st.get("valid_severities")
        if sev_field and valid_sev:
            fields_ok = fields_ok and doc.get(sev_field) in valid_sev
        sig["fields_complete"] = fields_ok

        # (5) timeline com timestamps ISO monotônicos crescentes
        tl = doc.get(st.get("timeline_field", "timeline")) if st.get("timeline_field") else None
        if isinstance(tl, list) and tl:
            tss = []
            ok = True
            for item in tl:
                ts = item.get("ts") if isinstance(item, dict) else None
                if not isinstance(ts, str):
                    ok = False
                    break
                try:
                    from datetime import datetime
                    tss.append(datetime.fromisoformat(ts.replace("Z", "+00:00")))
                except ValueError:
                    ok = False
                    break
            sig["timeline_ordered"] = ok and all(tss[i] <= tss[i + 1] for i in range(len(tss) - 1))

        # (6) durações numéricas > 0 (e mtta <= mttr quando há duas)
        durs = [doc.get(f) for f in st.get("duration_fields", [])]
        nums_ok = bool(durs) and all(isinstance(d, (int, float)) and not isinstance(d, bool) and d > 0
                                     for d in durs)
        if nums_ok and len(durs) >= 2:
            nums_ok = durs[0] <= durs[1]
        sig["durations_valid"] = nums_ok

        # (7) rollback documentado com passos
        rb = doc.get(st.get("rollback_field", "rollback")) if st.get("rollback_field") else None
        sig["rollback_documented"] = isinstance(rb, dict) and rb.get("documented") is True \
            and isinstance(rb.get("steps"), list) and bool(rb.get("steps"))

        # (8) follow-ups acionáveis (cada um com action e owner)
        fu = doc.get(st.get("followups_field", "followups")) if st.get("followups_field") else None
        sig["followups_actionable"] = isinstance(fu, list) and bool(fu) and all(
            isinstance(x, dict) and _nonempty(x.get("action")) and _nonempty(x.get("owner")) for x in fu)

        # (9) sem placeholder de preenchimento vazio (anti-gaming)
        up = [s.upper() for s in _walk_strings(doc)]
        sig["no_placeholder_gaming"] = not any(tok in s for s in up for tok in _PLACEHOLDER_TOKENS)

    static_ok = all(sig[k] for k in STRUCT_NECESSARIOS)
    first_fail = next((k for k in STRUCT_NECESSARIOS if not sig[k]), None)
    # ASSISTED: sem execução, a estrutura NUNCA credita delivered (garantia parcial, honesta).
    return {"signals": sig, "static_ok": static_ok, "first_fail": first_fail,
            "tests_pass": "N/A", "delivered_ok": False}
