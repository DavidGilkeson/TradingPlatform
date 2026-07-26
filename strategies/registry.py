"""Explicit strategy registry for predictable discovery."""

from __future__ import annotations

from collections.abc import Callable

from .atlas_composite import AtlasCompositeStrategy
from .base_strategy import BaseStrategy
from .momentum import MomentumStrategy
from .moving_average import MovingAverageCrossStrategy
from .rsi_pullback import RSIPullbackStrategy


StrategyFactory = Callable[[], BaseStrategy]


STRATEGY_REGISTRY: dict[str, StrategyFactory] = {
    "moving_average_cross": MovingAverageCrossStrategy,
    "rsi_pullback": RSIPullbackStrategy,
    "momentum": MomentumStrategy,
    "atlas_composite": AtlasCompositeStrategy,
}


def register_strategy(
    key: str,
    factory: StrategyFactory,
    *,
    replace: bool = False,
) -> None:
    """Register a strategy factory for use by Atlas."""

    normalised_key = key.strip().lower()

    if not normalised_key:
        raise ValueError("Strategy key cannot be empty.")

    if normalised_key in STRATEGY_REGISTRY and not replace:
        raise KeyError(f"Strategy '{normalised_key}' is already registered.")

    strategy = factory()
    if not isinstance(strategy, BaseStrategy):
        raise TypeError("Registered factory must create a BaseStrategy instance.")

    STRATEGY_REGISTRY[normalised_key] = factory
