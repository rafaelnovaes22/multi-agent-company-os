# Imagem de EXECUÇÃO terraform do VERIFY-IN-EVAL (F4a, natureza ops/dry-run) — terraform test.
# Construída UMA vez (com rede) no nightly; os contêineres de execução rodam SEM rede
# (--network none), read-only, non-root. Os eval-cases NÃO usam providers de cloud — só o
# core do terraform (variables/locals/outputs/funções/validations) — então `terraform init
# -backend=false` e `terraform test` (command=plan) não tocam a rede e são determinísticos.
# Espelha exec.Dockerfile (pytest) / exec.node.Dockerfile (vitest), trocando o runtime.
FROM hashicorp/terraform:1.9

# Na imagem oficial o terraform é o ENTRYPOINT; o executor roda `sh -c <test_cmd>`, então
# reseta o entrypoint p/ o shell (alpine) receber o comando.
ENTRYPOINT []

# Sem rede em runtime: desliga checkpoint (telemetria/versão), modo automação e HOME=/tmp
# gravável (rootfs é read-only; só /work [volume] e /tmp [tmpfs] são graváveis).
ENV CHECKPOINT_DISABLE=1 \
    TF_IN_AUTOMATION=1 \
    HOME=/tmp

# Workspace montado em /work (volume rw); container roda --user non-root + read-only + /tmp tmpfs.
WORKDIR /work
