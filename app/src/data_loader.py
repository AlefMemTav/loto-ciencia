# app/src/data_loader.py
import pandas as pd
from app.src.logger import logger
from app.src.games import GameConfig


class DataLoadError(Exception):
    pass


class MissingColumnError(DataLoadError):
    pass


def carregar_dados_loteria_excel(
    config: GameConfig, caminho_arquivo: str
) -> pd.DataFrame:
    logger.info(f"📂 [DATA] Carregando {caminho_arquivo} para {config.name}")

    try:
        df = pd.read_excel(caminho_arquivo)
        logger.info(
            f"✅ [DATA] {config.name}: {len(df)} sorteios carregados, colunas: {list(df.columns)}"
        )
        if df.empty:
            logger.warning(f"⚠️ [DATA] {config.name}: DataFrame vazio!")
    except FileNotFoundError as e:
        logger.error(f"❌ [DATA] Arquivo não encontrado: {caminho_arquivo}")
        raise
    except Exception as e:
        logger.critical(
            f"❌ [DATA] Erro ao carregar  {caminho_arquivo}: {str(e)}", exc_info=True
        )
        raise DataLoadError(f"Erro ao carregar dados: {e}") from e

    cols_norm = {c: str(c).strip().lower() for c in df.columns}

    concurso_col = None
    for c, cn in cols_norm.items():
        if cn == "concurso":
            concurso_col = c
            break
    if concurso_col is None:
        logger.error(
            f"Coluna 'Concurso' não encontrada em {caminho_arquivo}. Cols: {list(cols_norm.values())}"
        )
        raise MissingColumnError("Coluna 'Concurso' não encontrada.")

    bola_cols = []
    for i in range(1, config.k + 1):
        alvo = f"bola {i}"
        achou = None
        for c, cn in cols_norm.items():
            if cn == alvo:
                achou = c
                break
        if achou is None:
            logger.error(f"Colunas ausentes em {caminho_arquivo}: {alvo}")
            raise MissingColumnError(
                f"Coluna '{alvo}' não encontrada (esperado k={config.k})."
            )
        bola_cols.append(achou)

    out = df[[concurso_col] + bola_cols].copy()
    out[concurso_col] = pd.to_numeric(out[concurso_col], errors="coerce")
    out = out.dropna(subset=[concurso_col])
    out[concurso_col] = out[concurso_col].astype(int)
    out = out.set_index(concurso_col)

    out.columns = config.draw_cols
    for c in out.columns:
        out[c] = pd.to_numeric(out[c], errors="coerce")

    out = out.dropna().astype(int)

    if config.slug == "loto_mania_sorteio":
        out = out.replace(0, 100)

    mask = (out >= 1) & (out <= config.n_numbers)
    out = out[mask.all(axis=1)]
    return out.sort_index()
