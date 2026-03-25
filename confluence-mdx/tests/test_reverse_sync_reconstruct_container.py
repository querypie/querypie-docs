"""Phase 4 container reconstruction 메타데이터 및 reconstructor 테스트."""
import pytest
from pathlib import Path
from bs4 import BeautifulSoup

from reverse_sync.sidecar import build_sidecar, _build_reconstruction_metadata
from reverse_sync.mapping_recorder import BlockMapping, record_mapping
from reverse_sync.xhtml_normalizer import (
    normalize_fragment,
    extract_plain_text,
    extract_fragment_by_xpath,
)
from reverse_sync.reconstructors import (
    reconstruct_container_fragment,
    container_sidecar_requires_reconstruction,
    _has_inline_markup,
    _rewrite_paragraph_on_template,
)
from reverse_sync.sidecar import SidecarBlock


CALLOUT_XHTML = (
    '<ac:structured-macro ac:name="info">'
    '<ac:rich-text-body>'
    '<p>First paragraph.</p>'
    '<p>Second paragraph.</p>'
    '</ac:rich-text-body>'
    '</ac:structured-macro>'
)
CALLOUT_MDX = "<Callout type='info'>\nFirst paragraph.\n\nSecond paragraph.\n</Callout>\n"

TESTCASES = Path(__file__).parent / 'testcases'


class TestContainerReconstructionMetadata:
    def test_container_block_kind_is_container(self):
        """container 블록의 reconstruction kind는 'container'여야 한다."""
        sidecar = build_sidecar(CALLOUT_XHTML, CALLOUT_MDX)
        block = sidecar.blocks[0]
        assert block.reconstruction is not None
        assert block.reconstruction['kind'] == 'container'

    def test_container_children_count(self):
        """container children 수가 XHTML body 자식 수와 일치한다."""
        sidecar = build_sidecar(CALLOUT_XHTML, CALLOUT_MDX)
        block = sidecar.blocks[0]
        children = block.reconstruction['children']
        assert len(children) == 2

    def test_container_child_has_required_fields(self):
        """각 child entry에 xpath, fragment, plain_text, type이 있다."""
        sidecar = build_sidecar(CALLOUT_XHTML, CALLOUT_MDX)
        block = sidecar.blocks[0]
        child = block.reconstruction['children'][0]
        assert 'xpath' in child
        assert 'fragment' in child
        assert 'plain_text' in child
        assert 'type' in child
        assert 'First paragraph' in child['fragment']

    def test_container_child_plain_text_matches_fragment(self):
        """child plain_text가 fragment의 extract_plain_text 결과와 일치한다."""
        sidecar = build_sidecar(CALLOUT_XHTML, CALLOUT_MDX)
        for block in sidecar.blocks:
            recon = block.reconstruction
            if not recon or recon.get('kind') != 'container':
                continue
            for child in recon.get('children', []):
                assert child['plain_text'].strip() == extract_plain_text(child['fragment']).strip()

    def test_container_child_xpaths_backward_compat(self):
        """child_xpaths backward-compat 필드가 children xpath와 일치한다."""
        sidecar = build_sidecar(CALLOUT_XHTML, CALLOUT_MDX)
        block = sidecar.blocks[0]
        recon = block.reconstruction
        expected = [c['xpath'] for c in recon['children']]
        assert recon['child_xpaths'] == expected

    def test_child_with_image_has_anchors(self):
        """ac:image가 있는 child에는 anchors 목록이 포함된다."""
        image_xhtml = '<ac:image><ri:attachment ri:filename="test.png"/></ac:image>'
        xhtml = (
            '<ac:structured-macro ac:name="info">'
            '<ac:rich-text-body>'
            f'<p>text {image_xhtml} more</p>'
            '</ac:rich-text-body>'
            '</ac:structured-macro>'
        )
        mdx = "<Callout type='info'>\ntext more\n</Callout>\n"
        sidecar = build_sidecar(xhtml, mdx)
        block = sidecar.blocks[0]
        child = block.reconstruction['children'][0]
        assert 'anchors' in child
        assert len(child['anchors']) == 1
        assert 'test.png' in child['anchors'][0]['raw_xhtml']


class TestHasInlineMarkup:
    def test_plain_text_returns_false(self):
        assert _has_inline_markup('<p>simple text</p>') is False

    def test_strong_returns_true(self):
        assert _has_inline_markup('<p>text <strong>bold</strong></p>') is True

    def test_link_returns_true(self):
        assert _has_inline_markup(
            '<p>see <ac:link><ri:page ri:content-title="X"/></ac:link></p>'
        ) is True

    def test_image_only_returns_false(self):
        """ac:image는 anchor로 별도 처리되므로 inline markup 아님."""
        assert _has_inline_markup('<p>text<ac:image/></p>') is False

    def test_empty_fragment_returns_false(self):
        assert _has_inline_markup('') is False

    def test_no_p_tag_returns_false(self):
        assert _has_inline_markup('<ul><li>text</li></ul>') is False


class TestRewriteParagraphOnTemplate:
    def test_plain_text_change_preserves_strong(self):
        """bold 태그를 유지하며 텍스트만 업데이트한다."""
        template = '<p>Click <strong>here</strong> to continue.</p>'
        new_frag = '<p>Click here to proceed.</p>'
        result = _rewrite_paragraph_on_template(template, new_frag)
        assert '<strong>' in result
        assert 'proceed' in result

    def test_link_preserved_on_text_change(self):
        """ac:link 구조를 유지하며 주변 텍스트를 갱신한다."""
        template = (
            '<p>자세한 내용은 <ac:link>'
            '<ri:page ri:content-title="가이드"/>'
            '<ac:plain-text-link-body><![CDATA[가이드]]></ac:plain-text-link-body>'
            '</ac:link> 참고.</p>'
        )
        new_frag = '<p>자세한 내용은 가이드 참고하세요.</p>'
        result = _rewrite_paragraph_on_template(template, new_frag)
        assert 'ac:link' in result
        assert '가이드' in result

    def test_same_text_returns_template(self):
        """텍스트가 동일하면 template_fragment를 그대로 반환한다."""
        template = '<p>text <strong>bold</strong></p>'
        new_frag = '<p>text bold</p>'
        result = _rewrite_paragraph_on_template(template, new_frag)
        assert result == template

    def test_em_tag_preserved(self):
        template = '<p>이것은 <em>강조</em>된 텍스트입니다.</p>'
        new_frag = '<p>이것은 강조된 다른 텍스트입니다.</p>'
        result = _rewrite_paragraph_on_template(template, new_frag)
        assert '<em>' in result


class TestContainerSidecarRequiresReconstruction:
    def test_returns_false_for_none(self):
        assert container_sidecar_requires_reconstruction(None) is False

    def test_returns_false_for_clean_container(self):
        block = SidecarBlock(
            block_index=0, xhtml_xpath='macro-info[1]',
            xhtml_fragment='<ac:structured-macro ac:name="info"/>',
            reconstruction={
                'kind': 'container',
                'children': [
                    {'xpath': 'macro-info[1]/p[1]', 'fragment': '<p>text</p>',
                     'plain_text': 'text', 'type': 'paragraph'},
                ],
                'child_xpaths': ['macro-info[1]/p[1]'],
            },
        )
        assert container_sidecar_requires_reconstruction(block) is False

    def test_returns_true_when_child_has_anchors(self):
        block = SidecarBlock(
            block_index=0, xhtml_xpath='macro-info[1]',
            xhtml_fragment='<ac:structured-macro ac:name="info"/>',
            reconstruction={
                'kind': 'container',
                'children': [
                    {
                        'xpath': 'macro-info[1]/p[1]',
                        'fragment': '<p>text<ac:image/></p>',
                        'plain_text': 'text',
                        'type': 'paragraph',
                        'anchors': [{'kind': 'image', 'offset': 4, 'raw_xhtml': '<ac:image/>'}],
                    },
                ],
                'child_xpaths': ['macro-info[1]/p[1]'],
            },
        )
        assert container_sidecar_requires_reconstruction(block) is True

    def test_returns_false_when_only_inline_markup(self):
        """inline markup만 있고 anchor가 없는 container는 reconstruction 불필요.

        reconstruction은 anchor(ac:image) 기반으로만 트리거된다.
        inline markup 보존은 anchor로 트리거된 reconstruction 내에서 함께 처리된다.
        """
        block = SidecarBlock(
            block_index=0, xhtml_xpath='macro-info[1]',
            xhtml_fragment='<ac:structured-macro ac:name="info"/>',
            reconstruction={
                'kind': 'container',
                'children': [
                    {
                        'xpath': 'macro-info[1]/p[1]',
                        'fragment': '<p>Click <strong>here</strong> to continue.</p>',
                        'plain_text': 'Click here to continue.',
                        'type': 'paragraph',
                    },
                ],
                'child_xpaths': ['macro-info[1]/p[1]'],
            },
        )
        assert container_sidecar_requires_reconstruction(block) is False


class TestReconstructContainerFragment:
    def _make_sidecar_block(self, children_meta):
        return SidecarBlock(
            block_index=0,
            xhtml_xpath='macro-info[1]',
            xhtml_fragment='',
            reconstruction={
                'kind': 'container',
                'children': children_meta,
                'child_xpaths': [c['xpath'] for c in children_meta],
            },
        )

    def test_clean_container_returned_as_is(self):
        """anchor 없는 container는 new_fragment를 그대로 반환한다."""
        new_frag = (
            '<ac:structured-macro ac:name="info">'
            '<ac:rich-text-body><p>Updated text.</p></ac:rich-text-body>'
            '</ac:structured-macro>'
        )
        block = self._make_sidecar_block([
            {'xpath': 'macro-info[1]/p[1]', 'fragment': '<p>Original text.</p>',
             'plain_text': 'Original text.', 'type': 'paragraph'},
        ])
        result = reconstruct_container_fragment(new_frag, block)
        assert result == new_frag

    def test_container_with_anchor_reinjects_image(self):
        """child에 ac:image가 있으면 new_fragment에 재삽입된다."""
        image_xhtml = '<ac:image><ri:attachment ri:filename="test.png"/></ac:image>'
        new_fragment = (
            '<ac:structured-macro ac:name="info">'
            '<ac:rich-text-body><p>updated text</p></ac:rich-text-body>'
            '</ac:structured-macro>'
        )
        block = self._make_sidecar_block([
            {
                'xpath': 'macro-info[1]/p[1]',
                'fragment': f'<p>text {image_xhtml}</p>',
                'plain_text': 'text',
                'type': 'paragraph',
                'anchors': [{'kind': 'image', 'offset': len('text '), 'raw_xhtml': image_xhtml}],
            },
        ])
        result = reconstruct_container_fragment(new_fragment, block)
        assert 'ac:image' in result
        assert 'test.png' in result

    def test_container_with_inline_markup_preserves_strong_when_anchor_present(self):
        """anchor child가 있어 reconstruction이 트리거되면, inline markup child도 함께 보존된다.

        anchor 없는 child라도 inline markup이 있으면 _rewrite_paragraph_on_template으로 보존.
        """
        image_xhtml = '<ac:image><ri:attachment ri:filename="diagram.png"/></ac:image>'
        xhtml_fragment = (
            '<ac:structured-macro ac:name="info">'
            '<ac:rich-text-body>'
            '<p><strong>Title</strong></p>'
            f'<p>See diagram {image_xhtml} for details.</p>'
            '</ac:rich-text-body>'
            '</ac:structured-macro>'
        )
        new_fragment = (
            '<ac:structured-macro ac:name="info">'
            '<ac:rich-text-body>'
            '<p>Title</p>'
            '<p>See diagram for details.</p>'
            '</ac:rich-text-body>'
            '</ac:structured-macro>'
        )
        block = SidecarBlock(
            block_index=0,
            xhtml_xpath='macro-info[1]',
            xhtml_fragment=xhtml_fragment,
            reconstruction={
                'kind': 'container',
                'children': [
                    {
                        'xpath': 'macro-info[1]/p[1]',
                        'fragment': '<p><strong>Title</strong></p>',
                        'plain_text': 'Title',
                        'type': 'paragraph',
                    },
                    {
                        'xpath': 'macro-info[1]/p[2]',
                        'fragment': f'<p>See diagram {image_xhtml} for details.</p>',
                        'plain_text': 'See diagram for details.',
                        'type': 'paragraph',
                        'anchors': [{'kind': 'image', 'offset': 12, 'raw_xhtml': image_xhtml}],
                    },
                ],
                'child_xpaths': ['macro-info[1]/p[1]', 'macro-info[1]/p[2]'],
            },
        )
        result = reconstruct_container_fragment(new_fragment, block)
        # anchor child: ac:image 재삽입됨
        assert 'diagram.png' in result
        # inline markup child: <strong> 보존됨
        assert '<strong>' in result

    def test_outer_wrapper_macro_attributes_preserved(self):
        """sidecar xhtml_fragment의 macro 속성이 결과 wrapper에 유지된다."""
        xhtml_fragment = (
            '<ac:structured-macro ac:name="info" ac:schema-version="1">'
            '<ac:parameter ac:name="icon">false</ac:parameter>'
            '<ac:rich-text-body><p>Original.</p></ac:rich-text-body>'
            '</ac:structured-macro>'
        )
        image_xhtml = '<ac:image><ri:attachment ri:filename="x.png"/></ac:image>'
        new_fragment = (
            '<ac:structured-macro ac:name="info">'
            '<ac:rich-text-body><p>Updated</p></ac:rich-text-body>'
            '</ac:structured-macro>'
        )
        block = SidecarBlock(
            block_index=0,
            xhtml_xpath='macro-info[1]',
            xhtml_fragment=xhtml_fragment,
            reconstruction={
                'kind': 'container',
                'children': [
                    {
                        'xpath': 'macro-info[1]/p[1]',
                        'fragment': f'<p>Original {image_xhtml}</p>',
                        'plain_text': 'Original',
                        'type': 'paragraph',
                        'anchors': [{'kind': 'image', 'offset': 9, 'raw_xhtml': image_xhtml}],
                    },
                ],
                'child_xpaths': ['macro-info[1]/p[1]'],
            },
        )
        result = reconstruct_container_fragment(new_fragment, block)
        assert 'ac:schema-version="1"' in result
        assert 'ac:parameter' in result
        assert 'x.png' in result

    def test_no_sidecar_block_returns_new_fragment(self):
        new_frag = (
            '<ac:structured-macro ac:name="info">'
            '<ac:rich-text-body><p>x</p></ac:rich-text-body>'
            '</ac:structured-macro>'
        )
        result = reconstruct_container_fragment(new_frag, None)
        assert result == new_frag


@pytest.mark.parametrize("page_id", ['544112828', '1454342158', '544379140', 'panels'])
def test_container_child_fragment_oracle(page_id):
    """각 container 블록의 child fragment가 page.xhtml 실제 내용과 normalize-equal."""
    xhtml_path = TESTCASES / page_id / 'page.xhtml'
    mdx_path = TESTCASES / page_id / 'expected.mdx'
    if not xhtml_path.exists() or not mdx_path.exists():
        pytest.skip(f'{page_id} fixture not found')
    xhtml = xhtml_path.read_text(encoding='utf-8')
    mdx = mdx_path.read_text(encoding='utf-8')
    sidecar = build_sidecar(xhtml, mdx)

    container_count = 0
    for block in sidecar.blocks:
        recon = block.reconstruction
        if not recon or recon.get('kind') != 'container':
            continue
        container_count += 1
        for child in recon.get('children', []):
            stored_norm = normalize_fragment(child['fragment'])
            plain_from_fragment = extract_plain_text(child['fragment']).strip()
            assert child['plain_text'].strip() == plain_from_fragment, (
                f"{page_id}: child {child['xpath']} plain_text mismatch"
            )
            # page.xhtml에서 child xpath로 추출한 fragment와 normalize-equal 검증
            extracted = extract_fragment_by_xpath(xhtml, child['xpath'])
            if extracted is not None:
                assert stored_norm == normalize_fragment(extracted), (
                    f"{page_id}: child {child['xpath']} fragment mismatch"
                )

    # 알려진 container-bearing fixture는 반드시 container가 1개 이상이어야 한다
    if page_id in ('panels', '1454342158'):
        assert container_count > 0, f"{page_id}: expected container blocks, got zero"


# ── end-to-end pipeline 연결 테스트 ──────────────────────────────────────────

import yaml
from reverse_sync.block_diff import diff_blocks
from reverse_sync.mapping_recorder import record_mapping as _record_mapping
from reverse_sync.mdx_block_parser import parse_mdx_blocks
from reverse_sync.patch_builder import build_patches
from reverse_sync.sidecar import (
    SidecarEntry,
    build_mdx_to_sidecar_index,
    build_xpath_to_mapping,
    generate_sidecar_mapping,
)
from reverse_sync.xhtml_patcher import patch_xhtml


def _run_pipeline(xhtml, original_mdx, improved_mdx):
    original_blocks = parse_mdx_blocks(original_mdx)
    improved_blocks = parse_mdx_blocks(improved_mdx)
    changes, alignment = diff_blocks(original_blocks, improved_blocks)
    mappings = _record_mapping(xhtml)
    roundtrip_sidecar = build_sidecar(xhtml, original_mdx)
    sidecar_yaml = generate_sidecar_mapping(xhtml, original_mdx)
    sidecar_data = yaml.safe_load(sidecar_yaml) or {}
    entries = [
        SidecarEntry(
            xhtml_xpath=item['xhtml_xpath'],
            xhtml_type=item.get('xhtml_type', ''),
            mdx_blocks=item.get('mdx_blocks', []),
            mdx_line_start=item.get('mdx_line_start', 0),
            mdx_line_end=item.get('mdx_line_end', 0),
        )
        for item in sidecar_data.get('mappings', [])
    ]
    mdx_to_sidecar = build_mdx_to_sidecar_index(entries)
    xpath_to_mapping = build_xpath_to_mapping(mappings)
    patches = build_patches(
        changes, original_blocks, improved_blocks, mappings,
        mdx_to_sidecar, xpath_to_mapping, alignment,
        roundtrip_sidecar=roundtrip_sidecar,
    )
    return patches, patch_xhtml(xhtml, patches)


class TestContainerPipelineEndToEnd:
    """container reconstruction이 실제 patch 파이프라인에 연결됐는지 검증한다."""

    def test_callout_with_image_routes_to_replace_fragment(self):
        """ac:image 포함 callout 변경 시 containing 전략이 replace_fragment를 생성한다."""
        image_xhtml = '<ac:image ac:inline="true"><ri:attachment ri:filename="diagram.png"/></ac:image>'
        xhtml = (
            '<ac:structured-macro ac:name="info">'
            '<ac:rich-text-body>'
            f'<p>Original text {image_xhtml} end.</p>'
            '</ac:rich-text-body>'
            '</ac:structured-macro>'
        )
        original_mdx = (
            "<Callout type='info'>\n"
            "Original text <img src='/diagram.png' alt='diagram.png'/> end.\n"
            "</Callout>\n"
        )
        improved_mdx = (
            "<Callout type='info'>\n"
            "Updated text <img src='/diagram.png' alt='diagram.png'/> end.\n"
            "</Callout>\n"
        )

        patches, patched = _run_pipeline(xhtml, original_mdx, improved_mdx)

        replace_patches = [p for p in patches if p.get('action') == 'replace_fragment']
        assert replace_patches, "container with image should produce replace_fragment patch"
        assert 'ac:image' in patched, "ac:image should be preserved in output"
        assert 'diagram.png' in patched
        assert 'Updated text' in patched
        # img 태그는 Confluence 마크업으로 교체되어야 한다
        assert '<img src=' not in patched

    def test_clean_callout_uses_replace_fragment(self):
        """clean callout은 replace_fragment 경로를 사용한다.

        anchor 재구성이 불필요한 container도 containing 전략에서 _build_replace_fragment_patch로
        전환되어 outer wrapper 속성(local-id, ac:macro-id 등)을 보존한다 (Phase 5 Axis 1).
        """
        xhtml = (
            '<ac:structured-macro ac:name="info">'
            '<ac:rich-text-body>'
            '<p>Original text.</p>'
            '</ac:rich-text-body>'
            '</ac:structured-macro>'
        )
        original_mdx = "<Callout type='info'>\nOriginal text.\n</Callout>\n"
        improved_mdx = "<Callout type='info'>\nUpdated text.\n</Callout>\n"

        patches, patched = _run_pipeline(xhtml, original_mdx, improved_mdx)

        replace_patches = [p for p in patches if p.get('action') == 'replace_fragment']
        # clean callout도 replace_fragment를 사용함 (Phase 5 Axis 1)
        assert any(
            p.get('xhtml_xpath') == 'macro-info[1]'
            for p in replace_patches
        )
        assert 'Updated text' in patched
