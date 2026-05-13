"""
决策引擎 - 策略管理器

支持运行时切换多种决策算法：
- greedy: 贪心策略（默认）
- conservative: 保守策略
- aggressive: 激进策略
"""
from __future__ import annotations

import logging
from typing import Optional

from .context import BattleContext, DecisionResult
from .strategies import GreedyStrategy, ConservativeStrategy, AggressiveStrategy

logger = logging.getLogger(__name__)


class StrategyManager:
    """
    策略管理器

    用法：
        mgr = StrategyManager()
        mgr.set_strategy('conservative')
        result = mgr.decide(battle_context)
    """

    def __init__(self):
        self.strategies = {
            'greedy': GreedyStrategy(),
            'conservative': ConservativeStrategy(),
            'aggressive': AggressiveStrategy(),
        }
        self.current_strategy: str = 'greedy'

    def set_strategy(self, name: str):
        """切换策略"""
        if name not in self.strategies:
            available = list(self.strategies.keys())
            raise ValueError(f"未知策略: {name}，可用: {available}")
        old = self.current_strategy
        self.current_strategy = name
        logger.info(f"决策策略: {old} → {name}")

    def decide(self, ctx: BattleContext) -> DecisionResult:
        """使用当前策略做出决策"""
        strategy = self.strategies[self.current_strategy]
        result = strategy.decide(ctx)
        result.strategy = strategy.name()
        return result

    def list_strategies(self) -> list[dict]:
        """列出所有可用策略"""
        return [
            {"key": k, "name": v.name()}
            for k, v in self.strategies.items()
        ]

    @property
    def current(self) -> str:
        return self.current_strategy
