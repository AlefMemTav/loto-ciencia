"""Testes de regressão e validação estatística para os Blocos 1–5."""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.cli import conferir, game_day
from app.core.lottery.catalog import LOTOFACIL, LOTOMANIA, MEGASENA, QUINA
from app.core.matrices import (
    construir_covering_design,
    gerar_fechamento_detalhado,
    sugerir_base_antipopular,
    verificar_garantia_fechamento,
)
from app.core.statistics.advanced import indice_dispersao
from app.core.statistics.auditoria_registro import (
    auditar_historico_registro,
    calcular_e_valor_sequencial,
    calcular_tamanho_amostra_auditoria,
    formatar_relatorio_auditoria,
)
from app.core.statistics.cluster_profile import analisar_perfil_cluster
from app.core.statistics.clustering import (
    INDEPENDENT_FEATURE_INDICES,
    clusterizar_jogos_kmeans,
)
from app.core.statistics.distributions import (
    analise_poisson,
    testar_distribuicao_gaps_bilhete,
)
from app.core.statistics.monte_carlo import bootstrap_ic_soma
from app.core.statistics.ordem_saida import auditar_ordem_saida
from app.core.statistics.patterns import detectar_progressao_aritmetica_geral
from app.core.statistics.popularidade_medida import (
    filtrar_arrecadacao_valida_causal,
    treinar_modelo_popularidade,
)
from app.core.statistics.prize_model import (
    calcular_kelly_fracionado,
    comparar_ev_modalidades,
    estimar_ev_concurso_ex_ante,
)
from app.core.statistics.strategy_matrix import _score_composto
from app.core.validator import validar_jogo
from app.services.lottery_service import LotteryService
from app.ui.views.bolao import _processar_input_jogos
import atualizar_loterias


# =====================================================================
# BLOCO 1: Econometria de Popularidade & Gatekeeper EV / Conformal / Kelly
# =====================================================================


def test_filtrar_arrecadacao_valida_causal_descarta_anomalia_tipo_concurso_994():
    arr = np.full(60, 35_000_000.0)
    arr[45] = 158.15  # anomalia de 5 ordens de grandeza
    mask = filtrar_arrecadacao_valida_causal(arr)
    assert bool(mask[45]) is False
    assert int(mask.sum()) == 59


def test_popularidade_medida_megasena_huber_e_pares_real():
    svc = LotteryService()
    ctx = svc.get_context(MEGASENA.slug)
    mod = ctx.modelo_popularidade
    assert mod is not None
    diag = mod.diagnostico_modelo()
    assert diag["n_outliers_filtrados"] >= 1
    assert diag["r2_cv"] > 0.65
    assert diag["conformal_q90_log"] > 0.0
    assert diag["usa_huber"] is True
    assert diag["usa_interacoes_pares"] is True

    aval = mod.avaliar([7, 19, 34, 41, 52, 58])
    assert aval["razao_ic90_low"] <= aval["razao_ganhadores"] <= aval["razao_ic90_high"]


def test_prize_model_concursos_especiais_ex_ante_e_conformal():
    # Verifica nos dados reais que Virada 2955 não dispara falso EV positivo
    det = pd.read_csv(Path("data/detalhes/megasena_detalhes.csv"))
    det_pre = det[det["Concurso"] <= 2954].copy()
    if len(det_pre) > 100:
        ev = estimar_ev_concurso_ex_ante(
            MEGASENA,
            detalhes_df=det_pre,
            razao_popularidade=0.75,
            conformal_q90_log_pop=0.25,
        )
        assert ev["disponivel"] is True
        assert ev["concurso_especial_detectado"] is True
        assert ev["ev_por_real_ic90_low"] <= ev["ev_por_real_ajustado"] <= ev["ev_por_real_ic90_high"]
        assert ev["recomendacao_aposta"] != "APOSTAR_EV_POSITIVO"


def test_kelly_fracionado_zera_em_ev_negativo_e_limita_em_ev_positivo():
    k_neg = calcular_kelly_fracionado(MEGASENA, ev_por_real=0.72, pool1_estimado=5e7, banca=1000.0)
    assert k_neg["aposta_sugerida"] == 0.0
    assert k_neg["jogos_sugeridos"] == 0

    k_pos = calcular_kelly_fracionado(
        MEGASENA,
        ev_por_real=1.25,
        pool1_estimado=1e8,
        banca=10_000.0,
        fracao_kelly=0.25,
        teto_banca=0.05,
    )
    assert 0.0 < k_pos["f_kelly_fracionado"] <= 0.05
    assert k_pos["aposta_sugerida"] <= 500.0


def test_comparar_ev_modalidades_retorna_ranking_ordenado():
    comp = comparar_ev_modalidades(agio_bolao=0.10, banca=500.0, modo_estrito=True)
    assert len(comp["ranking"]) == 4
    evs = [r["ev_por_real_ajustado"] for r in comp["ranking"] if r.get("disponivel")]
    assert evs == sorted(evs, reverse=True)


# =====================================================================
# BLOCO 2: Matrizes de Fechamento (Covering Designs Verificados)
# =====================================================================


@pytest.mark.parametrize(
    "v,k,t,m",
    [
        (8, 6, 5, 6),   # Mega Quina-se-6
        (9, 6, 4, 6),   # Mega Quadra-se-6
        (8, 6, 4, 4),   # Mega Quadra-se-4
        (7, 5, 4, 5),   # Quina Quadra-se-5
        (8, 5, 3, 5),   # Quina Terno-se-5
        (8, 5, 3, 3),   # Quina Terno-se-3
    ],
)
def test_covering_designs_verificacao_exaustiva_100pct(v, k, t, m):
    blocos = construir_covering_design(v=v, k=k, t=t, m=m)
    base = list(range(1, v + 1))
    jogos = [[base[idx] for idx in b] for b in blocos]
    ver = verificar_garantia_fechamento(jogos, base, t_garantia=t, m_condicao=m)
    assert ver["verificado"] is True
    assert ver["cobertura_pct"] == 100.0
    assert ver["piso_acertos"] >= t


def test_fechamento_detalhado_e_sugestao_antipopular():
    svc = LotteryService()
    ctx = svc.get_context(MEGASENA.slug)
    base = sugerir_base_antipopular(MEGASENA, 9, ctx.modelo_popularidade)
    assert len(base) == 9
    assert len(set(base)) == 9
    assert all(1 <= n <= 60 for n in base)

    det = gerar_fechamento_detalhado(base, MEGASENA, garantia_t=4, condicao_m=6)
    assert det["garantia_verificada"] is True
    assert det["garantia_t"] == 4 and det["condicao_m"] == 6
    ver = verificar_garantia_fechamento(det["jogos"], base, t_garantia=4, m_condicao=6)
    assert ver["verificado"] is True and ver["cobertura_pct"] == 100.0
    assert len(det["jogos"]) < 84  # bem menor que C(9,6)=84


# =====================================================================
# BLOCO 3: Correções Estatísticas e Bugs Estruturais
# =====================================================================


def test_bootstrap_predicao_bilhete_unico_lotomania_e_megasena():
    rng = np.random.default_rng(123)
    svc = LotteryService()

    for cfg in (MEGASENA, LOTOMANIA):
        ctx = svc.get_context(cfg.slug)
        ic = bootstrap_ic_soma(ctx.df, cfg, n_iteracoes=1000, random_state=42)
        assert "pred_lower" in ic and "pred_upper" in ic
        assert "ic_media_lower" in ic and "ic_media_upper" in ic
        assert ic["pred_upper"] - ic["pred_lower"] > ic["ic_media_upper"] - ic["ic_media_lower"]

        dentro = 0
        for _ in range(100):
            jogo = rng.choice(np.arange(1, cfg.n_numbers + 1), size=cfg.bet_size, replace=False)
            if ic["pred_lower"] <= int(jogo.sum()) <= ic["pred_upper"]:
                dentro += 1
        assert dentro >= 85, f"{cfg.slug}: apenas {dentro}/100 bilhetes aleatórios dentro de pred 95%"


def test_cluster_mahalanobis_nao_colinear_e_lotomania_sem_100pct_outliers():
    assert len(INDEPENDENT_FEATURE_INDICES) == 7
    svc = LotteryService()
    ctx_lm = svc.get_context(LOTOMANIA.slug)
    rng = np.random.default_rng(77)

    outliers = 0
    for _ in range(40):
        jogo = sorted(rng.choice(np.arange(1, 101), size=50, replace=False).tolist())
        perfil = analisar_perfil_cluster(
            jogo, ctx_lm.df, LOTOMANIA, clusters_cache=ctx_lm.clusters_historicos
        )
        assert perfil["disponivel"] is True
        assert "distancia_mahalanobis" in perfil
        assert "limiar_mahalanobis_p95" in perfil
        if perfil["is_outlier"]:
            outliers += 1
    assert outliers <= 10, f"Muitos falsos outliers na Lotomania: {outliers}/40"


def test_pa_completa_detectada_em_lotofacil_e_lotomania():
    pa_lf = list(range(1, 16))
    r_lf = detectar_progressao_aritmetica_geral(pa_lf, LOTOFACIL)
    assert r_lf["pa_detectada"] is True
    assert r_lf["tipo"] == "completa"
    assert r_lf["penalidade"] >= 20

    pa_lm = list(range(1, 51))
    r_lm = detectar_progressao_aritmetica_geral(pa_lm, LOTOMANIA)
    assert r_lm["pa_detectada"] is True
    assert r_lm["tipo"] == "completa"
    assert r_lm["penalidade"] >= 20


def test_analise_poisson_e_indice_dispersao_sem_reposicao():
    svc = LotteryService()
    ctx_lf = svc.get_context(LOTOFACIL.slug)

    res_p = analise_poisson(ctx_lf.df, LOTOFACIL, alpha=1.01)
    assert isinstance(res_p, list)
    assert len(res_p) == 10
    assert all("p_value_bruto" in item and "p_value" in item for item in res_p)
    assert all(item["p_value"] >= item["p_value_bruto"] - 1e-6 for item in res_p)

    disp = indice_dispersao(ctx_lf.df, LOTOFACIL)
    assert "fator_sem_reposicao" in disp
    expected_fpc = (1.0 - LOTOFACIL.k / LOTOFACIL.n_numbers) * LOTOFACIL.n_numbers / (
        LOTOFACIL.n_numbers - 1
    )
    assert disp["fator_sem_reposicao"] == pytest.approx(expected_fpc, rel=1e-3)


def test_gaps_bilhete_calibrado_discretamente_sem_falsos_positivos_em_jogos_densos():
    rng = np.random.default_rng(99)
    alertas = 0
    for _ in range(50):
        jogo = sorted(rng.choice(np.arange(1, 26), size=15, replace=False).tolist())
        res = testar_distribuicao_gaps_bilhete(jogo, LOTOFACIL)
        if res["penalidade"] > 0:
            alertas += 1
    assert alertas <= 10


def test_ordem_saida_inclui_fft_fisher_e_sample_entropy():
    svc = LotteryService()
    ctx = svc.get_context(MEGASENA.slug)
    aud = auditar_ordem_saida(ctx.df, MEGASENA)
    assert aud["disponivel"] is True
    assert "fft_d1_g" in aud
    assert "fft_d1_p_fisher" in aud
    assert 0.0 <= aud["fft_d1_p_fisher"] <= 1.0
    assert "sampen_d1" in aud
    assert aud["sampen_d1"] is not None and aud["sampen_d1"] > 0.0


def test_aneis_centro_simetrico_zero_based():
    aneis = MEGASENA.layout.aneis
    # Os 4 cantos (1, 10, 51, 60) devem estar todos no anel Externo por simetria exata
    for canto in (1, 10, 51, 60):
        assert canto in aneis["Externo"]
    # O miolo central (25, 26, 35, 36) deve estar no anel Interno
    for centro in (25, 26, 35, 36):
        assert centro in aneis["Interno"]


def test_strategy_matrix_score_composto_respeita_densidade():
    def _m(v: float) -> dict[str, float]:
        return {"media": v, "desvio": 0.0}

    metrics = {
        "hit_4": _m(10.0),
        "hit_5": _m(1.0),
        "hit_6": _m(0.0),
        "delta_medio_acertos_vs_mc": _m(0.0),
        "max_acertos_observado": _m(13.0),
        "win_rate_media_acertos_vs_mc": _m(0.5),
        "ic95_delta_acertos_low": _m(-0.1),
        "delta_medio_vs_acaso": _m(0.0),
        "roi": _m(-0.3),
        "delta_medio_receita_vs_mc": _m(0.0),
        "win_rate_receita_vs_mc": _m(0.5),
        "max_exposicao": _m(14.0),         # normal na Lotofácil (lim 15), extremo na Mega (lim 6)
        "overlap_max": _m(11.0),           # normal na Lotofácil (lim 12), extremo na Mega (lim 3)
        "pares_repetidos_acima_2": _m(50.0),
        "trincas_repetidas": _m(40.0),
        "quadras_repetidas": _m(10.0),
        "calibracao_js_vs_alvo": _m(0.03),
    }
    sc_dense = _score_composto(metrics, [{"jogo": "loto_facil_sorteio"}, {"jogo": "loto_facil_sorteio"}])
    sc_sparse = _score_composto(metrics, [{"jogo": "mega_sena_sorteio"}, {"jogo": "mega_sena_sorteio"}])
    assert sc_dense > sc_sparse + 20.0


# =====================================================================
# BLOCO 4: UI Bolão & Atualizador sem FutureWarning
# =====================================================================


def test_bolao_normaliza_00_para_100_na_lotomania():
    nums_txt = "00 " + " ".join(f"{n:02d}" for n in range(1, 50))
    validos, invalidos, _ = _processar_input_jogos(nums_txt, LOTOMANIA)
    assert len(validos) == 1
    assert len(invalidos) == 0
    assert 100 in validos[0]
    assert 0 not in validos[0]


def test_atualizar_loterias_sem_future_warning_e_sem_duplicatas(tmp_path, monkeypatch):
    monkeypatch.setattr(atualizar_loterias, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(atualizar_loterias, "DETALHES_DIR", str(tmp_path / "detalhes"))

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        atualizar_loterias.salvar_detalhes(
            "megasena",
            pd.DataFrame(),
            [{"Concurso": 10, "Data": "01/01/2026", "valorArrecadado": 1000.0}],
        )
        df_exist = pd.read_csv(tmp_path / "detalhes" / "megasena_detalhes.csv")
        atualizar_loterias.salvar_detalhes(
            "megasena",
            df_exist,
            [
                {"Concurso": 10, "Data": "01/01/2026", "valorArrecadado": 1000.0},
                {"Concurso": 11, "Data": "04/01/2026", "valorArrecadado": 2000.0},
            ],
        )

    future_warns = [w for w in caught if issubclass(w.category, FutureWarning)]
    assert future_warns == []

    df_det = pd.read_csv(tmp_path / "detalhes" / "megasena_detalhes.csv")
    assert df_det["Concurso"].tolist() == [11, 10]


# =====================================================================
# BLOCO 5: Auditoria Sequencial Anytime-Valid & CLIs
# =====================================================================


def test_e_valor_sequencial_controla_nulo_e_detecta_drift():
    rng = np.random.default_rng(2026)
    nulo = rng.uniform(-0.4, 0.4, size=120)
    res_nulo = calcular_e_valor_sequencial(nulo, bilateral=True)
    assert res_nulo["rejeita_alpha_01"] is False
    assert 0.0 < res_nulo["p_anytime"] <= 1.0

    sinal = np.full(80, 0.30)
    res_sinal = calcular_e_valor_sequencial(sinal, bilateral=False)
    assert res_sinal["rejeita_alpha_05"] is True
    assert res_sinal["p_anytime"] < 0.01


def test_calculadora_poder_amostral_todas_modalidades():
    for j in ("mega_sena", "quina", "loto_facil", "loto_mania"):
        p = calcular_tamanho_amostra_auditoria(j, n_jogos_pacote=10)
        assert p["disponivel"] is True
        assert p["eventos_rateados_para_retencao_10pct"] > p["eventos_rateados_para_retencao_20pct"] > 0
        assert p["pacotes_para_retencao_10pct"] > p["pacotes_para_retencao_20pct"] > 0


def test_conferir_com_rateio_real_e_auditoria_sequencial_end_to_end(tmp_path):
    # Usa um concurso real de data/detalhes/megasena_detalhes.csv
    det = pd.read_csv(Path("data/detalhes/megasena_detalhes.csv"))
    conc_real = int(det.iloc[0]["Concurso"])
    pacote = {
        "status": "aprovado",
        "meta": {"ultimo_concurso": conc_real - 1},
        "jogos": [
            [1, 2, 3, 4, 5, 6],
            [10, 20, 30, 40, 50, 60],
        ],
        "validacao": [
            {"jogo": [1, 2, 3, 4, 5, 6], "razao_ganhadores": 0.72},
            {"jogo": [10, 20, 30, 40, 50, 60], "razao_ganhadores": 0.68},
        ],
    }
    res = conferir.conferir_pacote(
        "mega_sena",
        pacote,
        conc_real,
        {1, 2, 3, 4, 50, 60},  # acerta Quadra no jogo 1
        pasta_dados=Path("data"),
    )
    assert res["status"] == "conferido"
    assert res["auditoria_rateio"]["disponivel"] is True
    assert res["auditoria_rateio"]["custo_pacote"] == 12.0
    assert res["auditoria_rateio"]["premio_realizado_total"] > 0.0
    assert res["auditoria_rateio"]["razao_ganhadores_media_pacote"] == pytest.approx(0.70, abs=1e-4)

    # Grava no diretório temporário + um pacote reprovado não conferido para testar alerta de censura
    dir_ok = tmp_path / "pacotes" / "2026-11-17" / "mega_sena"
    dir_ok.mkdir(parents=True)
    (dir_ok / "package.json").write_text(json.dumps(pacote), encoding="utf-8")
    (dir_ok / "resultado.json").write_text(json.dumps(res), encoding="utf-8")

    dir_rep = tmp_path / "pacotes" / "2026-11-19" / "mega_sena"
    dir_rep.mkdir(parents=True)
    (dir_rep / "package.json").write_text(
        json.dumps({"status": "reprovado", "jogos": pacote["jogos"]}), encoding="utf-8"
    )

    aud = auditar_historico_registro(tmp_path)
    assert aud["disponivel"] is True
    assert aud["global"]["n_pacotes_conferidos"] == 1
    assert aud["por_jogo"]["mega_sena"]["censura_amostral"]["alerta_censura"] is True
    txt = formatar_relatorio_auditoria(aud)
    assert "Auditoria Sequencial Anytime-Valid" in txt
    assert "Censura amostral" in txt


def test_game_day_comparar_modalidades_cli(capsys):
    rc = game_day.main(["--comparar-modalidades", "--agio", "0.15", "--banca", "500"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Comparativo Ex-Ante de EV entre Modalidades" in out
    assert "Mega-Sena" in out
    assert "Lotofácil" in out
