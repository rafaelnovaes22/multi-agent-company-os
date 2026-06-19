# Ambiente de STAGING (Railway)

Staging é um **serviço separado** (`nucleo-staging`) no **mesmo projeto/environment** do Railway
que produção, com **deploy nativo do Railway** (GitHub auto-deploy) a partir do branch `staging`.
URL: `https://nucleo-staging-production.up.railway.app`.

```
feature/*  --PR (forge-gate roda)-->  staging  --(Railway auto-deploy)-->  nucleo-staging
                                          │  valida em Vertex real
                                          └--PR-->  main  -->  produção (nucleo-demo)
```

Como é serviço no mesmo environment de prod, ele **herda as variáveis compartilhadas do
environment** — inclusive o `GOOGLE_CREDENTIALS_JSON`. Por isso o staging já fala com **Vertex
real** sem credencial setada por serviço (confirmado: `/api/health` →
`GoogleProvider/...vertex:acme-multiagentes/us-central1`). A imagem é a de produção
(`demo/live/Dockerfile`, healthcheck `/api/health`).

## Setup

### 1. Branch `staging`
Depois que o gate (#62) entrar no `main`:

```bash
git fetch origin
git switch -c staging origin/main
git push -u origin staging
```

### 2. Railway — apontar o serviço para o branch `staging`
No dashboard: **serviço `nucleo-staging` → Settings → Source →** branch de deploy = **`staging`**
(hoje ele provavelmente aponta para `main`). A partir daí, **todo push/merge em `staging`
dispara o deploy** automaticamente pelo Railway — **sem token nem GitHub Actions**.

### 3. Variáveis (já resolvidas)
- LLM real (Vertex): `LLM_PROVIDER=vertex`, `GOOGLE_GENAI_USE_VERTEXAI=true`,
  `GOOGLE_CLOUD_PROJECT=acme-multiagentes`, `GOOGLE_CLOUD_LOCATION=us-central1` no serviço;
  `GOOGLE_CREDENTIALS_JSON` herdado do environment. Nada a fazer no repo.

## Fluxo de promoção e gate

- O gate de qualidade roda como **check de PR** (`forge-gate` em [.github/workflows/forge.yml](../../.github/workflows/forge.yml),
  já com `pre_pr_gate` + `forge_check` + suíte). Ele controla o que pode **entrar** no `staging`.
- **Sempre promova via PR para `staging`** (não dê push direto): push direto pula o gate, pois o
  Railway deploya na hora. Proteja o branch `staging` exigindo PR + check verde se quiser travar isso.
- Validado em staging (Vertex real, mesma imagem de prod), promova o mesmo commit via PR para
  `main` → produção (`nucleo-demo`).

## Operação

- **Logs / rollback / redeploy:** dashboard Railway, serviço `nucleo-staging`.
- **Healthcheck:** `GET https://nucleo-staging-production.up.railway.app/api/health` deve
  responder `200`; o campo `llm` mostra o provider ativo (`GoogleProvider/...vertex` = real;
  `FakeLLMProvider` = caiu offline, credencial não pegou).
