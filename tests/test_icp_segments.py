import unittest

from nucleo.kernel.skills import _score_lead_against_icp


class ICPSegmentScoringTest(unittest.TestCase):
    def test_ceo_bombeiro_segment_qualifies_from_1m_to_20m_yearly_revenue(self):
        lead = {
            "revenue_brl_year": 18_000_000,
            "founder_led": True,
            "sells_well": True,
            "lacks_process": True,
            "firefighter": True,
        }

        score, signals, reasons = _score_lead_against_icp(lead)

        self.assertGreaterEqual(score, 60)
        self.assertTrue(signals["segmento_ceo_bombeiro_1a20M"])
        self.assertIn("ceo_bombeiro", signals["icp_segments"])
        self.assertTrue(any("R$1-20M" in reason for reason in reasons))

    def test_enterprise_segment_qualifies_around_100m_with_process_pain(self):
        lead = {
            "revenue_brl_year": 100_000_000,
            "enterprise": True,
            "sells_well": True,
            "lacks_process": True,
            "firefighter": False,
            "ops_mature": False,
        }

        score, signals, reasons = _score_lead_against_icp(lead)

        self.assertGreaterEqual(score, 60)
        self.assertTrue(signals["segmento_enterprise_100M"])
        self.assertIn("enterprise_100M", signals["icp_segments"])
        self.assertTrue(any("R$100M" in reason for reason in reasons))

    def test_mature_enterprise_without_process_pain_is_disqualified(self):
        lead = {
            "revenue_brl_year": 100_000_000,
            "enterprise": True,
            "sells_well": True,
            "lacks_process": False,
            "ops_mature": True,
        }

        score, signals, reasons = _score_lead_against_icp(lead)

        self.assertLess(score, 60)
        self.assertTrue(signals["ops_madura"])
        self.assertTrue(any("madura" in reason.lower() for reason in reasons))


if __name__ == "__main__":
    unittest.main()
