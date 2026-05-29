"""/evolve — promove instincts recorrentes a SKILLS compartilhadas (ECC).

Enquanto o Hermes acumula fatos na memória de CADA agente, o /evolve olha o
corpo de memória inteiro, agrupa fatos por tópico e, quando um tópico tem
suporte suficiente, promove-o a uma skill da empresa em company/skills/ — para
a frota inteira reusar (não só o agente que aprendeu). Ver 02-ARQUITETURA §7.
"""
from __future__ import annotations
import os

# Tópicos reconhecidos (palavras-chave). Em produção: clustering por embedding.
_TOPICS = {
    "criterio-icp-faturamento": ["r$1-5m", "faixa de faturamento", "faixa r$1-5m"],
    "validacao-outcome-c2": ["delivered_event", "validação c2", "specs reprovadas", "cláusula"],
    "sinais-desqualificacao-lead": ["desqualifica", "descarte"],
    "sinais-highfit-lead": ["high-fit", "score>=75", "trilha assistida"],
}

_TITLES = {
    "criterio-icp-faturamento": "Faixa de faturamento R$1-5M é critério decisivo de fit de ICP",
    "validacao-outcome-c2": "Validação da cláusula de outcome (C2): o que reprova uma spec",
    "sinais-desqualificacao-lead": "Sinais que desqualificam um lead",
    "sinais-highfit-lead": "Sinais que produzem lead high-fit",
}


def _company_skills_dir(store_root: str) -> str:
    # company/ fica ao lado de nucleo/ ; store_root = .../nucleo/.brain/store
    nucleo_dir = os.path.dirname(os.path.dirname(store_root))
    d = os.path.join(nucleo_dir, "company", "skills")
    os.makedirs(d, exist_ok=True)
    return d


def run_evolve(store, brain, min_support: int = 2, verbose: bool = True) -> dict:
    # 1. coleta todos os fatos de memória de todos os agentes
    corpus = []  # (agent_id, fact_line)
    for aid in store.subdirs(("snapshots",)):
        for fact in store.search(("agent", aid, "memory")):
            corpus.append((aid, str(fact)))

    # 2. agrupa por tópico
    clusters = {}
    for aid, line in corpus:
        low = line.lower()
        for topic, kws in _TOPICS.items():
            if any(kw in low for kw in kws):
                clusters.setdefault(topic, {"facts": [], "agents": set()})
                clusters[topic]["facts"].append(line)
                clusters[topic]["agents"].add(aid)

    # 3. promove os que têm suporte suficiente
    skills_dir = _company_skills_dir(store.root)
    promoted = []
    for topic, data in clusters.items():
        if len(data["facts"]) >= min_support:
            path = os.path.join(skills_dir, topic + ".md")
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"# Skill (evolved): {_TITLES.get(topic, topic)}\n\n")
                f.write(f"> Promovida pelo /evolve a partir de {len(data['facts'])} instincts "
                        f"de {len(data['agents'])} agente(s): {', '.join(sorted(data['agents']))}.\n\n")
                f.write("Fatos de suporte:\n")
                for fl in data["facts"]:
                    f.write(f"- {fl}\n")
            promoted.append({"topic": topic, "support": len(data["facts"]),
                             "agents": sorted(data["agents"]), "path": path})
            if verbose:
                print(f"  /evolve -> skill '{topic}' ({len(data['facts'])} fatos, "
                      f"agentes: {', '.join(sorted(data['agents']))})")

    brain.emit_event({"actor": "evolve", "action": "skills_evolved",
                      "count": len(promoted), "topics": [p["topic"] for p in promoted]})
    return {"promoted": promoted, "corpus_size": len(corpus)}
