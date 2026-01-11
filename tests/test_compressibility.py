"""
Testes para detectores de compressibilidade e raridade estrutural (Issue #10).

Testa as funcionalidades de:
- Detector de múltiplos de d
- Análise de primos com extremos
- Detector de quase-reta no grid
- Índice de compressibilidade
- Raridade conjunta
"""

import pytest
from app.core.statistics import detectar_multiplos_de_d, calcular_indice_compressibilidade
from app.core.validator import validar_jogo
from app.core.lottery.catalog import MEGASENA, LOTOFACIL


class TestDetectarMultiplos:
    """Testes para detector de múltiplos de d."""
    
    def test_todos_multiplos_de_5(self):
        """100% múltiplos de 5 deve ter penalidade máxima."""
        resultado = detectar_multiplos_de_d([5, 10, 15, 20, 25, 30], MEGASENA)
        assert resultado['divisor_dominante'] == 5
        assert resultado['fracao_maxima'] == 1.0
        assert resultado['penalidade'] >= 20
    
    def test_todos_pares(self):
        """Todos pares deve ter penalidade alta."""
        resultado = detectar_multiplos_de_d([2, 4, 6, 8, 10, 12], MEGASENA)
        assert resultado['divisor_dominante'] == 2
        assert resultado['fracao_maxima'] == 1.0
        assert resultado['penalidade'] >= 20
    
    def test_todos_multiplos_de_10(self):
        """Múltiplos de 10 são mais raros, penalidade máxima."""
        resultado = detectar_multiplos_de_d([10, 20, 30, 40, 50, 60], MEGASENA)
        assert resultado['divisor_dominante'] == 10
        assert resultado['fracao_maxima'] == 1.0
        assert resultado['penalidade'] >= 25
    
    def test_distribuicao_normal(self):
        """Jogo normal não deve ter penalidade."""
        resultado = detectar_multiplos_de_d([3, 17, 25, 38, 44, 59], MEGASENA)
        assert resultado['penalidade'] == 0


class TestPrimosExtremos:
    """Testes para análise de primos com extremos."""
    
    def test_todos_primos(self):
        """Todos primos deve ter penalidade severa."""
        report = validar_jogo([2, 3, 5, 7, 11, 13], MEGASENA)
        assert report['score'] < 75
        assert any('primos' in msg.lower() for msg in report['msgs'])
    
    def test_zero_primos(self):
        """Zero primos deve ser alertado."""
        report = validar_jogo([4, 6, 8, 10, 12, 14], MEGASENA)
        # Deve ter alerta sobre primos (mas também sobre pares)
        assert report['score'] < 80


class TestQuaseReta:
    """Testes para detector de quase-reta no grid."""
    
    def test_linha_concentrada_mega(self):
        """5+ na mesma linha deve penalizar."""
        # Linha 1 da Mega-Sena: 1-10
        report = validar_jogo([1, 2, 3, 4, 5, 6], MEGASENA)
        assert report['metricas'].get('max_numa_linha', 0) >= 5
        assert report['score'] < 70


class TestRaridadeConjunta:
    """Testes para penalidade de raridade conjunta."""
    
    def test_multiplos_alertas(self):
        """Jogo com múltiplos padrões raros deve ter penalidade extra."""
        # Progressão aritmética + todos múltiplos de 5
        report = validar_jogo([5, 10, 15, 20, 25, 30], MEGASENA)
        assert report['metricas'].get('alertas_estruturais', 0) >= 2
        assert report['score'] < 50


class TestIndiceCompressibilidade:
    """Testes para índice de compressibilidade."""
    
    def test_jogo_compressivel(self):
        """Jogo com padrões deve ter índice baixo."""
        report = validar_jogo([5, 10, 15, 20, 25, 30], MEGASENA)
        compressibilidade = report['metricas'].get('compressibilidade', {})
        # Should be less than 70 (not "Bom")
        assert compressibilidade.get('indice', 100) < 70
        # Should have multiple flags
        assert compressibilidade.get('total_flags', 0) >= 2
    
    def test_jogo_aleatorio(self):
        """Jogo variado deve ter índice alto."""
        report = validar_jogo([3, 17, 28, 39, 47, 58], MEGASENA)
        compressibilidade = report['metricas'].get('compressibilidade', {})
        assert compressibilidade.get('indice', 0) >= 70
