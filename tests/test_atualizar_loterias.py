"""Testes offline do atualizador (sem acessar a API), usando respostas reais."""

import json

import pandas as pd
import pytest

import atualizar_loterias as al

MEGA_3082 = {
    "loteria": "megasena",
    "concurso": 3082,
    "data": "06/11/2026",
    "local": "ESPAÇO DA SORTE em SÃO PAULO, SP",
    "concursoEspecial": False,
    "dezenasOrdemSorteio": ["24", "38", "04", "16", "23", "44"],
    "premiacoes": [
        {"descricao": "6 acertos", "faixa": 1, "ganhadores": 0, "valorPremio": 0.0},
        {"descricao": "5 acertos", "faixa": 2, "ganhadores": 81, "valorPremio": 20116.27},
        {"descricao": "4 acertos", "faixa": 3, "ganhadores": 4527, "valorPremio": 514.19},
    ],
    "acumulou": True,
    "localGanhadores": [],
    "valorArrecadado": 53156880.0,
    "valorAcumuladoConcursoEspecial": 146458644.0,
    "valorAcumuladoProximoConcurso": 53861161.13,
    "valorEstimadoProximoConcurso": 60000000.0,
}

LOTOFACIL_3823 = {
    "loteria": "lotofacil",
    "concurso": 3823,
    "data": "06/11/2026",
    "local": "ESPAÇO DA SORTE em SÃO PAULO, SP",
    "concursoEspecial": False,
    "premiacoes": [
        {"faixa": 1, "ganhadores": 2, "valorPremio": 976316.42},
        {"faixa": 2, "ganhadores": 140, "valorPremio": 2924.45},
        {"faixa": 3, "ganhadores": 5639, "valorPremio": 35.0},
        {"faixa": 4, "ganhadores": 81952, "valorPremio": 14.0},
        {"faixa": 5, "ganhadores": 490644, "valorPremio": 7.0},
    ],
    "acumulou": False,
    "localGanhadores": [
        {"ganhadores": 1, "municipio": "CANAL ELETRONICO", "uf": "--"},
        {"ganhadores": 1, "municipio": "SAO BERNARDO DO CAMPO", "uf": "SP"},
    ],
    "valorArrecadado": 21188296.5,
    "valorAcumuladoProximoConcurso": 0.0,
    "valorEstimadoProximoConcurso": 2000000.0,
}


def test_linha_megasena():
    linha = al.criar_linha_detalhes(MEGA_3082)
    assert linha["Concurso"] == 3082
    assert linha["acumulou"] is True
    assert linha["valorArrecadado"] == 53156880.0
    assert linha["faixa3_ganhadores"] == 4527
    assert linha["faixa2_premio"] == 20116.27
    assert "faixa4_ganhadores" not in linha
    assert json.loads(linha["localGanhadores"]) == []


def test_linha_lotofacil_guarda_local_dos_ganhadores():
    linha = al.criar_linha_detalhes(LOTOFACIL_3823)
    assert linha["faixa5_ganhadores"] == 490644
    locais = json.loads(linha["localGanhadores"])
    assert [l["municipio"] for l in locais] == ["CANAL ELETRONICO", "SAO BERNARDO DO CAMPO"]


def test_concurso_antigo_com_campos_faltando_nao_quebra():
    linha = al.criar_linha_detalhes({"concurso": 1, "premiacoes": None})
    assert linha["Concurso"] == 1
    assert linha["valorArrecadado"] is None
    assert json.loads(linha["localGanhadores"]) == []


def test_salvar_ordena_colunas_e_nao_duplica(tmp_path, monkeypatch):
    monkeypatch.setattr(al, "DETALHES_DIR", str(tmp_path))
    mega = al.criar_linha_detalhes(MEGA_3082)
    antigo = al.criar_linha_detalhes({**MEGA_3082, "concurso": 3081})
    al.salvar_detalhes("megasena", al.ler_detalhes("megasena"), [antigo])
    al.salvar_detalhes("megasena", al.ler_detalhes("megasena"), [mega, mega])

    df = pd.read_csv(tmp_path / "megasena_detalhes.csv")
    assert list(df["Concurso"]) == [3082, 3081]
    cols = list(df.columns)
    assert cols.index("faixa1_ganhadores") < cols.index("faixa10_ganhadores") if "faixa10_ganhadores" in cols else True
    assert cols[-1] == "localGanhadores"


def test_backfill_respeita_limite_e_prioriza_recentes(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    pd.DataFrame({"Concurso": [5, 4, 3, 2, 1]}).to_excel(data / "x.xlsx", index=False)
    monkeypatch.setattr(al, "DATA_DIR", str(data))
    monkeypatch.setattr(al, "DETALHES_DIR", str(data / "detalhes"))
    monkeypatch.setattr(al, "LIMITE_BACKFILL", 2)
    monkeypatch.setattr(al.time, "sleep", lambda *_: None)
    buscados = []

    def falso(loteria, concurso):
        buscados.append(concurso)
        return {**MEGA_3082, "concurso": concurso}

    monkeypatch.setattr(al, "buscar_resultado_concurso", falso)
    al.atualizar_detalhes("megasena", "x.xlsx", [])
    assert buscados == [5, 4]
    assert set(al.ler_detalhes("megasena")["Concurso"]) == {5, 4}

    buscados.clear()
    al.atualizar_detalhes("megasena", "x.xlsx", [])
    assert buscados == [3, 2]


def test_backfill_para_apos_falhas_seguidas(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    pd.DataFrame({"Concurso": list(range(1, 21))}).to_excel(data / "x.xlsx", index=False)
    monkeypatch.setattr(al, "DATA_DIR", str(data))
    monkeypatch.setattr(al, "DETALHES_DIR", str(data / "detalhes"))
    monkeypatch.setattr(al.time, "sleep", lambda *_: None)
    chamadas = []
    monkeypatch.setattr(al, "buscar_resultado_concurso", lambda l, c: chamadas.append(c))
    al.atualizar_detalhes("megasena", "x.xlsx", [])
    assert len(chamadas) == al.MAX_FALHAS_SEGUIDAS
