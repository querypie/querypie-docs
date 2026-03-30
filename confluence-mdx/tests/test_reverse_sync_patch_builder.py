"""patch_builder 유닛 테스트.

build_patches 분기 경로
+ helper 함수 (is_markdown_table) 테스트.
"""
from reverse_sync.block_diff import BlockChange
from reverse_sync.mapping_recorder import BlockMapping
from reverse_sync.mdx_block_parser import MdxBlock
from reverse_sync.sidecar import (
    DocumentEnvelope,
    RoundtripSidecar,
    SidecarBlock,
    SidecarEntry,
    sha256_text,
)
from text_utils import normalize_mdx_to_plain
from reverse_sync.patch_builder import (
    _apply_mdx_diff_to_xhtml,
    _find_roundtrip_sidecar_block,
    _resolve_mapping_for_change,
    build_patches,
    is_markdown_table,
)
from reverse_sync.xhtml_patcher import patch_xhtml

# ── 헬퍼 팩토리 ──


def _make_mapping(
    block_id: str,
    xhtml_plain_text: str,
    xpath: str | None = None,
    type_: str = 'paragraph',
    children: list | None = None,
) -> BlockMapping:
    return BlockMapping(
        block_id=block_id,
        type=type_,
        xhtml_xpath=xpath or f'p[{block_id}]',
        xhtml_text=f'<p>{xhtml_plain_text}</p>',
        xhtml_plain_text=xhtml_plain_text,
        xhtml_element_index=0,
        children=children or [],
    )


def _make_block(
    content: str, type_: str = 'paragraph', line_start: int = 1,
) -> MdxBlock:
    lines = content.count('\n') + 1
    return MdxBlock(
        type=type_, content=content,
        line_start=line_start, line_end=line_start + lines - 1,
    )


def _make_change(
    index: int, old_content: str, new_content: str,
    type_: str = 'paragraph',
) -> BlockChange:
    return BlockChange(
        index=index,
        change_type='modified',
        old_block=_make_block(old_content, type_),
        new_block=_make_block(new_content, type_),
    )


def _make_sidecar(xpath: str, mdx_blocks: list) -> SidecarEntry:
    return SidecarEntry(xhtml_xpath=xpath, xhtml_type='paragraph', mdx_blocks=mdx_blocks)


def _make_roundtrip_sidecar(blocks):
    return RoundtripSidecar(
        page_id='test',
        blocks=blocks,
        separators=['\n'] * (len(blocks) - 1) if len(blocks) > 1 else [],
        document_envelope=DocumentEnvelope(prefix='', suffix='\n'),
    )



# ── Helper 함수 테스트 ──


class TestIsMarkdownTable:
    def test_valid_table(self):
        content = '| a | b |\n| --- | --- |\n| 1 | 2 |'
        assert is_markdown_table(content) is True

    def test_single_line_not_table(self):
        assert is_markdown_table('| a | b |') is False

    def test_no_pipes(self):
        assert is_markdown_table('hello\nworld') is False

    def test_only_separator(self):
        assert is_markdown_table('| --- | --- |') is False


# ── build_patches 분기 경로 테스트 ──


class TestBuildPatches:
    """build_patches()의 6가지 주요 분기 경로를 테스트한다."""

    def _setup_sidecar(self, xpath: str, mdx_idx: int):
        """sidecar와 xpath→mapping 인덱스를 구성하는 헬퍼."""
        entry = _make_sidecar(xpath, [mdx_idx])
        mdx_to_sidecar = {mdx_idx: entry}
        return mdx_to_sidecar

    # Path 1: 직접 sidecar 매칭 + 실제 텍스트 변경 → replace_fragment (has_content_change=True)
    # (Phase 5 Axis 3: build_list_item_patches 제거, 실제 변경 시 replace_fragment로 라우팅)
    def test_path1_direct_sidecar_match_list_with_content_change_regenerates(self):
        child = _make_mapping('c1', 'child text', xpath='li[1]')
        parent = _make_mapping('p1', 'parent text child text more', xpath='ul[1]',
                               type_='list', children=['c1'])
        mappings = [parent, child]
        xpath_to_mapping = {m.xhtml_xpath: m for m in mappings}

        change = _make_change(0, '- child text', '- updated child', type_='list')
        mdx_to_sidecar = self._setup_sidecar('ul[1]', 0)
        roundtrip_sidecar = _make_roundtrip_sidecar([
            SidecarBlock(0, 'ul[1]', '<li><p>child text</p></li>', 'hash1', (1, 1))
        ])

        patches = build_patches(
            [change], [change.old_block], [change.new_block],
            mappings, mdx_to_sidecar, xpath_to_mapping,
            roundtrip_sidecar=roundtrip_sidecar)

        # 실제 텍스트 변경(child text→updated child) → has_content_change=True → replace_fragment
        assert len(patches) == 1
        assert patches[0]['xhtml_xpath'] == 'ul[1]'
        assert patches[0]['action'] == 'replace_fragment'

    # Path 1b: 직접 sidecar 매칭 + 형식 전용 변경 (텍스트 동일) → skip
    # 예: [ **General** ] → [**General**] (링크 내 공백, collapse_ws 후 텍스트 동일)
    def test_path1b_direct_sidecar_format_only_change_skips(self):
        child = _make_mapping('c1', 'General text', xpath='li[1]')
        parent = _make_mapping('p1', 'General text more', xpath='ul[1]',
                               type_='list', children=['c1'])
        mappings = [parent, child]
        xpath_to_mapping = {m.xhtml_xpath: m for m in mappings}

        # 링크 공백 변경만: [**General**](url) → [ **General** ](url), 텍스트 동일
        change = _make_change(
            0,
            '* [**General**](company-management/general) text\n',
            '* [ **General** ](company-management/general) text\n',
            type_='list',
        )
        mdx_to_sidecar = self._setup_sidecar('ul[1]', 0)
        roundtrip_sidecar = _make_roundtrip_sidecar([
            SidecarBlock(0, 'ul[1]', '<li><p><a href="">General</a> text</p></li>', 'hash1', (1, 1))
        ])

        patches = build_patches(
            [change], [change.old_block], [change.new_block],
            mappings, mdx_to_sidecar, xpath_to_mapping,
            roundtrip_sidecar=roundtrip_sidecar)

        # 형식만 변경(링크 공백), normalize+collapse_ws 후 텍스트 동일 → skip
        assert patches == []

    # Path 1c: sidecar 매칭 → list type + roundtrip_sidecar 없음 + content change
    #          → clean list이면 replace_fragment (Phase 5: has_content_change → patch)
    def test_path1c_sidecar_match_list_without_roundtrip_sidecar_with_content_change_patches(self):
        child = _make_mapping('c1', 'child text', xpath='li[1]')
        parent = _make_mapping('p1', 'parent text child text more', xpath='ul[1]',
                               type_='list', children=['c1'])
        mappings = [parent, child]
        xpath_to_mapping = {m.xhtml_xpath: m for m in mappings}

        change = _make_change(0, '- child text', '- updated child', type_='list')
        mdx_to_sidecar = self._setup_sidecar('ul[1]', 0)

        patches = build_patches(
            [change], [change.old_block], [change.new_block],
            mappings, mdx_to_sidecar, xpath_to_mapping)

        # has_content_change=True + anchor markup 없음 → replace_fragment 적용
        assert len(patches) == 1
        assert patches[0]['xhtml_xpath'] == 'ul[1]'
        assert patches[0]['action'] == 'replace_fragment'

    # Path 1d: type-based sidecar 타입 불일치로 mapping=None → text fallback으로 복원
    #          → real content change → replace_fragment
    # 재현: CI 환경의 544382060 패턴 — type-based 매칭 실패 시에도 패치가 적용되어야 한다
    def test_path1d_no_sidecar_match_text_fallback_applies_replace_fragment(self):
        """type-based sidecar가 mapping을 찾지 못해도 text fallback으로 복원 후 replace_fragment."""
        list_mapping = _make_mapping(
            'lm1', '검색이 가능합니다 조건으로 검색', xpath='ul[1]', type_='list')
        mappings = [list_mapping]
        xpath_to_mapping = {m.xhtml_xpath: m for m in mappings}

        old_content = '1. 검색이 가능합니다 조건으로 검색\n'
        new_content = '1. 검색할 수 있습니다 조건으로 검색\n'
        change = _make_change(0, old_content, new_content, type_='list')

        # mdx_to_sidecar에 해당 블록 없음 — type-based 매칭 실패
        mdx_to_sidecar = {}
        roundtrip_sidecar = _make_roundtrip_sidecar([
            SidecarBlock(0, 'ul[1]', '<li><p>검색이 가능합니다 조건으로 검색</p></li>',
                         'different_hash', (10, 10)),
        ])

        patches = build_patches(
            [change], [change.old_block], [change.new_block],
            mappings, mdx_to_sidecar, xpath_to_mapping,
            roundtrip_sidecar=roundtrip_sidecar)

        # text fallback이 mapping 복원 → replace_fragment 적용
        assert len(patches) == 1
        assert patches[0]['xhtml_xpath'] == 'ul[1]'
        assert patches[0]['action'] == 'replace_fragment'

    # Path 1e: type-based sidecar 타입 불일치 + roundtrip_sidecar=None + content change
    #          → text fallback으로 mapping 복원 → clean list → replace_fragment
    def test_path1e_no_sidecar_match_no_roundtrip_sidecar_with_content_change_patches(self):
        """roundtrip_sidecar 없어도 has_content_change이면 text fallback 후 replace_fragment."""
        list_mapping = _make_mapping(
            'lm1', '검색이 가능합니다 조건으로 검색', xpath='ul[1]', type_='list')
        mappings = [list_mapping]
        xpath_to_mapping = {m.xhtml_xpath: m for m in mappings}

        old_content = '1. 검색이 가능합니다 조건으로 검색\n'
        new_content = '1. 검색할 수 있습니다 조건으로 검색\n'
        change = _make_change(0, old_content, new_content, type_='list')
        mdx_to_sidecar = {}

        patches = build_patches(
            [change], [change.old_block], [change.new_block],
            mappings, mdx_to_sidecar, xpath_to_mapping)

        # has_content_change=True + anchor markup 없음 → replace_fragment 적용
        assert len(patches) == 1
        assert patches[0]['xhtml_xpath'] == 'ul[1]'
        assert patches[0]['action'] == 'replace_fragment'

    # Path 2: sidecar 매칭 → children 있음 → roundtrip_sidecar 없음 + content change
    #          → clean list이면 replace_fragment (Phase 5: has_content_change → patch)
    def test_path2_sidecar_match_list_no_roundtrip_sidecar_with_content_change_patches(self):
        parent = _make_mapping('p1', 'totally different parent', xpath='ul[1]',
                               type_='list', children=['c1'])
        child = _make_mapping('c1', 'no match here', xpath='li[1]')
        mappings = [parent, child]
        xpath_to_mapping = {m.xhtml_xpath: m for m in mappings}

        change = _make_change(
            0, '- item one\n- item two', '- item one\n- item two\n- item three',
            type_='list')
        mdx_to_sidecar = self._setup_sidecar('ul[1]', 0)

        patches = build_patches(
            [change], [change.old_block], [change.new_block],
            mappings, mdx_to_sidecar, xpath_to_mapping)

        # has_content_change=True + anchor markup 없음 → replace_fragment 적용
        assert len(patches) == 1
        assert patches[0]['xhtml_xpath'] == 'ul[1]'
        assert patches[0]['action'] == 'replace_fragment'

    # Path 3: sidecar 매칭 → children 있음 → child 해석 실패
    #          → parent를 containing block으로 사용
    def test_path3_sidecar_child_fail_containing_block(self):
        """child 해석 실패 → parent containing → text-level 패치."""
        parent = _make_mapping(
            'p1', 'parent contains child text here', xpath='div[1]',
            children=['c1'])
        child = _make_mapping('c1', 'no match at all', xpath='span[1]')
        mappings = [parent, child]
        xpath_to_mapping = {m.xhtml_xpath: m for m in mappings}

        change = _make_change(0, 'child text', 'updated text')
        mdx_to_sidecar = self._setup_sidecar('div[1]', 0)

        patches = build_patches(
            [change], [change.old_block], [change.new_block],
            mappings, mdx_to_sidecar, xpath_to_mapping)

        assert len(patches) == 1
        assert patches[0]['xhtml_xpath'] == 'div[1]'
        assert 'updated text' in patches[0]['new_plain_text']

    def test_containing_child_of_parent_multi_changes_aggregated(self):
        """같은 containing parent에 대한 다중 child-of-parent 변경은 하나의 patch로 누적돼야 한다."""
        parent = _make_mapping(
            'p1', 'first and second', xpath='p[1]', children=['c1', 'c2'])
        child1 = _make_mapping('c1', 'first', xpath='span[1]')
        child2 = _make_mapping('c2', 'second', xpath='span[2]')
        mappings = [parent, child1, child2]
        xpath_to_mapping = {m.xhtml_xpath: m for m in mappings}

        changes = [
            _make_change(0, 'first', 'FIRST'),
            _make_change(1, 'second', 'SECOND'),
        ]
        mdx_to_sidecar = {
            0: _make_sidecar('p[1]', [0]),
            1: _make_sidecar('p[1]', [1]),
        }

        patches = build_patches(
            changes,
            [change.old_block for change in changes],
            [change.new_block for change in changes],
            mappings,
            mdx_to_sidecar,
            xpath_to_mapping,
        )

        assert len(patches) == 1
        assert patches[0]['xhtml_xpath'] == 'p[1]'
        assert patches[0]['new_plain_text'] == 'FIRST and SECOND'
        assert patch_xhtml('<p>first and second</p>', patches) == '<p>FIRST and SECOND</p>'

    # Path 4: sidecar 미스 → skip (텍스트 포함 검색 폴백 제거됨)
    def test_path4_sidecar_miss_text_search_containing(self):
        m1 = _make_mapping('m1', 'this mapping contains the search text here')
        mappings = [m1]
        xpath_to_mapping = {m.xhtml_xpath: m for m in mappings}

        change = _make_change(0, 'search text', 'replaced text')
        mdx_to_sidecar = {}  # 빈 sidecar → sidecar 미스 → skip

        patches = build_patches(
            [change], [change.old_block], [change.new_block],
            mappings, mdx_to_sidecar, xpath_to_mapping)

        assert len(patches) == 0

    # Path 5: sidecar 미스 → list/table 분리
    def test_path5_sidecar_miss_table_split(self):
        # table 타입이면서 sidecar 미스
        table_content_old = '| h1 | h2 |\n| --- | --- |\n| a | b |'
        table_content_new = '| h1 | h2 |\n| --- | --- |\n| x | y |'
        change = _make_change(0, table_content_old, table_content_new)

        # sidecar로 매핑할 수 없고, containing도 없고, table이면 build_table_row_patches
        # 하지만 table_row_patches도 sidecar 필요 → 결국 빈 결과
        patches = build_patches(
            [change], [change.old_block], [change.new_block],
            [], {}, {})

        assert patches == []

    # Path 6: sidecar 매칭 → children 없음 → sidecar를 신뢰하여 직접 매핑
    def test_path6_sidecar_match_text_mismatch_remapping(self):
        # sidecar가 p[1]을 가리키면 텍스트 불일치와 무관하게 p[1]로 직접 패치
        wrong = _make_mapping('wrong', 'completely wrong mapping', xpath='p[1]')
        better = _make_mapping('better', 'contains the target text here', xpath='p[2]')
        mappings = [wrong, better]
        xpath_to_mapping = {m.xhtml_xpath: m for m in mappings}

        change = _make_change(0, 'target text', 'updated target')
        mdx_to_sidecar = self._setup_sidecar('p[1]', 0)

        patches = build_patches(
            [change], [change.old_block], [change.new_block],
            mappings, mdx_to_sidecar, xpath_to_mapping)

        assert len(patches) == 1
        assert patches[0]['xhtml_xpath'] == 'p[1]'

    def test_clean_paragraph_generates_replace_fragment(self):
        m1 = _make_mapping('m1', 'hello  world', xpath='p[1]')
        mappings = [m1]
        xpath_to_mapping = {m.xhtml_xpath: m for m in mappings}

        change = _make_change(0, 'hello world', 'hello earth')
        mdx_to_sidecar = self._setup_sidecar('p[1]', 0)

        patches = build_patches(
            [change], [change.old_block], [change.new_block],
            mappings, mdx_to_sidecar, xpath_to_mapping)

        assert len(patches) == 1
        assert patches[0]['action'] == 'replace_fragment'
        assert patches[0]['new_element_xhtml'] == '<p>hello earth</p>'

    def test_paragraph_with_preserved_anchor_uses_template_rewrite(self):
        """ac:link 포함 블록은 원본 template 기반 텍스트 갱신 (Phase 5 Axis 1)."""
        m1 = _make_mapping(
            'm1',
            'hello world',
            xpath='p[1]',
        )
        m1.xhtml_text = '<p>hello <ac:link><ri:page ri:content-title="world" /></ac:link></p>'
        mappings = [m1]
        xpath_to_mapping = {m.xhtml_xpath: m for m in mappings}

        change = _make_change(0, 'hello world', 'hello earth')
        mdx_to_sidecar = self._setup_sidecar('p[1]', 0)

        patches = build_patches(
            [change], [change.old_block], [change.new_block],
            mappings, mdx_to_sidecar, xpath_to_mapping)

        assert len(patches) == 1
        assert patches[0]['action'] == 'replace_fragment'
        # ac:link 구조가 보존되어야 함
        assert '<ac:link>' in patches[0]['new_element_xhtml']

    def test_roundtrip_sidecar_paragraph_without_anchors_uses_replace_fragment(self):
        m1 = _make_mapping('m1', 'hello world', xpath='p[1]')
        mappings = [m1]
        xpath_to_mapping = {m.xhtml_xpath: m for m in mappings}
        mdx_to_sidecar = self._setup_sidecar('p[1]', 0)
        roundtrip_sidecar = _make_roundtrip_sidecar([
            SidecarBlock(
                0, 'p[1]', '<p>hello world</p>', 'hash1', (1, 1),
                reconstruction={'kind': 'paragraph', 'old_plain_text': 'hello world', 'anchors': []},
            )
        ])

        change = _make_change(0, 'hello world', 'hello earth')
        patches = build_patches(
            [change], [change.old_block], [change.new_block],
            mappings, mdx_to_sidecar, xpath_to_mapping,
            roundtrip_sidecar=roundtrip_sidecar)

        assert len(patches) == 1
        assert patches[0]['action'] == 'replace_fragment'
        assert patches[0]['new_element_xhtml'] == '<p>hello earth</p>'

    def test_roundtrip_sidecar_paragraph_with_anchors_stays_modify(self):
        m1 = _make_mapping('m1', 'hello world', xpath='p[1]')
        mappings = [m1]
        xpath_to_mapping = {m.xhtml_xpath: m for m in mappings}
        mdx_to_sidecar = self._setup_sidecar('p[1]', 0)
        roundtrip_sidecar = _make_roundtrip_sidecar([
            SidecarBlock(
                0, 'p[1]', '<p>hello world</p>', 'hash1', (1, 1),
                reconstruction={
                    'kind': 'paragraph',
                    'old_plain_text': 'hello world',
                    'anchors': [{'anchor_id': 'a1'}],
                },
            )
        ])

        change = _make_change(0, 'hello world', 'hello earth')
        patches = build_patches(
            [change], [change.old_block], [change.new_block],
            mappings, mdx_to_sidecar, xpath_to_mapping,
            roundtrip_sidecar=roundtrip_sidecar)

        assert len(patches) == 1
        assert patches[0].get('action', 'modify') == 'modify'
        assert 'new_plain_text' in patches[0] or 'new_inner_xhtml' in patches[0]

    def test_roundtrip_sidecar_without_reconstruction_stays_modify(self):
        m1 = _make_mapping('m1', 'hello world', xpath='p[1]')
        mappings = [m1]
        xpath_to_mapping = {m.xhtml_xpath: m for m in mappings}
        mdx_to_sidecar = self._setup_sidecar('p[1]', 0)
        roundtrip_sidecar = _make_roundtrip_sidecar([
            SidecarBlock(0, 'p[1]', '<p>hello world</p>', 'hash1', (1, 1), reconstruction=None)
        ])

        change = _make_change(0, 'hello world', 'hello earth')
        patches = build_patches(
            [change], [change.old_block], [change.new_block],
            mappings, mdx_to_sidecar, xpath_to_mapping,
            roundtrip_sidecar=roundtrip_sidecar)

        assert len(patches) == 1
        assert patches[0].get('action', 'modify') == 'modify'
        assert 'new_element_xhtml' not in patches[0]

    def test_roundtrip_sidecar_non_paragraph_reconstruction_stays_modify(self):
        m1 = _make_mapping('m1', 'hello world', xpath='p[1]')
        mappings = [m1]
        xpath_to_mapping = {m.xhtml_xpath: m for m in mappings}
        mdx_to_sidecar = self._setup_sidecar('p[1]', 0)
        roundtrip_sidecar = _make_roundtrip_sidecar([
            SidecarBlock(
                0, 'p[1]', '<p>hello world</p>', 'hash1', (1, 1),
                reconstruction={'kind': 'html_block', 'old_plain_text': 'hello world'},
            )
        ])

        change = _make_change(0, 'hello world', 'hello earth')
        patches = build_patches(
            [change], [change.old_block], [change.new_block],
            mappings, mdx_to_sidecar, xpath_to_mapping,
            roundtrip_sidecar=roundtrip_sidecar)

        assert len(patches) == 1
        assert patches[0].get('action', 'modify') == 'modify'
        assert 'new_element_xhtml' not in patches[0]

    def test_roundtrip_identity_fallback_rejects_cross_type_sidecar_block(self):
        mapping = _make_mapping('m1', 'same text', xpath='p[6]')
        change = _make_change(0, 'same text', 'updated text')
        roundtrip_sidecar = _make_roundtrip_sidecar([
            SidecarBlock(
                0,
                'table[2]',
                '<table><tr><td>same text</td></tr></table>',
                sha256_text(change.old_block.content),
                (change.old_block.line_start, change.old_block.line_end),
            )
        ])

        sidecar_block = _find_roundtrip_sidecar_block(
            change,
            mapping,
            roundtrip_sidecar,
            {block.xhtml_xpath: block for block in roundtrip_sidecar.blocks},
        )

        assert sidecar_block is None

    def test_list_roundtrip_identity_fallback_rejects_cross_type_mapping(self):
        m1 = _make_mapping('m1', 'same text', xpath='ul[1]', type_='list')
        m1.xhtml_text = '<ul><li><p>same text</p></li></ul>'
        mappings = [m1]
        xpath_to_mapping = {m.xhtml_xpath: m for m in mappings}
        mdx_to_sidecar = self._setup_sidecar('ul[1]', 0)
        change = _make_change(0, '- same text', '- updated text', type_='list')
        roundtrip_sidecar = _make_roundtrip_sidecar([
            SidecarBlock(
                0,
                'table[2]',
                '<table><tr><td>same text</td></tr></table>',
                sha256_text(change.old_block.content),
                (change.old_block.line_start, change.old_block.line_end),
            )
        ])

        patches = build_patches(
            [change], [change.old_block], [change.new_block],
            mappings, mdx_to_sidecar, xpath_to_mapping,
            roundtrip_sidecar=roundtrip_sidecar)

        assert len(patches) == 1
        assert patches[0]['action'] == 'replace_fragment'
        assert patches[0]['xhtml_xpath'] == 'ul[1]'

    def test_roundtrip_identity_fallback_accepts_ul_ol_same_list_family(self):
        mapping = _make_mapping('m1', 'same text', xpath='ul[1]', type_='list')
        change = _make_change(0, '- same text', '- updated text', type_='list')
        roundtrip_sidecar = _make_roundtrip_sidecar([
            SidecarBlock(
                0,
                'ol[2]',
                '<ol><li><p>same text</p></li></ol>',
                sha256_text(change.old_block.content),
                (change.old_block.line_start, change.old_block.line_end),
            )
        ])

        sidecar_block = _find_roundtrip_sidecar_block(
            change,
            mapping,
            roundtrip_sidecar,
            {block.xhtml_xpath: block for block in roundtrip_sidecar.blocks},
        )

        assert sidecar_block is not None
        assert sidecar_block.xhtml_xpath == 'ol[2]'

    def test_roundtrip_identity_fallback_accepts_heading_family(self):
        mapping = _make_mapping('m1', 'same heading', xpath='h2[1]', type_='heading')
        change = _make_change(0, '## same heading', '## updated heading', type_='heading')
        roundtrip_sidecar = _make_roundtrip_sidecar([
            SidecarBlock(
                0,
                'h3[4]',
                '<h3>same heading</h3>',
                sha256_text(change.old_block.content),
                (change.old_block.line_start, change.old_block.line_end),
            )
        ])

        sidecar_block = _find_roundtrip_sidecar_block(
            change,
            mapping,
            roundtrip_sidecar,
            {block.xhtml_xpath: block for block in roundtrip_sidecar.blocks},
        )

        assert sidecar_block is not None
        assert sidecar_block.xhtml_xpath == 'h3[4]'

    def test_roundtrip_identity_fallback_does_not_guess_without_mapping(self):
        change = _make_change(0, '- same text', '- updated text', type_='list')
        roundtrip_sidecar = _make_roundtrip_sidecar([
            SidecarBlock(
                0,
                'ol[2]',
                '<ol><li><p>same text</p></li></ol>',
                sha256_text(change.old_block.content),
                (change.old_block.line_start, change.old_block.line_end),
            )
        ])

        sidecar_block = _find_roundtrip_sidecar_block(
            change,
            None,
            roundtrip_sidecar,
            {block.xhtml_xpath: block for block in roundtrip_sidecar.blocks},
        )

        assert sidecar_block is None

    # NON_CONTENT_TYPES 스킵
    def test_skips_non_content_types(self):
        m1 = _make_mapping('m1', 'text', xpath='p[1]')
        mappings = [m1]
        xpath_to_mapping = {m.xhtml_xpath: m for m in mappings}

        change = _make_change(0, 'import X', 'import Y')
        change.old_block = _make_block('import X', 'import_statement')
        change.new_block = _make_block('import Y', 'import_statement')
        mdx_to_sidecar = self._setup_sidecar('p[1]', 0)

        patches = build_patches(
            [change], [change.old_block], [change.new_block],
            mappings, mdx_to_sidecar, xpath_to_mapping)

        assert patches == []

    def test_direct_inline_code_added_generates_replace_fragment(self):
        """simple paragraph는 inline formatting 변화도 fragment replacement를 사용한다."""
        m1 = _make_mapping('m1', 'QueryPie는 https://example.com/과 같은 URL', xpath='p[1]')
        mappings = [m1]
        xpath_to_mapping = {m.xhtml_xpath: m for m in mappings}

        change = _make_change(
            0,
            'QueryPie는 https://example.com/과 같은 URL',
            'QueryPie는 `https://example.com/`과 같은 URL',
        )
        mdx_to_sidecar = self._setup_sidecar('p[1]', 0)

        patches = build_patches(
            [change], [change.old_block], [change.new_block],
            mappings, mdx_to_sidecar, xpath_to_mapping)

        assert len(patches) == 1
        assert patches[0]['action'] == 'replace_fragment'
        assert '<code>https://example.com/</code>' in patches[0]['new_element_xhtml']
        assert patches[0]['new_element_xhtml'].startswith('<p>')

    def test_direct_text_only_change_uses_replace_fragment(self):
        """Phase 2: simple paragraph의 기본 경로는 whole-fragment replacement다."""
        m1 = _make_mapping('m1', 'hello world', xpath='p[1]')
        mappings = [m1]
        xpath_to_mapping = {m.xhtml_xpath: m for m in mappings}

        change = _make_change(0, 'hello world', 'hello earth')
        mdx_to_sidecar = self._setup_sidecar('p[1]', 0)

        patches = build_patches(
            [change], [change.old_block], [change.new_block],
            mappings, mdx_to_sidecar, xpath_to_mapping)

        assert len(patches) == 1
        assert patches[0]['action'] == 'replace_fragment'
        assert patches[0]['new_element_xhtml'] == '<p>hello earth</p>'

    # sidecar 미스 → skip (텍스트 포함 검색 폴백 제거됨)
    def test_multiple_changes_grouped_to_containing(self):
        container = _make_mapping(
            'm1', 'first part and second part', xpath='p[1]')
        mappings = [container]
        xpath_to_mapping = {m.xhtml_xpath: m for m in mappings}

        change1 = _make_change(0, 'first part', 'first UPDATED')
        change2 = _make_change(1, 'second part', 'second UPDATED')
        mdx_to_sidecar = {}  # sidecar 미스 → skip

        patches = build_patches(
            [change1, change2],
            [change1.old_block, change2.old_block],
            [change1.new_block, change2.new_block],
            mappings, mdx_to_sidecar, xpath_to_mapping)

        assert len(patches) == 0

    def test_direct_heading_inline_code_added(self):
        """heading은 fragment replacement를 사용한다."""
        m1 = _make_mapping('m1', 'kubectl 명령어 가이드', xpath='h2[1]',
                           type_='heading')
        mappings = [m1]
        xpath_to_mapping = {m.xhtml_xpath: m for m in mappings}

        change = _make_change(
            0,
            '### kubectl 명령어 가이드\n',
            '### `kubectl` 명령어 가이드\n',
            type_='heading',
        )
        mdx_to_sidecar = self._setup_sidecar('h2[1]', 0)

        patches = build_patches(
            [change], [change.old_block], [change.new_block],
            mappings, mdx_to_sidecar, xpath_to_mapping)

        assert len(patches) == 1
        assert patches[0]['action'] == 'replace_fragment'
        assert patches[0]['new_element_xhtml'] == '<h2><code>kubectl</code> 명령어 가이드</h2>'

    def test_direct_bold_added_generates_replace_fragment(self):
        """simple paragraph에서 bold가 추가되면 fragment replacement를 생성한다."""
        m1 = _make_mapping('m1', '중요한 설정입니다', xpath='p[1]')
        mappings = [m1]
        xpath_to_mapping = {m.xhtml_xpath: m for m in mappings}

        change = _make_change(
            0,
            '중요한 설정입니다',
            '**중요한** 설정입니다',
        )
        mdx_to_sidecar = self._setup_sidecar('p[1]', 0)

        patches = build_patches(
            [change], [change.old_block], [change.new_block],
            mappings, mdx_to_sidecar, xpath_to_mapping)

        assert len(patches) == 1
        assert patches[0]['action'] == 'replace_fragment'
        assert patches[0]['new_element_xhtml'] == '<p><strong>중요한</strong> 설정입니다</p>'

    def test_markdown_table_change_generates_replace_fragment(self):
        m1 = _make_mapping('m1', 'Header1 Header2 old_val other', xpath='table[1]',
                           type_='table')
        mappings = [m1]
        xpath_to_mapping = {m.xhtml_xpath: m for m in mappings}
        roundtrip_sidecar = _make_roundtrip_sidecar([
            SidecarBlock(0, 'table[1]', '<table><tbody></tbody></table>', 'hash1', (1, 3))
        ])

        change = _make_change(
            0,
            '| Header1 | Header2 |\n| --- | --- |\n| old_val | other |',
            '| Header1 | Header2 |\n| --- | --- |\n| new_val | other |',
        )
        mdx_to_sidecar = self._setup_sidecar('table[1]', 0)

        patches = build_patches(
            [change], [change.old_block], [change.new_block],
            mappings, mdx_to_sidecar, xpath_to_mapping,
            roundtrip_sidecar=roundtrip_sidecar)

        assert len(patches) == 1
        assert patches[0]['action'] == 'replace_fragment'
        assert '<table>' in patches[0]['new_element_xhtml']
        assert 'new_val' in patches[0]['new_element_xhtml']

    def test_delete_add_pair_clean_heading_uses_replace_fragment(self):
        m1 = _make_mapping('m1', 'Old Title', xpath='h2[1]', type_='heading')
        mappings = [m1]
        xpath_to_mapping = {m.xhtml_xpath: m for m in mappings}
        mdx_to_sidecar = self._setup_sidecar('h2[1]', 0)
        roundtrip_sidecar = _make_roundtrip_sidecar([
            SidecarBlock(0, 'h2[1]', '<h2>Old Title</h2>', 'hash1', (1, 1))
        ])

        old_block = _make_block('## Old Title\n', 'heading')
        new_block = _make_block('### New Title\n', 'heading')
        changes = [
            BlockChange(index=0, change_type='deleted', old_block=old_block, new_block=None),
            BlockChange(index=0, change_type='added', old_block=None, new_block=new_block),
        ]

        patches = build_patches(
            changes, [old_block], [new_block],
            mappings, mdx_to_sidecar, xpath_to_mapping,
            roundtrip_sidecar=roundtrip_sidecar)

        assert len(patches) == 1
        assert patches[0]['action'] == 'replace_fragment'
        assert patches[0]['new_element_xhtml'] == '<h2>New Title</h2>'

    def test_table_without_roundtrip_sidecar_returns_no_patch(self):
        """roundtrip_sidecar가 없는 table 변경은 Phase 5 Axis 3 이후 skip한다.

        현재: _can_replace_table_fragment(roundtrip_sidecar=None) → False →
              build_table_row_patches가 text-transfer 패치를 생성한다.
        Phase 5 Axis 3 이후: fallback 제거 → patches == [].
        """
        mapping = _make_mapping('m1', 'Header old_val', xpath='table[1]', type_='table')
        change = _make_change(
            0,
            '| Header |\n| --- |\n| old_val |',
            '| Header |\n| --- |\n| new_val |',
        )
        mdx_to_sidecar = {0: _make_sidecar('table[1]', [0])}
        xpath_to_mapping = {'table[1]': mapping}

        patches = build_patches(
            [change],
            [change.old_block],
            [change.new_block],
            [mapping],
            mdx_to_sidecar=mdx_to_sidecar,
            xpath_to_mapping=xpath_to_mapping,
            roundtrip_sidecar=None,
        )

        assert patches == [], "fallback 제거 후 roundtrip_sidecar 없는 table은 skip이어야 한다"

    def test_list_without_roundtrip_sidecar_but_content_change_patches(self):
        """roundtrip_sidecar 없어도 content change가 있으면 clean list를 패치한다.

        has_content_change=True이고 preserved anchor markup이 없는 경우,
        roundtrip_sidecar=None이어도 should_replace_clean_list=True가 되어
        replace_fragment 패치를 생성한다.
        """
        mapping = _make_mapping('m1', 'old item text', xpath='ul[1]', type_='list')
        change = _make_change(
            0, '* old item text\n', '* new item text\n', type_='list')
        mdx_to_sidecar = {0: _make_sidecar('ul[1]', [0])}
        xpath_to_mapping = {'ul[1]': mapping}

        patches = build_patches(
            [change],
            [change.old_block],
            [change.new_block],
            [mapping],
            mdx_to_sidecar=mdx_to_sidecar,
            xpath_to_mapping=xpath_to_mapping,
            roundtrip_sidecar=None,
        )

        # has_content_change=True + anchor markup 없음 → replace_fragment 적용
        assert len(patches) == 1
        assert patches[0]['xhtml_xpath'] == 'ul[1]'
        assert patches[0]['action'] == 'replace_fragment'

    def test_containing_without_roundtrip_sidecar_preserves_wrapper_attrs(self):
        """no-sidecar containing은 text-level 패치로 wrapper 속성을 보존한다."""
        mapping = _make_mapping(
            'callout-1',
            'Old text.',
            xpath='macro-info[1]',
            type_='html_block',
            children=['paragraph-1'],
        )
        mapping.xhtml_text = (
            '<ac:structured-macro ac:name="info" ac:schema-version="1" ac:macro-id="MID">'
            '<ac:rich-text-body><p>Old text.</p></ac:rich-text-body>'
            '</ac:structured-macro>'
        )
        change = _make_change(
            0,
            "<Callout type='info'>\nOld text.\n</Callout>\n",
            "<Callout type='info'>\nNew text.\n</Callout>\n",
            type_='callout',
        )
        mdx_to_sidecar = {0: _make_sidecar('macro-info[1]', [0])}
        xpath_to_mapping = {'macro-info[1]': mapping}

        patches = build_patches(
            [change],
            [change.old_block],
            [change.new_block],
            [mapping],
            mdx_to_sidecar=mdx_to_sidecar,
            xpath_to_mapping=xpath_to_mapping,
            roundtrip_sidecar=None,
        )
        patched = patch_xhtml(mapping.xhtml_text, patches)

        assert 'ac:macro-id="MID"' in patched
        assert 'ac:schema-version="1"' in patched
        assert 'New text.' in patched

    def test_paired_delete_add_list_without_roundtrip_sidecar_still_patches(self):
        """paired delete/add clean list는 no-sidecar여도 변경이 유실되면 안 된다."""
        mapping = _make_mapping('m1', 'old item text', xpath='ul[1]', type_='list')
        mapping.xhtml_text = '<ul><li><p>old item text</p></li></ul>'
        changes = [
            BlockChange(
                index=0,
                change_type='deleted',
                old_block=_make_block('* old item text\n', type_='list'),
                new_block=None,
            ),
            BlockChange(
                index=0,
                change_type='added',
                old_block=None,
                new_block=_make_block('* new item text\n', type_='list'),
            ),
        ]
        mdx_to_sidecar = {0: _make_sidecar('ul[1]', [0])}
        xpath_to_mapping = {'ul[1]': mapping}

        patches = build_patches(
            changes,
            [changes[0].old_block],
            [changes[1].new_block],
            [mapping],
            mdx_to_sidecar=mdx_to_sidecar,
            xpath_to_mapping=xpath_to_mapping,
            roundtrip_sidecar=None,
        )

        assert len(patches) == 1
        assert patches[0]['xhtml_xpath'] == 'ul[1]'
        # Phase 5 Axis 1: clean list는 replace_fragment로 전환
        assert patches[0]['action'] == 'replace_fragment'
        assert 'new item text' in patches[0]['new_element_xhtml']

    def test_paired_delete_add_clean_container_sidecar_preserves_inline_styling(self):
        """paired delete/add + clean callout + roundtrip sidecar 조합에서
        Confluence inline styling(<em><span style="color:...">)이 보존돼야 한다.

        Phase 5 Axis 1: clean container sidecar는 _build_replace_fragment_patch로 전환.
        reconstruct_container_fragment의 per-child 재구성이 inline styling을 보존한다.
        """
        styled_xhtml = (
            '<ac:structured-macro ac:name="info" ac:schema-version="1" ac:macro-id="MID">'
            '<ac:rich-text-body>'
            '<p><em><span style="color: rgb(255,86,48);">Deleted</span></em> old.</p>'
            '</ac:rich-text-body>'
            '</ac:structured-macro>'
        )
        mapping = _make_mapping(
            'callout-1',
            'Deleted old.',
            xpath='macro-info[1]',
            type_='html_block',
        )
        mapping.xhtml_text = styled_xhtml

        changes = [
            BlockChange(
                index=0,
                change_type='deleted',
                old_block=_make_block(
                    "<Callout type='info'>\n*Deleted* old.\n</Callout>\n",
                    type_='callout'),
                new_block=None,
            ),
            BlockChange(
                index=0,
                change_type='added',
                old_block=None,
                new_block=_make_block(
                    "<Callout type='info'>\n*Deleted* new.\n</Callout>\n",
                    type_='callout'),
            ),
        ]
        mdx_to_sidecar = {0: _make_sidecar('macro-info[1]', [0])}
        xpath_to_mapping = {'macro-info[1]': mapping}

        # clean container sidecar (anchor 없음)
        sidecar_block = SidecarBlock(
            block_index=0,
            xhtml_xpath='macro-info[1]',
            xhtml_fragment=styled_xhtml,
            reconstruction={
                'kind': 'container',
                'children': [
                    {'fragment': '<p><em><span style="color: rgb(255,86,48);">Deleted</span></em> old.</p>',
                     'plain_text': 'Deleted old.', 'type': 'paragraph'},
                ],
            },
        )
        roundtrip_sidecar = RoundtripSidecar(
            blocks=[sidecar_block],
        )

        patches = build_patches(
            changes,
            [changes[0].old_block],
            [changes[1].new_block],
            [mapping],
            mdx_to_sidecar=mdx_to_sidecar,
            xpath_to_mapping=xpath_to_mapping,
            roundtrip_sidecar=roundtrip_sidecar,
        )
        patched = patch_xhtml(styled_xhtml, patches)

        # inline styling이 보존되어야 한다
        assert 'style="color: rgb(255,86,48);"' in patched
        assert '<em>' in patched
        assert '<span' in patched
        # 텍스트 변경은 반영되어야 한다
        assert 'new.' in patched

    def test_paired_delete_add_parameter_bearing_macro_preserves_and_updates(self):
        """paired delete/add + parameter-bearing macro (expand 등)에서
        <ac:parameter> 보존과 body 텍스트 변경 적용 모두 되어야 한다.

        _apply_outer_wrapper_template이 body children만 교체하므로
        parameter는 보존되고 body는 정상 업데이트된다.
        """
        expand_xhtml = (
            '<ac:structured-macro ac:name="expand" ac:schema-version="1">'
            '<ac:parameter ac:name="title">TITLE</ac:parameter>'
            '<ac:rich-text-body><p>Old text.</p></ac:rich-text-body>'
            '</ac:structured-macro>'
        )
        mapping = _make_mapping(
            'expand-1',
            'TITLE Old text.',
            xpath='macro-expand[1]',
            type_='html_block',
        )
        mapping.xhtml_text = expand_xhtml

        changes = [
            BlockChange(
                index=0,
                change_type='deleted',
                old_block=_make_block(
                    "<details>\n<summary>TITLE</summary>\nOld text.\n</details>\n",
                    type_='html_block'),
                new_block=None,
            ),
            BlockChange(
                index=0,
                change_type='added',
                old_block=None,
                new_block=_make_block(
                    "<details>\n<summary>TITLE</summary>\nNew text.\n</details>\n",
                    type_='html_block'),
            ),
        ]
        mdx_to_sidecar = {0: _make_sidecar('macro-expand[1]', [0])}
        xpath_to_mapping = {'macro-expand[1]': mapping}

        # container sidecar (anchor 없음)
        sidecar_block = SidecarBlock(
            block_index=0,
            xhtml_xpath='macro-expand[1]',
            xhtml_fragment=expand_xhtml,
            reconstruction={
                'kind': 'container',
                'children': [
                    {'fragment': '<p>Old text.</p>',
                     'plain_text': 'Old text.', 'type': 'paragraph'},
                ],
            },
        )
        roundtrip_sidecar = RoundtripSidecar(
            blocks=[sidecar_block],
        )

        patches = build_patches(
            changes,
            [changes[0].old_block],
            [changes[1].new_block],
            [mapping],
            mdx_to_sidecar=mdx_to_sidecar,
            xpath_to_mapping=xpath_to_mapping,
            roundtrip_sidecar=roundtrip_sidecar,
        )
        patched = patch_xhtml(expand_xhtml, patches)

        # <ac:parameter> 보존
        assert '>TITLE<' in patched
        assert 'ac:name="title"' in patched
        # body 텍스트 변경이 실제로 적용되어야 한다 (silent no-op 금지)
        assert 'New text.' in patched
        assert 'Old text.' not in patched

    def test_paired_delete_add_parameter_bearing_macro_preserves_body_inline_styling(self):
        """parameter-bearing macro body의 Confluence inline styling도 보존되어야 한다.

        _build_replace_fragment_patch → reconstruct_container_fragment에서
        children 수 일치 시 per-child 재구성 loop으로 fall-through하여
        stored child fragment를 template으로 사용해 inline styling을 보존한다.
        """
        styled_expand_xhtml = (
            '<ac:structured-macro ac:name="expand" ac:schema-version="1">'
            '<ac:parameter ac:name="title">TITLE</ac:parameter>'
            '<ac:rich-text-body>'
            '<p><em><span style="color: rgb(255,86,48);">Deleted</span></em> old.</p>'
            '</ac:rich-text-body>'
            '</ac:structured-macro>'
        )
        mapping = _make_mapping(
            'expand-1',
            'TITLE Deleted old.',
            xpath='macro-expand[1]',
            type_='html_block',
        )
        mapping.xhtml_text = styled_expand_xhtml

        changes = [
            BlockChange(
                index=0,
                change_type='deleted',
                old_block=_make_block(
                    "<details>\n<summary>TITLE</summary>\n*Deleted* old.\n</details>\n",
                    type_='html_block'),
                new_block=None,
            ),
            BlockChange(
                index=0,
                change_type='added',
                old_block=None,
                new_block=_make_block(
                    "<details>\n<summary>TITLE</summary>\n*Deleted* new.\n</details>\n",
                    type_='html_block'),
            ),
        ]
        mdx_to_sidecar = {0: _make_sidecar('macro-expand[1]', [0])}
        xpath_to_mapping = {'macro-expand[1]': mapping}

        sidecar_block = SidecarBlock(
            block_index=0,
            xhtml_xpath='macro-expand[1]',
            xhtml_fragment=styled_expand_xhtml,
            reconstruction={
                'kind': 'container',
                'children': [
                    {'fragment': '<p><em><span style="color: rgb(255,86,48);">Deleted</span></em> old.</p>',
                     'plain_text': 'Deleted old.', 'type': 'paragraph'},
                ],
            },
        )
        roundtrip_sidecar = RoundtripSidecar(blocks=[sidecar_block])

        patches = build_patches(
            changes,
            [changes[0].old_block],
            [changes[1].new_block],
            [mapping],
            mdx_to_sidecar=mdx_to_sidecar,
            xpath_to_mapping=xpath_to_mapping,
            roundtrip_sidecar=roundtrip_sidecar,
        )
        patched = patch_xhtml(styled_expand_xhtml, patches)

        # parameter 보존
        assert '>TITLE<' in patched
        # body inline styling 보존
        assert 'style="color: rgb(255,86,48);"' in patched
        assert '<em>' in patched
        assert '<span' in patched
        # body 텍스트 변경 적용
        assert 'new.' in patched


# ── delete/insert 패치 생성 테스트 ──


class TestBuildDeletePatch:
    def test_delete_patch_from_sidecar(self):
        """deleted 변경이 sidecar에서 xpath를 찾아 delete 패치를 생성한다."""
        mapping = _make_mapping('m1', 'Delete this text', xpath='p[1]')
        sidecar = _make_sidecar('p[1]', [2])
        mdx_to_sidecar = {2: sidecar}
        xpath_to_mapping = {'p[1]': mapping}

        change = BlockChange(
            index=2, change_type='deleted',
            old_block=_make_block('Delete this text'),
            new_block=None,
        )
        patches = build_patches(
            [change], [], [], [mapping],
            mdx_to_sidecar, xpath_to_mapping, {})
        assert len(patches) == 1
        assert patches[0]['action'] == 'delete'
        assert patches[0]['xhtml_xpath'] == 'p[1]'

    def test_delete_empty_without_sidecar_skipped(self):
        """deleted된 empty 블록은 sidecar 매핑이 없으면 무시."""
        change = BlockChange(
            index=0, change_type='deleted',
            old_block=_make_block('', type_='empty'),
            new_block=None,
        )
        patches = build_patches([change], [], [], [], {}, {}, {})
        assert len(patches) == 0

    def test_delete_frontmatter_skipped(self):
        """deleted된 frontmatter 블록은 무시."""
        change = BlockChange(
            index=0, change_type='deleted',
            old_block=_make_block('---\ntitle: x\n---\n', type_='frontmatter'),
            new_block=None,
        )
        patches = build_patches([change], [], [], [], {}, {}, {})
        assert len(patches) == 0

    def test_delete_no_sidecar_skipped(self):
        """sidecar에 매핑되지 않은 삭제 블록은 무시."""
        change = BlockChange(
            index=5, change_type='deleted',
            old_block=_make_block('Unmapped text'),
            new_block=None,
        )
        patches = build_patches([change], [], [], [], {}, {}, {})
        assert len(patches) == 0


class TestBuildInsertPatch:
    def test_insert_patch_with_anchor(self):
        """added 변경이 선행 매칭 블록을 앵커로 insert 패치를 생성한다."""
        mapping = _make_mapping('m1', 'Anchor text', xpath='p[1]')
        sidecar = _make_sidecar('p[1]', [0])
        mdx_to_sidecar = {0: sidecar}
        xpath_to_mapping = {'p[1]': mapping}

        alignment = {0: 0}  # improved[0] → original[0]
        change = BlockChange(
            index=1, change_type='added',
            old_block=None,
            new_block=_make_block('New paragraph text'),
        )
        improved_blocks = [
            _make_block('Anchor text'),
            _make_block('New paragraph text'),
        ]
        patches = build_patches(
            [change], [_make_block('Anchor text')], improved_blocks,
            [mapping], mdx_to_sidecar, xpath_to_mapping, alignment)

        insert_patches = [p for p in patches if p.get('action') == 'insert']
        assert len(insert_patches) == 1
        assert insert_patches[0]['after_xpath'] == 'p[1]'
        assert '<p>' in insert_patches[0]['new_element_xhtml']

    def test_insert_at_beginning(self):
        """선행 매칭 블록이 없으면 after_xpath=None."""
        alignment = {}
        change = BlockChange(
            index=0, change_type='added',
            old_block=None,
            new_block=_make_block('Very first paragraph'),
        )
        patches = build_patches(
            [change], [], [_make_block('Very first paragraph')],
            [], {}, {}, alignment)

        insert_patches = [p for p in patches if p.get('action') == 'insert']
        assert len(insert_patches) == 1
        assert insert_patches[0]['after_xpath'] is None

    def test_insert_empty_generates_patch(self):
        """added된 empty 블록은 빈 <p> insert 패치를 생성한다."""
        change = BlockChange(
            index=0, change_type='added',
            old_block=None,
            new_block=_make_block('\n', type_='empty'),
        )
        patches = build_patches([change], [], [], [], {}, {}, {})
        assert len(patches) == 1
        assert patches[0]['action'] == 'insert'

    def test_insert_frontmatter_skipped(self):
        """added된 frontmatter 블록은 무시."""
        change = BlockChange(
            index=0, change_type='added',
            old_block=None,
            new_block=_make_block('---\ntitle: x\n---\n', type_='frontmatter'),
        )
        patches = build_patches([change], [], [], [], {}, {}, {})
        assert len(patches) == 0


# ── _resolve_mapping_for_change ──


class TestResolveMappingForChange:
    """_resolve_mapping_for_change 매핑 해석 함수 테스트."""

    def _make_context(self, mappings=None, mdx_to_sidecar=None,
                      xpath_to_mapping=None):
        """공통 컨텍스트 dict를 구성한다."""
        mappings = mappings or []
        return {
            'mappings': mappings,
            'used_ids': set(),
            'mdx_to_sidecar': mdx_to_sidecar or {},
            'xpath_to_mapping': xpath_to_mapping or {},
        }

    def _old_plain(self, change):
        """change에서 old_plain을 계산한다."""
        return normalize_mdx_to_plain(
            change.old_block.content, change.old_block.type)

    def test_no_sidecar_match_no_containing_returns_skip(self):
        change = _make_change(0, 'hello', 'world')
        ctx = self._make_context()
        strategy, mapping = _resolve_mapping_for_change(
            change, self._old_plain(change), **ctx)
        assert strategy == 'skip'
        assert mapping is None

    def test_sidecar_direct_match_returns_direct(self):
        m = _make_mapping('b1', 'hello', xpath='p[1]')
        se = _make_sidecar('p[1]', [{'mdx_index': 0}])
        ctx = self._make_context(
            mappings=[m],
            mdx_to_sidecar={0: se},
            xpath_to_mapping={'p[1]': m},
        )
        change = _make_change(0, 'hello', 'world')
        strategy, mapping = _resolve_mapping_for_change(
            change, self._old_plain(change), **ctx)
        assert strategy == 'direct'
        assert mapping.block_id == 'b1'

    def test_sidecar_match_with_children_returns_containing(self):
        child = _make_mapping('c1', 'child text', xpath='li[1]')
        parent = _make_mapping('p1', 'parent text', xpath='ul[1]',
                               children=['c1'])
        se = _make_sidecar('ul[1]', [{'mdx_index': 0}])
        ctx = self._make_context(
            mappings=[parent, child],
            mdx_to_sidecar={0: se},
            xpath_to_mapping={'ul[1]': parent},
        )
        change = _make_change(0, 'child text', 'new child')
        strategy, mapping = _resolve_mapping_for_change(
            change, self._old_plain(change), **ctx)
        assert strategy == 'containing'
        assert mapping.block_id == 'p1'

    def test_no_sidecar_list_type_returns_list(self):
        change = _make_change(0, '- item1\n- item2', '- item1\n- changed', type_='list')
        ctx = self._make_context()
        strategy, mapping = _resolve_mapping_for_change(
            change, self._old_plain(change), **ctx)
        assert strategy == 'list'

    def test_no_sidecar_table_type_returns_table(self):
        table = '| a | b |\n| --- | --- |\n| 1 | 2 |'
        change = _make_change(0, table, table.replace('1', 'X'))
        ctx = self._make_context()
        strategy, mapping = _resolve_mapping_for_change(
            change, self._old_plain(change), **ctx)
        assert strategy == 'table'

    def test_no_sidecar_containing_match_returns_skip(self):
        m = _make_mapping('b1', 'hello world full text here', xpath='div[1]')
        change = _make_change(0, 'hello world', 'hi world')
        ctx = self._make_context(mappings=[m])
        strategy, mapping = _resolve_mapping_for_change(
            change, self._old_plain(change), **ctx)
        assert strategy == 'skip'
        assert mapping is None


# ── build_patches 멱등성 (idempotency) 테스트 ──


class TestBuildPatchesIdempotency:
    """push+fetch 후 verify 재실행 시 멱등성(idempotency) 테스트.

    reverse_sync push로 Confluence 원문을 교정한 후 fetch하면,
    XHTML은 이미 새 텍스트를 포함한다. 이 상태에서 verify를 재실행하면
    MDX diff는 여전히 존재하지만 (base branch MDX가 아직 old이므로),
    XHTML은 이미 업데이트되었으므로 패치를 생성하지 않아야 한다.

    버그: build_patches가 collapse_ws(old_plain) != collapse_ws(xhtml_plain_text)
    조건에서 transfer_text_changes를 호출하는데, xhtml_text가 이미 new_plain과
    동일한 상태에서 old→new 변경을 다시 매핑하여 텍스트가 중복된다.
    """

    def _setup_sidecar(self, xpath: str, mdx_idx: int):
        entry = _make_sidecar(xpath, [mdx_idx])
        return {mdx_idx: entry}

    def test_direct_patch_skipped_when_xhtml_already_matches_new(self):
        """XHTML이 이미 new_plain과 일치하면 변경이 없는 패치를 생성해야 한다.

        재현 시나리오:
          Original MDX: "또한 네이티브로 Kubernetes를 지원하지만, 주로 ... 고객을 대상으로 권장됩니다."
          Improved MDX: "또한 Kubernetes를 네이티브로 지원하지만, 주로 ... 고객에게 권장됩니다."

        1차 verify+push 후 XHTML이 업데이트됨 → 2차 verify에서 text 중복 발생.
        "네이티브로" → "네이티브로 네이티브로", "에게" → "에게에게" 등.
        """
        old_content = (
            "또한 네이티브로 Kubernetes를 지원하지만, "
            "주로 Kubernetes DevOps 팀이 있는 고객을 대상으로 권장됩니다."
        )
        new_content = (
            "또한 Kubernetes를 네이티브로 지원하지만, "
            "주로 Kubernetes DevOps 팀이 있는 고객에게 권장됩니다."
        )
        # push+fetch 후 XHTML은 new_content와 동일한 텍스트를 포함
        xhtml_text = new_content

        m = _make_mapping('m1', xhtml_text, xpath='p[1]')
        mappings = [m]
        xpath_to_mapping = {m.xhtml_xpath: m for m in mappings}
        change = _make_change(0, old_content, new_content)
        mdx_to_sidecar = self._setup_sidecar('p[1]', 0)

        patches = build_patches(
            [change], [change.old_block], [change.new_block],
            mappings, mdx_to_sidecar, xpath_to_mapping)

        # 이미 적용된 변경이므로 패치가 없거나 no-op이어야 함
        for p in patches:
            if 'new_plain_text' in p:
                assert p['new_plain_text'] == p['old_plain_text'], (
                    f"XHTML이 이미 변경된 상태에서 불필요한 패치 생성. "
                    f"new_plain_text에 텍스트 중복 포함: {p['new_plain_text']!r}"
                )

    def test_direct_multi_sentence_patch_skipped_when_already_applied(self):
        """여러 문장을 포함하는 direct match 블록에서도 멱등성이 보장되어야 한다.

        재현 시나리오 (실제 system-architecture-overview.mdx paragraph-38):
          Original MDX (3개 문장의 단일 블록):
            "위의 구성은 ... 사례입니다."
            "이용자가 웹브라우저로 QueryPie에 연결하여 사용할 수 있습니다."
            "그뿐만 아니라, DataGrip ... 설치하여 사용할 수 있습니다."
          Improved MDX:
            "위의 구성은 ... 사례입니다."
            "이용자는 웹 브라우저로 QueryPie에 연결하여 사용할 수 있습니다."
            "또한 DataGrip ... 설치해 사용할 수 있습니다."

        push 후 XHTML이 업데이트된 상태에서 "또한" → "또한또한" 중복 발생.
        """
        old_content = (
            "위의 구성은 실제 사례입니다.\n"
            "이용자가 웹브라우저로 QueryPie에 연결하여 사용할 수 있습니다.\n"
            "그뿐만 아니라, DataGrip, MySQL Workbench 등 "
            "애플리케이션에서 DB, System에 접속하기 위해, "
            "QueryPie Agent를 PC에 설치하여 사용할 수 있습니다."
        )
        new_content = (
            "위의 구성은 실제 사례입니다.\n"
            "이용자는 웹 브라우저로 QueryPie에 연결하여 사용할 수 있습니다.\n"
            "또한 DataGrip, MySQL Workbench 등 "
            "애플리케이션으로 DB와 시스템에 접속하기 위해 "
            "QueryPie Agent를 PC에 설치해 사용할 수 있습니다."
        )
        # normalize_mdx_to_plain은 줄바꿈을 공백으로 치환하고 join
        # push+fetch 후 XHTML은 new_content의 normalize 결과와 동일한 텍스트를 포함
        xhtml_text = normalize_mdx_to_plain(new_content, 'paragraph')

        m = _make_mapping('m1', xhtml_text, xpath='p[1]')
        mappings = [m]
        xpath_to_mapping = {m.xhtml_xpath: m for m in mappings}
        change = _make_change(0, old_content, new_content)
        mdx_to_sidecar = self._setup_sidecar('p[1]', 0)

        patches = build_patches(
            [change], [change.old_block], [change.new_block],
            mappings, mdx_to_sidecar, xpath_to_mapping)

        # 이미 적용된 변경이므로 텍스트 중복이 없어야 함
        for p in patches:
            if 'new_plain_text' in p:
                assert '또한또한' not in p['new_plain_text'], (
                    f"텍스트 중복 발생: {p['new_plain_text']!r}"
                )
                assert p['new_plain_text'] == p['old_plain_text'], (
                    f"XHTML이 이미 변경된 상태에서 불필요한 패치 생성: "
                    f"new={p['new_plain_text']!r}"
                )


# ── Link body trailing space 제거 ──


class TestLinkBodyTrailingSpaceStrip:
    """<ac:link-body> trailing space가 파이프라인을 통해 자연스럽게 제거된다.

    재현 시나리오 (administrator-manual.mdx, page 544178405):
      Original MDX: `[Okta 연동하기 ](url)` (trailing space)
      Improved MDX: `[Okta 연동하기](url)` (trailing space 제거)
      XHTML: `<ac:link-body>Okta 연동하기 </ac:link-body>`
      기대: normalize_mdx_to_plain이 trailing space를 보존하여
            transfer_text_changes로 자연스럽게 전이된다.
    """

    def test_normalize_preserves_link_trailing_space(self):
        """normalize_mdx_to_plain이 link text의 trailing space를 보존한다."""
        with_space = '* [Okta 연동하기 ](url1)\n* [LDAP 연동하기](url2)'
        without_space = '* [Okta 연동하기](url1)\n* [LDAP 연동하기](url2)'
        old_plain = normalize_mdx_to_plain(with_space, 'html_block')
        new_plain = normalize_mdx_to_plain(without_space, 'html_block')
        assert old_plain != new_plain
        # trailing space 보존: 'Okta 연동하기 \n' vs 'Okta 연동하기\n'
        assert 'Okta 연동하기 \n' in old_plain
        assert 'Okta 연동하기 \n' not in new_plain

    def test_build_patches_transfers_trailing_space_change(self):
        """build_patches가 trailing space 변경을 template rewriting으로 전이한다 (Phase 5 Axis 1)."""
        xhtml_text = (
            '<table><tbody><tr><td>'
            '<ul><li><p>'
            '<ac:link><ri:page ri:content-title="Okta 연동하기"/>'
            '<ac:link-body>Okta 연동하기 </ac:link-body></ac:link>'
            '</p></li><li><p>'
            '<ac:link><ri:page ri:content-title="LDAP 연동하기"/>'
            '<ac:link-body>LDAP 연동하기</ac:link-body></ac:link>'
            '</p></li></ul>'
            '</td></tr></tbody></table>'
        )
        xhtml_plain = 'Okta 연동하기 LDAP 연동하기'
        mapping = BlockMapping(
            block_id='table-1', type='table',
            xhtml_xpath='table[1]',
            xhtml_text=xhtml_text,
            xhtml_plain_text=xhtml_plain,
            xhtml_element_index=0,
        )
        old_content = (
            '<table>\n<tbody>\n<tr>\n<td>\n'
            '* [Okta 연동하기 ](general/okta)\n'
            '* [LDAP 연동하기](general/ldap)\n'
            '</td>\n</tr>\n</tbody>\n</table>\n'
        )
        new_content = (
            '<table>\n<tbody>\n<tr>\n<td>\n'
            '* [Okta 연동하기](general/okta)\n'
            '* [LDAP 연동하기](general/ldap)\n'
            '</td>\n</tr>\n</tbody>\n</table>\n'
        )
        change = _make_change(0, old_content, new_content, type_='html_block')
        mdx_to_sidecar = {0: _make_sidecar('table[1]', [0])}
        xpath_to_mapping = {'table[1]': mapping}

        patches = build_patches(
            [change], [change.old_block], [change.new_block],
            [mapping], mdx_to_sidecar, xpath_to_mapping)

        assert len(patches) == 1
        # ac:link 구조가 보존된 replace_fragment 패치
        assert patches[0]['action'] == 'replace_fragment'
        assert '<ac:link>' in patches[0]['new_element_xhtml']

    def test_patch_xhtml_strips_link_body_trailing_space(self):
        """patch_xhtml가 <ac:link-body> trailing space를 자연스럽게 제거한다.

        end-to-end 테스트: text transfer 파이프라인으로 trailing space 제거.
        """
        xhtml = (
            '<table><tbody><tr><td>'
            '<ul><li><p>'
            '<ac:link><ri:page ri:content-title="Okta 연동하기"/>'
            '<ac:link-body>Okta 연동하기 </ac:link-body></ac:link>'
            '</p></li><li><p>'
            '<ac:link><ri:page ri:content-title="LDAP 연동하기"/>'
            '<ac:link-body>LDAP 연동하기</ac:link-body></ac:link>'
            '</p></li></ul>'
            '</td></tr></tbody></table>'
        )
        # trailing space가 제거되면 두 텍스트 사이의 separator도 사라짐
        patches = [{
            'xhtml_xpath': 'table[1]',
            'old_plain_text': 'Okta 연동하기 LDAP 연동하기',
            'new_plain_text': 'Okta 연동하기LDAP 연동하기',
        }]

        result = patch_xhtml(xhtml, patches)
        assert '<ac:link-body>Okta 연동하기</ac:link-body>' in result
        assert '<ac:link-body>Okta 연동하기 </ac:link-body>' not in result
        # LDAP은 원래 trailing space가 없으므로 변경 없음
        assert '<ac:link-body>LDAP 연동하기</ac:link-body>' in result

    def test_single_link_in_p_trailing_space(self):
        """<p> 내 단일 link의 trailing space가 edge trailing 로직으로 제거된다."""
        xhtml = (
            '<p>'
            '<ac:link><ri:page ri:content-title="Okta 연동하기"/>'
            '<ac:link-body>Okta 연동하기 </ac:link-body></ac:link>'
            '</p>'
        )
        patches = [{
            'xhtml_xpath': 'p[1]',
            'old_plain_text': 'Okta 연동하기 ',
            'new_plain_text': 'Okta 연동하기',
        }]

        result = patch_xhtml(xhtml, patches)
        assert '<ac:link-body>Okta 연동하기</ac:link-body>' in result
        assert '<ac:link-body>Okta 연동하기 </ac:link-body>' not in result


class TestBlockquoteDirectPatch:
    """blockquote 블록의 direct 패치 시 <p> 구조가 보존되어야 한다.

    재현 시나리오 (mongodb-specific-guide.mdx, page 544380381):
      Original MDX: '> text **bold** more text'
      Improved MDX: '> text **bold** changed text'
      XHTML: <blockquote><p>text <strong>bold</strong> more text</p></blockquote>
      현상: mdx_block_to_inner_xhtml()에 blockquote 핸들러가 없어
            > prefix가 XHTML에 그대로 삽입되고 <p> 래퍼가 소실됨
    """

    def test_mdx_block_to_inner_xhtml_blockquote(self):
        """blockquote content가 > prefix 제거 후 <p>로 감싸져야 한다."""
        from reverse_sync.mdx_to_xhtml_inline import mdx_block_to_inner_xhtml

        content = '> text with **bold** and `code` end\n'
        result = mdx_block_to_inner_xhtml(content, 'blockquote')

        # > prefix가 제거되어야 함
        assert '>' not in result.split('<')[0]  # 첫 태그 앞에 > 없음
        # <p> 래퍼가 있어야 함
        assert result.startswith('<p>')
        assert result.endswith('</p>')
        # inline 변환이 적용되어야 함
        assert '<strong>bold</strong>' in result
        assert '<code>code</code>' in result

    def test_blockquote_direct_patch_preserves_p_wrapper(self):
        """blockquote direct 패치가 <blockquote><p>...</p></blockquote> 구조를 보존한다."""
        xhtml = (
            '<blockquote><p>'
            '+srv 스킴은 <strong>tls=true</strong>를 수동으로 입력해줘야 합니다.'
            '</p></blockquote>'
        )
        xhtml_plain = '+srv 스킴은 tls=true를 수동으로 입력해줘야 합니다.'
        mapping = BlockMapping(
            block_id='bq-1', type='html_block',
            xhtml_xpath='blockquote[1]',
            xhtml_text=xhtml,
            xhtml_plain_text=xhtml_plain,
            xhtml_element_index=0,
        )
        old_content = '> +srv 스킴은 **tls=true**를 수동으로 입력해줘야 합니다.\n'
        new_content = '> +srv 스킴은 **tls=true**를 수동으로 입력해 주어야 합니다.\n'
        change = _make_change(0, old_content, new_content, type_='blockquote')

        mdx_to_sidecar = {0: _make_sidecar('blockquote[1]', [0])}
        xpath_to_mapping = {'blockquote[1]': mapping}

        patches = build_patches(
            [change], [change.old_block], [change.new_block],
            [mapping], mdx_to_sidecar, xpath_to_mapping)

        assert len(patches) == 1
        patch = patches[0]

        # new_inner_xhtml 패치가 생성되어야 함 (direct 전략)
        assert 'new_inner_xhtml' in patch
        inner = patch['new_inner_xhtml']
        # <p> 래퍼가 포함되어야 함
        assert '<p>' in inner
        # > prefix가 포함되면 안 됨
        assert '> +srv' not in inner
        # 변경된 텍스트가 반영되어야 함
        assert '입력해 주어야' in inner

        # end-to-end: patch_xhtml 적용 후 <blockquote><p> 구조가 유지
        result = patch_xhtml(xhtml, patches)
        assert '<blockquote>' in result
        assert '<p>' in result
        assert '> +srv' not in result
        assert '입력해 주어야' in result


# ── _apply_mdx_diff_to_xhtml 직접 테스트 ──


class TestApplyMdxDiffToXhtml:
    """text_transfer 삭제 후 핵심 알고리즘 regression 테스트."""

    def test_replace_preserves_xhtml_whitespace(self):
        """MDX 단어 교체가 XHTML의 다른 공백 구조를 보존하면서 적용된다."""
        mdx_old = '설정 순서 설정 항목 1 Databased Access Control 설정하기'
        mdx_new = '설정 순서 설정 항목 1 Database Access Control 설정하기'
        xhtml = '설정 순서설정 항목1Databased Access Control 설정하기'

        result = _apply_mdx_diff_to_xhtml(mdx_old, mdx_new, xhtml)
        assert result == '설정 순서설정 항목1Database Access Control 설정하기'

    def test_insert(self):
        """공백/문자 삽입이 올바르게 전이된다."""
        result = _apply_mdx_diff_to_xhtml(
            '잠금해제 수행자 정보', '잠금 해제 수행자 정보', '잠금해제 수행자 정보')
        assert result == '잠금 해제 수행자 정보'

    def test_delete(self):
        """텍스트 삭제가 올바르게 전파된다."""
        result = _apply_mdx_diff_to_xhtml(
            'hello world', 'hello', 'hello world')
        assert 'world' not in result
        assert 'hello' in result

    def test_no_change_returns_xhtml_unchanged(self):
        """변경이 없으면 XHTML 원문이 그대로 반환된다."""
        xhtml = 'Hello  world'
        result = _apply_mdx_diff_to_xhtml('Hello world', 'Hello world', xhtml)
        assert result == xhtml

    def test_repeated_pattern_long_text(self):
        """반복 패턴이 있는 긴 텍스트에서 로컬 변경만 적용된다."""
        xhtml = (
            '첫째 항목 텍스트입니다.'
            '둘째 항목 700MB를 초과 여부에 따라 재생화면을 노출합니다. '
            '700MB 미만 상단에 기본 정보가 노출됩니다. '
            '재생화면이 하단에 노출됩니다. '
            '700MB 이상 재생 화면 안에 실행 불가 문구를 제공합니다. '
            '파일 크기가 700MB를 초과하여 세션을 재생할 수 없습니다.'
        )
        mdx_old = (
            '첫째 항목 텍스트입니다. '
            '둘째 항목 700MB를 초과 여부에 따라 재생화면을 노출합니다. '
            '700MB 미만 상단에 기본 정보가 노출됩니다. '
            '재생화면이 하단에 노출됩니다. '
            '700MB 이상 재생 화면 안에 실행 불가 문구를 제공합니다. '
            '파일 크기가 700MB를 초과하여 세션을 재생할 수 없습니다.'
        )
        mdx_new = (
            '첫째 항목 텍스트입니다. '
            '둘째 항목 700MB 초과 여부에 따라 재생 화면을 노출합니다. '
            '700MB 미만 상단에 기본 정보가 노출됩니다. '
            '재생 화면이 하단에 노출됩니다. '
            '700MB 이상 재생 화면 안에 실행 불가 문구를 제공합니다. '
            '파일 크기가 700MB를 초과하여 세션을 재생할 수 없습니다.'
        )
        result = _apply_mdx_diff_to_xhtml(mdx_old, mdx_new, xhtml)
        assert '700MB 초과 여부' in result
        assert '700MB를 초과 여부' not in result
        assert '재생 화면을 노출합니다' in result
        assert '첫째 항목 텍스트입니다.' in result
        assert '700MB를 초과하여 세션을' in result

    def test_front_insert_mapped_to_middle_of_xhtml(self):
        """MDX 선두 삽입(pos 0)이 XHTML 중간 위치에 올바르게 매핑된다."""
        mdx_old = 'child text here'
        mdx_new = 'NEW child text here'
        xhtml = 'parent prefix child text here suffix'

        result = _apply_mdx_diff_to_xhtml(mdx_old, mdx_new, xhtml)
        assert result == 'parent prefix NEW child text here suffix'
