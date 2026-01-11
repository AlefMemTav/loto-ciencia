"""
Testes para o módulo de análises estatísticas avançadas.

Testa as funcionalidades de:
- Matriz de co-ocorrência
- Cadeias de Markov
- Teste de Runs (Wald-Wolfowitz)
- Índice de Dispersão (VMR)
"""

import pytest
import pandas as pd
import numpy as np
from app.core.statistics.advanced import (
    matriz_coocorrencia_numeros,
    get_pares_mais_frequentes,
    get_pares_que_se_repelem,
    calcular_matriz_transicao,
    analisar_transicoes_anomalas,
    teste_runs_numero,
    teste_runs_todos_numeros,
    indice_dispersao,
)
from app.core.lottery.catalog import MEGASENA, LOTOFACIL


@pytest.fixture
def df_mock():
    """DataFrame mock com 100 sorteios simulados da Mega-Sena."""
    np.random.seed(42)
    data = []
    for i in range(100):
        nums = sorted(np.random.choice(range(1, 61), size=6, replace=False))
        data.append({
            'Concurso': i + 1,
            'D1': nums[0],
            'D2': nums[1],
            'D3': nums[2],
            'D4': nums[3],
            'D5': nums[4],
            'D6': nums[5],
        })
    return pd.DataFrame(data).set_index('Concurso')


@pytest.fixture
def df_mock_lotofacil():
    """DataFrame mock com 50 sorteios simulados da Lotofácil."""
    np.random.seed(123)
    data = []
    for i in range(50):
        nums = sorted(np.random.choice(range(1, 26), size=15, replace=False))
        row = {'Concurso': i + 1}
        for j, num in enumerate(nums, 1):
            row[f'D{j}'] = num
        data.append(row)
    return pd.DataFrame(data).set_index('Concurso')


class TestMatrizCoocorrencia:
    """Testes para matriz de co-ocorrência."""
    
    def test_retorna_matriz_correta(self, df_mock):
        matriz = matriz_coocorrencia_numeros(df_mock, MEGASENA)
        assert matriz.shape == (60, 60)
        assert np.all(matriz >= 0)
    
    def test_diagonal_zero(self, df_mock):
        matriz = matriz_coocorrencia_numeros(df_mock, MEGASENA)
        # Diagonal deve ser zero (número não co-ocorre consigo mesmo)
        assert np.all(np.diag(matriz) == 0)
    
    def test_simetria(self, df_mock):
        matriz = matriz_coocorrencia_numeros(df_mock, MEGASENA)
        # Matriz deve ser simétrica
        assert np.allclose(matriz, matriz.T)
    
    def test_dataframe_vazio(self):
        df_empty = pd.DataFrame()
        matriz = matriz_coocorrencia_numeros(df_empty, MEGASENA)
        assert matriz.shape == (60, 60)
        assert np.all(matriz == 0)


class TestParesFrequentes:
    """Testes para pares mais frequentes."""
    
    def test_retorna_lista(self, df_mock):
        pares = get_pares_mais_frequentes(df_mock, MEGASENA, top_n=10)
        assert isinstance(pares, list)
        assert len(pares) <= 10
    
    def test_estrutura_resultado(self, df_mock):
        pares = get_pares_mais_frequentes(df_mock, MEGASENA, top_n=5)
        for par in pares:
            assert 'par' in par
            assert 'ocorrencias' in par
            assert 'razao' in par
            assert isinstance(par['par'], tuple)
            assert len(par['par']) == 2
    
    def test_ordem_decrescente(self, df_mock):
        pares = get_pares_mais_frequentes(df_mock, MEGASENA, top_n=20)
        if len(pares) > 1:
            # Verifica ordem decrescente de ocorrências
            for i in range(len(pares) - 1):
                assert pares[i]['ocorrencias'] >= pares[i + 1]['ocorrencias']
    
    def test_dataframe_vazio(self):
        df_empty = pd.DataFrame()
        pares = get_pares_mais_frequentes(df_empty, MEGASENA, top_n=10)
        assert pares == []


class TestParesRepelem:
    """Testes para pares que se repelem."""
    
    def test_retorna_lista(self, df_mock):
        pares = get_pares_que_se_repelem(df_mock, MEGASENA, top_n=10)
        assert isinstance(pares, list)
        assert len(pares) <= 10
    
    def test_estrutura_resultado(self, df_mock):
        pares = get_pares_que_se_repelem(df_mock, MEGASENA, top_n=5)
        for par in pares:
            assert 'par' in par
            assert 'ocorrencias' in par
            assert 'razao' in par
    
    def test_ordem_crescente(self, df_mock):
        pares = get_pares_que_se_repelem(df_mock, MEGASENA, top_n=20)
        if len(pares) > 1:
            # Verifica ordem crescente de ocorrências
            for i in range(len(pares) - 1):
                assert pares[i]['ocorrencias'] <= pares[i + 1]['ocorrencias']


class TestMatrizTransicao:
    """Testes para matriz de transição de Markov."""
    
    def test_retorna_matriz_probabilidades(self, df_mock):
        matriz = calcular_matriz_transicao(df_mock, MEGASENA)
        assert matriz.shape == (60, 60)
        # Cada linha deve somar aproximadamente 1
        somas = matriz.sum(axis=1)
        assert np.allclose(somas[somas > 0], 1, atol=0.01)
    
    def test_valores_entre_0_e_1(self, df_mock):
        matriz = calcular_matriz_transicao(df_mock, MEGASENA)
        assert np.all(matriz >= 0)
        assert np.all(matriz <= 1)
    
    def test_dataframe_vazio(self):
        df_empty = pd.DataFrame()
        matriz = calcular_matriz_transicao(df_empty, MEGASENA)
        assert matriz.shape == (60, 60)
        assert np.all(matriz == 0)
    
    def test_dataframe_com_um_sorteio(self, df_mock):
        df_single = df_mock.iloc[:1]
        matriz = calcular_matriz_transicao(df_single, MEGASENA)
        assert matriz.shape == (60, 60)


class TestTransicoesAnomalas:
    """Testes para análise de transições anômalas."""
    
    def test_retorna_lista(self, df_mock):
        anomalias = analisar_transicoes_anomalas(df_mock, MEGASENA, threshold_zscore=2.0)
        assert isinstance(anomalias, list)
    
    def test_estrutura_resultado(self, df_mock):
        anomalias = analisar_transicoes_anomalas(df_mock, MEGASENA, threshold_zscore=2.0)
        for anomalia in anomalias:
            assert 'de' in anomalia
            assert 'para' in anomalia
            assert 'observado' in anomalia
            assert 'esperado' in anomalia
            assert 'zscore' in anomalia
            assert 'tipo' in anomalia
            assert anomalia['tipo'] in ['excesso', 'deficit']
    
    def test_zscore_absoluto_acima_threshold(self, df_mock):
        threshold = 2.5
        anomalias = analisar_transicoes_anomalas(df_mock, MEGASENA, threshold_zscore=threshold)
        for anomalia in anomalias:
            assert abs(anomalia['zscore']) >= threshold
    
    def test_ordenacao_por_zscore(self, df_mock):
        anomalias = analisar_transicoes_anomalas(df_mock, MEGASENA, threshold_zscore=2.0)
        if len(anomalias) > 1:
            for i in range(len(anomalias) - 1):
                assert abs(anomalias[i]['zscore']) >= abs(anomalias[i + 1]['zscore'])


class TestTesteRuns:
    """Testes para teste de runs (Wald-Wolfowitz)."""
    
    def test_retorna_resultado_valido(self, df_mock):
        resultado = teste_runs_numero(df_mock, 7, MEGASENA)
        assert 'numero' in resultado
        assert resultado['numero'] == 7
        # Deve ter p_value ou erro
        assert 'p_value' in resultado or 'erro' in resultado
    
    def test_estrutura_resultado_completo(self, df_mock):
        resultado = teste_runs_numero(df_mock, 15, MEGASENA)
        if 'erro' not in resultado:
            assert 'n_aparicoes' in resultado
            assert 'n_ausencias' in resultado
            assert 'n_runs' in resultado
            assert 'n_runs_esperado' in resultado
            assert 'zscore' in resultado
            assert 'p_value' in resultado
            assert 'aleatorio' in resultado
            assert isinstance(resultado['aleatorio'], bool)
    
    def test_dataframe_vazio(self):
        df_empty = pd.DataFrame()
        resultado = teste_runs_numero(df_empty, 7, MEGASENA)
        assert 'erro' in resultado
    
    def test_todos_numeros(self, df_mock):
        resultado = teste_runs_todos_numeros(df_mock, MEGASENA)
        assert 'resultados' in resultado
        assert 'percentual_aleatorios' in resultado
        assert 'numeros_nao_aleatorios' in resultado
        assert 'resumo' in resultado
        assert len(resultado['resultados']) == 60
    
    def test_percentual_valido(self, df_mock):
        resultado = teste_runs_todos_numeros(df_mock, MEGASENA)
        assert 0 <= resultado['percentual_aleatorios'] <= 100
    
    def test_consistencia_nao_aleatorios(self, df_mock):
        resultado = teste_runs_todos_numeros(df_mock, MEGASENA)
        # Números não aleatórios devem estar nos resultados
        for num in resultado['numeros_nao_aleatorios']:
            # Encontra resultado deste número
            res_num = next(r for r in resultado['resultados'] if r['numero'] == num)
            assert 'erro' not in res_num
            assert not res_num['aleatorio']


class TestIndiceDispersao:
    """Testes para índice de dispersão (VMR)."""
    
    def test_retorna_vmr(self, df_mock):
        resultado = indice_dispersao(df_mock, MEGASENA)
        assert 'vmr' in resultado
        assert 'interpretacao' in resultado
    
    def test_vmr_positivo(self, df_mock):
        resultado = indice_dispersao(df_mock, MEGASENA)
        if 'erro' not in resultado:
            assert resultado['vmr'] > 0
    
    def test_estrutura_completa(self, df_mock):
        resultado = indice_dispersao(df_mock, MEGASENA)
        if 'erro' not in resultado:
            assert 'vmr' in resultado
            assert 'variancia' in resultado
            assert 'media' in resultado
            assert 'interpretacao' in resultado
            assert 'chi2_stat' in resultado
            assert 'p_value' in resultado
            assert 'dispersao_normal' in resultado
            assert isinstance(resultado['dispersao_normal'], bool)
    
    def test_dataframe_vazio(self):
        df_empty = pd.DataFrame()
        resultado = indice_dispersao(df_empty, MEGASENA)
        assert 'erro' in resultado
    
    def test_interpretacao_presente(self, df_mock):
        resultado = indice_dispersao(df_mock, MEGASENA)
        if 'erro' not in resultado:
            assert isinstance(resultado['interpretacao'], str)
            assert len(resultado['interpretacao']) > 0


class TestIntegracaoLotofacil:
    """Testes de integração com Lotofácil."""
    
    def test_matriz_coocorrencia_lotofacil(self, df_mock_lotofacil):
        matriz = matriz_coocorrencia_numeros(df_mock_lotofacil, LOTOFACIL)
        assert matriz.shape == (25, 25)
        assert np.all(matriz >= 0)
    
    def test_pares_lotofacil(self, df_mock_lotofacil):
        pares = get_pares_mais_frequentes(df_mock_lotofacil, LOTOFACIL, top_n=10)
        assert isinstance(pares, list)
        assert len(pares) <= 10
    
    def test_transicao_lotofacil(self, df_mock_lotofacil):
        matriz = calcular_matriz_transicao(df_mock_lotofacil, LOTOFACIL)
        assert matriz.shape == (25, 25)
    
    def test_runs_lotofacil(self, df_mock_lotofacil):
        resultado = teste_runs_numero(df_mock_lotofacil, 10, LOTOFACIL)
        assert 'numero' in resultado
    
    def test_vmr_lotofacil(self, df_mock_lotofacil):
        resultado = indice_dispersao(df_mock_lotofacil, LOTOFACIL)
        assert 'vmr' in resultado or 'erro' in resultado
