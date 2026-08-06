"""Guarda do diff_homogeneity — o tripwire mecânico contra gaming em massa.

Trava as duas assinaturas históricas: carimbo em massa de um campo (sinal A, #66-80) e casos
tautológicos clonados (sinal B, #30-32), sem disparar num agente que adiciona casos variados.
É TRIPWIRE, não matador-de-raiz: testa-se que ele PEGA o lote e DEIXA passar a variedade legítima.
"""

import unittest

from nucleo.quality import diff_homogeneity as dh


class SignalALineHomogeneityTest(unittest.TestCase):
    def test_carimbo_em_massa_dispara(self):
        # 20 casos recebendo a MESMA linha de provenance — assinatura do #66-80.
        diff = "+++ b/x/evals/cases.json\n" + "\n".join(
            ['+      "provenance": "independent",'] * 20
        )
        hits = dh.added_line_homogeneity(diff, threshold=12)
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0][1], 20)
        self.assertIn("provenance", hits[0][0])

    def test_punctuacao_estrutural_nao_dispara(self):
        diff = "+++ b/x.json\n" + "\n".join(["+  {", "+  },"] * 30)
        self.assertEqual(dh.added_line_homogeneity(diff, threshold=12), [])

    def test_abaixo_do_limiar_nao_dispara(self):
        diff = "+++ b/x.json\n" + "\n".join(['+      "provenance": "independent",'] * 5)
        self.assertEqual(dh.added_line_homogeneity(diff, threshold=12), [])

    def test_ignora_cabecalho_e_removidas(self):
        diff = "+++ b/x.json\n" + "\n".join(
            ['-      "provenance": "catalog",'] * 20
        )  # removidas não contam
        self.assertEqual(dh.added_line_homogeneity(diff, threshold=12), [])


class SignalBCloneClusterTest(unittest.TestCase):
    def _tautological(self, n):
        # mesma estrutura, valor praticamente igual (só o id varia) — #30-32.
        return [
            {"id": f"c{i}", "desc": f"caso {i}", "expected": {"ok": True, "ratio": 0.2}}
            for i in range(n)
        ]

    def _varied(self, n):
        # mesma estrutura, mas VALORES distintos — gerador honesto.
        return [
            {
                "id": f"v{i}",
                "desc": f"cenario {i}",
                "expected": {"ok": i % 2 == 0, "ratio": round(0.1 * i, 3)},
            }
            for i in range(n)
        ]

    def test_clones_tautologicos_disparam(self):
        flagged = dh.clone_clusters(self._tautological(20), min_size=10, diversity_floor=0.5)
        self.assertEqual(len(flagged), 1)
        self.assertEqual(flagged[0]["size"], 20)
        self.assertEqual(flagged[0]["distinct_values"], 1)  # id/desc excluídos -> 1 valor

    def test_casos_variados_nao_disparam(self):
        self.assertEqual(dh.clone_clusters(self._varied(20), min_size=10, diversity_floor=0.5), [])

    def test_cluster_pequeno_nao_dispara(self):
        self.assertEqual(dh.clone_clusters(self._tautological(8), min_size=10), [])

    def test_fingerprint_ignora_id_e_ordem_de_chave(self):
        a = {"id": "a", "expected": {"x": 1, "y": 2}}
        b = {"id": "b", "expected": {"y": 9, "x": 8}}  # mesma estrutura, valores e id diferentes
        self.assertEqual(dh.case_fingerprint(a), dh.case_fingerprint(b))

    def test_fingerprint_distingue_estrutura_diferente(self):
        a = {"id": "a", "expected": {"x": 1}}
        b = {"id": "b", "expected": {"x": 1, "z": 2}}
        self.assertNotEqual(dh.case_fingerprint(a), dh.case_fingerprint(b))

    def test_value_signature_exclui_id(self):
        a = {"id": "a", "expected": {"x": 1}}
        b = {"id": "b", "expected": {"x": 1}}
        self.assertEqual(dh.value_signature(a), dh.value_signature(b))


if __name__ == "__main__":
    unittest.main()
