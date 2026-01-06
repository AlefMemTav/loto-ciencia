# app/src/logger.py
import logging
import sys
from pathlib import Path

# Cria diretório de logs se não existir
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


def setup_logger(name: str = "LotoScience"):
    """
    Configura um logger estruturado que escreve em arquivo e no terminal.
    """
    logger = logging.getLogger(name)

    # Evita duplicação de handlers se recarregar o Streamlit
    if logger.hasHandlers():
        return logger

    logger.setLevel(logging.INFO)

    # Formato Profissional: [HORA] [NÍVEL] [ARQUIVO] Mensagem
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(module)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 1. Handler de Arquivo (para histórico)
    file_handler = logging.FileHandler(LOG_DIR / "system.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    # 2. Handler de Console (para ver no terminal enquanto roda)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# Instância global para importação direta
logger = setup_logger()
