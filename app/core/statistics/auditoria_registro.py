"""Auditoria sequencial anytime-valid e análise de poder para o histórico do registro.

Implementa:
1. E-values / martingales de teste exatos (desigualdade de Ville) sobre:
   - excesso de acertos por pacote (bilateral, condicionado ao espaço hipergeométrico),
   - excesso pareado na probabilidade de ao menos um prêmio (Rao-Blackwellizado).
   O p-valor anytime-valid `min(1, 1 / max_t M_t)` controla erro Tipo I em qualquer
   regra de parada (sem viés de *optional stopping* ao olhar o histórico todo dia).
2. Calculadora de poder estatístico e tamanho de amostra necessário (bilhetes/concursos)
   para detectar ganhos de retenção de prêmio (+10% / +20%) ou de taxa de premiação.
3. Auditoria completa da pasta `registro/pacotes/<data>/<jogo>/` com consolidação
   de acertos, retorno financeiro realizado (quando `auditoria_rateio` está disponível)
   e verificação de possível censura amostral (pacotes reprovados não conferidos).
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from statistics import NormalDist
from typing import Any

import numpy as np

_STD_NORMAL = NormalDist(0.0, 1.0)

# Grade log-espaçada fixa para mistura de martingales de apostas em Y_t in [-1, 1].
# Como cada fator (1 + lam * Y_t) > 0 tem esperança exata 1 sob H0, qualquer mistura
# com pesos fixos que somam 1 é um martingale não-negativo exato (Ville's inequality).
_LAMBDA_POS: tuple[float, ...] = (0.02, 0.05, 0.12, 0.25, 0.45)
_LAMBDA_BILATERAL: tuple[float, ...] = tuple(
    [-lam for lam in reversed(_LAMBDA_POS)] + list(_LAMBDA_POS)
)

# Parâmetros estruturais para cálculo de poder por modalidade
_MODALIDADE_SPECS: dict[str, dict[str, Any]] = {
    "mega_sena": {
        "n_universo": 60,
        "k_sorteio": 6,
        "k_aposta": 6,
        "faixas_pagas": (4, 5, 6),
        "faixa_var_ref": 4,  # Quadra (taxa mais alta entre faixas rateadas)
        "sigma_log_pop": 0.30,
    },
    "quina": {
        "n_universo": 80,
        "k_sorteio": 5,
        "k_aposta": 5,
        "faixas_pagas": (2, 3, 4, 5),
        "faixa_var_ref": 3,  # Terno
        "sigma_log_pop": 0.22,
    },
    "loto_facil": {
        "n_universo": 25,
        "k_sorteio": 15,
        "k_aposta": 15,
        "faixas_pagas": (11, 12, 13, 14, 15),
        "faixa_var_ref": 14,  # 14 acertos (primeira faixa rateada)
        "sigma_log_pop": 0.25,
    },
    "loto_mania": {
        "n_universo": 100,
        "k_sorteio": 20,
        "k_aposta": 50,
        "faixas_pagas": (0, 15, 16, 17, 18, 19, 20),
        "faixa_var_ref": 16,  # 16 acertos (rateada de boa frequência)
        "sigma_log_pop": 0.18,
    },
}


def calcular_e_valor_sequencial(
    incrementos: list[float] | np.ndarray,
    *,
    bilateral: bool = True,
    lambdas: tuple[float, ...] | None = None,
) -> dict[str, Any]:
    """
    Calcula o processo de e-valor (martingale de mistura) para incrementos
    limitados `Y_t in [-1, 1]` com média condicional zero sob H0.

    Por desigualdade de Ville:
        P_{H0}(exists t >= 1: M_t >= 1 / alpha) <= alpha.

    Retorna o e-valor atual (`e_valor_atual`), o máximo histórico (`e_valor_max`),
    o p-valor anytime-valid (`p_anytime = min(1, 1 / e_valor_max)`) e a trajetória.
    """
    arr = np.asarray(incrementos, dtype=float)
    arr = arr[np.isfinite(arr)]
    n = int(len(arr))
    if n == 0:
        return {
            "n_obs": 0,
            "e_valor_atual": 1.0,
            "e_valor_max": 1.0,
            "p_anytime": 1.0,
            "rejeita_alpha_05": False,
            "rejeita_alpha_01": False,
        }

    # Trava estritamente em [-1, 1] para garantir 1 + lam * y > 0
    y = np.clip(arr, -1.0, 1.0)
    grade = lambdas if lambdas is not None else (
        _LAMBDA_BILATERAL if bilateral else _LAMBDA_POS
    )
    lam_vec = np.asarray([float(l) for l in grade if -0.95 <= float(l) <= 0.95], dtype=float)
    if len(lam_vec) == 0:
        lam_vec = np.asarray(_LAMBDA_BILATERAL if bilateral else _LAMBDA_POS, dtype=float)

    # log M_t(lam) = sum_{s<=t} log(1 + lam * y_s) em espaço log para estabilidade numérica
    fatores = 1.0 + np.outer(y, lam_vec)  # (n, L)
    fatores = np.maximum(fatores, 1e-12)
    log_cum = np.cumsum(np.log(fatores), axis=0)  # (n, L)

    # log-mean-exp por linha: log( (1/L) * sum_j exp(log_cum[t, j]) )
    max_row = np.max(log_cum, axis=1, keepdims=True)
    log_m = (max_row[:, 0] + np.log(np.mean(np.exp(log_cum - max_row), axis=1)))
    m_traj = np.exp(np.clip(log_m, -500.0, 500.0))

    e_atual = float(m_traj[-1])
    e_max = float(max(1.0, float(np.max(m_traj))))
    p_anytime = float(min(1.0, 1.0 / e_max))

    return {
        "n_obs": n,
        "e_valor_atual": round(e_atual, 6),
        "e_valor_max": round(e_max, 6),
        "p_anytime": round(p_anytime, 6),
        "rejeita_alpha_05": bool(e_max >= 20.0),
        "rejeita_alpha_01": bool(e_max >= 100.0),
    }


def _prob_hiper(n_univ: int, k_sort: int, k_ap: int, h: int) -> float:
    rem_pool = n_univ - k_ap
    rem_draw = k_sort - h
    if h < 0 or rem_draw < 0 or h > k_ap or rem_draw > rem_pool:
        return 0.0
    return float(math.comb(k_ap, h) * math.comb(rem_pool, rem_draw) / math.comb(n_univ, k_sort))


def calcular_tamanho_amostra_auditoria(
    jogo: str,
    n_jogos_pacote: int = 10,
    alpha: float = 0.05,
    poder: float = 0.80,
    sigma_log_pop: float | None = None,
) -> dict[str, Any]:
    """
    Calcula o tamanho de amostra necessário (em eventos premiados e em pacotes conferidos)
    para detectar com poder `poder` (padrão 80%) e significância `alpha` (padrão 5%):
    1. Ganho de retenção de prêmio rateado (+10% e +20%) nos bilhetes premiados.
    2. Aumento relativo de +10% na taxa de pacotes com ao menos 1 prêmio usando
       controle pareado Rao-Blackwellizado (variância metade do pareamento 1:1).
    """
    spec = _MODALIDADE_SPECS.get(jogo)
    if spec is None:
        return {"disponivel": False, "motivo": f"Modalidade desconhecida: {jogo}"}

    n_univ = int(spec["n_universo"])
    k_sort = int(spec["k_sorteio"])
    k_ap = int(spec["k_aposta"])
    m = max(1, int(n_jogos_pacote))
    sig_log = float(sigma_log_pop if sigma_log_pop is not None else spec["sigma_log_pop"])

    z_alpha_one = float(_STD_NORMAL.inv_cdf(1.0 - alpha))
    z_alpha_two = float(_STD_NORMAL.inv_cdf(1.0 - alpha / 2.0))
    z_beta = float(_STD_NORMAL.inv_cdf(poder))

    # 1. Probabilidade de acertar alguma faixa paga e faixa rateada de referência
    p1_any = sum(_prob_hiper(n_univ, k_sort, k_ap, h) for h in spec["faixas_pagas"])
    p_pkg_any = 1.0 - (1.0 - p1_any) ** m
    p1_var = _prob_hiper(n_univ, k_sort, k_ap, int(spec["faixa_var_ref"]))
    p_pkg_var = 1.0 - (1.0 - p1_var) ** m

    # 2. Eventos premiados na faixa rateada necessários para detectar +10% e +20% de retenção
    # Teste unilateral sobre log(premio_real / premio_base): delta = log(1 + ganho)
    def _n_eventos_retencao(ganho_rel: float) -> tuple[int, int]:
        delta = math.log(1.0 + ganho_rel)
        n_ev = int(math.ceil(((z_alpha_one + z_beta) * sig_log / delta) ** 2))
        n_pacotes = int(math.ceil(n_ev / max(p_pkg_var, 1e-12)))
        return n_ev, n_pacotes

    ev_10, pac_10 = _n_eventos_retencao(0.10)
    ev_20, pac_20 = _n_eventos_retencao(0.20)

    # 3. Pacotes necessários para detectar +10% relativo em P(>=1 prêmio) com controle exato
    # Var sob Rao-Blackwell = p_0 * (1 - p_0) (metade de 2 * p_0 * (1 - p_0) do controle 1:1)
    delta_p = 0.10 * p_pkg_any
    if delta_p > 1e-12 and 0.0 < p_pkg_any < 1.0:
        n_pac_premio = int(
            math.ceil(((z_alpha_two + z_beta) ** 2) * p_pkg_any * (1.0 - p_pkg_any) / (delta_p ** 2))
        )
    else:
        n_pac_premio = 0

    return {
        "disponivel": True,
        "jogo": jogo,
        "n_jogos_pacote": m,
        "alpha": alpha,
        "poder": poder,
        "p_pacote_premiar_exata": round(p_pkg_any, 6),
        "faixa_rateada_ref": int(spec["faixa_var_ref"]),
        "p_pacote_faixa_rateada": round(p_pkg_var, 6),
        "sigma_log_popularidade": round(sig_log, 4),
        "eventos_rateados_para_retencao_10pct": ev_10,
        "pacotes_para_retencao_10pct": pac_10,
        "eventos_rateados_para_retencao_20pct": ev_20,
        "pacotes_para_retencao_20pct": pac_20,
        "pacotes_para_lift_10pct_taxa_premio": n_pac_premio,
    }


def auditar_historico_registro(
    registro_dir: str | Path,
    jogo: str | None = None,
    alpha: float = 0.05,
) -> dict[str, Any]:
    """
    Audita todos os pacotes conferidos em `<registro_dir>/pacotes/<data>/<jogo>/`.

    Retorna métricas por modalidade e resumo global, incluindo:
    - e-values e p-valores anytime-valid (acertos e taxa de premiação),
    - Z-score hipergeométrico exato combinado,
    - resumo financeiro realizado (quando `auditoria_rateio` foi gravado),
    - contagem de pacotes reprovados/pendentes para detectar censura amostral,
    - metas de tamanho amostral para 80% de poder.
    """
    raiz = Path(registro_dir)
    pasta_pacotes = raiz / "pacotes"
    if not pasta_pacotes.exists():
        return {
            "disponivel": False,
            "motivo": f"Pasta não encontrada: {pasta_pacotes}",
            "por_jogo": {},
        }

    registros_por_jogo: dict[str, list[dict[str, Any]]] = {}
    censura_por_jogo: dict[str, dict[str, int]] = {}

    for pkg_path in sorted(pasta_pacotes.glob("*/*/package.json")):
        destino = pkg_path.parent
        j_nome = destino.name
        dia_txt = destino.parent.name
        if jogo is not None and j_nome != jogo:
            continue
        if j_nome not in _MODALIDADE_SPECS:
            continue

        cens = censura_por_jogo.setdefault(
            j_nome,
            {
                "total_pacotes": 0,
                "aprovados": 0,
                "reprovados": 0,
                "conferidos": 0,
                "invalidos": 0,
                "reprovados_nao_conferidos": 0,
            },
        )
        cens["total_pacotes"] += 1

        try:
            pacote = json.loads(pkg_path.read_text(encoding="utf-8"))
        except Exception:
            continue

        status_pkg = str(pacote.get("status", "aprovado"))
        if status_pkg == "aprovado":
            cens["aprovados"] += 1
        else:
            cens["reprovados"] += 1

        res_path = destino / "resultado.json"
        if not res_path.exists():
            if status_pkg != "aprovado":
                cens["reprovados_nao_conferidos"] += 1
            continue

        try:
            res = json.loads(res_path.read_text(encoding="utf-8"))
        except Exception:
            continue

        if res.get("status") != "conferido":
            cens["invalidos"] += 1
            continue

        cens["conferidos"] += 1
        registros_por_jogo.setdefault(j_nome, []).append(
            {
                "data": dia_txt,
                "status_pacote": status_pkg,
                "n_jogos": len(pacote.get("jogos") or []),
                "resultado": res,
            }
        )

    por_jogo: dict[str, dict[str, Any]] = {}
    all_hit_inc: list[float] = []
    all_prize_inc: list[float] = []
    all_z_exact: list[float] = []
    total_conferidos = 0
    total_jogos = 0
    total_custo = 0.0
    total_premio = 0.0

    for j_nome, items in sorted(registros_por_jogo.items()):
        spec = _MODALIDADE_SPECS[j_nome]
        k_max = min(int(spec["k_sorteio"]), int(spec["k_aposta"]))
        hit_incs: list[float] = []
        prize_incs: list[float] = []
        z_exacts: list[float] = []
        medias_obs: list[float] = []
        esp_list: list[float] = []
        premiou_list: list[float] = []
        p_exata_list: list[float] = []

        custo_j = 0.0
        premio_j = 0.0
        n_com_rateio = 0
        razoes_pacote: list[float] = []
        n_jogos_j = 0

        for it in items:
            r = it["resultado"]
            n_j = int(it["n_jogos"])
            n_jogos_j += n_j
            media_obs = float(r.get("media_acertos", 0.0))
            esp = float(r.get("esperado_aleatorio", 0.0))
            medias_obs.append(media_obs)
            esp_list.append(esp)

            # Normalização estritamente limitada em [-1, 1] mantendo E[Y_t | F_{t-1}] == 0
            denom_hit = max(esp, float(k_max) - esp, 1.0)
            y_hit = (media_obs - esp) / denom_hit
            hit_incs.append(y_hit)
            all_hit_inc.append(y_hit)

            ctrl = r.get("controle_pareado") or {}
            if "delta_premio_pareado" in ctrl:
                d_prem = float(ctrl["delta_premio_pareado"])
                prize_incs.append(d_prem)
                all_prize_inc.append(d_prem)
                p_ex = float(ctrl.get("p_premio_aleatorio_exato", 0.0))
                p_exata_list.append(p_ex)
                premiou_list.append(1.0 if (r.get("premios") or []) else 0.0)
            if "z_exposicao_hipergeometrica" in ctrl and float(ctrl.get("dp_media_acertos_teorico", 0.0)) > 1e-9:
                z_v = float(ctrl["z_exposicao_hipergeometrica"])
                z_exacts.append(z_v)
                all_z_exact.append(z_v)

            rat = r.get("auditoria_rateio") or {}
            if rat.get("disponivel"):
                n_com_rateio += 1
                custo_j += float(rat.get("custo_pacote", 0.0))
                premio_j += float(rat.get("premio_realizado_total", 0.0))
                if rat.get("razao_ganhadores_media_pacote") is not None:
                    razoes_pacote.append(float(rat["razao_ganhadores_media_pacote"]))

        n_conf = len(items)
        total_conferidos += n_conf
        total_jogos += n_jogos_j
        total_custo += custo_j
        total_premio += premio_j

        e_acertos = calcular_e_valor_sequencial(hit_incs, bilateral=True)
        e_premio = calcular_e_valor_sequencial(prize_incs, bilateral=False)
        z_stouffer = (
            float(sum(z_exacts) / math.sqrt(len(z_exacts)))
            if z_exacts
            else 0.0
        )
        p_stouffer = (
            float(2.0 * (1.0 - _STD_NORMAL.cdf(abs(z_stouffer))))
            if z_exacts
            else 1.0
        )

        m_medio = max(1, int(round(n_jogos_j / max(1, n_conf))))
        poder_info = calcular_tamanho_amostra_auditoria(
            j_nome, n_jogos_pacote=m_medio, alpha=alpha
        )
        cens = censura_por_jogo.get(j_nome, {})
        alerta_censura = int(cens.get("reprovados_nao_conferidos", 0)) > 0

        por_jogo[j_nome] = {
            "n_pacotes_conferidos": n_conf,
            "n_jogos_total": n_jogos_j,
            "media_acertos_obs": round(float(np.mean(medias_obs)), 4) if medias_obs else 0.0,
            "esperado_aleatorio_medio": round(float(np.mean(esp_list)), 4) if esp_list else 0.0,
            "z_stouffer_exposicao": round(z_stouffer, 4),
            "p_stouffer_exposicao": round(p_stouffer, 6),
            "e_processo_acertos_bilateral": e_acertos,
            "e_processo_premio_positivo": e_premio,
            "taxa_pacotes_premiados_obs": round(float(np.mean(premiou_list)), 4) if premiou_list else None,
            "taxa_pacotes_premiados_exata": round(float(np.mean(p_exata_list)), 4) if p_exata_list else None,
            "financeiro_realizado": {
                "n_pacotes_com_rateio": n_com_rateio,
                "custo_total": round(custo_j, 2),
                "premio_bruto_total": round(premio_j, 2),
                "retorno_liquido": round(premio_j - custo_j, 2),
                "roi": round((premio_j - custo_j) / custo_j, 4) if custo_j > 0 else None,
                "razao_ganhadores_media_pacotes": round(float(np.mean(razoes_pacote)), 4)
                if razoes_pacote
                else None,
            },
            "censura_amostral": {
                **cens,
                "alerta_censura": alerta_censura,
            },
            "poder_amostral": poder_info,
        }

    e_global_acertos = calcular_e_valor_sequencial(all_hit_inc, bilateral=True)
    e_global_premio = calcular_e_valor_sequencial(all_prize_inc, bilateral=False)
    z_global = (
        float(sum(all_z_exact) / math.sqrt(len(all_z_exact)))
        if all_z_exact
        else 0.0
    )

    return {
        "disponivel": True,
        "alpha": alpha,
        "global": {
            "n_pacotes_conferidos": total_conferidos,
            "n_jogos_total": total_jogos,
            "z_stouffer_exposicao": round(z_global, 4),
            "p_stouffer_exposicao": round(
                float(2.0 * (1.0 - _STD_NORMAL.cdf(abs(z_global)))), 6
            )
            if all_z_exact
            else 1.0,
            "e_processo_acertos_bilateral": e_global_acertos,
            "e_processo_premio_positivo": e_global_premio,
            "custo_total_rastreado": round(total_custo, 2),
            "premio_bruto_rastreado": round(total_premio, 2),
            "roi_rastreado": round((total_premio - total_custo) / total_custo, 4)
            if total_custo > 0
            else None,
        },
        "por_jogo": por_jogo,
    }


def formatar_relatorio_auditoria(auditoria: dict[str, Any]) -> str:
    """Formata o resultado de `auditar_historico_registro` em texto legível (Markdown)."""
    if not auditoria.get("disponivel"):
        return f"Auditoria indisponível: {auditoria.get('motivo', 'sem dados')}."

    g = auditoria["global"]
    linhas = [
        "# Auditoria Sequencial Anytime-Valid do Registro",
        "",
        f"- Pacotes conferidos: **{g['n_pacotes_conferidos']}** ({g['n_jogos_total']} jogos)",
        f"- E-valor Acertos (bilateral): **{g['e_processo_acertos_bilateral']['e_valor_atual']:.4f}** "
        f"(máx {g['e_processo_acertos_bilateral']['e_valor_max']:.4f}, "
        f"p-anytime={g['e_processo_acertos_bilateral']['p_anytime']:.4f})",
        f"- E-valor Prêmio Pareado (+): **{g['e_processo_premio_positivo']['e_valor_atual']:.4f}** "
        f"(máx {g['e_processo_premio_positivo']['e_valor_max']:.4f}, "
        f"p-anytime={g['e_processo_premio_positivo']['p_anytime']:.4f})",
        f"- Z Stouffer (exposição hipergeométrica exata): **{g['z_stouffer_exposicao']:+.3f}** "
        f"(p={g['p_stouffer_exposicao']:.4f})",
    ]
    if g.get("custo_total_rastreado", 0.0) > 0:
        linhas.append(
            f"- Financeiro rastreado: custo R$ {g['custo_total_rastreado']:.2f} · "
            f"prêmio bruto R$ {g['premio_bruto_rastreado']:.2f} · "
            f"ROI {g['roi_rastreado'] * 100:+.2f}%"
        )

    for j_nome, info in (auditoria.get("por_jogo") or {}).items():
        ea = info["e_processo_acertos_bilateral"]
        ep = info["e_processo_premio_positivo"]
        pod = info["poder_amostral"]
        linhas += [
            "",
            f"## {j_nome}",
            f"- Conferidos: {info['n_pacotes_conferidos']} pacotes ({info['n_jogos_total']} jogos) · "
            f"média {info['media_acertos_obs']:.4f} vs aleatório {info['esperado_aleatorio_medio']:.4f}",
            f"- E-valor acertos: {ea['e_valor_atual']:.4f} (p-anytime={ea['p_anytime']:.4f}) · "
            f"E-valor prêmio(+): {ep['e_valor_atual']:.4f} (p-anytime={ep['p_anytime']:.4f})",
        ]
        if info["taxa_pacotes_premiados_obs"] is not None:
            linhas.append(
                f"- Taxa de pacotes premiados: {info['taxa_pacotes_premiados_obs'] * 100:.2f}% "
                f"(exato aleatório: {info['taxa_pacotes_premiados_exata'] * 100:.2f}%)"
            )
        if pod.get("disponivel"):
            linhas.append(
                f"- Poder 80% (α={auditoria['alpha']}): precisa ~{pod['eventos_rateados_para_retencao_10pct']} "
                f"acertos na faixa {pod['faixa_rateada_ref']} (~{pod['pacotes_para_retencao_10pct']} pacotes) "
                f"para +10% retenção, ou ~{pod['eventos_rateados_para_retencao_20pct']} acertos "
                f"(~{pod['pacotes_para_retencao_20pct']} pacotes) para +20% retenção."
            )
        if info["censura_amostral"].get("alerta_censura"):
            n_nc = info["censura_amostral"]["reprovados_nao_conferidos"]
            linhas.append(
                f"- ⚠️ Censura amostral detectada: {n_nc} pacote(s) reprovado(s) sem conferência "
                f"(use `python -m app.cli.conferir --incluir-reprovados`)."
            )
    return "\n".join(linhas)
