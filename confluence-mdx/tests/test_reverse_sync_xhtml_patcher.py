import pytest
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


# --- Phase 2: delete/insert 테스트 ---


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
