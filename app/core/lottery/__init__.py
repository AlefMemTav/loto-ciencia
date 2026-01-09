# app/core/lottery/__init__.py
from .models import GameConfig, BoardLayout
from .catalog import GAMES_REGISTRY as GAMES

__all__ = ["GameConfig", "BoardLayout", "GAMES"]
