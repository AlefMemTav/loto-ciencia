# app/api/deps.py
from functools import lru_cache
from app.services.lottery_service import LotteryService


@lru_cache(maxsize=1)
def get_service() -> LotteryService:
    return LotteryService()
