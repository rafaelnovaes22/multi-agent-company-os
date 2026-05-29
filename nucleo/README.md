# NÚCLEO — Sprint 0 (kernel + Fábrica + guilda-piloto)

Fatia mínima **funcional** que prova o loop end-to-end do plano, sobre **LangGraph**.
Contexto e arquitetura completos em [../README.md](../README.md) e [../02-ARQUITETURA.md](../02-ARQUITETURA.md).

## Como rodar

```bash
pip install -r ../requirements.txt        # langgraph, langchain-core, pydantic, pyyaml
python -m nucleo.demo                      # a partir da pasta Multi-Agentes
```

Roda **offline por padrão** (FakeLLMProvider — custo zero, sem rede, determinístico).
Para usar um LLM real (C7): `pip install anthropic` e defina `ANTHROPIC_API_KEY`.

## O que a demo prova

Materializa o agente **g13-po-guardian** a partir da sua `spec.yaml` (via a Fábrica) e
roda o grafo para duas specs-alvo (uma boa, uma ruim), em modo **SHADOW**:

```
load_context -> act -> self_critique -> gate[SHADOW] -> emit_artifact -> snapshot
   (SOUL/MEMORY)  (valida C2)  (guardians)   (NÃO entrega)   (Company Brain)   (learning loop)
```

- **SHADOW**: o output é calculado e medido, mas `delivered=False` e `billing=0` (C4).
- Toda ação vira **artefato** no Company Brain (`.brain/events/events.jsonl`) — C6 / YC#3.
- Cada run gera **snapshot** (`.brain/store/snapshots/...`) para o learning loop (Hermes).

## Mapa do código → camadas do plano

| Arquivo | Camada (ver 02-ARQUITETURA) |
|---|---|
| `kernel/state.py` | estado universal do agente |
| `kernel/providers/llm.py` | C7 — abstração de LLM (Fake / Anthropic) |
| `kernel/brain.py` | L0 — Company Brain (event store + store) |
| `kernel/self_harness.py` | L2 — load_context / emit_artifact / snapshot |
| `kernel/guardians.py` | L4 — validação C2 + self-critique |
| `kernel/gates.py` | C4 — gate SHADOW/PILOT/ASSISTED (interrupt) |
| `kernel/agent_template.py` | template universal → subgrafo LangGraph |
| `factory/factory.py` | L3 — a Fábrica (gate C1/C2/C3/C4 + materializa) |
| `guilds/g13_governanca/g13-po-guardian/` | a guilda-piloto (spec + soul + memory + evals) |
| `demo.py` | orquestra o end-to-end |

## Próximos passos (a partir daqui)

1. **Promoção por gate**: rodar em ASSISTED (exercita o `interrupt()` de aprovação humana) e PILOT.
2. **Supervisor de guilda**: `build_guild()` (langgraph-supervisor) roteando vários workers.
3. **Mais agentes**: escrever novas `spec.yaml` (a Fábrica materializa) — começar por G03/G04.
4. **Hermes learning loop**: cron que lê snapshots → instincts → PR de memória.
5. **Brain real**: trocar FileStore/JSONL por Postgres + pgvector (mesma interface, C7).
6. **Persistência durável**: trocar MemorySaver por PostgresSaver (checkpoint resumível).

## Demos (todos rodando, offline)

| Comando | Prova |
|---|---|
| `python -m nucleo.demo` | g13-po-guardian validando outcome (C2) em SHADOW |
| `python -m nucleo.demo_g8` | g8-lead-qualifier qualificando leads ancorado no ICP (`load_icp`) |
| `python -m nucleo.demo_assisted` | gate ASSISTED: human-in-the-loop via `interrupt()` (DRI aprova/rejeita) |
| `python -m nucleo.demo_g08_pipeline` | supervisor da G08: qualifier → (se qualified) → outbound-sdr |
| `python -m nucleo.demo_hermes` | Hermes learning loop: snapshots → fatos de memória (agente lembra) |
| `python -m nucleo.demo_evolve` | /evolve: instincts recorrentes → skills em `company/skills/` |
| `python -m nucleo.demo_diagnose` | g2-diagnose: 1º produto **cobrável** (diagnóstico C1) — baseline + outcome + SKUs |
| `python -m nucleo.demo_funnel` | **funil de receita** cross-guild: qualify → (qualified) diagnose → (go) prospect, com gate em cada etapa |
| `python -m nucleo.demo_prework` | **pré-work do workshop** (dogfooding): g1-market-intel (hard-filters) + g1-opportunity-sizer (TAM/SAM/SOM) por vertical candidato |
| `python -m nucleo.demo_eval` | **eval-harness** (C4): roda a eval-suite de toda a frota e mede pass-rate (Gate 4 da promoção) |
| `python -m nucleo.demo_promote` | **promotion gates** (C4): SHADOW→PILOT→ASSISTED→AUTONOMOUS com 6 gates + cross-approval (anti-self-approval) |
| `python -m nucleo.demo_agentshield` | **AgentShield**: scan de higiene/segurança das specs da frota (secrets, PII, guardians, C2/C3/C4/C7/C8) |
| `python -m nucleo.demo_root` | **supervisor-raiz (CEO-OS)**: roteia intenção em linguagem natural → guilda/funil (YC#5) |
| `python -m nucleo.demo_product_fin` | **PRODUTO multi-tenant**: agente `fin-caixa` atende 2 clientes de segmentos diferentes (contexto/memória por tenant, C5/C8) |
| `python -m nucleo.demo_product_inbox` | **PRODUTO multi-tenant**: agente `inbox-triage` classifica/roteia a caixa de entrada por tenant |
| `python -m nucleo.demo_onboarding` | **ONBOARDING ponta a ponta**: diagnóstico → ativa o fleet de produto (5 agentes) em SHADOW → painel do dono |

Fleet de produto (`product/`, 5 agentes live): `fin-caixa`, `inbox-triage`, `ops-followup`, `atendimento`, `painel-dono` + `onboarding.py`.

Fleet de produto (`product/`): `fin-caixa`, `inbox-triage` (live) + catálogo (`product/catalog.py`) de onde o `g2-diagnose` recomenda quais ativar por cliente.

> **Dois fleets:** `guilds/` = fleet INTERNO (nós, vendedor, usando a plataforma) · `product/` = fleet de PRODUTO (agentes de gestão multi-tenant vendidos ao cliente-bombeiro, agnósticos de segmento).

Módulos novos: `governance/promote.py` (gates C4), `security/agentshield.py`, `quality/eval_harness.py`+`graders.py`, e `build_root_supervisor` em `kernel/supervisor.py`.

Módulos novos: `kernel/skills.py` (registry de act-handlers), `kernel/supervisor.py`,
`kernel/loaders.py` (L0/C5), `learning/hermes.py`, `learning/evolve.py`.
