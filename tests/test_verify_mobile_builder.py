"""Regressão VERIFY-IN-EVAL F4d para `g3-mobile-builder`.

O agente mobile não deve continuar como contrato genérico `spec_driven`: o eval precisa
forçar artefatos `{files}` com oráculo held-out, e o handler `spec_executor` deve re-derivar
os sinais estáticos via `verify_code` sem creditar delivery offline.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

import yaml
from langgraph.checkpoint.memory import MemorySaver

from nucleo.kernel.brain import Brain, FileStore
from nucleo.kernel.providers.llm import get_llm
from nucleo.quality.eval_harness import run_evals

ROOT = Path(__file__).resolve().parents[1]
AGENT_DIR = ROOT / "nucleo/guilds/g03_engenharia/g3-mobile-builder"


class VerifyMobileBuilderTest(unittest.TestCase):
    def test_mobile_builder_is_spec_executor_with_heldout_oracles(self):
        spec = yaml.safe_load((AGENT_DIR / "spec.yaml").read_text(encoding="utf-8"))
        self.assertEqual(spec["act_handler"], "spec_executor")

        cases = json.loads((AGENT_DIR / "evals/cases.json").read_text(encoding="utf-8"))
        self.assertEqual(len(cases), 30)

        unique_bug_files = set()
        for case in cases:
            self.assertEqual(case["artifact_type"], "mobile_builder.artifact")
            self.assertIn("files", case["artifact"])
            self.assertIn("seed", case)
            oracle = case["oracle"]
            self.assertEqual(oracle.get("runtime"), "node")
            self.assertIn("heldout_files", oracle)
            self.assertTrue(oracle["heldout_files"])
            self.assertFalse(set(case["artifact"]["files"]) & set(oracle["heldout_files"]))
            unique_bug_files.add(oracle["bug_file"])
            exp = case["expected"]
            self.assertEqual(exp["handler_kind"], "spec_executor")
            self.assertTrue(exp["static_ok"])
            self.assertFalse(exp["delivered_ok"])
            self.assertEqual(exp["status"], "verified_static")
            self.assertEqual(exp["tests_pass"], "UNVERIFIED")

        self.assertGreaterEqual(len(unique_bug_files), 3)

    def test_mobile_builder_eval_suite_passes_with_oracle_signals(self):
        brain = Brain(str(ROOT / "nucleo/.brain-test-mobile/events"))
        store = FileStore(str(ROOT / "nucleo/.brain-test-mobile/store"))
        result = run_evals(str(AGENT_DIR), get_llm("worker"), brain, store, MemorySaver())
        self.assertEqual(result["act_handler"], "spec_executor")
        self.assertTrue(result["grader_specific"])
        self.assertEqual((result["passed"], result["total"]), (30, 30))


if __name__ == "__main__":
    unittest.main()
