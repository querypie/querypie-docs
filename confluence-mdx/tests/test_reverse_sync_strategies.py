"""Typed renderer strategy dispatch contract tests."""

from types import SimpleNamespace

import pytest

from reverse_sync.capabilities import RendererStrategy, StrategyDecision
from reverse_sync.strategies.dispatch import (
    STRATEGY_HANDLERS,
    dispatch_strategy,
)


def test_strategy_registry_covers_every_executable_strategy_once():
    assert set(STRATEGY_HANDLERS) == set(RendererStrategy) - {
        RendererStrategy.BLOCKED,
    }
    assert len(set(STRATEGY_HANDLERS.values())) == len(STRATEGY_HANDLERS)


def test_blocked_strategy_cannot_cross_renderer_dispatch_boundary():
    context = SimpleNamespace(
        decision=StrategyDecision(
            RendererStrategy.BLOCKED,
            "unknown",
            reason_code="missing_identity",
        )
    )

    with pytest.raises(
        ValueError,
        match="등록되지 않은 renderer strategy는 실행할 수 없습니다: blocked",
    ):
        dispatch_strategy(context)
