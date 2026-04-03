import pytest
from bs4 import BeautifulSoup
from reverse_sync.xhtml_patcher import patch_xhtml


def test_simple_text_replacement():
    xhtml = '<p>접근 제어를 설정합니다.</p>'
    patches = [
        {
            'xhtml_xpath': 'p[1]',
            'old_plain_text': '접근 제어를 설정합니다.',
            'new_plain_text': '접근 통제를 설정합니다.',
        }
    ]
    result = patch_xhtml(xhtml, patches)
    assert '접근 통제를 설정합니다.' in result
    assert '접근 제어' not in result


def test_preserve_inline_formatting():
    xhtml = '<p><strong>접근 제어</strong>를 설정합니다.</p>'
    patches = [
        {
            'xhtml_xpath': 'p[1]',
            'old_plain_text': '접근 제어를 설정합니다.',
            'new_plain_text': '접근 통제를 설정합니다.',
        }
    ]
    result = patch_xhtml(xhtml, patches)
    assert '<strong>접근 통제</strong>' in result
    assert '를 설정합니다.' in result


def test_heading_text_replacement():
    xhtml = '<h2>시스템 아키텍쳐</h2>'
    patches = [
        {
            'xhtml_xpath': 'h2[1]',
            'old_plain_text': '시스템 아키텍쳐',
            'new_plain_text': '시스템 아키텍처',
        }
    ]
    result = patch_xhtml(xhtml, patches)
    assert '<h2>시스템 아키텍처</h2>' in result


def test_no_change_when_text_not_found():
    xhtml = '<p>Original text.</p>'
    patches = [
        {
            'xhtml_xpath': 'p[1]',
            'old_plain_text': 'Not in document.',
            'new_plain_text': 'Replaced.',
        }
    ]
    result = patch_xhtml(xhtml, patches)
    assert result == xhtml  # 변경 없음


def test_compound_xpath_patches_callout_child():
    """복합 xpath로 callout 매크로 내부 자식 요소를 패치한다."""
    xhtml = (
        '<ac:structured-macro ac:name="info">'
        '<ac:rich-text-body>'
        '<p>Original text.</p>'
        '<p>Second para.</p>'
        '</ac:rich-text-body>'
        '</ac:structured-macro>'
    )
    patches = [
        {
            'xhtml_xpath': 'macro-info[1]/p[1]',
            'old_plain_text': 'Original text.',
            'new_plain_text': 'Updated text.',
        }
    ]
    result = patch_xhtml(xhtml, patches)
    assert 'Updated text.' in result
    assert 'Second para.' in result  # 다른 자식은 변경 없음


def test_compound_xpath_inner_html_replacement():
    """복합 xpath로 callout 매크로 자식의 innerHTML을 교체한다."""
    xhtml = (
        '<ac:structured-macro ac:name="note">'
        '<ac:rich-text-body>'
        '<p>Old content.</p>'
        '</ac:rich-text-body>'
        '</ac:structured-macro>'
    )
    patches = [
        {
            'xhtml_xpath': 'macro-note[1]/p[1]',
            'old_plain_text': 'Old content.',
            'new_inner_xhtml': '<strong>New</strong> content.',
        }
    ]
    result = patch_xhtml(xhtml, patches)
    assert '<strong>New</strong> content.' in result


def test_compound_xpath_nonexistent_parent():
    """존재하지 않는 부모 매크로의 복합 xpath는 무시된다."""
    xhtml = '<p>Simple paragraph.</p>'
    patches = [
        {
            'xhtml_xpath': 'macro-info[1]/p[1]',
            'old_plain_text': 'Simple paragraph.',
            'new_plain_text': 'Changed.',
        }
    ]
    result = patch_xhtml(xhtml, patches)
    assert result == xhtml  # 변경 없음


def test_compound_xpath_adf_extension():
    """ac:adf-extension 내부 자식 요소를 복합 xpath로 패치한다."""
    xhtml = (
        '<ac:adf-extension>'
        '<ac:adf-node type="panel">'
        '<ac:adf-attribute key="panel-type">note</ac:adf-attribute>'
        '<ac:adf-content>'
        '<p>Original text.</p>'
        '<p>Second para.</p>'
        '</ac:adf-content>'
        '</ac:adf-node>'
        '<ac:adf-fallback><div><p>Original text.</p></div></ac:adf-fallback>'
        '</ac:adf-extension>'
    )
    patches = [
        {
            'xhtml_xpath': 'ac:adf-extension[1]/p[1]',
            'old_plain_text': 'Original text.',
            'new_plain_text': 'Updated text.',
        }
    ]
    result = patch_xhtml(xhtml, patches)
    assert 'Updated text.' in result
    assert 'Second para.' in result


# --- Phase 2: replace_fragment / delete / insert 테스트 ---


class TestReplaceFragmentPatch:
    def test_replace_simple_paragraph(self):
        xhtml = '<p>Old text</p><p>Keep</p>'
        patches = [{
            'action': 'replace_fragment',
            'xhtml_xpath': 'p[1]',
            'new_element_xhtml': '<p><strong>New</strong> text</p>',
        }]
        result = patch_xhtml(xhtml, patches)
        assert '<p><strong>New</strong> text</p>' in result
        assert '<p>Keep</p>' in result
        assert 'Old text' not in result

    def test_replace_code_macro_restores_cdata(self):
        xhtml = '<ac:structured-macro ac:name="code"><ac:plain-text-body><![CDATA[old]]></ac:plain-text-body></ac:structured-macro>'
        patches = [{
            'action': 'replace_fragment',
            'xhtml_xpath': 'ac:structured-macro[1]',
            'new_element_xhtml': (
                '<ac:structured-macro ac:name="code">'
                '<ac:plain-text-body>SELECT * FROM test;</ac:plain-text-body>'
                '</ac:structured-macro>'
            ),
        }]
        result = patch_xhtml(xhtml, patches)
        assert '<![CDATA[SELECT * FROM test;]]>' in result

    def test_replace_fragment_preserves_inserted_siblings(self):
        xhtml = '<h1>Title</h1><p>Old text</p>'
        patches = [
            {
                'action': 'insert',
                'after_xpath': 'h1[1]',
                'new_element_xhtml': '<p>Inserted</p>',
            },
            {
                'action': 'replace_fragment',
                'xhtml_xpath': 'h1[1]',
                'new_element_xhtml': '<h1>Renamed</h1>',
            },
        ]
        result = patch_xhtml(xhtml, patches)
        assert '<h1>Renamed</h1><p>Inserted</p><p>Old text</p>' in result


class TestDeletePatch:
    def test_delete_paragraph(self):
        xhtml = '<h1>Title</h1><p>Para one</p><p>Para two</p>'
        patches = [{'action': 'delete', 'xhtml_xpath': 'p[1]'}]
        result = patch_xhtml(xhtml, patches)
        assert '<p>Para one</p>' not in result
        assert '<p>Para two</p>' in result
        assert '<h1>Title</h1>' in result

    def test_delete_heading(self):
        xhtml = '<h1>Title</h1><h2>Sub</h2><p>Text</p>'
        patches = [{'action': 'delete', 'xhtml_xpath': 'h2[1]'}]
        result = patch_xhtml(xhtml, patches)
        assert '<h2>Sub</h2>' not in result
        assert '<h1>Title</h1>' in result

    def test_delete_multiple_preserves_order(self):
        xhtml = '<p>A</p><p>B</p><p>C</p>'
        patches = [
            {'action': 'delete', 'xhtml_xpath': 'p[1]'},
            {'action': 'delete', 'xhtml_xpath': 'p[3]'},
        ]
        result = patch_xhtml(xhtml, patches)
        assert 'A' not in result
        assert '<p>B</p>' in result
        assert 'C' not in result

    def test_delete_nonexistent_xpath_skipped(self):
        xhtml = '<p>Only</p>'
        patches = [{'action': 'delete', 'xhtml_xpath': 'p[99]'}]
        result = patch_xhtml(xhtml, patches)
        assert '<p>Only</p>' in result


class TestInsertPatch:
    def test_insert_after_element(self):
        xhtml = '<h1>Title</h1><p>Existing</p>'
        patches = [{'action': 'insert', 'after_xpath': 'h1[1]',
                     'new_element_xhtml': '<p>New para</p>'}]
        result = patch_xhtml(xhtml, patches)
        assert '<p>New para</p>' in result
        h1_pos = result.index('<h1>')
        new_pos = result.index('New para')
        exist_pos = result.index('Existing')
        assert h1_pos < new_pos < exist_pos

    def test_insert_at_beginning(self):
        xhtml = '<h1>Title</h1><p>Text</p>'
        patches = [{'action': 'insert', 'after_xpath': None,
                     'new_element_xhtml': '<p>First</p>'}]
        result = patch_xhtml(xhtml, patches)
        assert '<p>First</p>' in result
        first_pos = result.index('First')
        title_pos = result.index('Title')
        assert first_pos < title_pos

    def test_insert_at_end(self):
        xhtml = '<h1>Title</h1><p>Last</p>'
        patches = [{'action': 'insert', 'after_xpath': 'p[1]',
                     'new_element_xhtml': '<p>After last</p>'}]
        result = patch_xhtml(xhtml, patches)
        assert '<p>After last</p>' in result
        last_pos = result.index('Last')
        after_pos = result.index('After last')
        assert last_pos < after_pos

    def test_insert_nonexistent_anchor_skipped(self):
        xhtml = '<p>Only</p>'
        patches = [{'action': 'insert', 'after_xpath': 'h1[99]',
                     'new_element_xhtml': '<p>Ghost</p>'}]
        result = patch_xhtml(xhtml, patches)
        assert 'Ghost' not in result


class TestPatchOrdering:
    def test_delete_before_insert_before_modify(self):
        xhtml = '<p>Delete me</p><p>Modify me</p><p>Keep</p>'
        patches = [
            {'action': 'delete', 'xhtml_xpath': 'p[1]'},
            {'action': 'insert', 'after_xpath': 'p[2]',
             'new_element_xhtml': '<p>Inserted</p>'},
            {'action': 'modify', 'xhtml_xpath': 'p[2]',
             'old_plain_text': 'Modify me', 'new_plain_text': 'Modified'},
        ]
        result = patch_xhtml(xhtml, patches)
        assert 'Delete me' not in result
        assert 'Inserted' in result
        assert 'Modified' in result

    def test_legacy_patch_without_action_treated_as_modify(self):
        xhtml = '<p>Old text</p>'
        patches = [{'xhtml_xpath': 'p[1]',
                     'old_plain_text': 'Old text',
                     'new_plain_text': 'New text'}]
        result = patch_xhtml(xhtml, patches)
        assert 'New text' in result


def test_remove_space_before_korean_particle_after_strong():
    """<strong> 뒤 조사 앞 공백 제거를 올바르게 패치한다.

    XHTML: <h3>... <strong>AGENT_SECRET</strong> 를 변경해도 괜찮은가요?</h3>
    교정: 'AGENT_SECRET 를' → 'AGENT_SECRET를' (공백 제거)

    old_plain_text는 xhtml_plain_text(element.get_text())에서 오므로 double-space를 포함.
    <strong> 다음 text node의 leading whitespace가 diff에서 삭제된 경우,
    xhtml_patcher가 해당 공백도 제거해야 한다.
    """
    xhtml = '<h3>Q: 운영 도중  <strong>AGENT_SECRET</strong> 를 변경해도 괜찮은가요?</h3>'
    patches = [
        {
            'xhtml_xpath': 'h3[1]',
            # old_plain_text는 element.get_text()에서 오므로 XHTML 그대로의 공백 포함
            'old_plain_text': 'Q: 운영 도중  AGENT_SECRET 를 변경해도 괜찮은가요?',
            'new_plain_text': 'Q: 운영 도중  AGENT_SECRET를 변경해도 괜찮은가요?',
        }
    ]
    result = patch_xhtml(xhtml, patches)
    assert '<strong>AGENT_SECRET</strong>를 변경해도' in result
    assert '<strong>AGENT_SECRET</strong> 를 변경해도' not in result


def test_insert_space_at_inline_element_boundary_not_duplicated():
    """인라인 요소 경계에 공백을 삽입할 때 양쪽 text node에 중복 삽입되지 않아야 한다.

    재현 시나리오:
      XHTML:  <p><ac:link ...><ac:link-body>설치 후 초기 설정</ac:link-body></ac:link>문서를 참조하여</p>
      교정:   '설치 후 초기 설정문서를 참조하여' → '설치 후 초기 설정 문서를 참조해'
              (link text와 후속 텍스트 사이에 공백 삽입 + 텍스트 변경)

    기대: 공백이 </ac:link> 뒤 text node에만 삽입됨.
    버그:  _map_text_range의 insert 조건 'start <= i1 <= end'가 경계 위치에서
          양쪽 node 모두에 매칭되어 link-body 안에 trailing space가 생김.
    """
    xhtml = (
        '<ul><li><p>'
        '<ac:link ac:card-appearance="inline">'
        '<ri:page ri:content-title="설치 후 초기 설정" />'
        '<ac:link-body>설치 후 초기 설정</ac:link-body>'
        '</ac:link>'
        '문서를 참조하여 공통 설정, 제품별 설정을 진행합니다.'
        '</p></li></ul>'
    )
    patches = [
        {
            'xhtml_xpath': 'ul[1]',
            'old_plain_text': '설치 후 초기 설정문서를 참조하여 공통 설정, 제품별 설정을 진행합니다.',
            'new_plain_text': '설치 후 초기 설정 문서를 참조해 공통 설정과 제품별 설정을 수행합니다.',
        }
    ]
    result = patch_xhtml(xhtml, patches)

    # link-body 내부에 trailing space가 들어가면 안 됨
    assert '<ac:link-body>설치 후 초기 설정</ac:link-body>' in result, (
        f'link-body에 trailing space가 생김: {result}'
    )
    # 공백은 </ac:link> 뒤 text node에만 있어야 함
    assert '</ac:link> 문서를 참조해' in result, (
        f'</ac:link> 뒤에 공백이 없거나 다른 위치에 삽입됨: {result}'
    )


def test_flat_list_append_text_stays_in_same_item():
    """flat list에서 항목 끝에 텍스트를 추가할 때 다음 항목으로 넘치지 않아야 한다.

    재현 시나리오:
      XHTML: <ul><li><p>이모지 깨지는 이슈</p></li><li><p>이름 변경</p></li></ul>
      교정: '이모지 깨지는 이슈' → '이모지가 깨지는 이슈 해결'

    기대: '해결'이 첫 번째 <li> 안에 남음.
    버그: _apply_text_changes가 insert를 노드 경계에서 다음 <li>의 text node에 할당하여
          '해결이름 변경'이 됨.
    """
    xhtml = (
        '<ul>'
        '<li><p>[MongoDB] 데이터 조회 시 이모지 깨지는 이슈</p></li>'
        '<li><p>[Privilege Type] Default Privilege Type 이름 변경</p></li>'
        '</ul>'
    )
    patches = [
        {
            'xhtml_xpath': 'ul[1]',
            'old_plain_text': (
                '[MongoDB] 데이터 조회 시 이모지 깨지는 이슈'
                '[Privilege Type] Default Privilege Type 이름 변경'
            ),
            'new_plain_text': (
                '[MongoDB] 데이터 조회 시 이모지가 깨지는 이슈 해결'
                '[Privilege Type] Default Privilege Type 이름 변경'
            ),
        }
    ]
    result = patch_xhtml(xhtml, patches)

    # '해결'이 첫 번째 항목에 남아야 함
    assert '이슈 해결</p></li>' in result, (
        f"'해결'이 첫 번째 <li> 안에 없음: {result}"
    )
    # '해결'이 두 번째 항목 앞에 붙으면 안 됨
    assert '해결[Privilege' not in result, (
        f"'해결'이 다음 항목으로 넘침: {result}"
    )


def test_flat_list_append_text_multiple_items():
    """여러 항목에서 동시에 텍스트를 추가해도 올바른 항목에 남아야 한다."""
    xhtml = (
        '<ul>'
        '<li><p>item A text</p></li>'
        '<li><p>item B text</p></li>'
        '<li><p>item C text</p></li>'
        '</ul>'
    )
    patches = [
        {
            'xhtml_xpath': 'ul[1]',
            'old_plain_text': 'item A textitem B textitem C text',
            'new_plain_text': 'item A text appendeditem B text modifieditem C text',
        }
    ]
    result = patch_xhtml(xhtml, patches)

    assert '<li><p>item A text appended</p></li>' in result, (
        f"첫 번째 항목에 ' appended' 누락: {result}"
    )
    assert '<li><p>item B text modified</p></li>' in result, (
        f"두 번째 항목에 ' modified' 누락: {result}"
    )


def test_flat_list_prepend_bracket_stays_in_correct_item():
    """리스트 항목 앞에 '[' 삽입 시 해당 항목에 남아야 한다 (이전 항목으로 이동하면 안 됨).

    재현 시나리오:
      old: "DynamoDB 데이터 조회 관련 이슈 개선Authentication Type 변경 시"
      new: "DynamoDB 데이터 조회 관련 이슈 개선[Authentication] Type 변경 시"

    기대: '[' 가 두 번째 <li>에 삽입됨.
    회귀 버그: block boundary fix가 '[' 를 이전 <li>에 잘못 할당.
    """
    xhtml = (
        '<ul>'
        '<li><p>DynamoDB 데이터 조회 관련 이슈 개선</p></li>'
        '<li><p>Authentication Type 변경 시 오류 메시지 개선</p></li>'
        '</ul>'
    )
    patches = [
        {
            'xhtml_xpath': 'ul[1]',
            'old_plain_text': (
                'DynamoDB 데이터 조회 관련 이슈 개선'
                'Authentication Type 변경 시 오류 메시지 개선'
            ),
            'new_plain_text': (
                'DynamoDB 데이터 조회 관련 이슈 개선'
                '[Authentication] Type 변경 시 오류 메시지 개선'
            ),
        }
    ]
    result = patch_xhtml(xhtml, patches)

    # DynamoDB 항목은 변경 없이 그대로
    assert '<li><p>DynamoDB 데이터 조회 관련 이슈 개선</p></li>' in result, (
        f"DynamoDB 항목이 변경됨: {result}"
    )
    # '[' 가 두 번째 항목에 삽입됨
    assert '<li><p>[Authentication] Type 변경 시 오류 메시지 개선</p></li>' in result, (
        f"Authentication 항목에 bracket이 없음: {result}"
    )


def test_list_patch_with_emoticon_uses_mapping_plain_text():
    """리스트에 ac:emoticon이 있어도 mapping plain_text(old_plain_text) 기준으로 패치해야 한다.

    실제 실패 사례(요약):
    - request-audit 계열 문서의 list 블록에서 old_plain_text는 element.get_text() 기반
    - patch 적용 시 비교를 emoticon fallback(:check_mark:) 포함 텍스트로 하면 불일치로 skip
    - 결과적으로 '검색이 가능합니다' → '검색할 수 있습니다' 변경이 적용되지 않음
    """
    xhtml = (
        '<ol>'
        '<li><p>결과 '
        '<ac:emoticon ac:emoji-fallback=":check_mark:" ac:name="tick"></ac:emoticon>'
        ' Success</p></li>'
        '<li><p>테이블 좌측 상단의 검색란을 통해 이하의 조건으로 검색이 가능합니다.</p></li>'
        '</ol>'
    )
    patches = [
        {
            'xhtml_xpath': 'ol[1]',
            # mapping_recorder(list)는 get_text() 기반 plain을 기록한다.
            'old_plain_text': '결과  Success테이블 좌측 상단의 검색란을 통해 이하의 조건으로 검색이 가능합니다.',
            'new_plain_text': '결과  Success테이블 좌측 상단의 검색란을 통해 이하의 조건으로 검색할 수 있습니다.',
        }
    ]

    result = patch_xhtml(xhtml, patches)
    assert '검색할 수 있습니다.' in result, f'리스트 텍스트 변경이 적용되지 않음: {result}'
    assert '검색이 가능합니다.' not in result, f'기존 문구가 남아 있음: {result}'


class TestOlStartPatch:
    """<ol start="N"> 속성 변경 패치 테스트."""

    def test_set_start_attribute_via_inner_xhtml(self):
        """new_inner_xhtml 경로에서 ol_start로 start 속성을 설정한다."""
        xhtml = '<ol><li><p>first</p></li><li><p>second</p></li></ol>'
        patches = [{
            'xhtml_xpath': 'ol[1]',
            'old_plain_text': 'firstsecond',
            'new_inner_xhtml': '<li><p>updated first</p></li><li><p>second</p></li>',
            'ol_start': 3,
        }]
        result = patch_xhtml(xhtml, patches)
        soup = BeautifulSoup(result, 'html.parser')
        ol = soup.find('ol')
        assert ol['start'] == '3'
        assert 'updated first' in result

    def test_remove_start_attribute_when_ol_start_is_one(self):
        """ol_start=1이면 기존 start 속성을 제거한다."""
        xhtml = '<ol start="3"><li><p>first</p></li></ol>'
        patches = [{
            'xhtml_xpath': 'ol[1]',
            'old_plain_text': 'first',
            'new_inner_xhtml': '<li><p>first item</p></li>',
            'ol_start': 1,
        }]
        result = patch_xhtml(xhtml, patches)
        soup = BeautifulSoup(result, 'html.parser')
        ol = soup.find('ol')
        assert ol.get('start') is None

    def test_set_start_attribute_via_text_transfer(self):
        """텍스트 전이 경로에서도 ol_start가 start 속성으로 적용된다."""
        xhtml = '<ol><li>first item</li></ol>'
        patches = [{
            'xhtml_xpath': 'ol[1]',
            'old_plain_text': 'first item',
            'new_plain_text': 'updated item',
            'ol_start': 5,
        }]
        result = patch_xhtml(xhtml, patches)
        soup = BeautifulSoup(result, 'html.parser')
        ol = soup.find('ol')
        assert ol['start'] == '5'
        assert 'updated' in result


class TestEmoticonReplacement:
    """<ac:emoticon> 커스텀 이모지가 텍스트로 교체되는 경우 테스트."""

    def test_emoticon_replaced_with_text(self):
        """커스텀 이모지 shortcode가 plain text로 교체될 때 <ac:emoticon> DOM 요소가 제거된다."""
        xhtml = (
            '<p>전송 토글 버튼을 '
            '<ac:emoticon ac:emoji-fallback=":토글off:" '
            'ac:emoji-id="c6944598" ac:emoji-shortname=":토글off:" '
            'ac:name="blue-star"></ac:emoticon>'
            ' 로 변경한 후 삭제해 주시기 바랍니다.</p>'
        )
        patches = [{
            'xhtml_xpath': 'p[1]',
            'old_plain_text': '전송 토글 버튼을 :토글off: 로 변경한 후 삭제해 주시기 바랍니다.',
            'new_plain_text': '전송 토글 버튼을 Off로 변경한 후 삭제해 주시기 바랍니다.',
        }]
        result = patch_xhtml(xhtml, patches)
        assert 'ac:emoticon' not in result
        assert 'Off로 변경한 후' in result

    def test_emoticon_unchanged_when_not_in_diff(self):
        """이모지가 변경 대상이 아니면 <ac:emoticon> 요소가 보존된다."""
        xhtml = (
            '<p>상태: '
            '<ac:emoticon ac:emoji-fallback=":check:" '
            'ac:emoji-shortname=":check:" ac:name="tick"></ac:emoticon>'
            ' 완료</p>'
        )
        patches = [{
            'xhtml_xpath': 'p[1]',
            'old_plain_text': '상태: :check: 완료',
            'new_plain_text': '상태: :check: 완료됨',
        }]
        result = patch_xhtml(xhtml, patches)
        assert 'ac:emoticon' in result
        assert '완료됨' in result

    def test_only_one_of_duplicate_shortcodes_is_replaced(self):
        """동일 shortcode가 여러 번 나와도 교체 대상 위치만 텍스트로 바뀐다."""
        xhtml = (
            '<p>'
            '<ac:emoticon ac:emoji-fallback=":check:" '
            'ac:emoji-shortname=":check:" ac:name="tick"></ac:emoticon>'
            ' A '
            '<ac:emoticon ac:emoji-fallback=":check:" '
            'ac:emoji-shortname=":check:" ac:name="tick"></ac:emoticon>'
            '</p>'
        )
        patches = [{
            'xhtml_xpath': 'p[1]',
            'old_plain_text': ':check: A :check:',
            'new_plain_text': ':check: A 확인',
        }]

        result = patch_xhtml(xhtml, patches)
        soup = BeautifulSoup(result, 'html.parser')

        assert len(soup.find_all('ac:emoticon')) == 1
        assert 'A 확인' in result


class TestGapWhitespaceReduction:
    """텍스트 노드 사이 gap 공백이 축소될 때 leading whitespace 처리 테스트."""

    def test_li_p_leading_space_removed_when_gap_reduced(self):
        """<p> trailing space + 내부 <p> leading space → 2공백 gap 축소 시 leading 제거.

        XHTML 구조: <p>...정의합니다. </p><ul><li><p> Admin ...</p></li></ul>
        old_plain_text에서 gap이 2공백("  "), new에서 1공백(" ")으로 축소될 때
        내부 <p>의 leading space가 제거되어야 한다.
        (FC가 leading space를 보존하면 "* ·Admin" → "*··Admin" 이중 공백이 됨)
        """
        xhtml = (
            '<ol>'
            '<li><p><strong>Allowed Zones</strong> : 정의합니다. </p>'
            '<ul><li><p> Admin 매핑합니다.</p></li></ul>'
            '</li>'
            '</ol>'
        )
        patches = [{
            'xhtml_xpath': 'ol[1]',
            # trailing " " + leading " " = gap 2
            'old_plain_text': 'Allowed Zones : 정의합니다.  Admin 매핑합니다.',
            # gap 2 → 1
            'new_plain_text': 'Allowed Zones : 정의합니다. Admin 매핑합니다.',
        }]
        result = patch_xhtml(xhtml, patches)
        assert '<p>Admin' in result, (
            f"leading space not removed when gap reduced: {result}"
        )

    def test_gap_fully_deleted(self):
        """gap이 완전히 삭제되면 기존 동작대로 leading을 제거한다."""
        xhtml = '<p><strong>IDENTIFIER</strong> 조사</p>'
        patches = [{
            'xhtml_xpath': 'p[1]',
            'old_plain_text': 'IDENTIFIER 조사',
            'new_plain_text': 'IDENTIFIER조사',
        }]
        result = patch_xhtml(xhtml, patches)
        assert 'IDENTIFIER</strong>조사' in result

    def test_gap_not_reduced_preserves_leading(self):
        """gap이 축소되지 않으면 leading whitespace를 보존한다."""
        xhtml = (
            '<ol>'
            '<li><p>텍스트. </p>'
            '<ul><li><p> 내용입니다.</p></li></ul>'
            '</li>'
            '</ol>'
        )
        patches = [{
            'xhtml_xpath': 'ol[1]',
            'old_plain_text': '텍스트.  내용입니다.',
            # gap 크기 동일 (2→2), 텍스트만 변경
            'new_plain_text': '텍스트.  내용변경.',
        }]
        result = patch_xhtml(xhtml, patches)
        # gap이 축소되지 않았으므로 leading space 보존
        assert '<p> 내용변경.' in result, (
            f"leading space should be preserved when gap not reduced: {result}"
        )
