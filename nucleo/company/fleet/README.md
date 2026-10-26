# Frota interna Novais Digital — Fase 0

Frota de gestão da **própria Novais Digital** (não vendida ao cliente — para a frota
de produto ver `nucleo/product/`). Implementa a **Fase 0** do
[PLANO-TIMES-AGENTES-NOVAIS-2026-10](../../../../PLANO-TIMES-AGENTES-NOVAIS-2026-10.md):
os 4 agentes que cobrem o que não pode parar + o Prefeito (painel de 10 números com fonte).

| Agente | Setor (plano) | Papel | Reconcilia com | Handler |
|---|---|---|---|---|
| `fila` | Atendimento | Gerente (inbound/SLA 15min) | g9-custops-supervisor | `nv_inbound_queue` |
| `ponte` | Atendimento | Dev (saúde do canal WhatsApp/formulário) | g9-messaging-concierge | `nv_channel_health` |
| `turno` | Operações | Gerente (rodada diária de deploys) | g14-aiops-supervisor | `nv_ops_round` |
| `ciclo` | Financeiro | Gerente (recorrência/cobrança/MRR) | g10-treasury + g8-dunning-agent | `nv_billing_cycle` |
| `prefeito` | Coordenação | Chief-of-staff (painel 08h/18h) | g6-dashboard-builder | `nv_prefeito_panel` |

Regras herdadas do plano (codificadas nas specs e handlers):
- Nascem em **SHADOW**; nenhum papel nasce AUTONOMOUS (C4).
- `ledger: operating` (interno, token-max) — não é frota billable.
- Número nunca se fecha na conversa: banda pro Rafael por escrito (`ciclo`, `fila`).
- Painel do Prefeito: **todo número com fonte**; métrica sem fonte = semáforo vermelho.
- Prova no `nucleo/demo_fase0.py` (offline, FakeLLM) + eval-suite por agente.
