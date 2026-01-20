"""
Testes para as análises estatísticas da Fase 2.

Testa as funcionalidades de:
- Bootstrap e Monte Carlo
- Análise de gaps geométricos
- Autocorrelação temporal
- Clusterização (K-Means e DBSCAN)
"""

import pytest
import pandas as pd
import numpy as np
from app.core.statistics.monte_carlo import (
    bootstrap_ic_soma,
    monte_carlo_probabilidade_acerto,
)
from app.core.statistics.similarity import (
    analisar_gaps_geometricos,
    analisar_gaps_todos_numeros,
)
from app.core.statistics.temporal import (
    calcular_autocorrelacao_frequencias,
    detectar_tendencia_frequencia,
)
from app.core.statistics.clustering import (
    extrair_features_jogo,
    clusterizar_jogos_kmeans,
    clusterizar_jogos_dbscan,
    encontrar_numero_otimo_clusters,
)
from app.core.lottery.catalog import MEGASENA, LOTOFACIL


@pytest.fixture
def df_mock():
    """DataFrame mock com 200 sorteios simulados da Mega-Sena."""
    np.random.seed(42)
    data = []
    for i in range(200):
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
    """DataFrame mock com 100 sorteios simulados da Lotofácil."""
    np.random.seed(123)
    data = []
    for i in range(100):
        nums = sorted(np.random.choice(range(1, 26), size=15, replace=False))
        row = {'Concurso': i + 1}
        for j, num in enumerate(nums, 1):
            row[f'D{j}'] = num
        data.append(row)
    return pd.DataFrame(data).set_index('Concurso')


class TestBootstrap:
    """Testes para Bootstrap IC."""
    
    def test_retorna_dicionario(self, df_mock):
        resultado = bootstrap_ic_soma(df_mock, MEGASENA, n_iteracoes=100, random_state=42)
        assert isinstance(resultado, dict)
    
    def test_estrutura_resultado(self, df_mock):
        resultado = bootstrap_ic_soma(df_mock, MEGASENA, n_iteracoes=100, random_state=42)
        assert 'media_bootstrap' in resultado
        assert 'std_bootstrap' in resultado
        assert 'ic_lower' in resultado
        assert 'ic_upper' in resultado
        assert 'nivel_confianca' in resultado
        assert 'n_iteracoes' in resultado
        assert 'mediana_bootstrap' in resultado
    
    def test_ic_valido(self, df_mock):
        resultado = bootstrap_ic_soma(df_mock, MEGASENA, n_iteracoes=100, random_state=42)
        assert resultado['ic_lower'] < resultado['ic_upper']
    
    def test_dataframe_vazio(self):
        df_empty = pd.DataFrame()
        resultado = bootstrap_ic_soma(df_empty, MEGASENA, n_iteracoes=100)
        assert resultado is None
    
    def test_nivel_confianca_custom(self, df_mock):
        resultado = bootstrap_ic_soma(df_mock, MEGASENA, n_iteracoes=100, nivel_confianca=0.90, random_state=42)
        assert resultado['nivel_confianca'] == 0.90


class TestMonteCarlo:
    """Testes para Monte Carlo."""
    
    def test_retorna_dicionario(self, df_mock):
        numeros = [5, 12, 23, 34, 45, 56]
        resultado = monte_carlo_probabilidade_acerto(df_mock, MEGASENA, numeros, n_simulacoes=1000, random_state=42)
        assert isinstance(resultado, dict)
    
    def test_estrutura_resultado(self, df_mock):
        numeros = [5, 12, 23, 34, 45, 56]
        resultado = monte_carlo_probabilidade_acerto(df_mock, MEGASENA, numeros, n_simulacoes=1000, random_state=42)
        assert 'distribuicao_acertos' in resultado
        assert 'probabilidades' in resultado
        assert 'n_simulacoes' in resultado
        assert 'esperanca_acertos' in resultado
    
    def test_probabilidades_somam_um(self, df_mock):
        numeros = [5, 12, 23, 34, 45, 56]
        resultado = monte_carlo_probabilidade_acerto(df_mock, MEGASENA, numeros, n_simulacoes=1000, random_state=42)
        soma_prob = sum(resultado['probabilidades'].values())
        assert abs(soma_prob - 1.0) < 0.01
    
    def test_esperanca_valida(self, df_mock):
        numeros = [5, 12, 23, 34, 45, 56]
        resultado = monte_carlo_probabilidade_acerto(df_mock, MEGASENA, numeros, n_simulacoes=1000, random_state=42)
        assert 0 <= resultado['esperanca_acertos'] <= MEGASENA.k


class TestGapGeometrico:
    """Testes para análise de gaps geométricos."""
    
    def test_retorna_dicionario(self, df_mock):
        resultado = analisar_gaps_geometricos(df_mock, MEGASENA, numero=7)
        assert isinstance(resultado, dict)
    
    def test_estrutura_resultado(self, df_mock):
        resultado = analisar_gaps_geometricos(df_mock, MEGASENA, numero=7)
        if 'erro' not in resultado:
            assert 'numero' in resultado
            assert 'gaps' in resultado
            assert 'n_gaps' in resultado
            assert 'media_gap' in resultado
            assert 'std_gap' in resultado
            assert 'media_teorica' in resultado
            assert 'p_teorico' in resultado
            assert 'ks_statistic' in resultado
            assert 'ks_pvalue' in resultado
            assert 'conclusao' in resultado
    
    def test_numero_invalido(self, df_mock):
        resultado = analisar_gaps_geometricos(df_mock, MEGASENA, numero=0)
        assert resultado is None
        
        resultado = analisar_gaps_geometricos(df_mock, MEGASENA, numero=100)
        assert resultado is None
    
    def test_dataframe_vazio(self):
        df_empty = pd.DataFrame()
        resultado = analisar_gaps_geometricos(df_empty, MEGASENA, numero=7)
        assert resultado is None
    
    def test_todos_numeros(self, df_mock):
        resultado = analisar_gaps_todos_numeros(df_mock, MEGASENA)
        assert 'resultados_por_numero' in resultado
        assert 'numeros_anomalos' in resultado
        assert 'total_anomalos' in resultado
        assert 'percentual_anomalos' in resultado


class TestAutocorrelacao:
    """Testes para autocorrelação temporal."""
    
    def test_retorna_dicionario(self, df_mock):
        resultado = calcular_autocorrelacao_frequencias(df_mock, MEGASENA, max_lag=20, janela=10)
        assert isinstance(resultado, dict)
    
    def test_estrutura_resultado(self, df_mock):
        resultado = calcular_autocorrelacao_frequencias(df_mock, MEGASENA, max_lag=20, janela=10)
        if resultado:
            assert 'autocorrelacoes' in resultado
            assert 'lags' in resultado
            assert 'limite_significancia' in resultado
            assert 'lags_significativos' in resultado
            assert 'ciclo_detectado' in resultado
            assert 'n_janelas' in resultado
            assert 'tamanho_janela' in resultado
    
    def test_dataframe_pequeno(self, df_mock):
        df_small = df_mock.head(10)
        resultado = calcular_autocorrelacao_frequencias(df_small, MEGASENA, max_lag=20, janela=10)
        assert resultado is None
    
    def test_dataframe_vazio(self):
        df_empty = pd.DataFrame()
        resultado = calcular_autocorrelacao_frequencias(df_empty, MEGASENA)
        assert resultado is None


class TestTendencia:
    """Testes para detecção de tendência."""
    
    def test_retorna_dicionario(self, df_mock):
        resultado = detectar_tendencia_frequencia(df_mock, MEGASENA, numero=15, janela=50)
        assert isinstance(resultado, dict)
    
    def test_estrutura_resultado(self, df_mock):
        resultado = detectar_tendencia_frequencia(df_mock, MEGASENA, numero=15, janela=50)
        if resultado:
            assert 'numero' in resultado
            assert 'slope' in resultado
            assert 'r_squared' in resultado
            assert 'p_value' in resultado
            assert 'tendencia' in resultado
            assert 'frequencias_janela' in resultado
    
    def test_dataframe_pequeno(self, df_mock):
        df_small = df_mock.head(50)
        resultado = detectar_tendencia_frequencia(df_small, MEGASENA, numero=15, janela=50)
        assert resultado is None
    
    def test_dataframe_vazio(self):
        df_empty = pd.DataFrame()
        resultado = detectar_tendencia_frequencia(df_empty, MEGASENA, numero=15)
        assert resultado is None


class TestFeatureExtraction:
    """Testes para extração de features."""
    
    def test_retorna_array(self):
        features = extrair_features_jogo([5, 12, 23, 34, 45, 56], MEGASENA)
        assert isinstance(features, np.ndarray)
    
    def test_dimensao_correta(self):
        features = extrair_features_jogo([5, 12, 23, 34, 45, 56], MEGASENA)
        assert len(features) == 9
    
    def test_valores_validos(self):
        features = extrair_features_jogo([5, 12, 23, 34, 45, 56], MEGASENA)
        # Todas as features devem ser numéricas
        assert all(isinstance(f, (int, float, np.number)) for f in features)


class TestKMeans:
    """Testes para clusterização K-Means."""
    
    def test_retorna_dicionario(self, df_mock):
        jogos = [row[MEGASENA.draw_cols].tolist() for idx, row in df_mock.head(50).iterrows()]
        resultado = clusterizar_jogos_kmeans(jogos, MEGASENA, n_clusters=3, random_state=42)
        assert isinstance(resultado, dict)
    
    def test_estrutura_resultado(self, df_mock):
        jogos = [row[MEGASENA.draw_cols].tolist() for idx, row in df_mock.head(50).iterrows()]
        resultado = clusterizar_jogos_kmeans(jogos, MEGASENA, n_clusters=3, random_state=42)
        if 'erro' not in resultado:
            assert 'labels' in resultado
            assert 'n_clusters' in resultado
            assert 'silhouette_score' in resultado
            assert 'distribuicao' in resultado
            assert 'centroides' in resultado
            assert 'feature_names' in resultado
    
    def test_poucos_jogos(self):
        jogos = [[1, 2, 3, 4, 5, 6]]
        resultado = clusterizar_jogos_kmeans(jogos, MEGASENA, n_clusters=3)
        assert 'erro' in resultado
    
    def test_numero_clusters(self, df_mock):
        jogos = [row[MEGASENA.draw_cols].tolist() for idx, row in df_mock.head(50).iterrows()]
        resultado = clusterizar_jogos_kmeans(jogos, MEGASENA, n_clusters=3, random_state=42)
        if 'erro' not in resultado:
            assert resultado['n_clusters'] == 3
            assert len(resultado['centroides']) <= 3


class TestDBSCAN:
    """Testes para clusterização DBSCAN."""
    
    def test_retorna_dicionario(self, df_mock):
        jogos = [row[MEGASENA.draw_cols].tolist() for idx, row in df_mock.head(50).iterrows()]
        resultado = clusterizar_jogos_dbscan(jogos, MEGASENA, eps=0.5, min_samples=3)
        assert isinstance(resultado, dict)
    
    def test_estrutura_resultado(self, df_mock):
        jogos = [row[MEGASENA.draw_cols].tolist() for idx, row in df_mock.head(50).iterrows()]
        resultado = clusterizar_jogos_dbscan(jogos, MEGASENA, eps=0.5, min_samples=3)
        if 'erro' not in resultado:
            assert 'labels' in resultado
            assert 'n_clusters' in resultado
            assert 'n_outliers' in resultado
            assert 'indices_outliers' in resultado
            assert 'jogos_outliers' in resultado
            assert 'distribuicao' in resultado
    
    def test_poucos_jogos(self):
        jogos = [[1, 2, 3, 4, 5, 6]]
        resultado = clusterizar_jogos_dbscan(jogos, MEGASENA, eps=0.5, min_samples=5)
        assert 'erro' in resultado


class TestNumeroOtimoClusters:
    """Testes para encontrar número ótimo de clusters."""
    
    def test_retorna_dicionario(self, df_mock):
        jogos = [row[MEGASENA.draw_cols].tolist() for idx, row in df_mock.head(30).iterrows()]
        resultado = encontrar_numero_otimo_clusters(jogos, MEGASENA, k_min=2, k_max=5)
        assert isinstance(resultado, dict)
    
    def test_estrutura_resultado(self, df_mock):
        jogos = [row[MEGASENA.draw_cols].tolist() for idx, row in df_mock.head(30).iterrows()]
        resultado = encontrar_numero_otimo_clusters(jogos, MEGASENA, k_min=2, k_max=5)
        assert 'k_range' in resultado
        assert 'inercias' in resultado
        assert 'silhouettes' in resultado
        assert 'k_otimo_silhouette' in resultado
        assert 'melhor_silhouette' in resultado
    
    def test_tamanhos_listas(self, df_mock):
        jogos = [row[MEGASENA.draw_cols].tolist() for idx, row in df_mock.head(30).iterrows()]
        resultado = encontrar_numero_otimo_clusters(jogos, MEGASENA, k_min=2, k_max=5)
        assert len(resultado['k_range']) == len(resultado['inercias'])
        assert len(resultado['k_range']) == len(resultado['silhouettes'])


class TestIntegracaoLotofacil:
    """Testes de integração com Lotofácil."""
    
    def test_bootstrap_lotofacil(self, df_mock_lotofacil):
        resultado = bootstrap_ic_soma(df_mock_lotofacil, LOTOFACIL, n_iteracoes=100, random_state=42)
        assert isinstance(resultado, dict)
        assert 'ic_lower' in resultado
    
    def test_gaps_lotofacil(self, df_mock_lotofacil):
        resultado = analisar_gaps_geometricos(df_mock_lotofacil, LOTOFACIL, numero=10)
        assert isinstance(resultado, dict)
    
    def test_clustering_lotofacil(self, df_mock_lotofacil):
        jogos = [row[LOTOFACIL.draw_cols].tolist() for idx, row in df_mock_lotofacil.head(30).iterrows()]
        resultado = clusterizar_jogos_kmeans(jogos, LOTOFACIL, n_clusters=3, random_state=42)
        assert isinstance(resultado, dict)
