"""patch_builder 유닛 테스트.

기존 _find_containing_mapping 테스트 + build_patches 6개 분기 경로
+ helper 함수 (is_markdown_table, split_table_rows, normalize_table_row,
split_list_items, extract_list_marker_prefix, _resolve_child_mapping,
build_table_row_patches, build_list_item_patches) 테스트.
"""
from reverse_sync.block_diff import BlockChange
from reverse_sync.mapping_recorder import BlockMapping
from reverse_sync.mdx_block_parser import MdxBlock
from reverse_sync.sidecar import SidecarEntry
from text_utils import normalize_mdx_to_plain
from reverse_sync.patch_builder import (
    _find_containing_mapping,
    _flush_containing_changes,
    _resolve_child_mapping,
    _resolve_mapping_for_change,
    build_patches,
    build_list_item_patches,
    build_table_row_patches,
    has_inline_format_change,
    is_markdown_table,
    split_table_rows,
    normalize_table_row,
    split_list_items,
    extract_list_marker_prefix,
    _extract_inline_markers,
)


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


# ── _find_containing_mapping (기존 7개 테스트 유지) ──


class TestFindContainingMapping:
    def test_finds_mapping_containing_old_plain(self):
        m1 = _make_mapping('m1', 'Command Audit : Server내 수행 명령어 이력')
        m2 = _make_mapping('m2', 'General User Access History Activity Logs Servers Command Audit : Server내 수행 명령어 이력 Account Lock History')
        mappings = [m1, m2]
        result = _find_containing_mapping(
            'Command Audit : Server내 수행 명령어 이력', mappings, set())
        assert result is m1

    def test_skips_used_ids(self):
        m1 = _make_mapping('m1', 'Command Audit : Server내 수행 명령어 이력')
        m2 = _make_mapping('m2', 'General Servers Command Audit : Server내 수행 명령어 이력 Account Lock')
        mappings = [m1, m2]
        used = {'m1'}
        result = _find_containing_mapping(
            'Command Audit : Server내 수행 명령어 이력', mappings, used)
        assert result is m2

    def test_returns_none_for_short_text(self):
        m1 = _make_mapping('m1', 'hello world foo bar')
        result = _find_containing_mapping('abc', [m1], set())
        assert result is None

    def test_returns_none_for_empty_text(self):
        m1 = _make_mapping('m1', 'hello world foo bar')
        result = _find_containing_mapping('', [m1], set())
        assert result is None

    def test_returns_none_when_no_mapping_contains_text(self):
        m1 = _make_mapping('m1', 'completely different text here')
        result = _find_containing_mapping(
            'Command Audit : Server내 수행 명령어 이력', [m1], set())
        assert result is None

    def test_ignores_whitespace_differences(self):
        m1 = _make_mapping('m1', 'Command  Audit :  Server내   수행 명령어   이력')
        result = _find_containing_mapping(
            'Command Audit : Server내 수행 명령어 이력', [m1], set())
        assert result is m1

    def test_ignores_invisible_unicode_chars(self):
        m1 = _make_mapping(
            'm1',
            'Account Lock History\u3164 : QueryPie\u200b사용자별 서버 접속 계정')
        result = _find_containing_mapping(
            'Account Lock History : QueryPie사용자별 서버 접속 계정',
            [m1], set())
        assert result is m1


# ── _resolve_child_mapping ──


class TestResolveChildMapping:
    def test_exact_match_first_pass(self):
        child = _make_mapping('c1', 'child text')
        parent = _make_mapping('p1', 'parent text', children=['c1'])
        id_map = {'c1': child, 'p1': parent}
        result = _resolve_child_mapping('child text', parent, id_map)
        assert result is child

    def test_whitespace_collapsed_match(self):
        child = _make_mapping('c1', 'child  text  here')
        parent = _make_mapping('p1', 'parent', children=['c1'])
        id_map = {'c1': child, 'p1': parent}
        result = _resolve_child_mapping('child text here', parent, id_map)
        assert result is child

    def test_nospace_match(self):
        child = _make_mapping('c1', 'child  text')
        parent = _make_mapping('p1', 'parent', children=['c1'])
        id_map = {'c1': child, 'p1': parent}
        # collapse_ws doesn't match, but nospace does
        result = _resolve_child_mapping('childtext', parent, id_map)
        assert result is child

    def test_xhtml_list_marker_stripped(self):
        child = _make_mapping('c1', '- item text')
        parent = _make_mapping('p1', 'parent', children=['c1'])
        id_map = {'c1': child, 'p1': parent}
        result = _resolve_child_mapping('item text', parent, id_map)
        assert result is child

    def test_mdx_list_marker_stripped(self):
        child = _make_mapping('c1', 'item text')
        parent = _make_mapping('p1', 'parent', children=['c1'])
        id_map = {'c1': child, 'p1': parent}
        result = _resolve_child_mapping('- item text', parent, id_map)
        assert result is child

    def test_returns_none_when_no_match(self):
        child = _make_mapping('c1', 'completely different')
        parent = _make_mapping('p1', 'parent', children=['c1'])
        id_map = {'c1': child, 'p1': parent}
        result = _resolve_child_mapping('no match text here', parent, id_map)
        assert result is None

    def test_returns_none_for_empty_text(self):
        parent = _make_mapping('p1', 'parent', children=['c1'])
        child = _make_mapping('c1', 'child')
        id_map = {'c1': child, 'p1': parent}
        result = _resolve_child_mapping('', parent, id_map)
        assert result is None

    def test_missing_child_id(self):
        parent = _make_mapping('p1', 'parent', children=['missing'])
        id_map = {'p1': parent}
        result = _resolve_child_mapping('some text here', parent, id_map)
        assert result is None


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


class TestSplitTableRows:
    def test_splits_data_rows(self):
        content = '| h1 | h2 |\n| --- | --- |\n| a | b |\n| c | d |'
        rows = split_table_rows(content)
        assert rows == ['| h1 | h2 |', '| a | b |', '| c | d |']

    def test_skips_separator(self):
        content = '| h |\n| --- |\n| v |'
        rows = split_table_rows(content)
        assert '| --- |' not in rows

    def test_skips_empty_lines(self):
        content = '| a |\n\n| b |'
        rows = split_table_rows(content)
        assert rows == ['| a |', '| b |']


class TestNormalizeTableRow:
    def test_extracts_cell_text(self):
        assert normalize_table_row('| hello | world |') == 'hello world'

    def test_strips_bold(self):
        assert normalize_table_row('| **bold** | text |') == 'bold text'

    def test_strips_code(self):
        assert normalize_table_row('| `code` | text |') == 'code text'

    def test_strips_link(self):
        assert normalize_table_row('| [Title](url) | x |') == 'Title x'

    def test_empty_cells_skipped(self):
        assert normalize_table_row('|  | text |') == 'text'

    def test_unescapes_html(self):
        assert normalize_table_row('| A &amp; B | x |') == 'A & B x'


class TestSplitListItems:
    def test_dash_items(self):
        content = '- item one\n- item two\n- item three'
        items = split_list_items(content)
        assert items == ['- item one', '- item two', '- item three']

    def test_numbered_items(self):
        content = '1. first\n2. second'
        items = split_list_items(content)
        assert items == ['1. first', '2. second']

    def test_multiline_item(self):
        content = '- item one\n  continued\n- item two'
        items = split_list_items(content)
        assert len(items) == 2
        assert 'continued' in items[0]

    def test_blank_line_separator(self):
        content = '- item one\n\n- item two'
        items = split_list_items(content)
        assert items == ['- item one', '- item two']


class TestExtractListMarkerPrefix:
    def test_dash(self):
        assert extract_list_marker_prefix('- item') == '- '

    def test_asterisk(self):
        assert extract_list_marker_prefix('* item') == '* '

    def test_number(self):
        assert extract_list_marker_prefix('1. item') == '1. '

    def test_no_marker(self):
        assert extract_list_marker_prefix('plain text') == ''


# ── build_patches 분기 경로 테스트 ──


class TestBuildPatches:
    """build_patches()의 6가지 주요 분기 경로를 테스트한다."""

    def _setup_sidecar(self, xpath: str, mdx_idx: int):
        """sidecar와 xpath→mapping 인덱스를 구성하는 헬퍼."""
        entry = _make_sidecar(xpath, [mdx_idx])
        mdx_to_sidecar = {mdx_idx: entry}
        return mdx_to_sidecar

    # Path 1: sidecar 매칭 → children 있음 → child 해석 성공 → 직접 패치
    def test_path1_sidecar_match_child_resolved(self):
        child = _make_mapping('c1', 'child text', xpath='li[1]')
        parent = _make_mapping('p1', 'parent text child text more', xpath='ul[1]',
                               type_='list', children=['c1'])
        mappings = [parent, child]
        xpath_to_mapping = {m.xhtml_xpath: m for m in mappings}

        change = _make_change(0, 'child text', 'updated child')
        mdx_to_sidecar = self._setup_sidecar('ul[1]', 0)

        patches = build_patches(
            [change], [change.old_block], [change.new_block],
            mappings, mdx_to_sidecar, xpath_to_mapping)

        assert len(patches) == 1
        assert patches[0]['xhtml_xpath'] == 'li[1]'
        assert 'updated child' in patches[0]['new_plain_text']

    # Path 2: sidecar 매칭 → children 있음 → child 해석 실패
    #          → 텍스트 불일치 → list 분리 (반환 빈 = item 수 불일치)
    def test_path2_sidecar_match_child_fail_list_split(self):
        parent = _make_mapping('p1', 'totally different parent', xpath='ul[1]',
                               type_='list', children=['c1'])
        child = _make_mapping('c1', 'no match here', xpath='li[1]')
        mappings = [parent, child]
        xpath_to_mapping = {m.xhtml_xpath: m for m in mappings}

        # list type with different item count → returns []
        change = _make_change(
            0, '- item one\n- item two', '- item one\n- item two\n- item three',
            type_='list')
        mdx_to_sidecar = self._setup_sidecar('ul[1]', 0)

        patches = build_patches(
            [change], [change.old_block], [change.new_block],
            mappings, mdx_to_sidecar, xpath_to_mapping)

        # item count mismatch → build_list_item_patches returns []
        assert patches == []

    # Path 3: sidecar 매칭 → children 있음 → child 해석 실패
    #          → parent를 containing block으로 사용
    def test_path3_sidecar_child_fail_containing_block(self):
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

    # Path 4: sidecar 미스 → 텍스트 포함 검색 → containing block
    def test_path4_sidecar_miss_text_search_containing(self):
        m1 = _make_mapping('m1', 'this mapping contains the search text here')
        mappings = [m1]
        xpath_to_mapping = {m.xhtml_xpath: m for m in mappings}

        change = _make_change(0, 'search text', 'replaced text')
        mdx_to_sidecar = {}  # 빈 sidecar → sidecar 미스

        patches = build_patches(
            [change], [change.old_block], [change.new_block],
            mappings, mdx_to_sidecar, xpath_to_mapping)

        assert len(patches) == 1
        assert patches[0]['xhtml_xpath'] == m1.xhtml_xpath

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

    # Path 6: sidecar 매칭 → children 없음 → 텍스트 불일치 → 재매핑
    def test_path6_sidecar_match_text_mismatch_remapping(self):
        # sidecar 매핑이 있지만 텍스트가 포함되지 않음 → better 매핑 찾기
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
        assert patches[0]['xhtml_xpath'] == 'p[2]'

    # 직접 매칭 + text_transfer 사용
    def test_direct_match_with_transfer(self):
        m1 = _make_mapping('m1', 'hello  world', xpath='p[1]')
        mappings = [m1]
        xpath_to_mapping = {m.xhtml_xpath: m for m in mappings}

        change = _make_change(0, 'hello world', 'hello earth')
        mdx_to_sidecar = self._setup_sidecar('p[1]', 0)

        patches = build_patches(
            [change], [change.old_block], [change.new_block],
            mappings, mdx_to_sidecar, xpath_to_mapping)

        assert len(patches) == 1
        # text_transfer가 XHTML 공백을 보존하면서 변경 적용
        assert 'earth' in patches[0]['new_plain_text']

    # 직접 매칭 + text_transfer 미사용 (텍스트 동일)
    def test_direct_match_no_transfer(self):
        m1 = _make_mapping('m1', 'hello world', xpath='p[1]')
        mappings = [m1]
        xpath_to_mapping = {m.xhtml_xpath: m for m in mappings}

        change = _make_change(0, 'hello world', 'hello earth')
        mdx_to_sidecar = self._setup_sidecar('p[1]', 0)

        patches = build_patches(
            [change], [change.old_block], [change.new_block],
            mappings, mdx_to_sidecar, xpath_to_mapping)

        assert len(patches) == 1
        assert patches[0]['new_plain_text'] == 'hello earth'

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

    # Inline format 변경 → new_inner_xhtml 패치 생성
    def test_direct_inline_code_added_generates_inner_xhtml(self):
        """paragraph에서 backtick이 추가되면 new_inner_xhtml 패치를 생성한다."""
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
        assert 'new_inner_xhtml' in patches[0]
        assert '<code>https://example.com/</code>' in patches[0]['new_inner_xhtml']
        assert 'new_plain_text' not in patches[0]

    def test_direct_text_only_change_uses_plain_text_patch(self):
        """inline format 변경 없이 텍스트만 바뀌면 기존 text patch를 사용한다."""
        m1 = _make_mapping('m1', 'hello world', xpath='p[1]')
        mappings = [m1]
        xpath_to_mapping = {m.xhtml_xpath: m for m in mappings}

        change = _make_change(0, 'hello world', 'hello earth')
        mdx_to_sidecar = self._setup_sidecar('p[1]', 0)

        patches = build_patches(
            [change], [change.old_block], [change.new_block],
            mappings, mdx_to_sidecar, xpath_to_mapping)

        assert len(patches) == 1
        assert 'new_plain_text' in patches[0]
        assert 'new_inner_xhtml' not in patches[0]

    # 여러 변경이 동일 containing block에 그룹화
    def test_multiple_changes_grouped_to_containing(self):
        container = _make_mapping(
            'm1', 'first part and second part', xpath='p[1]')
        mappings = [container]
        xpath_to_mapping = {m.xhtml_xpath: m for m in mappings}

        change1 = _make_change(0, 'first part', 'first UPDATED')
        change2 = _make_change(1, 'second part', 'second UPDATED')
        mdx_to_sidecar = {}  # sidecar 미스 → containing 검색

        patches = build_patches(
            [change1, change2],
            [change1.old_block, change2.old_block],
            [change1.new_block, change2.new_block],
            mappings, mdx_to_sidecar, xpath_to_mapping)

        assert len(patches) == 1
        assert 'UPDATED' in patches[0]['new_plain_text']


# ── build_table_row_patches ──


class TestBuildTableRowPatches:
    def test_patches_changed_row(self):
        container = _make_mapping(
            'm1', 'Header1 Header2 old_val other', xpath='table[1]',
            type_='table')
        mappings = [container]
        mdx_to_sidecar = {0: _make_sidecar('table[1]', [0])}
        xpath_to_mapping = {'table[1]': container}

        change = _make_change(
            0,
            '| Header1 | Header2 |\n| --- | --- |\n| old_val | other |',
            '| Header1 | Header2 |\n| --- | --- |\n| new_val | other |',
        )

        patches = build_table_row_patches(
            change, mappings, set(), mdx_to_sidecar, xpath_to_mapping)

        assert len(patches) == 1
        assert 'new_val' in patches[0]['new_plain_text']

    def test_row_count_mismatch_returns_empty(self):
        container = _make_mapping('m1', 'text', xpath='table[1]')
        change = _make_change(
            0,
            '| a |\n| --- |\n| b |',
            '| a |\n| --- |\n| b |\n| c |',
        )
        patches = build_table_row_patches(
            change, [container], set(),
            {0: _make_sidecar('table[1]', [0])}, {'table[1]': container})
        assert patches == []

    def test_no_sidecar_returns_empty(self):
        change = _make_change(
            0, '| a |\n| --- |\n| b |', '| a |\n| --- |\n| c |')
        patches = build_table_row_patches(change, [], set(), {}, {})
        assert patches == []


# ── build_list_item_patches ──


class TestBuildListItemPatches:
    def test_patches_changed_item_with_child(self):
        child = _make_mapping('c1', 'old item', xpath='li[1]')
        parent = _make_mapping(
            'p1', 'list parent', xpath='ul[1]', children=['c1'])
        mappings = [parent, child]
        id_map = {m.block_id: m for m in mappings}
        mdx_to_sidecar = {0: _make_sidecar('ul[1]', [0])}
        xpath_to_mapping = {m.xhtml_xpath: m for m in mappings}

        change = _make_change(
            0, '- old item\n- keep item', '- new item\n- keep item',
            type_='list')

        patches = build_list_item_patches(
            change, mappings, set(),
            mdx_to_sidecar, xpath_to_mapping, id_map)

        assert len(patches) == 1
        assert 'new item' in patches[0]['new_plain_text']

    def test_item_count_mismatch_returns_empty(self):
        change = _make_change(
            0, '- item one\n- item two', '- item one',
            type_='list')
        patches = build_list_item_patches(change, [], set(), {}, {})
        assert patches == []

    def test_list_item_inline_code_added_generates_inner_xhtml(self):
        """리스트 항목에서 backtick 추가 시 new_inner_xhtml 패치를 생성한다."""
        child = _make_mapping('c1', 'use kubectl command', xpath='ul[1]/li[1]/p[1]')
        parent = _make_mapping('p1', 'use kubectl command', xpath='ul[1]',
                               type_='list', children=['c1'])
        mappings = [parent, child]
        xpath_to_mapping = {m.xhtml_xpath: m for m in mappings}
        id_to_mapping = {m.block_id: m for m in mappings}

        change = _make_change(
            0,
            '* use kubectl command\n',
            '* use `kubectl` command\n',
            type_='list',
        )
        mdx_to_sidecar = {0: _make_sidecar('ul[1]', [0])}

        patches = build_list_item_patches(
            change, mappings, set(),
            mdx_to_sidecar, xpath_to_mapping, id_to_mapping)

        assert len(patches) == 1
        assert 'new_inner_xhtml' in patches[0]
        assert '<code>kubectl</code>' in patches[0]['new_inner_xhtml']

    def test_child_miss_falls_back_to_containing(self):
        parent = _make_mapping(
            'p1', 'parent old text here in list', xpath='ul[1]',
            children=['c1'])
        child = _make_mapping('c1', 'no match whatsoever', xpath='li[1]')
        mappings = [parent, child]
        id_map = {m.block_id: m for m in mappings}
        mdx_to_sidecar = {0: _make_sidecar('ul[1]', [0])}
        xpath_to_mapping = {m.xhtml_xpath: m for m in mappings}

        change = _make_change(
            0, '- old text', '- new text',
            type_='list')

        patches = build_list_item_patches(
            change, mappings, set(),
            mdx_to_sidecar, xpath_to_mapping, id_map)

        assert len(patches) == 1
        assert patches[0]['xhtml_xpath'] == 'ul[1]'


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

    def test_delete_non_content_skipped(self):
        """deleted된 empty/frontmatter 블록은 무시."""
        change = BlockChange(
            index=0, change_type='deleted',
            old_block=_make_block('', type_='empty'),
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

    def test_insert_non_content_skipped(self):
        """added된 empty 블록은 무시."""
        change = BlockChange(
            index=0, change_type='added',
            old_block=None,
            new_block=_make_block('\n', type_='empty'),
        )
        patches = build_patches([change], [], [], [], {}, {}, {})
        assert len(patches) == 0


# ── _flush_containing_changes ──


class TestFlushContainingChanges:
    """_flush_containing_changes 헬퍼 함수 테스트."""

    def test_empty_dict_returns_empty(self):
        assert _flush_containing_changes({}) == []

    def test_single_change(self):
        m = _make_mapping('b1', 'hello world', xpath='p[1]')
        cc = {'b1': (m, [('hello', 'hi')])}
        patches = _flush_containing_changes(cc)
        assert len(patches) == 1
        assert patches[0]['xhtml_xpath'] == 'p[1]'
        assert patches[0]['old_plain_text'] == 'hello world'
        assert 'hi' in patches[0]['new_plain_text']

    def test_multiple_changes_same_block(self):
        m = _make_mapping('b1', 'aaa bbb ccc', xpath='p[1]')
        cc = {'b1': (m, [('aaa', 'AAA'), ('bbb', 'BBB')])}
        patches = _flush_containing_changes(cc)
        assert len(patches) == 1
        assert 'AAA' in patches[0]['new_plain_text']
        assert 'BBB' in patches[0]['new_plain_text']

    def test_used_ids_updated(self):
        m = _make_mapping('b1', 'text', xpath='p[1]')
        cc = {'b1': (m, [('text', 'changed')])}
        used = set()
        _flush_containing_changes(cc, used_ids=used)
        assert 'b1' in used

    def test_used_ids_none_no_error(self):
        m = _make_mapping('b1', 'text', xpath='p[1]')
        cc = {'b1': (m, [('text', 'changed')])}
        patches = _flush_containing_changes(cc, used_ids=None)
        assert len(patches) == 1

    def test_multiple_blocks(self):
        m1 = _make_mapping('b1', 'alpha', xpath='p[1]')
        m2 = _make_mapping('b2', 'beta', xpath='p[2]')
        cc = {
            'b1': (m1, [('alpha', 'ALPHA')]),
            'b2': (m2, [('beta', 'BETA')]),
        }
        patches = _flush_containing_changes(cc)
        assert len(patches) == 2

    def test_inline_change_in_containing_still_uses_text_patch(self):
        """containing block에서는 inline 변경이 있어도 text patch를 유지한다."""
        m = _make_mapping('m1', 'use command and url', xpath='p[1]')
        containing_changes = {
            'm1': (m, [
                ('use command and url', 'use command and url'),
            ]),
        }
        patches = _flush_containing_changes(containing_changes)
        assert len(patches) == 1
        assert 'new_plain_text' in patches[0]
        assert 'new_inner_xhtml' not in patches[0]


# ── _resolve_mapping_for_change ──


class TestResolveMappingForChange:
    """_resolve_mapping_for_change 매핑 해석 함수 테스트."""

    def _make_context(self, mappings=None, mdx_to_sidecar=None,
                      xpath_to_mapping=None, id_to_mapping=None):
        """공통 컨텍스트 dict를 구성한다."""
        mappings = mappings or []
        return {
            'mappings': mappings,
            'used_ids': set(),
            'mdx_to_sidecar': mdx_to_sidecar or {},
            'xpath_to_mapping': xpath_to_mapping or {},
            'id_to_mapping': id_to_mapping or {m.block_id: m for m in mappings},
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

    def test_sidecar_match_with_children_resolved_returns_direct(self):
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
        assert strategy == 'direct'
        assert mapping.block_id == 'c1'

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

    def test_no_sidecar_containing_match_returns_containing(self):
        m = _make_mapping('b1', 'hello world full text here', xpath='div[1]')
        change = _make_change(0, 'hello world', 'hi world')
        ctx = self._make_context(mappings=[m])
        strategy, mapping = _resolve_mapping_for_change(
            change, self._old_plain(change), **ctx)
        assert strategy == 'containing'
        assert mapping.block_id == 'b1'


# ── Inline format 변경 감지 테스트 ──


class TestExtractInlineMarkers:
    """_extract_inline_markers()의 inline 포맷 마커 추출을 테스트한다."""

    def test_no_markers(self):
        assert _extract_inline_markers('plain text only') == []

    def test_code_span(self):
        markers = _extract_inline_markers('use `kubectl` command')
        assert len(markers) == 1
        assert markers[0][0] == 'code'
        assert markers[0][2] == 'kubectl'

    def test_bold(self):
        markers = _extract_inline_markers('this is **important** text')
        assert len(markers) == 1
        assert markers[0][0] == 'bold'
        assert markers[0][2] == 'important'

    def test_italic(self):
        markers = _extract_inline_markers('this is *emphasized* text')
        assert len(markers) == 1
        assert markers[0][0] == 'italic'
        assert markers[0][2] == 'emphasized'

    def test_link(self):
        markers = _extract_inline_markers('see [docs](https://example.com)')
        assert len(markers) == 1
        assert markers[0][0] == 'link'
        assert markers[0][2] == 'docs'
        assert markers[0][3] == 'https://example.com'

    def test_multiple_markers_sorted_by_position(self):
        markers = _extract_inline_markers('**bold** and `code`')
        assert len(markers) == 2
        assert markers[0][0] == 'bold'
        assert markers[1][0] == 'code'

    def test_code_inside_bold_not_double_counted(self):
        """bold 내부의 backtick은 code로만 감지된다."""
        markers = _extract_inline_markers('use `code` here')
        code_markers = [m for m in markers if m[0] == 'code']
        assert len(code_markers) == 1


class TestHasInlineFormatChange:
    """has_inline_format_change()의 inline 변경 감지를 테스트한다."""

    def test_no_change_plain_text(self):
        assert has_inline_format_change('hello world', 'hello earth') is False

    def test_code_added(self):
        assert has_inline_format_change(
            'use https://example.com/ URL',
            'use `https://example.com/` URL',
        ) is True

    def test_code_removed(self):
        assert has_inline_format_change(
            'use `kubectl` command',
            'use kubectl command',
        ) is True

    def test_code_content_changed(self):
        assert has_inline_format_change(
            'use `old_cmd` here',
            'use `new_cmd` here',
        ) is True

    def test_bold_added(self):
        assert has_inline_format_change(
            'important note',
            '**important** note',
        ) is True

    def test_link_changed(self):
        assert has_inline_format_change(
            'see [docs](https://old.com)',
            'see [docs](https://new.com)',
        ) is True

    def test_same_markers_no_change(self):
        assert has_inline_format_change(
            '**bold** and `code`',
            '**bold** and `code`',
        ) is False

    def test_text_only_change_with_existing_markers(self):
        """마커 외부의 텍스트만 변경 → inline 변경 아님."""
        assert has_inline_format_change(
            '앞문장 `code` 뒷문장',
            '변경된 앞문장 `code` 변경된 뒷문장',
        ) is False
