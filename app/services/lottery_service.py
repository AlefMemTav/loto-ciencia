# app/services/lottery_service.py
from dataclasses import dataclass
from datetime import timedelta
import os
import streamlit as st
from typing import Any, Optional, List
import pandas as pd
from app.core.logger import logger
from app.core.lottery import GAMES, GameConfig
from app.services.data_loader import carregar_dados_loteria_excel

from app.core.statistics import (
    calcular_distribuicao_quadrantes,
    calcular_distribuicoes_geometricas,
    calcular_taxa_regressao,
    get_numeros_quentes_frios,
    analise_poisson,
    get_tabela_inteligencia,
    get_historico_jogos,
    analise_intervalo_confianca,
    calcular_atrasos,
    calcular_chi_quadrado,
    calcular_coeficiente_variacao,
    get_reis_da_sequencia,
    verificar_historico,
)
from app.core.generator import (
    gerar_jogo_perfeito,
    gerar_multiplos_jogos,
    gerar_com_restricoes,
    gerar_fechamento,
)
from app.core.validator import validar_jogo


@dataclass(frozen=True)
class GameContext:
    """Contexto completo de um jogo, pré-computado e cacheado."""

    config: GameConfig
    df: Any
    freq: Any
    poisson_finais: Any
    tabela: Any
    historico_set: Any
    ic_info: Any
    atrasos: Any
    chi2: Optional[dict]
    coef_variacao: Optional[dict]
    reis_sequencia: List[int]
    distribuicoes_geometricas: Any
    stats_quadrantes: Any
    taxa_regressao: Optional[dict] = None


class LotteryService:
    """
    Serviço centralizado para lógica de loteria.
    """

    def get_config(self, slug: str) -> GameConfig:
        return GAMES[slug]

    def _get_file_hash(self, filepath: str) -> str:
        """Hash do arquivo para detectar mudanças"""
        if not os.path.exists(filepath):
            return "missing"
        mtime = os.path.getmtime(filepath)
        # Retorna caminho + data de modificação. Se o arquivo mudar, isso muda.
        return f"{filepath}:{mtime}"

    @staticmethod
    @st.cache_resource(ttl=timedelta(hours=12), show_spinner="Carregando dados...")
    def _build_context_static(
        slug: str, file_hash: str, config: GameConfig
    ) -> GameContext:
        """
        Método estático puro.
        A chave do cache será composta por: (slug, file_hash, config).
        """
        logger.info(
            f"🔄 [CACHE] get_context({slug}) - hash {file_hash} - Calculando..."
        )

        # Como não tem 'self', usamos o 'config' passado como argumento
        # Ajuste o caminho conforme sua estrutura, ou passe o path no config
        filepath = f"data/{slug}.xlsx"
        df = carregar_dados_loteria_excel(config, filepath)

        if df is None or df.empty:
            logger.warning(f"⚠️ [CACHE] {slug}: DataFrame vazio ou não encontrado!")
            # Retornamos um contexto "zerado" manualmente para não quebrar o sistema
            return GameContext(
                config=config,
                df=pd.DataFrame(),
                freq={},
                poisson_finais={},
                tabela=pd.DataFrame(),
                historico_set=set(),
                ic_info={},
                atrasos=pd.Series(),
                chi2={},
                coef_variacao={},
                reis_sequencia={},
                distribuicoes_geometricas={},
                stats_quadrantes={},
                taxa_regressao=None,
            )

        grupos_geometricos = config.get_geometric_groups()
        distribuicoes = calcular_distribuicoes_geometricas(
            df, grupos_geometricos, config
        )
        quadrantes = calcular_distribuicao_quadrantes(df, config)

        freq = get_numeros_quentes_frios(df, config)
        poisson_finais = analise_poisson(df, config, 0.05)
        tabela = get_tabela_inteligencia(df, config)
        historico_set = get_historico_jogos(df, config)
        ic_info = analise_intervalo_confianca(df, config)
        atrasos = calcular_atrasos(df, config)
        chi2 = calcular_chi_quadrado(df, config)
        coef_variacao = calcular_coeficiente_variacao(df, config)
        reis_sequencia = get_reis_da_sequencia(df, config)
        taxa_regressao = calcular_taxa_regressao(df, config, janela=100)

        logger.info(f"✅ [CACHE] {slug}: Contexto pronto e cacheado.")

        return GameContext(
            config=config,
            df=df,
            freq=freq,
            poisson_finais=poisson_finais,
            tabela=tabela,
            historico_set=historico_set,
            ic_info=ic_info,
            atrasos=atrasos,
            chi2=chi2,
            coef_variacao=coef_variacao,
            reis_sequencia=reis_sequencia,
            distribuicoes_geometricas=distribuicoes,
            stats_quadrantes=quadrantes,
            taxa_regressao=taxa_regressao,
        )

    def get_context(self, slug: str) -> GameContext:
        """Wrapper público"""
        filepath = f"data/{slug}.xlsx"

        # 1. Calcula o Hash atual
        current_hash = self._get_file_hash(filepath)

        # 2. Pega a config (necessária para o método estático)
        config = self.get_config(slug)

        # 3. Chama o estático
        # Se 'current_hash' for igual ao da última vez, o Streamlit retorna o cache instantaneamente.
        return self._build_context_static(slug, current_hash, config)

    def _build_empty_context(self, config, df):
        return GameContext(
            config=config,
            df=df,
            freq=None,
            poisson_finais=[],
            tabela=None,
            historico_set=set(),
            ic_info=None,
            atrasos=None,
            chi2=None,
            coef_variacao=None,
            reis_sequencia=[],
            distribuicoes_geometricas={},
            stats_quadrantes={},
            taxa_regressao=None,
        )

    def validate(self, slug: str, numbers: List[int]) -> dict:
        ctx = self.get_context(slug)
        return validar_jogo(
            numbers,
            ctx.config,
            historico_jogos=ctx.historico_set,
            ic_info=ctx.ic_info,
            df_historico=ctx.df,
            distribuicoes_geometricas=ctx.distribuicoes_geometricas,
            stats_quadrantes=ctx.stats_quadrantes,
        )

    def generate(self, slug: str, payload: dict) -> List[List[int]]:
        ctx = self.get_context(slug)

        # Extrai parâmetros
        qtd = int(payload.get("quantidade", 1))
        estrategia = payload.get("estrategia", "balanceada")
        fixos = payload.get("numeros_fixos")
        evitados = payload.get("numeros_evitados")
        garantir_div = payload.get("garantir_diversidade", True)

        contexto_dict = {
            "tabela": ctx.tabela,
            "historico_jogos": ctx.historico_set,
            "ic_info": ctx.ic_info,
            "distribuicoes_geometricas": ctx.distribuicoes_geometricas,
        }

        # Validação Rápida antes de chamar o gerador (Fail Fast)
        if fixos and len(fixos) > ctx.config.bet_size:
            raise ValueError(f"Quantidade de fixos maior que o tamanho do jogo.")

        return gerar_multiplos_jogos(
            df=ctx.df,
            config=ctx.config,
            finais_poisson=ctx.poisson_finais,
            quantidade=qtd,
            estrategia=estrategia,
            garantir_diversidade=garantir_div,
            numeros_fixos=fixos,
            numeros_evitados=evitados,
            contexto_precomputado=contexto_dict,
        )

    def closures(
        self, slug: str, base: List[int], max_combinacoes: int = 1000
    ) -> List[List[int]]:
        ctx = self.get_context(slug)
        res = gerar_fechamento(base, ctx.config, max_combinacoes=max_combinacoes)
        if isinstance(res, dict) and "erro" in res:
            raise ValueError(res["erro"])
        return res

    def check_historical_matches(self, slug: str, numbers: List[int], targets=None):
        ctx = self.get_context(slug)
        if targets is None:
            if ctx.config.slug == "loto_mania_sorteio":
                targets = [20, 19, 18, 0]
            else:
                targets = [ctx.config.k, ctx.config.k - 1, ctx.config.k - 2]

        return verificar_historico(numbers, ctx.df, ctx.config, alvos=targets)

    def analyze_distributions(self, slug: str, grupos: dict) -> dict:
        ctx = self.get_context(slug)
        return calcular_distribuicoes_geometricas(ctx.df, grupos, ctx.config)

    def analyze_regression(self, slug: str, janela: int = 100):
        ctx = self.get_context(slug)
        return calcular_taxa_regressao(ctx.df, ctx.config, janela)
