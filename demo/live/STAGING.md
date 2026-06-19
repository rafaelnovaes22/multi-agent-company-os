# Ambiente de STAGING (Railway)

Staging é um **serviço separado** (`nucleo-staging`) no **mesmo projeto/environment** do Railway
que produção. URL: `https://nucleo-staging-production.up.railway.app`.

O deploy é **gated por GitHub Actions** ([.github/workflows/deploy-staging.yml](../../.github/workflows/deploy-staging.yml)):
no push ao branch `staging`, o gate de qualidade (`pre_pr_gate` + `forge_check` + suíte) roda
**antes** de publicar — só então o Railway recebe o deploy. É a "proteção do branch" por baixo
(o GitHub free não permite branch protection em repo privado): mesmo um push direto ao `staging`
passa pelo gate antes de virar deploy.

```
feature/*  --PR (forge-gate)-->  staging  --push--> [Actions: gate -> railway up] -->  nucleo-staging
                                    │  valida em Vertex real
                                    └--PR-->  main  -->  produção (nucleo-demo)
```

Como é serviço no mesmo environment de prod, ele **herda as variáveis compartilhadas do
environment** — inclusive o `GOOGLE_CREDENTIALS_JSON`. Por isso o staging fala com **Vertex
real** sem credencial por serviço (confirmado: `/api/health` →
`GoogleProvider/...vertex:acme-multiagentes/us-central1`). Imagem = a de produção
(`demo/live/Dockerfile`, healthcheck `/api/health`).

## Setup único

### 1. Railway — DESLIGAR o auto-deploy nativo do serviço `nucleo-staging`
**Settings → Source →** desconecte o branch de deploy automático (ou desative o auto-deploy).
O deploy passa a ser feito **só** pelo GitHub Actions — senão há deploy duplicado.

### 2. Railway — gerar o token de deploy
**Project Settings → Tokens →** gere um **token do projeto** com acesso ao environment onde o
`nucleo-staging` vive. O Actions seleciona o serviço por nome (`railway up --service nucleo-staging`).

### 3. GitHub — secret e variables
No repositório (**Settings → Secrets and variables → Actions**):

- **Secret** `RAILWAY_STAGING_TOKEN` = o token do passo 2. **← pendente** (cole via
  `gh secret set RAILWAY_STAGING_TOKEN` ou pela UI; nunca commitado).
- **Variable** `RAILWAY_STAGING_SERVICE` = `nucleo-staging`. ✅ definida.
- **Variable** `STAGING_URL` = `https://nucleo-staging-production.up.railway.app`. ✅ definida
  (usada no healthcheck pós-deploy).

### 4. Branch `staging`
Já existe. A partir do merge deste fluxo, **todo push/merge em `staging` dispara o deploy gated**.

## Fluxo de promoção

- Promova via **PR para `staging`** (o `forge-gate` roda como check de PR); ao mergear, o
  `deploy-staging` roda o gate de novo e publica. Push direto também é gated (gate antes do deploy).
- Validado em staging (Vertex real, mesma imagem de prod), promova o mesmo commit via PR para
  `main` → produção (`nucleo-demo`).

## Operação

- **Deploy manual:** Actions → *deploy-staging* → *Run workflow* (`workflow_dispatch`).
- **Logs / rollback:** dashboard Railway, serviço `nucleo-staging`.
- **Healthcheck:** `GET {STAGING_URL}/api/health` → `200`; o campo `llm` mostra o provider
  (`GoogleProvider/...vertex` = real; `FakeLLMProvider` = caiu offline, credencial não pegou).
- O deploy **falha cedo** se faltar `RAILWAY_STAGING_TOKEN` ou se o gate reprovar.
