"""Estratégias de geração suportadas e apelidos dos nomes antigos.

Em medição (Mega-Sena, 4 sementes x 20 jogos) as sete estratégias originais
geravam pacotes que diferiam entre si tanto quanto uma mesma estratégia
difere de si mesma com sementes diferentes. Restam três:

- balanceada: preset único para jogos densos (e padrão geral).
- cauda_controlada: preset para jogos esparsos, com seleção de portfólio por
  conjunto (tetos de exposição e de pares).
- pura: sem sinais históricos; serve de controle e de sorteio estrutural.

Os nomes antigos continuam aceitos como apelidos para não quebrar
configurações, scripts e relatórios já salvos.
"""

from __future__ import annotations

BALANCEADA = "balanceada"
CAUDA_CONTROLADA = "cauda_controlada"
PURA = "pura"

ESTRATEGIAS: tuple[str, ...] = (BALANCEADA, CAUDA_CONTROLADA, PURA)

APELIDOS: dict[str, str] = {
    "agressiva": BALANCEADA,
    "conservadora": BALANCEADA,
    "cauda_agressiva": CAUDA_CONTROLADA,
    "cauda_convexa": CAUDA_CONTROLADA,
}


def normalizar_estrategia(nome: str | None) -> str:
    """Devolve o nome canônico da estratégia (resolve apelidos)."""
    chave = (nome or BALANCEADA).strip().lower()
    chave = APELIDOS.get(chave, chave)
    if chave not in ESTRATEGIAS:
        validos = ", ".join(ESTRATEGIAS + tuple(APELIDOS))
        raise ValueError(f"Estratégia inválida: '{nome}'. Use uma de: {validos}.")
    return chave


def estrategia_padrao(config) -> str:
    """Estratégia padrão por densidade do jogo (esparso -> cauda_controlada)."""
    return CAUDA_CONTROLADA if getattr(config, "is_sparse", False) else BALANCEADA
