# Ambiente de STAGING (Railway)

Staging é um **serviço separado** (`nucleo-staging`) no mesmo projeto/environment do Railway
que produção, com URL estável (`https://nucleo-staging-production.up.railway.app`), deploy
automático no **push ao branch `staging`** e **LLM real (Vertex/Gemini)** — um espelho de
produção para validar antes de promover ao `main`.

```
feature/*  --PR-->  main (produção)
    │
    └--------------> staging (este ambiente)   # push no branch `staging` publica aqui
```

O deploy é feito por [.github/workflows/deploy-staging.yml](../../.github/workflows/deploy-staging.yml):
roda o gate de qualidade (`pre_pr_gate` + `forge_check` + suíte) e só então publica. A mesma
imagem de produção é usada (`demo/live/Dockerfile`); staging difere **apenas pelas variáveis
do environment** — nada de segredo no repo.

## Setup único (uma vez)

### 1. Railway — serviço `nucleo-staging` (mesmo environment de produção)
Já criado: um **serviço separado** no mesmo projeto/environment, apontando para
`demo/live/Dockerfile` (healthcheck `/api/health`). URL pública:
`https://nucleo-staging-production.up.railway.app`.

### 2. Railway — variáveis do serviço `nucleo-staging` (LLM real via Vertex)
No serviço `nucleo-staging`, defina:

| Variável | Valor | Observação |
|---|---|---|
| `LLM_PROVIDER` | `vertex` | liga o provider real (sem isto = FakeLLMProvider offline) |
| `GOOGLE_GENAI_USE_VERTEXAI` | `true` | usa Vertex AI |
| `GOOGLE_CLOUD_PROJECT` | `acme-multiagentes` | mesmo projeto GCP usado no `redteam.yml` |
| `GOOGLE_CLOUD_LOCATION` | `us-central1` | região do Vertex |
| `GOOGLE_CREDENTIALS_JSON` | *(JSON da service account, inteiro)* | o `server.py` materializa isto em arquivo e aponta `GOOGLE_APPLICATION_CREDENTIALS` (ADC) |
| `GEMINI_MODEL` *(opcional)* | ex. `gemini-2.0-flash` | senão usa o default do NÚCLEO |
| `PORT` | *(injetado pelo Railway)* | não precisa setar |

> **Segurança:** `GOOGLE_CREDENTIALS_JSON` é segredo — vive só no environment Railway, nunca
> no repo. Use uma **service account própria de staging**, com o mínimo de permissões Vertex.
> Considere uma cota/budget separada para não misturar custo de staging com produção.

### 3. Railway — gerar o token de deploy
**Project Settings → Tokens →** gere um **token do projeto** com acesso ao environment onde o
`nucleo-staging` vive. O deploy seleciona o serviço por **nome** (`railway up --service
nucleo-staging`), então o token só precisa alcançar o projeto/environment.

### 4. GitHub — secret, variables e environment
No repositório (**Settings → Secrets and variables → Actions**):

- **Secret** `RAILWAY_STAGING_TOKEN` = o token do passo 3. **← único pendente** (cole via
  `gh secret set RAILWAY_STAGING_TOKEN` ou pela UI; nunca commitado).
- **Variable** `RAILWAY_STAGING_SERVICE` = `nucleo-staging`. ✅ já definida.
- **Variable** `STAGING_URL` = `https://nucleo-staging-production.up.railway.app`. ✅ já definida
  (usada no healthcheck pós-deploy).

Crie também o **GitHub Environment** `staging` (**Settings → Environments → New**) — o job de
deploy é protegido por ele, então você pode exigir aprovação manual ou restringir branches.

### 5. Criar o branch `staging`
Depois que este PR e o do gate (#62) entrarem no `main`:

```bash
git fetch origin
git switch -c staging origin/main
git push -u origin staging
```

A partir daí, **todo push em `staging` dispara o deploy**. Para promover algo: faça merge da
feature em `staging` (testa) e, validado, siga para `main` (produção).

## Operação

- **Deploy manual:** Actions → *deploy-staging* → *Run workflow* (`workflow_dispatch`).
- **Logs/rollback:** no dashboard Railway, environment `staging`.
- **Healthcheck:** `GET {STAGING_URL}/api/health` deve responder `200`.
- O deploy **falha cedo** se faltar `RAILWAY_STAGING_TOKEN` ou se o gate de qualidade reprovar
  — staging nunca recebe código que não passa no `pre_pr_gate`/`forge_check`/testes.
