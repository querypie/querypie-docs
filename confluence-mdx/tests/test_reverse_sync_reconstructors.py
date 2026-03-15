"""reverse_sync/reconstructors.py unit tests."""

from reverse_sync.reconstructors import (
    reconstruct_fragment_with_sidecar,
    sidecar_block_requires_reconstruction,
)
from reverse_sync.sidecar import SidecarBlock


def _make_image_anchor(offset: int) -> dict:
    return {
        "kind": "image",
        "offset": offset,
        "raw_xhtml": (
            '<ac:image ac:inline="true">'
            '<ri:attachment ri:filename="sample.png"></ri:attachment>'
            '</ac:image>'
        ),
    }


def test_sidecar_block_requires_reconstruction_for_paragraph_anchors():
    sidecar_block = SidecarBlock(
        0,
        "p[1]",
        "<p>Hello world</p>",
        reconstruction={
            "kind": "paragraph",
            "old_plain_text": "Hello world",
            "anchors": [_make_image_anchor(6)],
        },
    )

    assert sidecar_block_requires_reconstruction(sidecar_block) is True


def test_sidecar_block_requires_reconstruction_for_list_item_anchors():
    sidecar_block = SidecarBlock(
        0,
        "ul[1]",
        "<ul><li><p>button</p></li></ul>",
        reconstruction={
            "kind": "list",
            "old_plain_text": "button",
            "items": [
                {
                    "kind": "image",
                    "path": [0],
                    "offset": 0,
                    "raw_xhtml": (
                        '<ac:image ac:inline="true">'
                        '<ri:attachment ri:filename="sample.png"></ri:attachment>'
                        '</ac:image>'
                    ),
                }
            ],
        },
    )

    assert sidecar_block_requires_reconstruction(sidecar_block) is True


def test_reconstruct_fragment_with_sidecar_rehydrates_paragraph_anchor():
    sidecar_block = SidecarBlock(
        0,
        "p[1]",
        "<p>Hello world</p>",
        reconstruction={
            "kind": "paragraph",
            "old_plain_text": "Hello world",
            "anchors": [_make_image_anchor(6)],
        },
    )

    result = reconstruct_fragment_with_sidecar(
        "<p>Hello brave world</p>",
        sidecar_block,
    )

    assert "<ac:image" in result
    assert "Hello" in result
    assert "brave world" in result
    assert "<img" not in result


def test_reconstruct_fragment_with_sidecar_rehydrates_list_item_anchor():
    sidecar_block = SidecarBlock(
        0,
        "ul[1]",
        "<ul><li><p>button</p></li></ul>",
        reconstruction={
            "kind": "list",
            "old_plain_text": "button",
            "items": [
                {
                    "kind": "image",
                    "path": [0],
                    "offset": 0,
                    "raw_xhtml": (
                        '<ac:image ac:inline="true">'
                        '<ri:attachment ri:filename="sample.png"></ri:attachment>'
                        '</ac:image>'
                    ),
                }
            ],
        },
    )

    result = reconstruct_fragment_with_sidecar(
        "<ul><li><p>button again</p></li></ul>",
        sidecar_block,
    )

    assert "<ac:image" in result
    assert "button again" in result
    assert "<img" not in result


def test_reconstruct_fragment_with_sidecar_returns_unchanged_when_no_sidecar():
    result = reconstruct_fragment_with_sidecar("<p>text</p>", None)
    assert result == "<p>text</p>"


def test_sidecar_block_requires_reconstruction_false_without_anchors():
    sidecar_block = SidecarBlock(
        0,
        "p[1]",
        "<p>Hello world</p>",
        reconstruction={
            "kind": "paragraph",
            "old_plain_text": "Hello world",
            "anchors": [],
        },
    )

    assert sidecar_block_requires_reconstruction(sidecar_block) is False
