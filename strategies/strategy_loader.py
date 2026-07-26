"""Strategy loading helpers."""

from __future__ import annotations

from .base_strategy import BaseStrategy
from .registry import STRATEGY_REGISTRY


def load_strategies() -> dict[str, BaseStrategy]:
    """Instantiate every registered Atlas strategy."""

    loaded: dict[str, BaseStrategy] = {}

    for key, factory in STRATEGY_REGISTRY.items():
        strategy = factory()

        if not isinstance(strategy, BaseStrategy):
            raise TypeError(
                f"Factory registered as '{key}' did not return BaseStrategy."
            )

        loaded[key] = strategy

    return loaded


def get_strategy(key: str) -> BaseStrategy:
    """Load one registered strategy by key."""

    normalised_key = key.strip().lower()

    try:
        factory = STRATEGY_REGISTRY[normalised_key]
    except KeyError as error:
        available = ", ".join(sorted(STRATEGY_REGISTRY))
        raise KeyError(
            f"Unknown strategy '{key}'. Available: {available}"
        ) from error

    return factory()


def strategy_options() -> dict[str, str]:
    """Return UI-friendly labels keyed by registry identifier."""

    return {
        key: factory().name
        for key, factory in STRATEGY_REGISTRY.items()
    }
