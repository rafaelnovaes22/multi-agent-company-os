# NÚCLEO como Fábrica de Agentes — visão, gap e roadmap

> Documento de alinhamento para a CEO. Estado: 2026-06-17. Ancorado no código real, não em aspiração.

## 1. A tese, dita sem rodeio

O NÚCLEO **já nasceu como fábrica de agentes** — essa é a tese fundadora ("não construímos 150 agentes à mão; construímos um Company-OS que os fabrica, governa e evolui"). A pergunta certa não é *"como viramos uma fábrica?"* — é **"qual é o último elo da linha de montagem que ainda falta, e como escalamos sem virar caos?"**.

A resposta deste documento: **falta a máquina de PROJETO (autoria) e a garantia de que o que sai da fábrica é verificável — não prosa convincente.** As duas coisas se resolvem na ordem certa, ou a fábrica escala teatro.

## 2. O que já é fábrica e funciona (a base é real)

| Camada | O que existe hoje | Onde vive |
|---|---|---|
| **Materialização** | 1 template universal materializa qualquer spec num subgrafo executável (`load_context→act→self_critique→gate→emit→snapshot`) | `nucleo/kernel/agent_template.py` |
| **Governança de fábrica** | Gate C2/C3/C4 antes de materializar; um agente malformado não entra na frota | `nucleo/factory/factory.py` |
| **Promoção controlada** | Gates G1–G6, SHADOW→ASSISTED→AUTONOMOUS, cross-approval (quem aprova ≠ quem promove), kill-switch de frota | `nucleo/governance/promote.py`, `nucleo/kernel/gates.py` |
| **Escala atual** | **158 agentes / 15 guildas** já materializados a partir de specs | `nucleo/guilds/` |

**Conclusão:** a máquina de MONTAGEM (spec → agente executável) é automática e escala. A governança que evita "150 agentes = caos" já é código, não slide.

## 3. O gap honesto — onde a fábrica ainda é manual

A materialização é automática. A **autoria não é.** Cada agente novo hoje =
4 artefatos escritos à mão (`spec.yaml` + `soul.md` + `memory.md` + ≥30 eval-cases) + um handler novo quando o comportamento não existe. **~2–6h de engenheiro humano por agente. Zero scaffold, zero gerador.**

A fábrica tem esteira de montagem, mas não tem **máquina de projeto**. É por isso que crescer a frota ainda custa headcount — exatamente o que a tese promete eliminar.

## 4. A tensão que precede qualquer decisão de "criar o que for"

Existem dois caminhos para escalar a frota. A diferença entre eles é o projeto inteiro.

- **Caminho fácil (e perigoso):** gerar centenas de agentes rápido. O próprio NÚCLEO já mediu para onde isso vai: o avaliador interno (`run_evals`) dá ~100%, mas o **juiz externo independente (gpt-5) dá 33% de aprovação** (N=24). A causa, vista no cache de artefatos: os agentes produzem **prosa-em-JSON que *descreve* a capacidade — não *é* o artefato/código real.** Escalar isso = multiplicar teatro.
- **Caminho correto (e mais lento):** a fábrica fabrica agentes **verificáveis por construção** — cada um nasce com um oráculo independente que separa *"entreguei"* de *"disse que entreguei"*. É exatamente o que o épico **VERIFY-IN-EVAL** vem instalando, agente a agente.

**Implicação estratégica:** VERIFY-IN-EVAL **não é um desvio da visão-fábrica — é a fundação dela.** A dimensão de verificabilidade (`c2_fit`) é o piso medido do juiz em 7/7 dos agentes técnicos. Sem fechar esse piso, "fábrica de agentes que cria o que for" significa "fábrica de plausível-não-confiável em escala".

## 5. As quatro alavancas (todas ancoradas no código)

1. **Meta-agente fabricante (`g0-agent-smith`)** — recebe uma intenção de capacidade e gera `spec`+`soul`+`memory`+stub de handler, já passando pelo `factory_gate`. Transforma 6h em minutos. O template universal e o gate **já são os trilhos** — falta o gerador que corre sobre eles. *É a máquina de projeto que falta.*

2. **Case-factory (o gargalo real)** — os geradores de eval-cases hoje são scripts ad-hoc escritos à mão por frente. Promovê-los a capability versionada do NÚCLEO. **Barreira inegociável:** quem gera o agente **não pode** gerar o próprio teste — senão o oráculo vira tautológico (já observado: "270/270 casos tautológicos" quando a independência vazou). Independência = held-out humano OU adversário separado. **Esta é a alavanca que não escala por config e precisa de dono** — é o limite honesto da automação.

3. **Loop de evolução ligado (Hermes + `/evolve`)** — o encanamento de aprendizado (run → instinct → skill compartilhada) existe, mas está **desligado no CI** (provider fake). Ligar o LLM real fecha o "exército que **evolui**", não só que nasce.

4. **Composição segura (supervisor→worker)** — a frota existe, mas supervisores chamam workers via `.invoke()` imperativo que **fura o gate C4 / human-in-the-loop** (há PoC de correção). Compor agentes sob demanda **sob governança** é pré-condição de "montar uma capacidade nova combinando agentes existentes".

## 6. Sequência recomendada (a ordem é a tese)

```
[AGORA]  Fechar VERIFY-IN-EVAL  ──►  fundação verificável
         (F4c landing/Lighthouse, F4d e2e/Playwright — os 2 técnicos browser que faltam)
            │
            ▼
[N+1]    Meta-agente fabricante (alavanca 1)
         autoria automática SOBRE a base verificável
            │
            ▼
[N+2]    Case-factory com independência (alavanca 2)
         semi-automatizar o oráculo SEM ferir a independência
            │
            ▼
[∞]      Evolução ligada (3) + Composição segura (4)
         exército que evolui e se recombina sob governança
```

**Não inverter.** Construir o gerador (alavanca 1) antes da verificabilidade (VERIFY-IN-EVAL) é escalar a autoria de agentes que o juiz reprova — acelerar na direção errada. A fábrica só vira ativo defensável quando **velocidade de autoria** e **garantia de verificabilidade** crescem juntas.

## 7. Riscos a nomear para a CEO

- **Independência do oráculo** é a linha vermelha: automatizar a geração de testes junto com a geração do agente destrói o valor (vira auto-aprovação). Há trabalho que **continua humano por design** (dono do held-out).
- **Verificabilidade é de amostra, não de cobertura.** A fábrica garante que *uma amostra* do comportamento é executável e honesta — não prova de corretude total. Isso é uma propriedade do produto, não um bug a esconder.
- **Capacidade generativa tem teto.** O oráculo **mede**, não faz o LLM gerar melhor. Subir a nota do juiz depende de capacidade + execução real (fontes certas por domínio + tooling), não de prompt/grounding — isso já foi medido e refutado (N=5).

## 8. O pitch de uma frase

> O NÚCLEO já monta agentes automaticamente e os governa sob constituição. O próximo salto é **autoria automática sobre uma base verificável-por-construção** — uma fábrica onde cada novo agente nasce já provando, contra um oráculo independente, que *fez* em vez de *dizer que fez*. É isso que separa "exército que cria o que for" de "exército de prosa em escala".
