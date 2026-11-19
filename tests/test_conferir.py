"""Testes do conferidor de pacotes."""

import csv
import json
from datetime import date

import pandas as pd
import pytest

from app.cli import conferir as cf


def _planilha(pasta, slug, linhas):
    pasta.mkdir(exist_ok=True)
    pd.DataFrame(linhas).to_excel(pasta / f"{slug}.xlsx", index=False)


def _pacote(registro, dia, jogo, jogos, ultimo=10, status="aprovado"):
    d = registro / "pacotes" / dia / jogo
    d.mkdir(parents=True)
    (d / "package.json").write_text(
        json.dumps({"status": status, "jogos": jogos, "meta": {"ultimo_concurso": ultimo}})
    )
    return d


def test_contar_acertos_e_esperado():
    assert cf.contar_acertos([1, 2, 3, 4, 5], {3, 4, 5, 70, 71}) == 3
    assert cf.acertos_esperados(60, 6, 6) == 0.6
    assert cf.acertos_esperados(100, 20, 50) == 10


def test_achar_sorteio_por_data(tmp_path):
    _planilha(tmp_path, "quina_sorteio", [
        {"Concurso": 11, "Data": "10/11/2026", "bola 1": 1, "bola 2": 2, "bola 3": 3, "bola 4": 4, "bola 5": 5},
        {"Concurso": 10, "Data": "09/11/2026", "bola 1": 9, "bola 2": 8, "bola 3": 7, "bola 4": 6, "bola 5": 5},
    ])
    assert cf.achar_sorteio("quina_sorteio", date(2026, 11, 10), tmp_path) == (11, {1, 2, 3, 4, 5})
    assert cf.achar_sorteio("quina_sorteio", date(2026, 11, 12), tmp_path) is None


def test_conferir_pacote_premiado_e_invalido():
    pacote = {"jogos": [[1, 2, 3, 4, 5], [1, 2, 3, 70, 71], [40, 41, 42, 43, 44]], "meta": {"ultimo_concurso": 10}}
    r = cf.conferir_pacote("quina", pacote, 11, {1, 2, 3, 4, 5})
    assert r["acertos"] == [5, 3, 0] and r["melhor"] == 5
    assert r["premios"] == ["quina", "terno"]
    pacote["meta"]["ultimo_concurso"] = 11  # gerado depois do sorteio
    assert cf.conferir_pacote("quina", pacote, 11, {1, 2, 3, 4, 5})["status"] == "invalido"


def test_main_confere_grava_historico_e_e_idempotente(tmp_path):
    dados, reg = tmp_path / "data", tmp_path / "registro"
    _planilha(dados, "quina_sorteio", [
        {"Concurso": 11, "Data": "10/11/2026", "bola 1": 1, "bola 2": 2, "bola 3": 3, "bola 4": 4, "bola 5": 5},
    ])
    d = _pacote(reg, "2026-11-10", "quina", [[1, 2, 3, 40, 41], [50, 51, 52, 53, 54]])
    pendente = _pacote(reg, "2026-11-12", "quina", [[1, 2, 3, 4, 5]], ultimo=11)
    reprovado = _pacote(reg, "2026-11-10", "mega_sena", [[1, 2, 3, 4, 5, 6]], status="reprovado")

    assert cf.main(["--registro", str(reg), "--dados", str(dados)]) == 0
    r = json.loads((d / "resultado.json").read_text())
    assert r["acertos"] == [3, 0] and r["premios"] == ["terno"]
    assert not (pendente / "resultado.json").exists()
    assert not (reprovado / "resultado.json").exists()
    linhas = list(csv.DictReader((reg / "historico.csv").open()))
    assert len(linhas) == 1 and linhas[0]["faixas"] == "terno" and linhas[0]["esperado_aleatorio"] == "0.3125"

    cf.main(["--registro", str(reg), "--dados", str(dados)])  # 2ª rodada não duplica
    assert len(list(csv.DictReader((reg / "historico.csv").open()))) == 1

    # Com --incluir-reprovados, pacotes reprovados também podem ser auditados sem censura
    _planilha(dados, "mega_sena_sorteio", [
        {"Concurso": 11, "Data": "10/11/2026", "bola 1": 1, "bola 2": 2, "bola 3": 3, "bola 4": 4, "bola 5": 5, "bola 6": 6},
    ])
    assert cf.main(["--registro", str(reg), "--dados", str(dados), "--incluir-reprovados"]) == 0
    assert (reprovado / "resultado.json").exists()


def test_variancia_media_acertos_exata_e_controle_pareado():
    # Lotofácil M=5 cíclico com exposição perfeitamente uniforme (cada dezena 1..25 aparece 3 vezes)
    jogos_uniformes = [
        list(range(1, 16)),
        list(range(6, 21)),
        list(range(11, 26)),
        list(range(1, 6)) + list(range(16, 26)),
        list(range(1, 11)) + list(range(21, 26)),
    ]
    assert cf.variancia_media_acertos_exata(jogos_uniformes, 25, 15) == pytest.approx(0.0, abs=1e-12)

    # Pacote concentrado tem variância positiva e controle pareado determinístico
    jogos_concentrados = [list(range(1, 16)) for _ in range(5)]
    var_conc = cf.variancia_media_acertos_exata(jogos_concentrados, 25, 15)
    assert var_conc > 1.0

    pacote = {"jogos": jogos_uniformes, "meta": {"ultimo_concurso": 10}}
    r = cf.conferir_pacote("loto_facil", pacote, 11, set(range(1, 16)))
    ctrl = r["controle_pareado"]
    assert ctrl["n_simulacoes"] == 100
    assert 0.0 <= ctrl["p_premio_controle_condicional"] <= 1.0
    assert 0.0 < ctrl["p_premio_aleatorio_exato"] < 1.0
    assert ctrl["media_bilhetes_premiados_exata"] > 0.0
    assert ctrl["delta_premio_pareado"] == pytest.approx(
        round(1.0 - ctrl["p_premio_aleatorio_exato"], 4), abs=1e-4
    )
    assert ctrl["dp_media_acertos_teorico"] == 0.0
    assert ctrl["z_exposicao_hipergeometrica"] == 0.0


def test_lotomania_normaliza_bola_zero_para_100_em_achar_sorteio_e_conferir(tmp_path):
    """Regressão: planilhas da Caixa gravam a bola 00 como 0, mas os jogos usam 1..100."""
    bolas_raw = [0] + list(range(1, 20))  # 20 bolas incluindo 00 -> 100
    linha = {"Concurso": 3001, "Data": "10/11/2026"}
    for i, b in enumerate(bolas_raw, start=1):
        linha[f"bola {i}"] = b
    _planilha(tmp_path, "loto_mania_sorteio", [linha])

    achado = cf.achar_sorteio("loto_mania_sorteio", date(2026, 11, 10), tmp_path)
    assert achado is not None
    concurso, sorteio = achado
    assert concurso == 3001
    assert 0 not in sorteio and 100 in sorteio and len(sorteio) == 20

    # Bilhete contendo 1..19 + 100 + 50..79 deve acertar todas as 20 bolas (inclusive 100)
    jogo_20 = list(range(1, 20)) + [100] + list(range(50, 80))
    assert len(jogo_20) == 50
    pacote = {"jogos": [jogo_20], "meta": {"ultimo_concurso": 3000}}

    # Deve funcionar tanto com o conjunto já normalizado quanto se o chamador passar 0 cru
    r_norm = cf.conferir_pacote("loto_mania", pacote, 3001, sorteio)
    r_raw = cf.conferir_pacote("loto_mania", pacote, 3001, set(bolas_raw))
    assert r_norm["acertos"] == [20]
    assert r_raw["acertos"] == [20]
    assert r_raw["sorteio"] == sorted(sorteio)
    assert r_raw["premios"] == ["20"]
    p1 = cf._prob_premio_bilhete_exata(100, 20, 50, set(cf.FAIXAS["loto_mania"].keys()))
    assert r_raw["controle_pareado"]["p_premio_aleatorio_exato"] == pytest.approx(p1, abs=1e-4)


def test_conferir_pacote_vazio_nao_quebra():
    pacote = {"jogos": [], "meta": {"ultimo_concurso": 10}}
    r = cf.conferir_pacote("quina", pacote, 11, {1, 2, 3, 4, 5})
    assert r["status"] == "invalido"
    assert r["motivo"] == "pacote sem jogos"
    assert r["concurso"] == 11
