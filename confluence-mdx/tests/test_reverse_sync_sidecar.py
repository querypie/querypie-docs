"""Sidecar 통합 모듈 유닛 테스트.

reverse_sync/sidecar.py의 핵심 기능을 검증한다:
  - Block-level roundtrip sidecar (RoundtripSidecar, build/load/write)
  - mapping.yaml 파일 로드 및 SidecarEntry 생성
  - MDX block index → SidecarEntry 역인덱스 구축
  - xhtml_xpath → BlockMapping 인덱스 구축
  - 2-hop 조회: MDX index → SidecarEntry → BlockMapping
  - XHTML + MDX로부터 mapping.yaml 생성 (generate_sidecar_mapping)
  - 텍스트 매칭 내부 함수들 (_find_text_match, _strip_all_ws)
"""
import pytest
import yaml
from pathlib import Path

from reverse_sync.sidecar import (
    ROUNDTRIP_SCHEMA_VERSION,
    RoundtripSidecar,
    build_sidecar,
    load_sidecar,
    sha256_text,
    write_sidecar,
    SidecarEntry,
    load_sidecar_mapping,
    build_mdx_to_sidecar_index,
    build_xpath_to_mapping,
    find_mapping_by_sidecar,
    generate_sidecar_mapping,
    _find_text_match,
    _strip_all_ws,
)
from reverse_sync.mapping_recorder import BlockMapping


# ── Roundtrip Sidecar (block-level) ──────────────────────────

class TestSha256Text:
    def test_stable(self):
        assert sha256_text("abc") == sha256_text("abc")

    def test_different(self):
        assert sha256_text("abc") != sha256_text("abcd")


class TestBuildSidecar:
    def test_contains_hashes_and_fragments(self):
        xhtml = "<h1>Title</h1><p>Body</p>"
        mdx = "## Title\n\nBody\n"
        sidecar = build_sidecar(xhtml, mdx, page_id="123")
        assert sidecar.schema_version == ROUNDTRIP_SCHEMA_VERSION
        assert sidecar.page_id == "123"
        assert sidecar.reassemble_xhtml() == xhtml
        assert sidecar.mdx_sha256 == sha256_text(mdx)
        assert sidecar.source_xhtml_sha256 == sha256_text(xhtml)
        assert len(sidecar.blocks) == 2


class TestWriteAndLoadSidecar:
    def test_roundtrip(self, tmp_path):
        xhtml = "<h1>T</h1>"
        mdx = "## T\n"
        sidecar = build_sidecar(xhtml, mdx, page_id="case-1")
        path = tmp_path / "expected.roundtrip.json"
        write_sidecar(sidecar, path)

        loaded = load_sidecar(path)
        assert loaded.schema_version == ROUNDTRIP_SCHEMA_VERSION
        assert loaded.page_id == "case-1"
        assert loaded.reassemble_xhtml() == xhtml
        assert loaded.mdx_sha256 == sha256_text(mdx)


# ── SidecarEntry ──────────────────────────────────────────────

class TestSidecarEntry:
    def test_basic_creation(self):
        entry = SidecarEntry(
            xhtml_xpath='p[1]', xhtml_type='paragraph', mdx_blocks=[0, 1])
        assert entry.xhtml_xpath == 'p[1]'
        assert entry.xhtml_type == 'paragraph'
        assert entry.mdx_blocks == [0, 1]

    def test_default_mdx_blocks(self):
        entry = SidecarEntry(xhtml_xpath='h2[1]', xhtml_type='heading')
        assert entry.mdx_blocks == []


# ── load_sidecar_mapping ──────────────────────────────────────

class TestLoadSidecarMapping:
    def test_load_valid_mapping(self, tmp_path):
        mapping_data = {
            'version': 1,
            'source_page_id': '12345',
            'mdx_file': 'page.mdx',
            'mappings': [
                {'xhtml_xpath': 'h2[1]', 'xhtml_type': 'heading', 'mdx_blocks': [2]},
                {'xhtml_xpath': 'p[1]', 'xhtml_type': 'paragraph', 'mdx_blocks': [4, 5]},
                {'xhtml_xpath': 'p[2]', 'xhtml_type': 'paragraph', 'mdx_blocks': []},
            ]
        }
        mapping_file = tmp_path / 'mapping.yaml'
        mapping_file.write_text(yaml.dump(mapping_data, allow_unicode=True))

        entries = load_sidecar_mapping(str(mapping_file))
        assert len(entries) == 3
        assert entries[0].xhtml_xpath == 'h2[1]'
        assert entries[0].xhtml_type == 'heading'
        assert entries[0].mdx_blocks == [2]
        assert entries[1].mdx_blocks == [4, 5]
        assert entries[2].mdx_blocks == []

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError, match='Sidecar mapping not found'):
            load_sidecar_mapping('/nonexistent/mapping.yaml')

    def test_empty_mappings(self, tmp_path):
        mapping_file = tmp_path / 'mapping.yaml'
        mapping_file.write_text(yaml.dump({'version': 1, 'mappings': []}))
        entries = load_sidecar_mapping(str(mapping_file))
        assert entries == []

    def test_empty_yaml_file(self, tmp_path):
        mapping_file = tmp_path / 'mapping.yaml'
        mapping_file.write_text('')
        entries = load_sidecar_mapping(str(mapping_file))
        assert entries == []

    def test_missing_optional_fields(self, tmp_path):
        mapping_data = {
            'version': 1,
            'mappings': [
                {'xhtml_xpath': 'h2[1]'},  # xhtml_type, mdx_blocks 생략
            ]
        }
        mapping_file = tmp_path / 'mapping.yaml'
        mapping_file.write_text(yaml.dump(mapping_data))
        entries = load_sidecar_mapping(str(mapping_file))
        assert entries[0].xhtml_type == ''
        assert entries[0].mdx_blocks == []


# ── build_mdx_to_sidecar_index ────────────────────────────────

class TestBuildMdxToSidecarIndex:
    def test_basic_index(self):
        e1 = SidecarEntry('h2[1]', 'heading', [2])
        e2 = SidecarEntry('p[1]', 'paragraph', [4, 5])
        index = build_mdx_to_sidecar_index([e1, e2])
        assert index[2] is e1
        assert index[4] is e2
        assert index[5] is e2
        assert 0 not in index
        assert 3 not in index

    def test_empty_mdx_blocks(self):
        e = SidecarEntry('p[2]', 'paragraph', [])
        index = build_mdx_to_sidecar_index([e])
        assert len(index) == 0

    def test_multiple_entries_single_blocks(self):
        entries = [
            SidecarEntry('h2[1]', 'heading', [0]),
            SidecarEntry('p[1]', 'paragraph', [2]),
            SidecarEntry('p[2]', 'paragraph', [4]),
        ]
        index = build_mdx_to_sidecar_index(entries)
        assert len(index) == 3
        assert index[0].xhtml_xpath == 'h2[1]'
        assert index[2].xhtml_xpath == 'p[1]'
        assert index[4].xhtml_xpath == 'p[2]'


# ── build_xpath_to_mapping ────────────────────────────────────

def _make_mapping(block_id, xpath, plain_text='', type_='paragraph', children=None):
    return BlockMapping(
        block_id=block_id,
        type=type_,
        xhtml_xpath=xpath,
        xhtml_text='',
        xhtml_plain_text=plain_text,
        xhtml_element_index=0,
        children=children or [],
    )


class TestBuildXpathToMapping:
    def test_basic_index(self):
        m1 = _make_mapping('heading-1', 'h2[1]')
        m2 = _make_mapping('paragraph-1', 'p[1]')
        index = build_xpath_to_mapping([m1, m2])
        assert index['h2[1]'] is m1
        assert index['p[1]'] is m2
        assert 'p[2]' not in index

    def test_empty_mappings(self):
        index = build_xpath_to_mapping([])
        assert len(index) == 0


# ── find_mapping_by_sidecar ───────────────────────────────────

class TestFindMappingBySidecar:
    def setup_method(self):
        self.m1 = _make_mapping('heading-1', 'h2[1]', 'Overview')
        self.m2 = _make_mapping('paragraph-1', 'p[1]', 'Some content')
        self.xpath_index = build_xpath_to_mapping([self.m1, self.m2])

        e1 = SidecarEntry('h2[1]', 'heading', [2])
        e2 = SidecarEntry('p[1]', 'paragraph', [5])
        self.sidecar_index = build_mdx_to_sidecar_index([e1, e2])

    def test_found_via_sidecar(self):
        result = find_mapping_by_sidecar(2, self.sidecar_index, self.xpath_index)
        assert result is self.m1

        result = find_mapping_by_sidecar(5, self.sidecar_index, self.xpath_index)
        assert result is self.m2

    def test_mdx_index_not_in_sidecar(self):
        result = find_mapping_by_sidecar(99, self.sidecar_index, self.xpath_index)
        assert result is None

    def test_xpath_not_in_mapping_index(self):
        """sidecar에는 있지만 xpath_to_mapping에는 없는 경우."""
        e3 = SidecarEntry('p[99]', 'paragraph', [10])
        sidecar_index = build_mdx_to_sidecar_index([e3])
        result = find_mapping_by_sidecar(10, sidecar_index, self.xpath_index)
        assert result is None


# ── _strip_all_ws ─────────────────────────────────────────────

class TestStripAllWs:
    def test_basic(self):
        assert _strip_all_ws('hello world') == 'helloworld'

    def test_tabs_and_newlines(self):
        assert _strip_all_ws('a\tb\nc d') == 'abcd'

    def test_empty(self):
        assert _strip_all_ws('') == ''

    def test_only_whitespace(self):
        assert _strip_all_ws('   \t\n  ') == ''


# ── _find_text_match ──────────────────────────────────────────

class TestFindTextMatch:
    def test_exact_match_at_start(self):
        """1차: collapse_ws 후 완전 일치."""
        indices = [0, 1, 2]
        plains = {0: 'Hello World', 1: 'Foo Bar', 2: 'Baz'}
        result = _find_text_match('Hello World', indices, plains, 0, 5)
        assert result == 0

    def test_exact_match_at_offset(self):
        indices = [0, 1, 2]
        plains = {0: 'AAA', 1: 'BBB', 2: 'CCC'}
        result = _find_text_match('BBB', indices, plains, 0, 5)
        assert result == 1

    def test_whitespace_insensitive_match(self):
        """2차: 공백 무시 완전 일치."""
        indices = [0, 1]
        plains = {0: 'Hello  World', 1: 'Foo'}
        # xhtml_plain 'HelloWorld' vs mdx 'Hello  World' → strip_all_ws 비교
        result = _find_text_match('Hello World', indices, plains, 0, 5)
        # 1차에서 실패하지만 2차 공백무시에서 매칭
        assert result is not None

    def test_prefix_match(self):
        """3차: prefix 포함 매칭."""
        indices = [0]
        long_text = 'A' * 60
        plains = {0: long_text + ' extra'}
        # xhtml_plain의 앞 50자가 mdx에 포함
        result = _find_text_match(long_text, indices, plains, 0, 5)
        assert result is not None

    def test_no_match(self):
        indices = [0, 1]
        plains = {0: 'AAA', 1: 'BBB'}
        result = _find_text_match('CCC', indices, plains, 0, 5)
        assert result is None

    def test_start_ptr_skips_earlier(self):
        """start_ptr 이전의 블록은 검색하지 않는다."""
        indices = [0, 1, 2]
        plains = {0: 'Target', 1: 'Other', 2: 'More'}
        result = _find_text_match('Target', indices, plains, 1, 5)
        assert result is None  # index 0은 검색 범위 밖

    def test_lookahead_limit(self):
        """lookahead 범위를 초과하면 매칭하지 않는다."""
        indices = [0, 1, 2, 3, 4, 5]
        plains = {i: f'block-{i}' for i in range(6)}
        result = _find_text_match('block-5', indices, plains, 0, 3)
        assert result is None  # lookahead=3이므로 index 0,1,2만 검색

    def test_short_text_no_prefix_match(self):
        """10자 미만의 짧은 텍스트는 prefix 매칭을 시도하지 않는다."""
        indices = [0]
        plains = {0: 'AB extra'}
        result = _find_text_match('AB', indices, plains, 0, 5)
        assert result is None


# ── generate_sidecar_mapping ──────────────────────────────────

class TestGenerateSidecarMapping:
    """XHTML + MDX로부터 mapping.yaml을 생성하는 통합 테스트."""

    def test_simple_heading_paragraph(self):
        """heading + paragraph → 각각 MDX 블록에 매핑된다."""
        xhtml = '<h2>Overview</h2><p>This is content.</p>'
        mdx = (
            '---\ntitle: Test\n---\n\n'
            '## Overview\n\n'
            'This is content.\n'
        )
        result = generate_sidecar_mapping(xhtml, mdx, '12345')
        data = yaml.safe_load(result)

        assert data['version'] == 1
        assert data['source_page_id'] == '12345'
        assert len(data['mappings']) >= 2

        # heading과 paragraph 모두 비어있지 않은 mdx_blocks를 가져야 함
        heading_entry = next(
            e for e in data['mappings'] if e['xhtml_type'] == 'heading')
        para_entry = next(
            e for e in data['mappings'] if e['xhtml_type'] == 'paragraph')
        assert len(heading_entry['mdx_blocks']) >= 1
        assert len(para_entry['mdx_blocks']) >= 1

    def test_empty_xhtml_block_gets_empty_mdx_blocks(self):
        """이미지 등 텍스트가 없는 XHTML 블록은 빈 mdx_blocks를 받는다."""
        xhtml = (
            '<h2>Title</h2>'
            '<ac:image><ri:attachment ri:filename="img.png"/></ac:image>'
            '<p>Paragraph content.</p>'
        )
        mdx = (
            '---\ntitle: Test\n---\n\n'
            '## Title\n\n'
            '![img](/images/img.png)\n\n'
            'Paragraph content.\n'
        )
        result = generate_sidecar_mapping(xhtml, mdx)
        data = yaml.safe_load(result)

        # image 블록은 빈 텍스트이므로 빈 mdx_blocks
        image_entries = [
            e for e in data['mappings'] if e.get('mdx_blocks') == []]
        assert len(image_entries) >= 1

    def test_yaml_format_output(self):
        """생성된 YAML이 올바른 형식인지 확인한다."""
        xhtml = '<p>Hello World.</p>'
        mdx = '---\ntitle: Test\n---\n\nHello World.\n'
        result = generate_sidecar_mapping(xhtml, mdx, 'page-1')

        # YAML 파싱 가능
        data = yaml.safe_load(result)
        assert isinstance(data, dict)
        assert 'mappings' in data
        assert isinstance(data['mappings'], list)

    def test_page_id_in_output(self):
        xhtml = '<p>Content.</p>'
        mdx = '---\ntitle: Test\n---\n\nContent.\n'
        result = generate_sidecar_mapping(xhtml, mdx, 'my-page-42')
        data = yaml.safe_load(result)
        assert data['source_page_id'] == 'my-page-42'

    def test_multiple_paragraphs_sequential_matching(self):
        """여러 paragraph가 순서대로 MDX 블록에 매칭된다."""
        xhtml = '<p>First paragraph.</p><p>Second paragraph.</p><p>Third paragraph.</p>'
        mdx = (
            '---\ntitle: Test\n---\n\n'
            'First paragraph.\n\n'
            'Second paragraph.\n\n'
            'Third paragraph.\n'
        )
        result = generate_sidecar_mapping(xhtml, mdx)
        data = yaml.safe_load(result)

        matched = [e for e in data['mappings'] if e['mdx_blocks']]
        assert len(matched) == 3

        # MDX 블록 인덱스가 순서대로 증가해야 함
        all_indices = [e['mdx_blocks'][0] for e in matched]
        assert all_indices == sorted(all_indices)

    def test_callout_macro_with_children(self):
        """Callout 매크로 (ac:structured-macro) → 컨테이너 + children 매핑."""
        xhtml = (
            '<ac:structured-macro ac:name="info">'
            '<ac:rich-text-body>'
            '<p>Info paragraph 1.</p>'
            '<p>Info paragraph 2.</p>'
            '</ac:rich-text-body>'
            '</ac:structured-macro>'
        )
        mdx = (
            '---\ntitle: Test\n---\n\n'
            ':::info\n\n'
            'Info paragraph 1.\n\n'
            'Info paragraph 2.\n\n'
            ':::\n'
        )
        result = generate_sidecar_mapping(xhtml, mdx)
        data = yaml.safe_load(result)

        # 컨테이너 매핑이 여러 MDX 블록을 포함해야 함
        container_entries = [
            e for e in data['mappings'] if len(e.get('mdx_blocks', [])) > 1
        ]
        assert len(container_entries) >= 1


# ── 실제 테스트 케이스 기반 통합 테스트 ───────────────────────

class TestGenerateSidecarMappingFromTestCases:
    """tests/testcases/에 있는 실제 테스트 데이터로 검증한다."""

    @pytest.fixture
    def testcase_dir(self):
        return Path(__file__).parent / 'testcases'

    def _get_reverse_sync_test_ids(self, testcase_dir):
        """reverse-sync 입력 파일이 있는 테스트 케이스 ID 목록."""
        ids = []
        if not testcase_dir.exists():
            return ids
        for d in sorted(testcase_dir.iterdir()):
            if d.is_dir() and (d / 'original.mdx').exists() and (d / 'page.xhtml').exists():
                ids.append(d.name)
        return ids

    def test_all_reverse_sync_cases_produce_valid_yaml(self, testcase_dir):
        """모든 reverse-sync 테스트 케이스에서 유효한 mapping.yaml을 생성한다."""
        test_ids = self._get_reverse_sync_test_ids(testcase_dir)
        if not test_ids:
            pytest.skip('No reverse-sync test cases found')

        for test_id in test_ids:
            case_dir = testcase_dir / test_id
            xhtml = (case_dir / 'page.xhtml').read_text()
            mdx = (case_dir / 'original.mdx').read_text()

            result = generate_sidecar_mapping(xhtml, mdx, test_id)
            data = yaml.safe_load(result)

            assert data is not None, f'{test_id}: YAML 파싱 실패'
            assert 'mappings' in data, f'{test_id}: mappings 키 누락'
            assert isinstance(data['mappings'], list), f'{test_id}: mappings가 리스트가 아님'

    def test_all_reverse_sync_cases_have_nonempty_mappings(self, testcase_dir):
        """모든 reverse-sync 테스트 케이스에서 최소 1개의 매핑이 MDX 블록을 가진다."""
        test_ids = self._get_reverse_sync_test_ids(testcase_dir)
        if not test_ids:
            pytest.skip('No reverse-sync test cases found')

        for test_id in test_ids:
            case_dir = testcase_dir / test_id
            xhtml = (case_dir / 'page.xhtml').read_text()
            mdx = (case_dir / 'original.mdx').read_text()

            result = generate_sidecar_mapping(xhtml, mdx, test_id)
            data = yaml.safe_load(result)
            matched = [e for e in data['mappings'] if e.get('mdx_blocks')]
            assert len(matched) >= 1, \
                f'{test_id}: MDX 블록에 매핑된 엔트리가 없음 ({len(data["mappings"])}개 매핑 중)'

    def test_mdx_block_indices_are_unique(self, testcase_dir):
        """하나의 MDX 블록 인덱스가 중복 매핑되지 않는다."""
        test_ids = self._get_reverse_sync_test_ids(testcase_dir)
        if not test_ids:
            pytest.skip('No reverse-sync test cases found')

        for test_id in test_ids:
            case_dir = testcase_dir / test_id
            xhtml = (case_dir / 'page.xhtml').read_text()
            mdx = (case_dir / 'original.mdx').read_text()

            result = generate_sidecar_mapping(xhtml, mdx, test_id)
            data = yaml.safe_load(result)

            all_indices = []
            for entry in data['mappings']:
                all_indices.extend(entry.get('mdx_blocks', []))
            assert len(all_indices) == len(set(all_indices)), \
                f'{test_id}: MDX 블록 인덱스 중복 발견: {[i for i in all_indices if all_indices.count(i) > 1]}'

    def test_mdx_block_indices_are_ascending(self, testcase_dir):
        """MDX 블록 인덱스가 매핑 순서대로 증가한다."""
        test_ids = self._get_reverse_sync_test_ids(testcase_dir)
        if not test_ids:
            pytest.skip('No reverse-sync test cases found')

        for test_id in test_ids:
            case_dir = testcase_dir / test_id
            xhtml = (case_dir / 'page.xhtml').read_text()
            mdx = (case_dir / 'original.mdx').read_text()

            result = generate_sidecar_mapping(xhtml, mdx, test_id)
            data = yaml.safe_load(result)

            all_indices = []
            for entry in data['mappings']:
                all_indices.extend(entry.get('mdx_blocks', []))
            assert all_indices == sorted(all_indices), \
                f'{test_id}: MDX 블록 인덱스가 오름차순이 아님'


# ── 2-hop 조회 통합 테스트 ────────────────────────────────────

class TestSidecarTwoHopLookup:
    """sidecar 파일 → 인덱스 구축 → 2-hop 조회 전체 경로 테스트."""

    def test_full_pipeline(self, tmp_path):
        """mapping.yaml 로드 → 인덱스 구축 → find_mapping_by_sidecar 전체 경로."""
        # 1. mapping.yaml 생성
        mapping_data = {
            'version': 1,
            'source_page_id': '12345',
            'mappings': [
                {'xhtml_xpath': 'h2[1]', 'xhtml_type': 'heading', 'mdx_blocks': [2]},
                {'xhtml_xpath': 'p[1]', 'xhtml_type': 'paragraph', 'mdx_blocks': [4]},
                {'xhtml_xpath': 'p[2]', 'xhtml_type': 'paragraph', 'mdx_blocks': [6]},
            ]
        }
        mapping_file = tmp_path / 'mapping.yaml'
        mapping_file.write_text(yaml.dump(mapping_data))

        # 2. sidecar 로드 + 인덱스 구축
        entries = load_sidecar_mapping(str(mapping_file))
        mdx_to_sidecar = build_mdx_to_sidecar_index(entries)

        # 3. BlockMapping 구축 (실제로는 record_mapping()이 생성)
        m1 = _make_mapping('heading-1', 'h2[1]', 'Overview', 'heading')
        m2 = _make_mapping('paragraph-1', 'p[1]', 'First paragraph.')
        m3 = _make_mapping('paragraph-2', 'p[2]', 'Second paragraph.')
        xpath_to_mapping = build_xpath_to_mapping([m1, m2, m3])

        # 4. 2-hop 조회
        assert find_mapping_by_sidecar(2, mdx_to_sidecar, xpath_to_mapping) is m1
        assert find_mapping_by_sidecar(4, mdx_to_sidecar, xpath_to_mapping) is m2
        assert find_mapping_by_sidecar(6, mdx_to_sidecar, xpath_to_mapping) is m3
        assert find_mapping_by_sidecar(99, mdx_to_sidecar, xpath_to_mapping) is None

    def test_container_with_multiple_mdx_blocks(self, tmp_path):
        """컨테이너가 여러 MDX 블록에 매핑된 경우, 모든 MDX 블록이 같은 매핑으로 조회된다."""
        mapping_data = {
            'version': 1,
            'mappings': [
                {
                    'xhtml_xpath': 'ac:structured-macro[1]',
                    'xhtml_type': 'html_block',
                    'mdx_blocks': [3, 5, 7, 9],
                },
            ]
        }
        mapping_file = tmp_path / 'mapping.yaml'
        mapping_file.write_text(yaml.dump(mapping_data))

        entries = load_sidecar_mapping(str(mapping_file))
        mdx_to_sidecar = build_mdx_to_sidecar_index(entries)

        container = _make_mapping(
            'html_block-1', 'ac:structured-macro[1]',
            'Container text', 'html_block',
            children=['paragraph-10', 'paragraph-11'])
        xpath_to_mapping = build_xpath_to_mapping([container])

        # 모든 MDX 블록이 같은 컨테이너를 가리킴
        for idx in [3, 5, 7, 9]:
            result = find_mapping_by_sidecar(idx, mdx_to_sidecar, xpath_to_mapping)
            assert result is container
