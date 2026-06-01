"""Guarda de regressão do scoring de ICP (company/icp.md — dois perfis, decisão CEO 2026-05-30).

Trava os 3 eixos que a materialização anterior havia estreitado: enterprise é faixa ABERTA
(> R$100M, não 80–130M fechado), setor público é alvo (qualifica independente de faturamento),
e os sinais enterprise (processos desorganizados / time grande / custo de pessoal) pontuam.
"""
import unittest

from nucleo.kernel.skills import _score_lead_against_icp


class ICPSegmentScoringTest(unittest.TestCase):
    def test_bombeiro_1m_a_20m_qualifica(self):
        score, signals, reasons = _score_lead_against_icp({
            "revenue_brl_year": 18_000_000, "founder_led": True,
            "sells_well": True, "lacks_process": True, "firefighter": True,
        })
        self.assertGreaterEqual(score, 60)
        self.assertEqual(signals["icp_tier"], "bombeiro")
        self.assertTrue(signals["faturamento_1a20M"])

    def test_enterprise_faixa_aberta_acima_de_130M_qualifica(self):
        # Regressão-guarda: > R$130M NÃO pode cair em "fora do ICP" (bug da faixa fechada).
        score, signals, _ = _score_lead_against_icp({
            "revenue_brl_year": 500_000_000, "process_disorganized": True, "large_team": True,
        })
        self.assertEqual(signals["icp_tier"], "enterprise")
        self.assertGreaterEqual(score, 60)

    def test_setor_publico_qualifica_independe_de_faturamento(self):
        # Regressão-guarda: setor público é alvo explícito, mesmo sem faturamento alto.
        score, signals, _ = _score_lead_against_icp({
            "revenue_brl_year": 0, "public_sector": True, "process_disorganized": True,
        })
        self.assertEqual(signals["icp_tier"], "enterprise")
        self.assertTrue(signals["setor_publico"])
        self.assertGreaterEqual(score, 60)

    def test_sinais_enterprise_pontuam(self):
        # Regressão-guarda: time grande + custo de pessoal alto devem somar pontos.
        score, signals, _ = _score_lead_against_icp({
            "revenue_brl_year": 200_000_000, "team_size": 80, "high_personnel_cost": True,
        })
        self.assertTrue(signals["time_grande"])
        self.assertTrue(signals["custo_pessoal_alto"])
        self.assertGreaterEqual(score, 60)

    def test_mid_market_20M_a_100M_fica_fora(self):
        score, signals, _ = _score_lead_against_icp({"revenue_brl_year": 50_000_000})
        self.assertEqual(signals["icp_tier"], "mid_market")
        self.assertLess(score, 60)

    def test_abaixo_de_1M_fica_fora(self):
        score, signals, _ = _score_lead_against_icp({"revenue_brl_year": 500_000})
        self.assertEqual(signals["icp_tier"], "fora")
        self.assertLess(score, 60)


if __name__ == "__main__":
    unittest.main()
