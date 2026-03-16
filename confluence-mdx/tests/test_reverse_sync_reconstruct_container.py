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
