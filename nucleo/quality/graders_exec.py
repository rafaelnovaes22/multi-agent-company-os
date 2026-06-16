"""Grader do handler `spec_executor` (épico VERIFY-IN-EVAL, F0).

Diferente do generic_contract_grader (que só checa presença/compatibilidade de contrato e
dava 30/30 verde a blueprints), este grader confere os SINAIS DO ORÁCULO que o handler
re-derivou do artefato: `static_ok`, `delivered_ok`, `first_fail` e os sinais necessários.

O `expected` do caso é AUTORADO da intenção do cenário (ex.: "deleta o teste-alvo ⇒
static_ok=False, first_fail=protected_unmodified") — independente do handler. A concordância
caso×oráculo é o sinal: se `verify_code` tivesse bug, o expected divergiria. É a mesma
disciplina dos handlers determinísticos da frota.
"""
from __future__ import annotations

from .graders import register

# Chaves de sinal que o caso PODE asseverar (todas opcionais; só checa as presentes no expected).
_SIGNAL_KEYS = (
    "static_ok", "delivered_ok", "first_fail",
    # code-exec (F0/F3/F4a)
    "artifact_parseable", "touches_bug_file", "bug_addressed",
    "protected_unmodified", "heldout_untouched", "result_parses", "no_test_gaming",
    # estrutural (F4b — incident-responder)
    "target_present", "doc_parses", "fields_complete", "timeline_ordered", "durations_valid",
    "rollback_documented", "followups_actionable", "no_placeholder_gaming",
    "handler_kind", "status", "requires_human_review",
)


@register("spec_executor")
def _g_spec_executor(out, exp):
    if not out:
        return False
    for key in _SIGNAL_KEYS:
        if key in exp and out.get(key) != exp[key]:
            return False
    return True
