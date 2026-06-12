# Imagem de EXECUÇÃO Node do VERIFY-IN-EVAL (F3, natureza BUILD do frontend) — runner vitest.
# Construída UMA vez COM rede no job nightly; os contêineres de execução rodam SEM rede
# (--network none), read-only, non-root — então o runner é instalado no BUILD, nunca em runtime.
# Sem segredos, sem toolchain extra. Espelha exec.Dockerfile (pytest), trocando o runtime.
FROM node:20-slim

# vitest num prefixo fixo (/opt/runner); o symlink deixa `vitest` no PATH p/ rodar de /work.
# esbuild (transpila TS on-the-fly, sem tsconfig) vem junto e é compilado p/ linux no build.
WORKDIR /opt/runner
RUN npm init -y >/dev/null 2>&1 \
 && npm install --no-audit --no-fund --no-save vitest@^2.1 \
 && ln -s /opt/runner/node_modules/.bin/vitest /usr/local/bin/vitest

# Resolve `import ... from 'vitest'` a partir de /work (o vitest também alia o próprio runtime).
ENV NODE_PATH=/opt/runner/node_modules
# Workspace montado em /work (volume rw); container roda --user non-root + read-only + /tmp tmpfs.
WORKDIR /work
