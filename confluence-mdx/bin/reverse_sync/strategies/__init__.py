"""Typed renderer strategy dispatch boundary."""

from reverse_sync.strategies.contracts import (
    StrategyPrimitives,
    StrategyRenderContext,
)
from reverse_sync.strategies.dispatch import dispatch_strategy

__all__ = [
    "StrategyPrimitives",
    "StrategyRenderContext",
    "dispatch_strategy",
]
