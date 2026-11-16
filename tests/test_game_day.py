"""Testes do CLI game_day (sem gerar pacotes de verdade: rápidos)."""

from datetime import date

import pandas as pd

from app.cli import game_day as gd


def _checar(jogos, validacoes=None, diag=None, **kw):
    base = dict(k=5, n_numbers=80, overlap_limit=3, esparso=True, quantidade=len(jogos))
    base.update(kw)
    validacoes = validacoes or [{"ja_saiu": False, "risco_divisao": "Baixo"} for _ in jogos]
    return gd.checar_pacote(jogos, validacoes, diag or {}, **base)


def test_jogos_do_dia_segue_calendario():
    assert gd.jogos_do_dia(date(2026, 11, 10)) == ["mega_sena", "quina", "loto_facil"]  # terça
    assert gd.jogos_do_dia(date(2026, 11, 9)) == ["quina", "loto_facil", "loto_mania"]  # segunda
    assert gd.jogos_do_dia(date(2026, 11, 8)) == []  # domingo


def test_pacote_valido_sem_erros():
    erros, avisos = _checar([[1, 2, 3, 4, 5], [10, 20, 30, 40, 50]])
    assert erros == [] and avisos == []


def test_detecta_jogo_ja_sorteado_e_risco_alto():
    vals = [{"ja_saiu": True, "risco_divisao": "Baixo"}, {"ja_saiu": False, "risco_divisao": "ALTO"}]
    erros, _ = _checar([[1, 2, 3, 4, 5], [10, 20, 30, 40, 50]], vals)
    assert len(erros) == 2


def test_detecta_jogos_repetidos_invalidos_e_quantidade():
    erros, _ = _checar([[1, 2, 3, 4, 5], [5, 4, 3, 2, 1]], quantidade=3)
    assert any("repetidos" in e for e in erros)
    assert any("esperado 3" in e for e in erros)
    erros, _ = _checar([[1, 1, 3, 4, 5]])
    assert any("inválido" in e for e in erros)
    erros, _ = _checar([[1, 2, 3, 4, 99]])
    assert any("inválido" in e for e in erros)


def test_trincas_so_viram_aviso_em_jogos_esparsos():
    diag = {"trincas_repetidas": 2, "max_repeticao_par": 4, "overlap_max": 4}
    _, avisos = _checar([[1, 2, 3, 4, 5]], diag=diag, esparso=True)
    assert len(avisos) == 3
    _, avisos = _checar([[1, 2, 3, 4, 5]], diag=diag, esparso=False)
    assert len(avisos) == 1  # só a sobreposição


def test_dias_desde():
    assert gd._dias_desde("07/11/2026", date(2026, 11, 10)) == 3
    assert gd._dias_desde(None, date(2026, 11, 10)) is None
    assert gd._dias_desde("lixo", date(2026, 11, 10)) is None


def test_ultimo_concurso_le_data_da_planilha(tmp_path, monkeypatch):
    (tmp_path / "data").mkdir()
    pd.DataFrame(
        {"Concurso": [3, 2, 1], "Data": ["09/11/2026", "07/11/2026", "05/11/2026"]}
    ).to_excel(tmp_path / "data" / "quina_sorteio.xlsx", index=False)
    monkeypatch.chdir(tmp_path)
    assert gd._ultimo_concurso(None, "quina_sorteio") == (3, "09/11/2026")


def test_main_rejeita_argumentos_invalidos(capsys):
    assert gd.main(["--quantidade", "0"]) == 2
    assert gd.main(["--data", "xx"]) == 2


def test_main_sem_sorteio_nao_faz_nada(tmp_path):
    assert gd.main(["--data", "2026-11-08", "--out", str(tmp_path)]) == 0
    assert list(tmp_path.iterdir()) == []


def test_main_codigo_de_saida_parcial_em_hoje(tmp_path, monkeypatch):
    chamadas = []

    def falso(jogo, hoje, quantidade, esforco, saida, force):
        chamadas.append(jogo)
        return jogo != "quina"

    monkeypatch.setattr(gd, "gerar", falso)
    assert gd.main(["--data", "2026-11-10", "--out", str(tmp_path)]) == 0
    assert chamadas == ["mega_sena", "quina", "loto_facil"]


def test_main_codigo_de_saida_falha_no_modo_jogo_unico(tmp_path, monkeypatch):
    monkeypatch.setattr(gd, "gerar", lambda *a, **k: False)
    assert gd.main(["--game", "quina", "--data", "2026-11-10", "--out", str(tmp_path)]) == 1


def test_gerar_pula_quando_pacote_ja_existe(tmp_path):
    destino = tmp_path / "2026-11-10" / "quina"
    destino.mkdir(parents=True)
    (destino / "package.json").write_text("{}")
    assert gd.gerar("quina", date(2026, 11, 10), 3, "rapido", tmp_path, force=False) is True
