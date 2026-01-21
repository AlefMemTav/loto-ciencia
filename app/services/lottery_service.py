# app/services/lottery_service.py
"""
Serviço de Loteria com Validação.
Versão 2.1: CORREÇÕES CRÍTICAS APLICADAS
- Threshold de validação aumentado (20 → 70)
- Fator de excesso aumentado (5 → 10)
- Fallback inteligente quando poucos jogos passam
"""

from dataclasses import dataclass
from datetime import timedelta
import os
import streamlit as st
from typing import Any, Optional, List
import pandas as pd
from app.core.generator_fast import gerar_jogos_vetorizado
from app.core.generator_genetic import gerar_jogos_geneticos
from app.core.logger import logger
from app.core.lottery import GAMES, GameConfig
from app.core.statistics.clustering import clusterizar_jogos_kmeans
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
    calcular_ciclo_atual,
    analise_temporal_somas,
    analise_temporal_repetidos,
    detectar_tendencia_frequencia,
    matriz_coocorrencia_numeros,
    calcular_matriz_transicao,
    calibrar_pesos_dinamicos,
)
from app.core.matrices import gerar_fechamento
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
    ciclo_atual: Optional[dict] = None
    analise_somas: Optional[dict] = None
    analise_repetidos: Optional[dict] = None
    clusters_historicos: Optional[dict] = None
    tendencias: Optional[dict] = None
    pesos_dinamicos: Optional[dict] = None
    matriz_coocorrencia: Optional[Any] = None
    matriz_transicao: Optional[Any] = None


class LotteryService:
    @staticmethod
    def build_context_from_df(config, df):
        """
        Constrói um GameContext a partir de um DataFrame e config, para uso em backtest.
        """
        logger.info(" Contexto para Backtext ativado")
        if df is None or df.empty:
            return GameContext(
                config=config,
                df=df,
                freq={},
                poisson_finais={},
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
                ciclo_atual={},
                analise_somas={},
                analise_repetidos={},
                clusters_historicos={},
                tendencias={},
                pesos_dinamicos={},
                matriz_coocorrencia={},
                matriz_transicao={},
            )

        grupos_geometricos = config.get_geometric_groups()
        distribuicoes = calcular_distribuicoes_geometricas(
            df, grupos_geometricos, config
        )
        quadrantes = calcular_distribuicao_quadrantes(df, config)
        freq = get_numeros_quentes_frios(df, config)
        poisson_finais = analise_poisson(df, config, 0.05)
        tabela = get_tabela_inteligencia(df, config)
        pesos_dinamicos = calibrar_pesos_dinamicos(df, config)
        historico_set = get_historico_jogos(df, config)
        ic_info = analise_intervalo_confianca(df, config)
        atrasos = calcular_atrasos(df, config)
        chi2 = calcular_chi_quadrado(df, config)
        coef_variacao = calcular_coeficiente_variacao(df, config)
        reis_sequencia = get_reis_da_sequencia(df, config)
        taxa_regressao = calcular_taxa_regressao(df, config, janela=100)
        ciclo_atual = calcular_ciclo_atual(df, config)
        analise_somas = analise_temporal_somas(df, config, janela=30)
        analise_repetidos = analise_temporal_repetidos(df, config, janela=30)
        matriz_cooc = matriz_coocorrencia_numeros(df, config)
        matriz_transicao = calcular_matriz_transicao(df, config)
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
            ciclo_atual=ciclo_atual,
            analise_somas=analise_somas,
            analise_repetidos=analise_repetidos,
            clusters_historicos=None,
            tendencias=None,
            pesos_dinamicos=pesos_dinamicos,
            matriz_coocorrencia=matriz_cooc,
            matriz_transicao=matriz_transicao,
        )

    def _validar_lote_com_cache(
        self, candidatos, ctx, score_cache, threshold, jogos_existentes
    ):
        """
        Valida um lote de jogos, usando e atualizando o cache de scores.
        Retorna lista de (score, jogo) aprovados e atualiza jogos_existentes.
        """
        jogos_aprovados = []
        for jogo in candidatos:
            jogo_tuple = tuple(jogo)
            if jogo_tuple in jogos_existentes:
                continue
            if jogo_tuple in score_cache:
                score = score_cache[jogo_tuple]
            else:
                report = validar_jogo(
                    jogo,
                    ctx.config,
                    historico_jogos=ctx.historico_set,
                    ic_info=ctx.ic_info,
                    df_historico=ctx.df,
                    distribuicoes_geometricas=ctx.distribuicoes_geometricas,
                    stats_quadrantes=ctx.stats_quadrantes,
                )
                score = report["score"]
                score_cache[jogo_tuple] = score
            if score >= threshold:
                jogos_aprovados.append((score, jogo))
                jogos_existentes.add(jogo_tuple)
        return jogos_aprovados

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

        filepath = f"data/{slug}.xlsx"
        df = carregar_dados_loteria_excel(config, filepath)

        if df is None or df.empty:
            logger.warning(f"⚠️ [CACHE] {slug}: DataFrame vazio ou não encontrado!")
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
                ciclo_atual={},
                analise_somas={},
                analise_repetidos={},
                clusters_historicos={},
                tendencias={},
                pesos_dinamicos={},
                matriz_coocorrencia={},
                matriz_transicao={},
            )

        # --- CÁLCULOS ---
        grupos_geometricos = config.get_geometric_groups()
        distribuicoes = calcular_distribuicoes_geometricas(
            df, grupos_geometricos, config
        )
        quadrantes = calcular_distribuicao_quadrantes(df, config)

        freq = get_numeros_quentes_frios(df, config)
        poisson_finais = analise_poisson(df, config, 0.05)
        tabela = get_tabela_inteligencia(df, config)
        pesos_dinamicos = calibrar_pesos_dinamicos(df, config)
        historico_set = get_historico_jogos(df, config)
        ic_info = analise_intervalo_confianca(df, config)
        atrasos = calcular_atrasos(df, config)
        chi2 = calcular_chi_quadrado(df, config)
        coef_variacao = calcular_coeficiente_variacao(df, config)
        reis_sequencia = get_reis_da_sequencia(df, config)
        taxa_regressao = calcular_taxa_regressao(df, config, janela=100)
        ciclo_atual = calcular_ciclo_atual(df, config)
        analise_somas = analise_temporal_somas(df, config, janela=30)
        analise_repetidos = analise_temporal_repetidos(df, config, janela=30)
        matriz_cooc = matriz_coocorrencia_numeros(df, config)
        matriz_transicao = calcular_matriz_transicao(df, config)

        todos_jogos = [sorted(row.tolist()) for row in df[config.draw_cols].values]

        # Executa o K-Means
        clusters_historicos = clusterizar_jogos_kmeans(
            todos_jogos, config, n_clusters=3, random_state=42
        )
        lista_tendencias = []
        for n in range(1, config.n_numbers + 1):
            res = detectar_tendencia_frequencia(df, config, numero=n, janela=30)
            if res and res["p_value"] < 0.10:
                lista_tendencias.append(res)

        # Separa em Alta e Baixa
        em_alta = sorted(
            [t for t in lista_tendencias if t["slope"] > 0],
            key=lambda x: x["slope"],
            reverse=True,
        )
        em_baixa = sorted(
            [t for t in lista_tendencias if t["slope"] < 0], key=lambda x: x["slope"]
        )

        tendencias = {
            "alta": em_alta[:5],
            "baixa": em_baixa[:5],
        }
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
            ciclo_atual=ciclo_atual,
            analise_somas=analise_somas,
            analise_repetidos=analise_repetidos,
            clusters_historicos=clusters_historicos,
            tendencias=tendencias,
            pesos_dinamicos=pesos_dinamicos,
            matriz_coocorrencia=matriz_cooc,
            matriz_transicao=matriz_transicao,
        )

    def get_context(self, slug: str) -> GameContext:
        """Wrapper público"""
        filepath = f"data/{slug}.xlsx"

        # 1. Calcula o Hash atual
        current_hash = self._get_file_hash(filepath)

        # 2. Pega a config (necessária para o método estático)
        config = self.get_config(slug)

        # 3. Chama o estático
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
            ciclo_atual={},
            analise_somas={},
            analise_repetidos={},
            tendencias={},
            pesos_dinamicos={},
            matriz_coocorrencia={},
            matriz_transicao={},
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

    def generate(
        self, slug: str, payload: dict, ctx: GameContext = None
    ) -> List[List[int]]:
        if ctx is None:
            ctx = self.get_context(slug)

        # Extrai parâmetros
        qtd = int(payload.get("quantidade", 1))
        estrategia = payload.get("estrategia", "balanceada")
        fixos = payload.get("numeros_fixos")
        evitados = payload.get("numeros_evitados")
        seed = payload.get("seed", None)

        if fixos and len(fixos) > ctx.config.bet_size:
            raise ValueError(f"Quantidade de fixos maior que o tamanho do jogo.")

        fator_excesso = 10
        batch_size = min(qtd * fator_excesso, 500)
        max_candidatos = min(qtd * fator_excesso * 4, 2000)
        jogos_avaliados = []
        score_cache = {}
        jogos_existentes = set()
        total_gerados = 0
        threshold = 70
        relax_threshold = 55

        while len(jogos_avaliados) < qtd and total_gerados < max_candidatos:
            candidatos = gerar_jogos_vetorizado(
                ctx=ctx,
                quantidade=batch_size,
                estrategia=estrategia,
                numeros_fixos=fixos,
                numeros_evitados=evitados,
                seed=seed,
            )
            total_gerados += len(candidatos)
            aprovados = self._validar_lote_com_cache(
                candidatos, ctx, score_cache, threshold, jogos_existentes
            )
            jogos_avaliados.extend(aprovados)
            if len(jogos_avaliados) >= qtd:
                break

        jogos_avaliados.sort(key=lambda x: x[0], reverse=True)
        melhores_jogos = [j[1] for j in jogos_avaliados[:qtd]]

        # RELAXAMENTO: garantir unicidade mínima (não duplicar histórico ou já aceitos)
        if len(melhores_jogos) < qtd:
            logger.warning(
                f"⚠️ Apenas {len(melhores_jogos)} jogos passaram no filtro score>={threshold}. "
                f"Relaxando para score>={relax_threshold}..."
            )
            set_melhores = set(tuple(j) for j in melhores_jogos)
            sorted_cache = sorted(
                score_cache.items(), key=lambda kv: kv[1], reverse=True
            )
            for jogo_tuple, score in sorted_cache:
                if len(melhores_jogos) >= qtd:
                    break
                if jogo_tuple in set_melhores:
                    continue
                # Unicidade mínima: não duplicar histórico nem já aceitos
                if jogo_tuple in ctx.historico_set:
                    continue
                if score >= relax_threshold:
                    melhores_jogos.append(list(jogo_tuple))
                    set_melhores.add(jogo_tuple)

            logger.info(f"✅ Após relaxamento: {len(melhores_jogos)} jogos disponíveis")

        if not melhores_jogos:
            if score_cache:
                top_from_cache = [
                    j
                    for j in sorted(
                        score_cache.items(), key=lambda kv: kv[1], reverse=True
                    )
                    if j[0] not in ctx.historico_set
                ][:qtd]
                return [list(j[0]) for j in top_from_cache]
            logger.warning(f"⚠️ Validador rejeitou todos os candidatos. Usando brutos.")
            return candidatos[:qtd]

        return melhores_jogos

    # Substitua apenas o método generate_genetic existente por este trecho.
    def generate_genetic(
        self, slug: str, payload: dict, ctx: GameContext = None
    ) -> List[List[int]]:
        if ctx is None:
            ctx = self.get_context(slug)

        """
        Motor Evolutivo com Validação e cache, unificado com generate.
        """
        logger.info(f"🧬 Iniciando Mineração Genética para {slug}")

        qtd_alvo = int(payload.get("quantidade", 1))
        fixos = payload.get("numeros_fixos")
        estrategia = payload.get("estrategia", "balanceada")
        seed = payload.get("seed", None)

        qtd_bruta = min(qtd_alvo * 5, 100)
        threshold = payload.get("threshold", 70)
        relax_threshold = payload.get("relax_threshold", 55)
        score_cache = {}
        jogos_existentes = set()
        jogos_avaliados = []

        try:
            candidatos = gerar_jogos_geneticos(
                ctx=ctx,
                quantidade=qtd_bruta,
                estrategia=estrategia,
                fixos=fixos,
                seed=seed,
            )
            aprovados = self._validar_lote_com_cache(
                candidatos, ctx, score_cache, threshold, jogos_existentes
            )
            jogos_avaliados.extend(aprovados)

            jogos_avaliados.sort(key=lambda x: x[0], reverse=True)
            melhores = [j[1] for j in jogos_avaliados[:qtd_alvo]]

            if len(melhores) < qtd_alvo:
                logger.warning(
                    f"⚠️ Apenas {len(melhores)} jogos genéticos passaram no filtro score>={threshold}. "
                    f"Relaxando para score>={relax_threshold}..."
                )
                set_melhores = set(tuple(j) for j in melhores)
                # ordena cache por score decrescente e tenta completar com revalidação mínima
                for jogo_tuple, score in sorted(
                    score_cache.items(), key=lambda kv: kv[1], reverse=True
                ):
                    if len(melhores) >= qtd_alvo:
                        break
                    if jogo_tuple in set_melhores:
                        continue
                    if score >= relax_threshold:
                        # Revalidação mínima: evitar duplicatas no histórico
                        if jogo_tuple in jogos_existentes:
                            continue
                        melhores.append(list(jogo_tuple))
                        set_melhores.add(jogo_tuple)

                logger.info(
                    f"✅ Após relaxamento: {len(melhores)} jogos genéticos disponíveis"
                )

            return melhores

        except Exception as e:
            logger.error(f"❌ Erro no Algoritmo Genético: {e}")
            logger.warning("⚠️ Usando fallback vetorial.")
            # passe o ctx para o fallback para evitar look-ahead
            return self.generate(slug, payload, ctx=ctx)

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
