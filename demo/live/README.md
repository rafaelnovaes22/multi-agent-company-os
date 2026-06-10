# Demo viva Acme Multi-Agentes

Front estático + servidor stdlib que materializa a frota real do NÚCLEO e expõe uma API mínima para a landing/demo.

## O que entra neste diretório

- `index.html` — experiência visual da demo.
- `server.py` — servidor HTTP local/containerizado; serve o front e responde `POST /api/intent` usando `build_company`.
- `.brain-web/` — estado runtime regenerável; **não é versionado** por causa do `.gitignore` do repo.

## Rodar localmente

A partir da raiz do repo:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python demo/live/server.py
```

Abrir: <http://127.0.0.1:8765>

Sem configuração adicional, o NÚCLEO usa o provider fake/offline. Para LLM real, configure as variáveis do provider do NÚCLEO antes de subir o servidor, por exemplo `LLM_PROVIDER=google`/`vertex` e as credenciais correspondentes.

## API

- `GET /api/health` — status da frota carregada.
- `POST /api/intent` — executa uma intenção na frota real.

Exemplo:

```bash
curl -s http://127.0.0.1:8765/api/health
curl -s -X POST http://127.0.0.1:8765/api/intent \
  -H 'Content-Type: application/json' \
  -d '{"intent":"qualifique este lead","context":{"company":"Acme Limpeza","revenue_brl_year":3000000,"founder_led":true,"sells_well":true,"lacks_process":true,"firefighter":true}}'
```

## Container / Cloud Run

Build a partir da raiz do repo:

```bash
docker build -f demo/live/Dockerfile -t nucleo-live-demo .
docker run --rm -p 8080:8080 -e PORT=8080 nucleo-live-demo
```

Para Cloud Run, o container escuta `0.0.0.0:$PORT` por padrão no Dockerfile.
