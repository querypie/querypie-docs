"""RendererStrategy를 concrete handler로 연결하는 typed dispatch."""

from __future__ import annotations

from types import MappingProxyType
from typing import Callable, Mapping

from reverse_sync.capabilities import RendererStrategy
from reverse_sync.strategies.container_strategy import render_container
from reverse_sync.strategies.contracts import StrategyRenderContext
from reverse_sync.strategies.list_strategy import render_list
from reverse_sync.strategies.table_strategy import render_table
from reverse_sync.strategies.text_strategy import (
    render_preserved_anchor,
    render_text_block,
)

StrategyHandler = Callable[[StrategyRenderContext], None]

STRATEGY_HANDLERS: Mapping[RendererStrategy, StrategyHandler] = MappingProxyType(
    {
        RendererStrategy.TEXT_BLOCK: render_text_block,
        RendererStrategy.LIST: render_list,
        RendererStrategy.PRESERVED_ANCHOR: render_preserved_anchor,
        RendererStrategy.CONTAINER: render_container,
        RendererStrategy.TABLE: render_table,
    }
)


def dispatch_strategy(context: StrategyRenderContext) -> None:
    """typed strategy의 handler를 호출하고 미등록 strategy는 fail-closed합니다."""
    try:
        handler = STRATEGY_HANDLERS[context.decision.strategy]
    except KeyError as exc:
        raise ValueError(
            "등록되지 않은 renderer strategy는 실행할 수 없습니다: "
            f"{context.decision.strategy.value}"
        ) from exc
    handler(context)
