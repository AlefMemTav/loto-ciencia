"""
Testes para as novas funcionalidades de validação avançada de bilhetes.

Testa as funcionalidades implementadas na Issue #8:
- Distribuição de gaps (KS test)
- Min-gap e span
- Order statistics
- Entropia em faixas
- Detecção de motifs
- Simetria por reflexão
"""

import pytest
from app.core.statistics import (
    testar_distribuicao_gaps_bilhete,
    calcular_min_gap_e_span,
    calcular_order_statistics,
    calcular_entropia_faixas,
    detectar_motifs_gaps,
    calcular_simetria_reflexao,
)
from app.core.lottery.catalog import MEGASENA


class TestDistribuicaoGaps:
    """Testes para testar_distribuicao_gaps_bilhete."""
    
    def test_jogo_pequeno(self):
        """Deve retornar erro para jogo com menos de 3 números."""
        resultado = testar_distribuicao_gaps_bilhete([1, 2], MEGASENA)
        assert 'erro' in resultado
    
    def test_progressao_aritmetica(self):
        """Deve detectar progressão aritmética (gaps iguais)."""
        # 1, 6, 11, 16, 21, 26 (gaps: 5, 5, 5, 5, 5)
        resultado = testar_distribuicao_gaps_bilhete([1, 6, 11, 16, 21, 26], MEGASENA)
        assert resultado['penalidade'] >= 15
        assert '❌' in resultado['conclusao']
        assert resultado['cv_gaps'] == 0  # Coeficiente de variação zero
    
    def test_gaps_naturais(self):
        """Gaps variados devem ter baixa/zero penalidade."""
        # Gaps mais variados: 1, 5, 12, 23, 40, 58
        resultado = testar_distribuicao_gaps_bilhete([1, 5, 12, 23, 40, 58], MEGASENA)
        assert resultado['penalidade'] <= 5
        assert 'gaps' in resultado
        assert len(resultado['gaps']) == 5
    
    def test_estrutura_retorno(self):
        """Verifica estrutura do dicionário retornado."""
        resultado = testar_distribuicao_gaps_bilhete([3, 10, 22, 35, 48, 60], MEGASENA)
        assert 'gaps' in resultado
        assert 'gap_medio' in resultado
        assert 'gap_esperado' in resultado
        assert 'cv_gaps' in resultado
        assert 'ks_statistic' in resultado
        assert 'ks_pvalue' in resultado
        assert 'conclusao' in resultado
        assert 'penalidade' in resultado


class TestMinGapSpan:
    """Testes para calcular_min_gap_e_span."""
    
    def test_jogo_pequeno(self):
        """Deve retornar erro para jogo com menos de 2 números."""
        resultado = calcular_min_gap_e_span([5], MEGASENA)
        assert 'erro' in resultado
    
    def test_sequencia_consecutiva(self):
        """Números consecutivos devem ter min_gap = 1."""
        resultado = calcular_min_gap_e_span([10, 11, 12, 13, 14, 15], MEGASENA)
        assert resultado['min_gap'] == 1
        assert resultado['max_gap'] == 1
        assert resultado['span'] == 5
        assert resultado['compactacao'] == 'extrema'
    
    def test_numeros_dispersos(self):
        """Números dispersos devem ter gaps maiores."""
        resultado = calcular_min_gap_e_span([1, 20, 30, 40, 50, 60], MEGASENA)
        assert resultado['min_gap'] >= 9
        assert resultado['span'] == 59
        assert resultado['compactacao'] == 'normal'
    
    def test_span_relativo(self):
        """Span relativo deve estar entre 0 e 1."""
        resultado = calcular_min_gap_e_span([1, 30, 60], MEGASENA)
        assert 0 <= resultado['span_relativo'] <= 1
    
    def test_estrutura_retorno(self):
        """Verifica estrutura do dicionário retornado."""
        resultado = calcular_min_gap_e_span([5, 15, 25, 35, 45, 55], MEGASENA)
        assert 'min_gap' in resultado
        assert 'max_gap' in resultado
        assert 'span' in resultado
        assert 'span_relativo' in resultado
        assert 'gaps' in resultado
        assert 'compactacao' in resultado


class TestOrderStatistics:
    """Testes para calcular_order_statistics."""
    
    def test_distribuicao_uniforme(self):
        """Números uniformemente distribuídos devem ter baixa penalidade."""
        # Para Mega-Sena (60 números), 6 números esperados em:
        # posições aprox: 8.5, 17, 25.5, 34, 42.5, 51
        resultado = calcular_order_statistics([9, 17, 26, 34, 43, 51], MEGASENA)
        assert resultado['penalidade'] <= 3
    
    def test_distribuicao_atipica(self):
        """Números muito concentrados devem ter penalidade."""
        # Todos no começo
        resultado = calcular_order_statistics([1, 2, 3, 4, 5, 6], MEGASENA)
        assert resultado['penalidade'] > 0
    
    def test_estrutura_detalhes(self):
        """Verifica estrutura dos detalhes."""
        resultado = calcular_order_statistics([10, 20, 30, 40, 50, 60], MEGASENA)
        assert 'detalhes' in resultado
        assert len(resultado['detalhes']) == 6
        
        for detalhe in resultado['detalhes']:
            assert 'posicao' in detalhe
            assert 'numero' in detalhe
            assert 'esperado' in detalhe
            assert 'desvio' in detalhe
            assert 'desvio_relativo' in detalhe
    
    def test_desvio_medio(self):
        """Desvio médio deve ser numérico."""
        resultado = calcular_order_statistics([5, 15, 25, 35, 45, 55], MEGASENA)
        assert isinstance(resultado['desvio_medio'], float)
        assert resultado['desvio_medio'] >= 0


class TestEntropiaFaixas:
    """Testes para calcular_entropia_faixas."""
    
    def test_concentracao_extrema(self):
        """Todos números em uma faixa devem ter alta penalidade."""
        # Todos entre 1-6 (primeira faixa)
        resultado = calcular_entropia_faixas([1, 2, 3, 4, 5, 6], MEGASENA, n_faixas=10)
        assert resultado['penalidade'] > 0
        assert resultado['entropia_normalizada'] < 0.5
        assert resultado['faixas_vazias'] >= 8
    
    def test_distribuicao_uniforme(self):
        """Números bem distribuídos devem ter baixa penalidade."""
        # Um número de cada faixa (60/10 = 6 por faixa)
        # Pegando um de cada: 3, 9, 15, 21, 27, 33
        resultado = calcular_entropia_faixas([3, 9, 15, 21, 27, 33], MEGASENA, n_faixas=10)
        assert resultado['penalidade'] == 0
        assert resultado['entropia_normalizada'] >= 0.9
    
    def test_estrutura_retorno(self):
        """Verifica estrutura do dicionário retornado."""
        resultado = calcular_entropia_faixas([10, 20, 30, 40, 50, 60], MEGASENA)
        assert 'entropia' in resultado
        assert 'entropia_maxima' in resultado
        assert 'entropia_normalizada' in resultado
        assert 'distribuicao' in resultado
        assert 'faixas_vazias' in resultado
        assert 'conclusao' in resultado
        assert 'penalidade' in resultado
    
    def test_entropia_normalizada_range(self):
        """Entropia normalizada deve estar entre 0 e 1."""
        resultado = calcular_entropia_faixas([5, 15, 25, 35, 45, 55], MEGASENA)
        assert 0 <= resultado['entropia_normalizada'] <= 1


class TestDetectarMotifs:
    """Testes para detectar_motifs_gaps."""
    
    def test_jogo_pequeno(self):
        """Jogos com menos de 4 números não devem detectar motifs."""
        resultado = detectar_motifs_gaps([1, 10, 20])
        assert not resultado['motif_detectado']
        assert resultado['penalidade'] == 0
    
    def test_progressao_aritmetica(self):
        """Deve detectar progressão aritmética."""
        resultado = detectar_motifs_gaps([5, 10, 15, 20, 25, 30])
        assert resultado['motif_detectado']
        assert resultado['penalidade'] == 20
        assert 'Progressão aritmética' in resultado['tipo_motif']
    
    def test_alternancia(self):
        """Deve detectar alternância [a, b, a, b, ...]."""
        # Gaps: 2, 5, 2, 5, 2
        resultado = detectar_motifs_gaps([1, 3, 8, 10, 15, 17])
        assert resultado['motif_detectado']
        assert resultado['penalidade'] == 15
        assert 'Alternância' in resultado['tipo_motif']
    
    def test_sem_motif(self):
        """Gaps variados não devem detectar motifs."""
        resultado = detectar_motifs_gaps([1, 5, 12, 23, 40, 58])
        assert not resultado['motif_detectado']
        assert resultado['penalidade'] == 0
    
    def test_retorna_gaps(self):
        """Deve retornar lista de gaps."""
        resultado = detectar_motifs_gaps([10, 15, 22, 30, 45])
        assert 'gaps' in resultado
        assert len(resultado['gaps']) == 4


class TestSimetriaReflexao:
    """Testes para calcular_simetria_reflexao."""
    
    def test_sem_simetria(self):
        """Jogo sem pares simétricos não deve ter penalidade."""
        resultado = calcular_simetria_reflexao([1, 10, 20, 30, 40, 50], MEGASENA)
        assert resultado['n_pares'] == 0
        assert resultado['penalidade'] == 0
        assert '✅' in resultado['conclusao']
    
    def test_um_par_simetrico(self):
        """Um par simétrico deve ter penalidade moderada."""
        # N=60: espelho de 1 é 60, espelho de 10 é 51
        resultado = calcular_simetria_reflexao([1, 10, 20, 30, 40, 60], MEGASENA)
        assert resultado['n_pares'] == 1
        assert resultado['penalidade'] == 5
        assert (1, 60) in resultado['pares_simetricos']
    
    def test_multiplos_pares(self):
        """Múltiplos pares simétricos devem ter alta penalidade."""
        # Espelhos: 1-60, 10-51
        resultado = calcular_simetria_reflexao([1, 10, 20, 51, 55, 60], MEGASENA)
        assert resultado['n_pares'] == 2
        assert resultado['penalidade'] == 15
        assert '🚨' in resultado['conclusao']
    
    def test_taxa_simetria(self):
        """Taxa de simetria deve estar entre 0 e 1."""
        resultado = calcular_simetria_reflexao([1, 15, 30, 46, 60], MEGASENA)
        assert 0 <= resultado['taxa_simetria'] <= 1
    
    def test_estrutura_retorno(self):
        """Verifica estrutura do dicionário retornado."""
        resultado = calcular_simetria_reflexao([5, 15, 25, 35, 45, 55], MEGASENA)
        assert 'pares_simetricos' in resultado
        assert 'n_pares' in resultado
        assert 'numeros_com_espelho' in resultado
        assert 'taxa_simetria' in resultado
        assert 'conclusao' in resultado
        assert 'penalidade' in resultado
    
    def test_numero_auto_espelho(self):
        """Verifica comportamento com pares espelho centrais."""
        # Para N=60, espelho de 30 é 31 (61-30=31, 61-31=30)
        # Eles formam um par válido
        resultado = calcular_simetria_reflexao([30, 31], MEGASENA)
        # 30 e 31 SÃO espelhos em N=60
        assert resultado['n_pares'] == 1
        assert (30, 31) in resultado['pares_simetricos']


class TestIntegracaoValidator:
    """Testes de integração com o validador."""
    
    def test_validador_com_novas_analises(self):
        """Validador deve incluir novas métricas."""
        from app.core.validator import validar_jogo
        
        numeros = [10, 20, 30, 40, 50, 60]
        report = validar_jogo(numeros, MEGASENA)
        
        # Verifica que novas métricas estão presentes
        assert 'metricas' in report
        metricas = report['metricas']
        
        # Métricas de span e gaps
        assert 'span' in metricas
        assert 'span_relativo' in metricas
        assert 'min_gap' in metricas
        
        # Outras métricas novas
        assert 'pares_simetricos' in metricas
        assert 'desvio_posicional' in metricas
        assert 'entropia_faixas' in metricas
        assert 'faixas_vazias' in metricas
    
    def test_penalizacao_progressao_aritmetica(self):
        """Validador deve penalizar progressão aritmética."""
        from app.core.validator import validar_jogo
        
        # Progressão aritmética severa
        numeros_ruins = [5, 10, 15, 20, 25, 30]
        report_ruim = validar_jogo(numeros_ruins, MEGASENA)
        
        # Números variados
        numeros_bons = [3, 15, 27, 34, 49, 58]
        report_bom = validar_jogo(numeros_bons, MEGASENA)
        
        # Score de progressão aritmética deve ser pior
        assert report_ruim['score'] < report_bom['score']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
