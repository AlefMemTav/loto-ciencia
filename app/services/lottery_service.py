# app/services/lottery_service.py
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
from app.core.statistics.advanced import calibrar_pesos_dinamicos
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

        todos_jogos = [sorted(row.tolist()) for row in df[config.draw_cols].values]

        # Executa o K-Means
        clusters_historicos = clusterizar_jogos_kmeans(
            todos_jogos, config, n_clusters=3, random_state=42
        )
        lista_tendencias = []
        for n in range(1, config.n_numbers + 1):
            # Janela de 30 a 50 concursos é ideal para tendência de curto prazo
            res = detectar_tendencia_frequencia(df, config, numero=n, janela=30)
            if (
                res and res["p_value"] < 0.10
            ):  # Filtra apenas tendências com alguma relevância
                lista_tendencias.append(res)

        # Separa em Alta e Baixa
        em_alta = sorted(
            [t for t in lista_tendencias if t["slope"] > 0],
            key=lambda x: x["slope"],
            reverse=True,
        )
        em_baixa = sorted(
            [t for t in lista_tendencias if t["slope"] < 0], key=lambda x: x["slope"]
        )  # Menor slope (mais negativo) primeiro

        tendencias = {
            "alta": em_alta[:5],  # Top 5 subindo
            "baixa": em_baixa[:5],  # Top 5 descendo
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
            ciclo_atual={},
            analise_somas={},
            analise_repetidos={},
            tendencias={},
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

        # Validação Rápida antes de chamar o gerador (Fail Fast)
        if fixos and len(fixos) > ctx.config.bet_size:
            raise ValueError(f"Quantidade de fixos maior que o tamanho do jogo.")

        fator_excesso = 5
        qtd_bruta = qtd * fator_excesso

        # Limite de segurança para não travar em pedidos gigantes
        qtd_bruta = min(qtd_bruta, 1000)

        candidatos = gerar_jogos_vetorizado(
            ctx=ctx,
            quantidade=qtd_bruta,
            estrategia=estrategia,
            numeros_fixos=fixos,
            numeros_evitados=evitados,
        )

        jogos_avaliados = []

        for jogo in candidatos:
            # Validamos cada candidato.
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

            # Critério de corte básico (opcional): rejeitar lixo total
            if score > 20:
                jogos_avaliados.append((score, jogo))

        # 5. Seleção dos Melhores (Ranking)
        # Ordena pelo Score (decrescente)
        jogos_avaliados.sort(key=lambda x: x[0], reverse=True)

        # Pega apenas a quantidade que o usuário pediu
        melhores_jogos = [j[1] for j in jogos_avaliados[:qtd]]

        # Fallback: Se o validador rejeitou tudo (muito raro), devolve os brutos
        if not melhores_jogos:
            logger.warning(
                f"Validador rejeitou todos os {len(candidatos)} candidatos. Usando brutos."
            )
            return candidatos[:qtd]

        return melhores_jogos

    def generate_genetic(self, slug: str, payload: dict) -> List[List[int]]:
        """
        Fachada para o Motor Evolutivo com Validação Final.

        Fluxo:
        1. Pede ao GA para evoluir 3x mais jogos do que o necessário.
        2. Passa os sobreviventes pelo Validador Oficial (juiz severo).
        3. Retorna apenas a Elite da Elite.
        """
        logger.info(f"🧬 Iniciando Mineração Genética para {slug}")

        ctx = self.get_context(slug)

        # Parâmetros
        qtd_alvo = int(payload.get("quantidade", 1))
        fixos = payload.get("numeros_fixos")
        estrategia = payload.get("estrategia", "balanceada")
        # Tática de Over-provisioning:
        # Pedimos o triplo de jogos para poder descartar os que tiverem Score baixo
        qtd_bruta = qtd_alvo * 3
        # Trava de segurança para não explodir o tempo de processamento
        qtd_bruta = min(qtd_bruta, 50)

        try:
            # 1. Mineração Evolutiva (Otimiza matemática interna)
            candidatos = gerar_jogos_geneticos(
                ctx=ctx, quantidade=qtd_bruta, estrategia=estrategia, fixos=fixos
            )

            # 2. Refinamento pelo Validador (Alinha com a expectativa visual do usuário)
            jogos_avaliados = []

            for jogo in candidatos:
                # O validador aplica critérios que o GA talvez não veja (ex: Simetria Visual)
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

                # Aceitamos apenas jogos decentes
                if score >= 50:
                    jogos_avaliados.append((score, jogo))

            # 3. Ordenação (Ranking)
            # Queremos os maiores scores primeiro
            jogos_avaliados.sort(key=lambda x: x[0], reverse=True)

            logger.info(
                f"🧬 Evolução: {len(candidatos)} candidatos -> {len(jogos_avaliados)} aprovados."
            )

            # Retorna apenas a quantidade solicitada
            melhores = [j[1] for j in jogos_avaliados[:qtd_alvo]]

            # Se o filtro genético + validador foi muito rigoroso e sobrou pouco,
            # completa com os candidatos brutos do genético (melhor que falhar)
            if len(melhores) < qtd_alvo:
                faltam = qtd_alvo - len(melhores)
                extras = [j for j in candidatos if j not in melhores][:faltam]
                melhores.extend(extras)

            return melhores

        except Exception as e:
            logger.error(f"Erro no Algoritmo Genético: {e}")
            logger.warning("Usando fallback vetorial.")
            # Fallback para o método padrão se o genético falhar
            return self.generate(slug, payload)

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
