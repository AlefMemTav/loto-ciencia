# app/core/statistics/auditoria_independencia.py
"""
Auditoria de independência entre sorteios consecutivos.

Reúne em uma bateria só os testes que perguntam se o histórico mostra alguma
dependência que valha explorar:

- Soma jogo a jogo: autocorrelação, Ljung-Box, tamanho da variação, transição
  entre faixas de soma e sequência de somas acima/abaixo da mediana.
- Repetição de números do sorteio anterior, contra a distribuição
  hipergeométrica que valeria sem dependência.
- Ordem de saída das bolas: correlação entre a posição de saída e o valor da
  bola, e posição em que sai o menor número.

A hipótese nula é a de sorteios independentes e bolas em ordem uniforme. Como
são vários testes de uma vez, os p-valores são ajustados (Holm por padrão).

Um resultado sem rejeição NÃO prova independência; só diz que esta bateria não
achou evidência. E um resultado com rejeição não é, sozinho, sinal explorável:
o caminho certo é confirmá-lo fora da amostra (walk-forward) antes de usá-lo.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats

from app.core.statistics.multiple_testing import benjamini_hochberg, holm_bonferroni
from app.core.statistics.ordem_saida import mascara_ordem_de_saida

ALFA = 0.05
N_PERMUTACOES = 2000
MIN_SORTEIOS = 100
MIN_SORTEIOS_ORDEM = 50
LAGS_LJUNG_BOX = 10

_AJUSTES = {"holm": holm_bonferroni, "bh": benjamini_hochberg}


@dataclass(frozen=True)
class ResultadoTeste:
    nome: str
    descricao: str
    estatistica: float
    p_valor: float
    p_ajustado: float


@dataclass
class AuditoriaIndependencia:
    jogo: str
    n_sorteios: int
    n_sorteios_ordem: int
    alfa: float
    ajuste: str
    testes: list[ResultadoTeste] = field(default_factory=list)

    @property
    def rejeitados(self) -> list[ResultadoTeste]:
        return [t for t in self.testes if t.p_ajustado < self.alfa]

    @property
    def n_rejeitados(self) -> int:
        return len(self.rejeitados)

    def conclusao(self) -> str:
        if not self.rejeitados:
            return (
                f"sem evidência de dependência em {len(self.testes)} testes "
                f"(nível {self.alfa:.0%}, ajuste {self.ajuste})"
            )
        nomes = ", ".join(t.nome for t in self.rejeitados)
        return (
            f"possível dependência em {self.n_rejeitados} de "
            f"{len(self.testes)} testes: {nomes}. Confirme fora da amostra "
            "antes de usar."
        )

    def para_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "teste": t.nome,
                    "estatistica": t.estatistica,
                    "p_valor": t.p_valor,
                    "p_ajustado": t.p_ajustado,
                    "rejeita": t.p_ajustado < self.alfa,
                    "descricao": t.descricao,
                }
                for t in self.testes
            ]
        )

    def para_dict(self) -> dict:
        return {
            "jogo": self.jogo,
            "n_sorteios": self.n_sorteios,
            "n_sorteios_ordem": self.n_sorteios_ordem,
            "alfa": self.alfa,
            "ajuste": self.ajuste,
            "n_rejeitados": self.n_rejeitados,
            "conclusao": self.conclusao(),
            "testes": self.para_dataframe().to_dict("records"),
        }


# ----------------------------------------------------------------------
# Auxiliares
# ----------------------------------------------------------------------
def _autocorrelacao(x: np.ndarray, lag: int) -> float:
    centrada = x - x.mean()
    denominador = float((centrada * centrada).sum())
    if denominador == 0:
        return 0.0
    return float((centrada[:-lag] * centrada[lag:]).sum() / denominador)


def _p_permutacao(observado: float, nulos: np.ndarray) -> float:
    """p-valor bilateral de Monte Carlo (o observado conta como uma amostra)."""
    centro = float(nulos.mean())
    mais_extremos = int((np.abs(nulos - centro) >= abs(observado - centro)).sum())
    return (1 + mais_extremos) / (len(nulos) + 1)


def _agrupar_esperado_minimo(
    observado: np.ndarray, esperado: np.ndarray, minimo: float = 5.0
) -> tuple[np.ndarray, np.ndarray]:
    """Junta classes vizinhas até que cada uma tenha esperado >= minimo."""
    obs_g: list[float] = []
    esp_g: list[float] = []
    acum_o = acum_e = 0.0
    for o, e in zip(observado, esperado):
        acum_o += o
        acum_e += e
        if acum_e >= minimo:
            obs_g.append(acum_o)
            esp_g.append(acum_e)
            acum_o = acum_e = 0.0
    if acum_e > 0 or acum_o > 0:
        if obs_g:
            obs_g[-1] += acum_o
            esp_g[-1] += acum_e
        else:
            obs_g.append(acum_o)
            esp_g.append(acum_e)
    return np.array(obs_g), np.array(esp_g)


def _qui_quadrado(observado: np.ndarray, esperado: np.ndarray) -> tuple[float, float]:
    obs, esp = _agrupar_esperado_minimo(observado, esperado)
    if len(obs) < 2:
        return 0.0, 1.0
    estatistica = float(((obs - esp) ** 2 / esp).sum())
    return estatistica, float(stats.chi2.sf(estatistica, len(obs) - 1))


Teste = tuple[str, str, float, float]  # nome, descrição, estatística, p-valor


# ----------------------------------------------------------------------
# Testes sobre a soma jogo a jogo
# ----------------------------------------------------------------------
def _testes_soma(soma: np.ndarray, n_permutacoes: int, rng: np.random.Generator) -> list[Teste]:
    testes: list[Teste] = []

    # Autocorrelação lag 1 e tamanho médio da variação: os dois por permutação,
    # embaralhando a ordem dos sorteios (hipótese nula: ordem irrelevante)
    centrada = soma - soma.mean()
    denominador = float((centrada * centrada).sum())
    r1 = (
        float((centrada[:-1] * centrada[1:]).sum() / denominador)
        if denominador > 0
        else 0.0
    )
    variacao = float(np.abs(np.diff(soma)).mean())
    nulos_r1 = np.empty(n_permutacoes)
    nulos_var = np.empty(n_permutacoes)
    for b in range(n_permutacoes):
        embaralhada = rng.permutation(soma)
        c = embaralhada - embaralhada.mean()
        nulos_r1[b] = (c[:-1] * c[1:]).sum() / denominador if denominador > 0 else 0.0
        nulos_var[b] = np.abs(np.diff(embaralhada)).mean()

    testes.append(
        (
            "soma_autocorrelacao_lag1",
            "Autocorrelação lag 1 da soma (permutação)",
            r1,
            _p_permutacao(r1, nulos_r1),
        )
    )
    testes.append(
        (
            "soma_variacao_absoluta",
            "Média de |soma[t] - soma[t-1]| (permutação)",
            variacao,
            _p_permutacao(variacao, nulos_var),
        )
    )

    # Ljung-Box nos primeiros lags
    n = len(soma)
    lags = np.arange(1, min(LAGS_LJUNG_BOX, n - 1) + 1)
    r = np.array([_autocorrelacao(soma, int(lag)) for lag in lags])
    q = float(n * (n + 2) * (r**2 / (n - lags)).sum())
    testes.append(
        (
            f"soma_ljung_box_{len(lags)}",
            f"Ljung-Box da soma em {len(lags)} lags",
            q,
            float(stats.chi2.sf(q, len(lags))),
        )
    )

    # Transição entre tercis da soma (baixa/média/alta) no sorteio seguinte
    cortes = np.quantile(soma, [1 / 3, 2 / 3])
    faixa = np.digitize(soma, cortes)
    tabela = np.zeros((3, 3))
    for de, para in zip(faixa[:-1], faixa[1:]):
        tabela[de, para] += 1
    tabela = tabela[tabela.sum(axis=1) > 0][:, tabela.sum(axis=0) > 0]
    if tabela.shape[0] >= 2 and tabela.shape[1] >= 2:
        qui2, p_qui2, _, _ = stats.chi2_contingency(tabela)
        testes.append(
            (
                "soma_transicao_tercis",
                "Faixa da soma no sorteio seguinte, dada a faixa atual (qui-quadrado)",
                float(qui2),
                float(p_qui2),
            )
        )

    # Runs da soma acima/abaixo da mediana (Wald-Wolfowitz)
    acima = (soma > np.median(soma)).astype(int)
    n1 = int(acima.sum())
    n0 = len(acima) - n1
    if n1 > 0 and n0 > 0 and len(acima) > 2:
        runs = 1 + int((np.diff(acima) != 0).sum())
        media_runs = 2 * n1 * n0 / (n1 + n0) + 1
        var_runs = (media_runs - 1) * (media_runs - 2) / (n1 + n0 - 1)
        if var_runs > 0:
            z = (runs - media_runs) / np.sqrt(var_runs)
            testes.append(
                (
                    "soma_runs_mediana",
                    "Runs da soma acima/abaixo da mediana (Wald-Wolfowitz)",
                    float(z),
                    float(2 * stats.norm.sf(abs(z))),
                )
            )

    return testes


# ----------------------------------------------------------------------
# Repetição do sorteio anterior
# ----------------------------------------------------------------------
def _teste_repeticao(valores: np.ndarray, n_numeros: int, k: int) -> Teste:
    n_sorteios = len(valores)
    presenca = np.zeros((n_sorteios, n_numeros), dtype=bool)
    presenca[np.repeat(np.arange(n_sorteios), k), valores.ravel() - 1] = True
    repetidos = (presenca[1:] & presenca[:-1]).sum(axis=1)

    observado = np.bincount(repetidos, minlength=k + 1).astype(float)
    esperado = (
        stats.hypergeom.pmf(np.arange(k + 1), n_numeros, k, k) * len(repetidos)
    )
    qui2, p = _qui_quadrado(observado, esperado)
    return (
        "repeticao_sorteio_anterior",
        "Quantos números repetem do sorteio anterior vs hipergeométrica",
        qui2,
        p,
    )


# ----------------------------------------------------------------------
# Ordem de saída
# ----------------------------------------------------------------------
def _testes_ordem(df: pd.DataFrame, config) -> tuple[list[Teste], int]:
    mascara = mascara_ordem_de_saida(df, config)
    valores = df[list(config.draw_cols)].to_numpy(dtype=int)[mascara]
    n_validos, k = valores.shape
    if n_validos < MIN_SORTEIOS_ORDEM or k < 3:
        return [], int(n_validos)

    testes: list[Teste] = []

    # Spearman entre posição de saída e valor, sorteio a sorteio. Sem
    # dependência, a média dos rhos é 0 e a variância de cada um é 1/(k-1).
    ranks = np.argsort(np.argsort(valores, axis=1), axis=1)
    posicao = np.arange(k)
    rho = 1.0 - 6.0 * ((ranks - posicao) ** 2).sum(axis=1) / (k * (k**2 - 1))
    z = float(rho.mean() * np.sqrt((k - 1) * n_validos))
    testes.append(
        (
            "ordem_posicao_x_valor",
            "Correlação entre posição de saída e valor da bola (Spearman médio)",
            z,
            float(2 * stats.norm.sf(abs(z))),
        )
    )

    # Em que posição de saída aparece o menor número do sorteio
    contagens = np.bincount(valores.argmin(axis=1), minlength=k).astype(float)
    esperado = np.full(k, n_validos / k)
    qui2, p = _qui_quadrado(contagens, esperado)
    testes.append(
        (
            "ordem_posicao_do_minimo",
            "Posição de saída em que sai o menor número (uniforme?)",
            qui2,
            p,
        )
    )
    return testes, int(n_validos)


# ----------------------------------------------------------------------
# API pública
# ----------------------------------------------------------------------
def auditar_independencia(
    df: pd.DataFrame,
    config,
    n_permutacoes: int = N_PERMUTACOES,
    seed: int = 0,
    alfa: float = ALFA,
    ajuste: str = "holm",
) -> AuditoriaIndependencia | None:
    """
    Roda a bateria de testes de independência no histórico de um jogo.

    Parameters
    ----------
    df : pd.DataFrame
        Histórico em ordem cronológica, com as colunas `config.draw_cols` na
        ordem em que as bolas foram sorteadas.
    config : GameConfig
        Configuração do jogo.
    n_permutacoes : int
        Embaralhamentos usados nos testes por permutação.
    seed : int
        Semente, para resultado reprodutível.
    alfa : float
        Nível de significância depois do ajuste para múltiplos testes.
    ajuste : {"holm", "bh"}
        "holm" controla a chance de qualquer falso positivo; "bh" controla a
        proporção de falsos positivos entre os rejeitados.

    Returns
    -------
    AuditoriaIndependencia | None
        None se o histórico tiver menos de 100 sorteios.
    """
    if ajuste not in _AJUSTES:
        raise ValueError(f"ajuste deve ser um de {sorted(_AJUSTES)}, recebido {ajuste!r}")
    if df is None or len(df) < MIN_SORTEIOS:
        return None

    valores = df[list(config.draw_cols)].to_numpy(dtype=int)
    rng = np.random.default_rng(seed)
    soma = valores.sum(axis=1).astype(float)

    brutos: list[Teste] = []
    brutos += _testes_soma(soma, max(1, int(n_permutacoes)), rng)
    brutos.append(_teste_repeticao(valores, config.n_numbers, config.k))
    testes_ordem, n_validos = _testes_ordem(df, config)
    brutos += testes_ordem

    p_ajustados = _AJUSTES[ajuste](np.array([t[3] for t in brutos]))
    testes = [
        ResultadoTeste(
            nome=nome,
            descricao=descricao,
            estatistica=round(float(estatistica), 6),
            p_valor=float(p),
            p_ajustado=float(p_aj),
        )
        for (nome, descricao, estatistica, p), p_aj in zip(brutos, p_ajustados)
    ]
    return AuditoriaIndependencia(
        jogo=getattr(config, "name", getattr(config, "slug", "")),
        n_sorteios=len(df),
        n_sorteios_ordem=n_validos,
        alfa=alfa,
        ajuste=ajuste,
        testes=testes,
    )
