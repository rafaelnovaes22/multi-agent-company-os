"""LLM-as-judge da QUALIDADE generativa da frota (VERIFY-IN-EVAL F3b — juiz externo).

Mede o que o grader de contrato (run_evals) NÃO mede: o CONTEÚDO gerado é fiel à persona
(soul), honra a cláusula de outcome (C2), respeita o anti-vazamento e é ÚTIL (não genérico)?

Junto com `exec_report` (oráculo determinístico, F0–F3) este relatório é o lado VIVO da
correlação run_evals×juiz: run_evals dá ~100% aos técnicos enquanto o juiz reprovava por
"blueprint, não código" (DESCASAMENTO DE INSTRUMENTO). O oráculo fecha o gap de MEDIÇÃO; a
nota do juiz só sobe com capacidade generativa + execução (F2+). Versionar o juiz permite
acompanhar essa subida ao longo do tempo, em vez de re-rodar ad-hoc.

- Gerador: a frota real (LLM_PROVIDER; em CI = Vertex/gemini via WIF). Sem provider real
  (FakeLLMProvider) o conteúdo é determinístico e o juiz não informa nada — por isso o
  gerador real é pré-requisito (guard --require-judge).
- Juiz: separado do gerador p/ reduzir auto-viés. JUDGE=openai (gpt-5, lê OPENAI_API_KEY do
  ambiente — em CI via secrets) | sonnet (claude) | pro (gemini/vertex). Família distinta do
  gerador (gemini) dá mais independência — por isso o default do workflow F3b é openai.
- Task: derivada do próprio outcome_clause do agente (tarefa real, não os casos estruturais).

Uso (CI, F3b):
    JUDGE=openai OPENAI_API_KEY=... LLM_PROVIDER=vertex GOOGLE_GENAI_USE_VERTEXAI=true \
      GOOGLE_CLOUD_PROJECT=acme-multiagentes GOOGLE_CLOUD_LOCATION=us-central1 \
      python -m nucleo.quality.judge_eval --require-judge --json-output judge_report.json
Sem chave do juiz (e sem --require-judge): sai inerte (0) — "pronto, aguardando o secret".
"""
from __future__ import annotations
import argparse
import glob
import json
import os
import re
import sys
import tempfile

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from langgraph.checkpoint.memory import MemorySaver

from ..factory.factory import load_spec, build_from_spec
from ..kernel.brain import Brain, FileStore
from ..kernel.providers.llm import get_llm

SONNET_MODEL = "claude-sonnet-4-6"
GEMINI_JUDGE_MODEL = "gemini-2.5-pro"
OPENAI_MODEL = os.environ.get("OPENAI_JUDGE_MODEL", "gpt-5")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _judge_key_present(judge: str) -> bool:
    """Há credencial p/ o juiz selecionado? (openai/sonnet = chave; pro/vertex = ADC do runner)."""
    if judge == "openai":
        return bool(os.environ.get("OPENAI_API_KEY"))
    if judge == "sonnet":
        return bool(os.environ.get("ANTHROPIC_API_KEY"))
    return True  # gemini/vertex usa ADC (WIF no CI) — não há env-key explícita p/ checar aqui


def _make_judge(judge: str):
    """Devolve (judge_name, complete_fn). Importa o SDK só do juiz escolhido (lazy)."""
    if judge == "sonnet":
        import anthropic
        client = anthropic.Anthropic()

        def complete(prompt: str) -> str:
            msg = client.messages.create(model=SONNET_MODEL, max_tokens=1024,
                                         messages=[{"role": "user", "content": prompt}])
            return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
        return f"Anthropic/{SONNET_MODEL}", complete

    if judge == "openai":
        import openai
        client = openai.OpenAI()  # lê OPENAI_API_KEY do ambiente (secret no CI)

        def complete(prompt: str) -> str:
            # gpt-5 é reasoning: max_completion_tokens (não max_tokens) com folga p/ reasoning+saída;
            # senão o reasoning consome tudo e content volta vazio. json_object exige "json" no prompt.
            r = client.chat.completions.create(
                model=OPENAI_MODEL, max_completion_tokens=8000,
                reasoning_effort=os.environ.get("REASONING_EFFORT", "medium"),
                response_format={"type": "json_object"},
                messages=[{"role": "user", "content": prompt}])
            return (r.choices[0].message.content or "").strip()
        return f"OpenAI/{OPENAI_MODEL}", complete

    from google import genai
    from google.genai import types
    client = genai.Client(vertexai=True,
                          project=os.environ.get("GOOGLE_CLOUD_PROJECT", "acme-multiagentes"),
                          location=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"))

    def complete(prompt: str) -> str:
        cfg = types.GenerateContentConfig(max_output_tokens=4096)
        r = client.models.generate_content(model=GEMINI_JUDGE_MODEL, contents=prompt, config=cfg)
        return (r.text or "").strip()
    return f"GoogleProvider(direct)/{GEMINI_JUDGE_MODEL}/vertex", complete


def _judge_prompt(spec: dict, statement: str, content: str) -> str:
    oc = spec.get("outcome_clause") or {}
    soul = ""
    sd = spec.get("_dir")
    if sd:
        try:
            soul = open(os.path.join(sd, spec.get("soul_ref", "soul.md")), encoding="utf-8").read().strip()
        except OSError:
            pass
    pos = "\n- ".join(map(str, oc.get("positive_examples", []))) or "(nenhum)"
    neg = "\n- ".join(map(str, oc.get("negative_examples", []))) or "(nenhum)"
    return f"""Você é um avaliador RIGOROSO de qualidade de artefatos de agentes de IA.
Avalie o ARTEFATO produzido pelo agente {spec['id']} contra a persona e a cláusula de outcome.

PERSONA (soul):
{soul[:1800]}

CLÁUSULA DE OUTCOME (C2): {oc.get('statement', '(sem)')}
CONTA COMO ENTREGUE:
- {pos}
NÃO CONTA / EVITE:
- {neg}

TAREFA DADA AO AGENTE:
{statement}

ARTEFATO PRODUZIDO PELO AGENTE:
{content[:16000]}

Responda APENAS com um objeto JSON (sem markdown), com as chaves:
{{"persona_fit": <int 1-5, reflete voz/missão/princípios do soul>,
 "c2_fit": <int 1-5, honra o outcome e os positive_examples e evita os negative_examples>,
 "anti_leak": <"pass"|"fail", NÃO revelou vertical/mercado não-definido nem violou restrições>,
 "utilidade": <int 1-5, conteúdo específico e acionável vs genérico/vazio/meta>,
 "overall_pass": <true|false, você aprovaria como artefato utilizável em SHADOW>,
 "justificativa": "<= 280 chars, objetiva"}}
Calibração: 5=excelente/pronto; 3=aceitável com ressalvas; 1=genérico/fora do escopo.
Seja crítico: penalize vagueza, hype vazio, meta-resposta ("eu faria..."), ou ignorar o C2."""


def _judge(complete_fn, spec, statement, content) -> dict:
    txt = complete_fn(_judge_prompt(spec, statement, content))
    m = re.search(r"\{.*\}", txt, re.DOTALL)
    if not m:
        return {"error": "no-json", "raw": txt[:200]}
    try:
        return json.loads(m.group(0))
    except Exception as e:  # noqa: BLE001
        return {"error": f"parse:{e}", "raw": txt[:200]}


def _realistic_task(spec: dict):
    oc = spec.get("outcome_clause") or {}
    aid = spec["id"]
    artifact = (aid.split("-", 1)[-1] if "-" in aid else aid) + ".artifact"
    statement = (
        f"Cumpra sua missão como {aid} e produza AGORA o artefato concreto correspondente, "
        f"para o NÚCLEO (tenant zero, build-in-public). "
        f"Outcome esperado (C2): {oc.get('statement', 'cumprir a missão do agente')}. "
        f"Entregue o conteúdo final pronto para uso — não descreva como faria."
    )
    return statement, artifact


def _targets():
    """Agentes generativos (spec_driven) — é o conteúdo que o juiz consegue avaliar."""
    out = []
    for f in sorted(glob.glob(os.path.join(ROOT, "nucleo", "guilds", "**", "spec.yaml"), recursive=True)):
        sp = load_spec(os.path.dirname(f))
        if sp.get("act_handler") == "spec_driven":
            sp["_dir"] = os.path.dirname(f)
            out.append((os.path.dirname(f), sp))
    return out


def _avg(rows, key):
    xs = [r[key] for r in rows if isinstance(r.get(key), (int, float))]
    return round(sum(xs) / len(xs), 2) if xs else 0.0


def run(judge: str, complete_fn, *, limit: int = 0) -> dict:
    gen_llm = get_llm("worker")
    tmp = tempfile.mkdtemp(prefix="judge-")
    brain = Brain(os.path.join(tmp, "events"))
    store = FileStore(os.path.join(tmp, "store"))
    cp = MemorySaver()

    targets = _targets()
    if limit:
        targets = targets[:limit]

    rows = []
    for sd, spec in targets:
        statement, artifact = _realistic_task(spec)
        try:
            _, agent, _ = build_from_spec(sd, gen_llm, brain, store, cp)
            state = {"task": {"agent_id": spec["id"], "guild": spec["guild"], "statement": statement,
                              "artifact_type": artifact, "risk": "low"},
                     "mode": "SHADOW", "ledger": spec.get("ledger"),
                     "run_id": "q-" + spec["id"], "verbose": False}
            out = agent.invoke(state, config={"configurable": {"thread_id": state["run_id"]}}).get("output") or {}
            content = out.get("content", "") or ""
            v = _judge(complete_fn, spec, statement, content)
        except Exception as e:  # noqa: BLE001
            content = ""
            v = {"error": f"run:{e}"}
        v.update({"_id": spec["id"], "_guild": spec["guild"], "_content_len": len(content)})
        rows.append(v)

    ok = [r for r in rows if "error" not in r]
    npass = sum(1 for r in ok if r.get("overall_pass") is True)
    leak_fail = [r for r in ok if r.get("anti_leak") == "fail"]
    dims = {"persona_fit": _avg(ok, "persona_fit"), "c2_fit": _avg(ok, "c2_fit"),
            "utilidade": _avg(ok, "utilidade")}
    lowest_dim = min(dims, key=dims.get) if ok else None
    return {
        "generator": gen_llm.name,
        "judge": judge,
        "total": len(rows),
        "evaluated_ok": len(ok),
        "errors": [{"id": r.get("_id"), "error": r.get("error")} for r in rows if "error" in r],
        "overall_pass": {"passed": npass, "total": len(ok),
                         "percent": round(100 * npass / len(ok), 1) if ok else 0.0},
        "avg_dimensions": dims,
        "lowest_dimension": lowest_dim,   # tese: c2_fit (verificabilidade) é o piso nos técnicos
        "anti_leak_fail": [r["_id"] for r in leak_fail],
        "rows": rows,
    }


def render_text(rep: dict) -> str:
    op = rep["overall_pass"]
    d = rep["avg_dimensions"]
    lines = [
        f"judge_eval — gerador={rep['generator']}  juiz={rep['judge']}",
        f"  avaliados      = {rep['evaluated_ok']}/{rep['total']}",
        f"  overall_pass   = {op['passed']}/{op['total']}  ({op['percent']:.0f}%)",
        f"  médias         = persona={d['persona_fit']}  c2={d['c2_fit']}  utilidade={d['utilidade']}",
        f"  menor dimensão = {rep['lowest_dimension']}  ← oráculo VERIFY-IN-EVAL ataca exatamente isto",
    ]
    if rep["anti_leak_fail"]:
        lines.append(f"  ⚠ anti_leak FALHOU: {rep['anti_leak_fail']}")
    if rep["errors"]:
        lines.append(f"  erros: {len(rep['errors'])}")
    return "\n".join(lines)


def _parse(argv):
    p = argparse.ArgumentParser(description="LLM-as-judge da qualidade generativa (F3b).")
    p.add_argument("--require-judge", action="store_true",
                   help="exige credencial do juiz; sem ela, exit 1 (em vez de sair inerte).")
    p.add_argument("--limit", type=int, default=0, help="avalia só os N primeiros agentes (debug/custo).")
    p.add_argument("--json-output", help="grava o relatório JSON neste caminho.")
    return p.parse_args(argv)


def main(argv):
    args = _parse(argv)
    judge = os.environ.get("JUDGE", "openai").strip().lower()
    if not _judge_key_present(judge):
        msg = (f"[judge_eval] credencial do juiz '{judge}' ausente — relatório F3b não roda "
               f"(configure o secret e re-dispare).")
        if args.require_judge:
            print(msg, file=sys.stderr)
            return 1
        print(msg + " (inerte: --require-judge não setado)")
        return 0

    judge_name, complete_fn = _make_judge(judge)
    rep = run(judge, complete_fn, limit=args.limit)
    rep["judge"] = judge_name
    text = render_text(rep)
    if args.json_output:
        with open(args.json_output, "w", encoding="utf-8") as f:
            f.write(json.dumps(rep, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
