# app/services/lottery_service.py
from dataclasses import dataclass
from functools import lru_cache
from logging import config
from typing import Any, Optional
from app.core.logger import logger
from app.core.advanced_statistics import (
    calcular_distribuicao_quadrantes,
    calcular_distribuicoes_geometricas,
)
from app.core.game_constants import (
    get_constants_for_game,
    get_grupos_geometricos_essenciais,
)
from app.core.games import GAMES, GameConfig
from app.services.data_loader import carregar_dados_loteria_excel
from app.core.statistics import (
    get_numeros_quentes_frios,
    analise_poisson,
    get_tabela_inteligencia,
    get_historico_jogos,
    analise_intervalo_confianca,
    calcular_atrasos,
    calcular_chi_quadrado,
    calcular_coeficiente_variacao,
    get_reis_da_sequencia,
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
    """
    Contexto completo de um jogo, pré-computado e cacheado.
    Contém histórico + todas as estatísticas derivadas.
    """

    config: GameConfig
    df: Any

    # Básicos (usado por UI e API)
    freq: Any
    poisson_finais: Any

    # Usados pelo gerador/validador
    tabela: Any
    historico_set: Any
    ic_info: Any

    # Estatísticas do painel (pré-computadas)
    atrasos: Any
    chi2: Optional[dict]
    coef_variacao: Optional[dict]
    reis_sequencia: list[int]
    distribuicoes_geometricas: Any
    stats_quadrantes: Any


class LotteryService:
    """
    Serviço centralizado para lógica de loteria.
    Compartilhado entre UI Streamlit e API FastAPI.
    """

    def get_config(self, slug: str) -> GameConfig:
        """Retorna configuração do jogo."""
        return GAMES[slug]

    @lru_cache(maxsize=32)
    def get_context(self, slug: str) -> GameContext:
        """
        Carrega e pré-computa TUDO para um jogo.
        Resultado é cacheado (maxsize=32 jogos diferentes).
        """
        logger.info(f"🔄 [CACHE] get_context({slug}) - calculando contexto...")
        config = self.get_config(slug)
        df = carregar_dados_loteria_excel(config, f"data/{slug}.xlsx")

        if df is None or df.empty:
            logger.warning(
                f"⚠️ [CACHE] {slug}: DataFrame vazio, retornando contexto mínimo"
            )
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
            )

        grupos_geometricos = get_grupos_geometricos_essenciais(config)

        distribuicoes = calcular_distribuicoes_geometricas(
            df, grupos_geometricos, config
        )

        quadrantes = calcular_distribuicao_quadrantes(df, config)

        # Se não tem dados, devolve contexto vazio
        if df is None or df.empty:
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
                distribuicoes_geometricas=distribuicoes,
                stats_quadrantes=quadrantes,
            )

        # Estatísticas básicas
        freq = get_numeros_quentes_frios(df, config)
        poisson_finais = analise_poisson(df, config, 0.05)

        # Para gerador/validador
        tabela = get_tabela_inteligencia(df, config)
        historico_set = get_historico_jogos(df, config)
        ic_info = analise_intervalo_confianca(df, config)

        # Para painel
        atrasos = calcular_atrasos(df, config)
        chi2 = calcular_chi_quadrado(df, config)
        coef_variacao = calcular_coeficiente_variacao(df, config)
        reis_sequencia = get_reis_da_sequencia(df, config)

        logger.info(
            f"✅ [CACHE] {slug}: contexto completo carregado ({len(df)} sorteios)"
        )
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
        )

    def refresh_context(self, slug: str) -> None:
        """
        Limpa cache e força recálculo na próxima chamada.
        Útil quando o arquivo Excel é atualizado.
        """
        self.get_context.cache_clear()

    def validate(self, slug: str, numbers: list[int]) -> dict:
        """
        Valida um jogo usando o validador do core.
        Retorna dict com score, msgs, status, risco_divisao, etc.
        """
        logger.info(f"[API] validate() chamado: slug={slug}, numbers={numbers}")
        ctx = self.get_context(slug)

        logger.info(f"[API] validate({slug}): obtendo contexto...")
        cache_info = self.get_context.cache_info()
        ctx = self.get_context(slug)
        new_cache_info = self.get_context.cache_info()

        if new_cache_info.hits > cache_info.hits:
            logger.debug(
                f"✅ [CACHE HIT] {slug} (hits={new_cache_info.hits}, misses={new_cache_info.misses})"
            )
        else:
            logger.info(f"❌ [CACHE MISS] {slug} - contexto recalculado")

        result = validar_jogo(
            numbers,
            ctx.config,
            historico_jogos=ctx.historico_set,
            ic_info=ctx.ic_info,
            df_historico=ctx.df,
            distribuicoes_geometricas=ctx.distribuicoes_geometricas,
            stats_quadrantes=ctx.stats_quadrantes,
        )
        logger.info(
            f"[API] validate() retornou: score={result['score']}, status={result['status']}"
        )
        return result

    def generate(self, slug: str, payload: dict) -> list[list[int]]:
        """
        Gera jogos usando o gerador do core.

        payload esperado:
        {
            "quantidade": int (default 1),
            "estrategia": "balanceada" | "conservadora" | "agressiva" | "pura",
            "garantir_diversidade": bool (default True),
            "numeros_fixos": list[int] | None,
            "numeros_evitados": list[int] | None,
        }

        Retorna lista de jogos (cada jogo é lista de ints ordenados).
        """
        logger.info(f"[API] generate() chamado: slug={slug}, payload={payload}")
        ctx = self.get_context(slug)
        qtd = payload.get("quantidade", 1)
        estrategia = payload.get("estrategia", "balanceada")
        fixos = payload.get("numeros_fixos")
        evitados = payload.get("numeros_evitados")
        garantir_div = payload.get("garantir_diversidade", True)
        contexto = {
            "tabela": ctx.tabela,
            "historico_jogos": ctx.historico_set,
            "ic_info": ctx.ic_info,
            "distribuicoes_geometricas": ctx.distribuicoes_geometricas,
        }
        # Se tem restrições (fixos ou evitados), usa gerador específico
        if fixos or evitados:
            jogo = gerar_com_restricoes(
                ctx.df,
                ctx.config,
                numeros_fixos=fixos,
                numeros_evitados=evitados,
                estrategia=estrategia,
                contexto_precomputado=contexto,
            )
            if isinstance(jogo, dict) and "erro" in jogo:
                raise ValueError(jogo["erro"])
            return [jogo]

        # Geração normal
        if qtd == 1:
            return [
                gerar_jogo_perfeito(
                    ctx.df,
                    ctx.config,
                    estrategia=estrategia,
                    contexto_precomputado=contexto,
                )
            ]

        jogos = gerar_multiplos_jogos(
            ctx.df,
            ctx.config,
            quantidade=qtd,
            estrategia=estrategia,
            garantir_diversidade=garantir_div,
            contexto_precomputado=contexto,
        )
        logger.info(f"[API] generate() gerou {len(jogos)} jogos")
        return jogos

    def closures(
        self, slug: str, numeros_base: list[int], max_combinacoes: int = 1000
    ) -> list[list[int]]:
        """
        Gera fechamento (todas as combinações possíveis).

        Retorna lista de jogos OU levanta ValueError se exceder max_combinacoes.
        """
        ctx = self.get_context(slug)
        res = gerar_fechamento(
            numeros_base, ctx.config, max_combinacoes=max_combinacoes
        )

        # gerar_fechamento pode retornar dict com erro
        if isinstance(res, dict) and "erro" in res:
            raise ValueError(res["erro"])

        return res

    def analyze_distributions(self, slug: str, grupos_geometricos: dict) -> dict:
        """
        Calcula distribuições empíricas dos grupos geométricos.

        Args:
            slug: Identificador do jogo
            grupos_geometricos: Dict com {nome_grupo: [numeros]}

        Returns:
            Dict com {nome_grupo: DistributionStats}
        """
        ctx = self.get_context(slug)
        from app.core.advanced_statistics import calcular_distribuicoes_geometricas

        return calcular_distribuicoes_geometricas(
            ctx.df, grupos_geometricos, ctx.config
        )

    def analyze_regression(self, slug: str, janela: int = 100) -> dict | None:
        """
        Valida hipótese de regressão à média.

        Args:
            slug: Identificador do jogo
            janela: Tamanho da janela histórica

        Returns:
            Dict com correlação, taxa_retorno, interpretação, p_value
            ou None se dados insuficientes
        """
        ctx = self.get_context(slug)
        from app.core.advanced_statistics import calcular_taxa_regressao

        return calcular_taxa_regressao(ctx.df, ctx.config, janela)

    def check_historical_matches(
        self, slug: str, numbers: list[int], targets: list[int] | None = None
    ) -> dict[int, list[str]]:
        """
        Verifica quantas vezes os números apostados acertariam no histórico.

        Args:
            slug: Identificador do jogo
            numbers: Lista de números apostados
            targets: Lista de alvos (ex: [6, 5, 4]). Se None, usa padrão do jogo.

        Returns:
            Dict com {acertos: [lista de concursos]}
            Ex: {6: ['Conc. 2705', 'Conc. 2680'], 5: ['Conc. 2700'], 4: []}
        """
        ctx = self.get_context(slug)
        from app.core.statistics import verificar_historico

        if targets is None:
            # Define alvos padrão baseado no jogo
            if ctx.config.slug == "loto_mania_sorteio":
                targets = [20, 19, 18, 0]  # Lotomania tem prêmio em 0 acertos
            else:
                targets = [ctx.config.k, ctx.config.k - 1, ctx.config.k - 2]

        return verificar_historico(numbers, ctx.df, ctx.config, alvos=targets)
