# Imagem de EXECUÇÃO do VERIFY-IN-EVAL F2 — minimal, só o runner de teste.
# Construída UMA vez (com rede) no job nightly; os contêineres de execução rodam SEM rede
# (--network none), então nada é instalado em runtime. Sem segredos, sem ferramentas extras.
FROM python:3.13-slim
RUN pip install --no-cache-dir "pytest==8.*"
# Workspace é montado em /work (volume rw) e o container roda --user non-root + read-only.
WORKDIR /work
