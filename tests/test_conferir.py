"""Testes do conferidor de pacotes."""

import csv
import json
from datetime import date

import pandas as pd

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
