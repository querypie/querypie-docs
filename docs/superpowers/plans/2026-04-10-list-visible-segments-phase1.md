# Reverse Sync Visible Segments Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace lossy list-only normalization with a lossless visible-segment abstraction and migrate the reverse-sync list strategy to use it first.

**Architecture:** Add a new `visible_segments` module that extracts lossless visible/structural segment models from MDX lists and XHTML lists. Update the list branch in `patch_builder.py` to base patch decisions on `visible_text` and structural fingerprints instead of list-specific whitespace helpers.

**Tech Stack:** Python, pytest, BeautifulSoup, existing reverse-sync patch builder utilities

---

## Chunk 1: Spec-Backed Test Scaffolding

### Task 1: Add failing tests for visible-segment extraction and list decisions

**Files:**
- Modify: `confluence-mdx/tests/test_reverse_sync_patch_builder.py`
- Create: `confluence-mdx/tests/test_reverse_sync_visible_segments.py`
- Reference: `docs/superpowers/specs/2026-04-10-list-visible-segments-phase1-design.md`

- [ ] **Step 1: Write failing extraction tests**

Add tests covering:

- MDX list extraction preserves marker-post whitespace
- MDX list extraction preserves link trailing space at item edges
- XHTML list extraction preserves DOM whitespace and list structure

- [ ] **Step 2: Run extraction tests to verify they fail**

Run: `pytest -q tests/test_reverse_sync_visible_segments.py`
Expected: FAIL because the new module/functions do not exist yet

- [ ] **Step 3: Write failing list-strategy regression tests**

Add or update tests covering:

- clean list trailing-space change must emit a patch
- preserved-anchor no-op marker-space change must emit no patch
- continuation-line reflow remains no-op

- [ ] **Step 4: Run targeted builder tests to verify they fail**

Run: `pytest -q tests/test_reverse_sync_patch_builder.py -k 'visible_segments or trailing_space or marker_space or continuation_line_reflow'`
Expected: FAIL with current list-path behavior

## Chunk 2: Visible Segment Module

### Task 2: Implement the new visible-segment extraction module

**Files:**
- Create: `confluence-mdx/bin/reverse_sync/visible_segments.py`
- Reference: `confluence-mdx/bin/reverse_sync/xhtml_normalizer.py`
- Test: `confluence-mdx/tests/test_reverse_sync_visible_segments.py`

- [ ] **Step 1: Add the minimal dataclasses and extraction entry points**

Implement:

- `VisibleSegment`
- `VisibleContentModel`
- `extract_list_model_from_mdx(content: str)`
- `extract_list_model_from_xhtml(fragment: str)`

- [ ] **Step 2: Run extraction tests**

Run: `pytest -q tests/test_reverse_sync_visible_segments.py`
Expected: still failing on incomplete extraction behavior

- [ ] **Step 3: Implement minimal lossless segment extraction**

Support:

- marker tokenization
- whitespace tokenization
- item boundaries
- structural fingerprint for ordered start and item path
- XHTML text-node extraction with preserved anchors skipped from visible text but tracked structurally

- [ ] **Step 4: Re-run extraction tests**

Run: `pytest -q tests/test_reverse_sync_visible_segments.py`
Expected: PASS

## Chunk 3: Patch Builder Migration

### Task 3: Replace list-only normalization logic with visible models

**Files:**
- Modify: `confluence-mdx/bin/reverse_sync/patch_builder.py`
- Test: `confluence-mdx/tests/test_reverse_sync_patch_builder.py`
- Reference: `confluence-mdx/bin/reverse_sync/reconstructors.py`

- [ ] **Step 1: Wire list strategy to visible models**

Replace the current list-path use of:

- `_normalize_list_for_content_compare()`
- `_has_marker_ws_change()`
- `_detect_list_item_space_change()`

with:

- `extract_list_model_from_mdx()`
- `extract_list_model_from_xhtml()` as needed
- `visible_text` and structural fingerprint comparisons

- [ ] **Step 2: Run targeted list tests**

Run: `pytest -q tests/test_reverse_sync_patch_builder.py -k 'ListWhitespace or MarkerWhitespace or CalloutChildListSpaceChange or BuildPatchesIdempotency or visible_segments'`
Expected: FAIL until all list decisions are updated

- [ ] **Step 3: Implement minimal green-path migration**

Behavior:

- visible-only list diffs stay in text/template transfer path
- structural list diffs continue through existing rebuild/merge path
- no-op visible diffs emit no patch

- [ ] **Step 4: Re-run targeted list tests**

Run: `pytest -q tests/test_reverse_sync_patch_builder.py -k 'ListWhitespace or MarkerWhitespace or CalloutChildListSpaceChange or BuildPatchesIdempotency or visible_segments'`
Expected: PASS

## Chunk 4: Broader Verification and Cleanup

### Task 4: Remove obsolete helper coverage and verify reverse-sync behavior

**Files:**
- Modify: `confluence-mdx/bin/reverse_sync/patch_builder.py`
- Modify: `confluence-mdx/tests/test_reverse_sync_patch_builder.py`
- Modify: `confluence-mdx/tests/test_reverse_sync_visible_segments.py`

- [ ] **Step 1: Remove obsolete helper tests or rewrite them to behavior-based tests**

Focus test names on:

- visible diff applies
- structural diff rebuilds
- no-op emits no patch

- [ ] **Step 2: Run the focused reverse-sync suites**

Run: `pytest -q tests/test_reverse_sync_visible_segments.py tests/test_reverse_sync_patch_builder.py tests/test_reverse_sync_xhtml_patcher.py tests/test_reverse_sync_xhtml_normalizer.py`
Expected: PASS

- [ ] **Step 3: Run a broader reverse-sync safety sweep**

Run: `pytest -q tests/test_reverse_sync_patch_builder.py tests/test_reverse_sync_mapping_recorder.py tests/test_reverse_sync_sidecar.py tests/test_reverse_sync_cli.py`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/specs/2026-04-10-list-visible-segments-phase1-design.md \
        docs/superpowers/plans/2026-04-10-list-visible-segments-phase1.md \
        confluence-mdx/bin/reverse_sync/visible_segments.py \
        confluence-mdx/bin/reverse_sync/patch_builder.py \
        confluence-mdx/tests/test_reverse_sync_visible_segments.py \
        confluence-mdx/tests/test_reverse_sync_patch_builder.py
git commit -m "refactor: add visible segment model for reverse sync lists"
```
