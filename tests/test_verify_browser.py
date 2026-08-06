"""Trava de regressão da natureza BROWSER/E2E (VERIFY-IN-EVAL F4c — g4-e2e-playwright).

Prova o oráculo `verify_browser` para suítes Playwright geradas como artefato:
  - suíte completa passa os necessários estáticos (teste alvo, import Playwright, navegação,
    assertions e evidência configurada);
  - cada invariante falha com `first_fail` correto;
  - invariantes anti-gaming pegam `test.skip`/`test.only`/`page.route`/placeholders;
  - natureza atual é ASSISTED: sem browser real no gate offline ⇒ tests_pass="N/A" e
    delivered_ok=False. A execução real em browser fica para uma fase posterior.
"""

from __future__ import annotations

import unittest

from nucleo.kernel.verification import verify_browser

ORACLE = {
    "browser": {
        "target": "tests/onboarding.spec.ts",
        "required_routes": ["/signup", "/dashboard"],
        "required_assertions": ["Bem-vindo", "data-testid=activation-complete"],
        "evidence": ["trace", "screenshot"],
    }
}
GOOD_TEST = """import { test, expect } from '@playwright/test';

test('fluxo de ativacao self-serve gera evidencia', async ({ page }) => {
  await page.goto('/signup');
  await expect(page.getByText('Bem-vindo')).toBeVisible();
  await page.getByRole('button', { name: 'Começar' }).click();
  await page.goto('/dashboard');
  await expect(page.locator('[data-testid=activation-complete]')).toBeVisible();
  await page.screenshot({ path: 'artifacts/activation.png', fullPage: true });
});
"""
GOOD_CONFIG = """import { defineConfig } from '@playwright/test';
export default defineConfig({
  use: { trace: 'on', screenshot: 'on', video: 'retain-on-failure' },
});
"""


def run(files: dict[str, str]):
    return verify_browser({"files": files}, ORACLE)


class BrowserSuiteCorreta(unittest.TestCase):
    def test_suite_playwright_completa_passa_estatico(self):
        r = run({"tests/onboarding.spec.ts": GOOD_TEST, "playwright.config.ts": GOOD_CONFIG})
        self.assertTrue(r["static_ok"])
        self.assertIsNone(r["first_fail"])
        self.assertTrue(r["signals"]["target_present"])
        self.assertTrue(r["signals"]["uses_playwright"])
        self.assertTrue(r["signals"]["routes_covered"])
        self.assertTrue(r["signals"]["assertions_present"])
        self.assertTrue(r["signals"]["evidence_configured"])

    def test_natureza_assisted_nunca_credita_delivered(self):
        r = run({"tests/onboarding.spec.ts": GOOD_TEST, "playwright.config.ts": GOOD_CONFIG})
        self.assertEqual(r["tests_pass"], "N/A")
        self.assertFalse(r["delivered_ok"])


class InvariantesBrowser(unittest.TestCase):
    def test_texto_livre_reprova(self):
        r = verify_browser({"summary": "roteiro em prosa"}, ORACLE)
        self.assertEqual(r["first_fail"], "artifact_parseable")

    def test_target_ausente_reprova(self):
        r = run({"tests/other.spec.ts": GOOD_TEST, "playwright.config.ts": GOOD_CONFIG})
        self.assertEqual(r["first_fail"], "target_present")

    def test_sem_import_playwright_reprova(self):
        r = run(
            {
                "tests/onboarding.spec.ts": "test('x', async ({ page }) => { await page.goto('/signup'); });"
            }
        )
        self.assertEqual(r["first_fail"], "uses_playwright")

    def test_sem_rota_obrigatoria_reprova(self):
        bad = GOOD_TEST.replace("await page.goto('/dashboard');", "")
        r = run({"tests/onboarding.spec.ts": bad, "playwright.config.ts": GOOD_CONFIG})
        self.assertEqual(r["first_fail"], "routes_covered")

    def test_sem_assertion_obrigatoria_reprova(self):
        bad = GOOD_TEST.replace("data-testid=activation-complete", "data-testid=almost")
        r = run({"tests/onboarding.spec.ts": bad, "playwright.config.ts": GOOD_CONFIG})
        self.assertEqual(r["first_fail"], "assertions_present")

    def test_sem_evidencia_reprova(self):
        r = run({"tests/onboarding.spec.ts": GOOD_TEST})
        self.assertEqual(r["first_fail"], "evidence_configured")

    def test_skip_only_route_mock_e_placeholder_reprovam(self):
        for token in ["test.skip(", "test.only(", "page.route(", "TODO"]:
            bad = GOOD_TEST + f"\n// {token}\n"
            r = run({"tests/onboarding.spec.ts": bad, "playwright.config.ts": GOOD_CONFIG})
            self.assertEqual(r["first_fail"], "no_browser_gaming", token)


if __name__ == "__main__":
    unittest.main()
