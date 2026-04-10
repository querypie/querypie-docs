# Reverse Sync Visible Segments Phase 1 Design

**Goal**

Replace lossy list-content normalization in reverse sync with a lossless visible-segment model so visible whitespace edits are handled the same way as character edits and can be reflected back into Confluence XHTML.

**Problem**

The current list path in `confluence-mdx/bin/reverse_sync/patch_builder.py` depends on `normalize_mdx_to_plain()` and list-specific helpers such as `_normalize_list_for_content_compare()`, `_has_marker_ws_change()`, and `_detect_list_item_space_change()`. Those helpers exist because the plain-text normalization step drops visible information before patch strategy is selected. Once marker whitespace, edge whitespace, or link-boundary whitespace is removed, the downstream code can no longer distinguish:

- no-op continuation-line reflow
- real visible whitespace edits
- structural list edits that require reconstruction

That produces both missed edits and no-op patches.

**Non-Goals**

- Do not replace the paragraph/table/direct paths in this phase.
- Do not redesign the XHTML patcher in this phase.
- Do not eliminate `normalize_mdx_to_plain()` globally in this phase.

**Design Summary**

Introduce a new lossless abstraction for reverse sync list handling:

- `VisibleSegment`: a token-level representation of visible content and structural markers
- `VisibleContentModel`: a block-level container of ordered segments, `visible_text`, and structural fingerprint

The model is extracted directly from MDX list content and XHTML list fragments without passing through lossy plain-text normalization. The list strategy then computes one diff model from the extracted visible text and uses one structural fingerprint comparison for rebuild decisions.

In this phase:

- clean list visible-only edits should be handled by text transfer when safe
- preserved-anchor list visible-only edits should be handled by template-based text transfer
- structural list changes should still use existing rebuild/merge paths

**Core Data Model**

```python
@dataclass(frozen=True)
class VisibleSegment:
    kind: Literal["text", "ws", "anchor", "list_marker", "item_boundary"]
    text: str
    visible: bool
    structural: bool
    meta: dict[str, Any]


@dataclass(frozen=True)
class VisibleContentModel:
    segments: list[VisibleSegment]
    visible_text: str
    structural_fingerprint: tuple[Any, ...]
```

Design rules:

- Visible whitespace is represented explicitly as `ws` segments, not inferred later.
- `visible_text` is the lossless concatenation of visible segments.
- Marker text and item boundaries may be structural even when not applied as XHTML text.
- The extractor is not allowed to erase or trim visible whitespace.

**List Extraction**

MDX list extraction:

- Tokenize each list item into `list_marker`, post-marker `ws`, body `text/ws`, and `item_boundary`.
- Track ordered-list start value and nested item path in `meta`.
- Preserve link label whitespace in visible text.
- Canonicalize continuation-line reflow only when the rendered visible result is equivalent.

XHTML list extraction:

- Walk `<ul>/<ol>` and `<li>` in order.
- Emit `text/ws` segments from DOM text nodes without collapsing whitespace.
- Preserve `<ac:link>` and other preserved anchors as structural/anchor metadata while still aligning their visible text into `visible_text`.
- Track ordered-list start value, nested item path, and preserved-anchor locations in the structural fingerprint.

**List Strategy Decision Rules**

Given `old_mdx_model`, `new_mdx_model`, and `xhtml_model`:

1. `visible_diff = old_mdx_model.visible_text != new_mdx_model.visible_text`
2. `structural_changed = old_mdx_model.structural_fingerprint != new_mdx_model.structural_fingerprint`
3. `anchor_sensitive = xhtml_model` contains preserved anchors

Behavior:

- no visible diff and no structural diff: emit no patch
- visible diff and no structural diff:
  - clean list: apply visible diff on current XHTML text/template
  - preserved-anchor list: apply visible diff on stored XHTML template
- structural diff:
  - clean list: rebuild fragment
  - preserved-anchor list: reuse existing merge/reconstruct logic or skip when unsafe

This keeps whitespace edits inside the same path as regular character edits.

**Compatibility Strategy**

Phase 1 only changes the list strategy. Existing non-list callers keep using `normalize_mdx_to_plain()` until later phases migrate them to the same abstraction.

In this phase the following list-specific helpers become obsolete and should be removed or reduced to compatibility shims:

- `_normalize_list_for_content_compare()`
- `_has_marker_ws_change()`
- `_detect_list_item_space_change()`

**Verification Strategy**

Regression coverage must be organized around behavior instead of helper names.

Required list tests:

- visible diff only
  - marker post-space changes
  - in-item double-space changes
  - link-body trailing-space removal
  - item-edge trailing-space changes
- no visible diff
  - continuation-line reflow only
- structural diff
  - item addition/removal
  - nested path changes
  - ordered-list start changes
- preserved-anchor handling
  - visible diff updates template output
  - no-op visible diff emits no patch
- idempotency
  - when XHTML already matches the new visible state, no new patch is emitted

**Rollout**

Phase 1:

- add `reverse_sync/visible_segments.py`
- migrate list strategy in `patch_builder.py`
- add focused unit tests for extraction and list-strategy regressions

Later phases:

- migrate paragraph/direct blocks
- migrate table path
- migrate containing/callout child list handling
- collapse strategy branching toward a default “apply diff on template” path with rebuild as fallback
