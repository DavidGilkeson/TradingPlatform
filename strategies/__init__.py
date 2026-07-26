"""Public API for the Atlas strategy framework."""

from .atlas_composite import AtlasCompositeStrategy
from .base_strategy import BaseStrategy, StrategyResult
from .momentum import MomentumStrategy
from .moving_average import MovingAverageCrossStrategy
from .registry import STRATEGY_REGISTRY, register_strategy
from .rsi_pullback import RSIPullbackStrategy
from .strategy_loader import get_strategy, load_strategies, strategy_options

__all__ = [
    "AtlasCompositeStrategy",
    "BaseStrategy",
    "MomentumStrategy",
    "MovingAverageCrossStrategy",
    "RSIPullbackStrategy",
    "STRATEGY_REGISTRY",
    "StrategyResult",
    "get_strategy",
    "load_strategies",
    "register_strategy",
    "strategy_options",
]
