import unittest
import pandas as pd
from main import (
    verificar_quadrantes,
    validar_jogo,
    verificar_historico,
    get_numeros_quentes_frios,
)


class TestLotoScience(unittest.TestCase):

    def setUp(self):
        """Cria um Banco de Dados falso (Mock) para os testes"""
        data = {
            "Concurso": [1, 2, 3],
            "Data": ["01/01/2020", "02/01/2020", "03/01/2020"],
            "D1": [1, 10, 99],  # Mudei o último de 5 para 99 para tirar o empate
            "D2": [2, 11, 15],
            "D3": [3, 12, 25],
            "D4": [4, 13, 35],
            "D5": [5, 14, 45],
            "D6": [
                6,
                15,
                55,
            ],  # O 15 aparece aqui e na D2 (Total: 2 vezes). O 5 agora só aparece 1 vez.
        }
        # Cria um DataFrame similar ao que seu app carrega do Excel
        self.df_mock = pd.DataFrame(data)

    # --- TESTE 1: MATEMÁTICA DOS QUADRANTES ---
    def test_verificar_quadrantes(self):
        # Caso A: Jogo concentrado no topo esquerdo (Q1)
        # Números: 1, 2, 3, 11, 12, 13
        # Esperado: [6, 0, 0, 0]
        jogo_q1 = [1, 2, 3, 11, 12, 13]
        resultado = verificar_quadrantes(jogo_q1)
        self.assertEqual(
            resultado, [6, 0, 0, 0], "Erro: Não identificou concentração no Q1"
        )

        # Caso B: Jogo Espalhado (Cruzado)
        # 1 (Q1), 6 (Q2), 31 (Q3), 36 (Q4), 11 (Q1), 16 (Q2)
        # Q1: 1, 11 (2 nums)
        # Q2: 6, 16 (2 nums)
        # Q3: 31 (1 num)
        # Q4: 36 (1 num)
        jogo_espalhado = [1, 6, 31, 36, 11, 16]
        resultado = verificar_quadrantes(jogo_espalhado)
        self.assertEqual(
            resultado, [2, 2, 1, 1], "Erro: Contagem de quadrantes incorreta"
        )

    # --- TESTE 2: VALIDADOR DE REGRAS (SCORE) ---
    def test_validar_jogo_ruim(self):
        # Jogo Horrível: 1, 2, 3, 4, 5, 6
        # Soma: 21 (Ruim)
        # Sequência: Total (Ruim)
        # Quadrante: Tudo no 1 (Ruim)
        jogo_ruim = [1, 2, 3, 4, 5, 6]
        report = validar_jogo(jogo_ruim)

        # O score deve ser baixo (menor que 50)
        self.assertLess(
            report["score"], 50, "Erro: Deu nota alta para um jogo horrível"
        )
        self.assertIn("❌", report["msgs"][0], "Erro: Não detectou soma ruim")

    def test_validar_jogo_bom(self):
        # Jogo Bom (Soma 186, Espalhado)
        # 04, 15, 22, 37, 49, 59
        jogo_bom = [4, 15, 22, 37, 49, 59]
        report = validar_jogo(jogo_bom)

        # O score deve ser alto (maior que 80)
        self.assertGreaterEqual(
            report["score"], 80, "Erro: Deu nota baixa para um jogo bom"
        )
        self.assertEqual(report["status"], "💎 Excelente (Científico)")

    # --- TESTE 3: HISTÓRICO (BACKTESTING) ---
    def test_verificar_historico(self):
        # No meu Mock (setUp), o Concurso 1 foi: 1, 2, 3, 4, 5, 6

        # Teste de Sena (Acertou tudo)
        sena, quina, quadra = verificar_historico([1, 2, 3, 4, 5, 6], self.df_mock)
        self.assertEqual(len(sena), 1, "Erro: Não detectou a Sena do histórico mockado")

        # Teste de Quina (Acertou 1, 2, 3, 4, 5 e errou o 6 jogando 99)
        sena, quina, quadra = verificar_historico([1, 2, 3, 4, 5, 99], self.df_mock)
        self.assertEqual(len(sena), 0)
        self.assertEqual(len(quina), 1, "Erro: Não detectou a Quina")

    # --- TESTE 4: QUENTES E FRIOS ---
    def test_quentes_frios(self):
        # No Mock:
        # 15 saiu no conc 2 e 3 (2 vezes)
        # 1 saiu só no conc 1 (1 vez)
        freq = get_numeros_quentes_frios(self.df_mock)

        # O número 15 deve estar no topo (mais frequente)
        self.assertEqual(freq.index[0], 15, "Erro: Calculo de frequência falhou")


if __name__ == "__main__":
    unittest.main()
