# Convert 파이프라인 코드 리뷰

`architecture-convert-pipeline.md`에서 파악한 코드 구조를 기반으로,
개선이 필요한 부분을 비판적으로 분석한 결과이다.

---

## Critical

### 1. 전역 가변 상태 (context.py L62-72)

```python
INPUT_FILE_PATH = ""
OUTPUT_FILE_PATH = ""
LANGUAGE = 'en'
PAGES_BY_TITLE: PagesDict = {}
PAGES_BY_ID: PagesDict = {}
GLOBAL_PAGE_V1: Optional[PageV1] = None
GLOBAL_ATTACHMENTS: List = []
GLOBAL_LINK_MAPPING: Dict[str, str] = {}
```

**문제**: 변환 컨텍스트가 모듈 수준 전역 변수로 관리된다.

- 병렬 처리가 구조적으로 불가능하다. 현재는 `convert_all.py`가 subprocess로 호출하므로 프로세스 격리가 되지만, in-process 병렬화를 시도하면 즉시 데이터 오염이 발생한다.
- 모든 파서 클래스(`SingleLineParser`, `MultiLineParser` 등)가 `import converter.context as ctx`로 전역 상태에 직접 접근한다. 의존성이 암묵적이어서 단위 테스트가 사실상 불가능하다.
- `load_pages_yaml()`이 딕셔너리를 누적(append)만 하고 초기화하지 않으므로, 같은 프로세스에서 두 번 호출하면 이전 데이터가 남는다.

**개선 방향**: 변환 컨텍스트를 데이터클래스로 묶어 `ConvertContext` 인스턴스를 만들고, 각 파서 클래스에 생성자 인자로 주입한다.

### 2. 안전하지 않은 언어 감지 (cli.py L148-158)

```python
detected_language = 'en'
for part in path_parts:
    if len(part) == 2 and part.isalpha():
        if part in ['ko', 'ja', 'en']:
            detected_language = part
            break
```

**문제**: 출력 경로의 아무 2글자 디렉토리와 매칭된다.

- `target/ko/...`에서 `ko`를 찾으려는 의도인데, 경로에 `db`나 `qa` 같은 2글자 디렉토리가 먼저 나오면 매칭 실패한다.
- 감지 실패 시 `en`으로 조용히 폴백하므로, 한국어 문서에 영어 날짜 포맷이 적용될 수 있다.

**개선 방향**: `--language` CLI 인자를 추가하거나, `convert_all.py`가 출력 디렉토리 기반으로 언어를 명시적으로 전달한다.

### 3. sidecar mapping 실패 무시 (cli.py L201-212)

```python
try:
    generate_sidecar_mapping(...)
except Exception as e:
    logging.warning(f"Sidecar mapping 생성 실패 (변환은 성공): {e}")
```

**문제**: 모든 예외를 삼킨다.

- mapping.yaml이 없는 MDX 파일은 역동기화(reverse sync)가 불가능하다.
- 디스크 부족, 권한 오류 같은 시스템 문제도 warning으로 묻힌다.
- 사용자는 변환 성공으로 알지만, 실제로는 round-trip 데이터가 누락된 상태이다.

**개선 방향**: exit code를 분리한다 (변환 성공 + mapping 실패 = 별도 exit code). 또는 `--strict` 모드에서는 mapping 실패도 에러로 처리한다.

---

## High

### 4. load_pages_yaml()의 혼란스러운 API (context.py L179-227)

```python
def load_pages_yaml(yaml_path, pages_by_title, pages_by_id):
    pages_dict: PagesDict = {}
    # ... pages_by_title과 pages_by_id를 직접 변이시킴 ...
    return pages_dict  # 항상 빈 딕셔너리 반환
```

**문제**:

- 인자로 받은 딕셔너리를 side-effect로 변이시키면서, 반환값은 사용하지 않는 빈 딕셔너리이다.
- 파일을 읽지 못했을 때 예외를 던지지 않고 빈 딕셔너리를 반환한다. 호출자(cli.py L177)는 로드 성공 여부를 확인하지 않는다.
- 중복 `title_orig`이 발견되면 warning만 남기고 해당 페이지를 건너뛴다. 이런 페이지는 내부 링크 해석이 실패하지만 원인을 추적하기 어렵다.

**개선 방향**: 두 딕셔너리를 반환값으로 돌려주고, 실패 시 예외를 던진다.

### 5. 테이블 rowspan/colspan 추적 오류 (core.py L1029-1076)

```python
for row_idx, row in enumerate(rows):
    col_idx = 0
    for tracked_col, (span_left, content) in sorted(rowspan_tracker.items()):
        # sorted()를 매 행마다 호출
        current_row.append(content)
        col_idx += 1
    for cell_idx, cell in enumerate(cells):
        if rowspan > 1:
            rowspan_tracker[col_idx + cell_idx] = (rowspan - 1, cell_content)
```

**문제**:

- `sorted(rowspan_tracker.items())`가 매 행마다 호출된다.
- `col_idx + cell_idx`로 열 위치를 추적하지만, colspan 셀이 있으면 실제 열 위치와 어긋난다. rowspan과 colspan이 동시에 사용된 테이블에서 셀이 어긋나는 버그가 있다.
- rowspan 추적기의 `content` 가 원본 셀 내용이므로, 병합된 셀 전체에 같은 내용이 반복된다 (Markdown 테이블에서는 빈 셀이 더 적절하다).

**개선 방향**: 열 위치를 2D 행렬로 관리하고, colspan과 rowspan을 동시에 추적하는 알고리즘으로 교체한다.

### 6. Confluence URL 하드코딩 (context.py L84-89, L403-408)

```python
def confluence_url():
    return f'https://querypie.atlassian.net/wiki/spaces/QM/pages/{page_id}/'

def resolve_external_link(link_text, space_key, target_title):
    href = f'https://querypie.atlassian.net/wiki/spaces/{space_key}/pages/{page_id}'
```

**문제**: `querypie.atlassian.net`과 space key `QM`이 코드 곳곳에 하드코딩되어 있다. 다른 Confluence 인스턴스나 space에서 재사용할 수 없다.

**개선 방향**: `fetch/config.py`에 이미 `base_url`과 `space_key`가 있으므로, converter에서도 같은 설정을 참조하도록 통합한다.

### 7. 경로 검증 부재 (convert_all.py L125-136)

```python
attachment_dir = os.path.normpath(os.path.join('/', rel_dir, Path(filename).stem))
```

**문제**:

- `os.path.join('/', ...)` 은 절대 경로를 만들려는 의도인데, `os.path.normpath`로 정규화하면 실제 절대 경로가 된다 (예: `/getting-started/installation`).
- `path` 필드에 `..` 이 포함되어 있어도 검증하지 않는다.
- 같은 slug를 가진 두 페이지가 있으면 출력 파일이 덮어써지지만 감지하지 않는다.

**개선 방향**: path traversal 검증을 추가하고, 출력 파일 충돌을 사전에 감지한다.

---

## Medium

### 8. SingleLineParser/MultiLineParser 인스턴스 남용 (core.py 전반)

```python
# core.py L719: 판정만을 위해 인스턴스를 생성하고 바로 버림
elif SingleLineParser(child).applicable:
    child_markdown.append(SingleLineParser(child).as_markdown)
```

**문제**: 같은 노드에 대해 `SingleLineParser`를 두 번 생성한다 — 한 번은 `applicable` 판정용, 한 번은 실제 변환용. `applicable` 프로퍼티가 전체 자손 트리를 재귀 순회하므로, 이 패턴이 테이블 셀마다 반복되면 비용이 누적된다.

**개선 방향**: `applicable` 체크와 변환을 하나의 인스턴스에서 수행한다.

```python
parser = SingleLineParser(child)
if parser.applicable:
    child_markdown.append(parser.as_markdown)
```

### 9. link mapping을 페이지마다 다시 파싱 (context.py L332-376)

```python
def build_link_mapping(page_v1):
    view_html = page_v1.get('body', {}).get('view', {}).get('value', '')
    soup = BeautifulSoup(view_html, 'html.parser')
    for link in soup.find_all('a', {'data-linked-resource-id': True}):
        link_map[text] = page_id
```

**문제**: 페이지마다 `body.view` HTML을 BeautifulSoup으로 파싱한다. 이 HTML은 수십~수백 KB일 수 있고, 500 페이지 배치 변환에서 무시 못 할 비용이 된다. 다만 현재는 subprocess로 호출되므로 캐싱이 구조적으로 어렵다.

**개선 방향**: in-process 변환으로 전환하면 캐싱이 가능해진다. 또는 fetch 단계에서 link mapping을 미리 추출하여 별도 YAML로 저장한다.

### 10. 정규표현식 미리 컴파일 안 됨 (context.py, cli.py)

`backtick_curly_braces()` (L432)와 `split_into_sentences()` (L481)에서 정규표현식 패턴이 매 호출마다 문자열로 전달된다.

```python
def backtick_curly_braces(text):
    pattern = r'(\{\{?[\w\s\-\_\.\|\:\u2026]{1,60}\}\}?)'
    return re.sub(pattern, r'`\1`', text)
```

**개선 방향**: 모듈 수준에서 `re.compile()`로 한 번만 컴파일한다.

### 11. Attachment 중복 및 누락 (core.py L1408-1422)

```python
ac_image_nodes = self.soup.find_all('ac:image')
for ac_image in ac_image_nodes:
    attachment_nodes = ac_image.find_all('ri:attachment')
```

**문제**:

- `<ac:image>` 안의 `<ri:attachment>`만 수집한다. `<ac:structured-macro name="view-file">` 안의 첨부파일은 포함되지 않는다.
- 같은 파일이 여러 번 참조되면 Attachment 인스턴스가 중복 생성되고, `copy_to_destination()`도 중복 실행된다 (동일 파일 비교 로직이 있어 실제 복사는 1회이지만 비효율적이다).

### 12. 디버그 코드 잔재 (core.py 전반)

```python
self._debug_tags = {
    # 'a', 'ac:link', 'ri:page', 'ac:link-body',
}
self._debug_markdown = False
```

코어 파서 클래스에 주석 처리된 디버그 태그와 `_debug_markdown` 플래그가 산재해 있다. `append_empty_line_unless_first_child()`는 디버그 모드에서만 사용되는 분기가 6줄이나 된다 (L614-632).

**개선 방향**: 구조적 로깅(`logging.debug`)으로 통합하고 디버그 플래그를 제거한다.

---

## Low

### 13. subprocess 기반 배치 변환의 오버헤드 (convert_all.py L144-153)

각 페이지마다 Python 인터프리터를 새로 기동한다. 500 페이지 변환 시 500번의 프로세스 생성, pages.yaml 500번 로드, BeautifulSoup 500번 import가 발생한다.

**개선 방향**: converter를 라이브러리로 호출하되, 전역 상태 문제(#1)를 먼저 해결해야 한다.

### 14. 에러 메시지 일관성 부족

- `core.py`의 warning: `f"SingleLineParser: Unexpected {print_node_with_properties(node)} from {ancestors(node)} in {ctx.INPUT_FILE_PATH}"`
- `context.py`의 warning: `f"Target title '{title}' not found in pages dictionary"`
- `cli.py`의 error: traceback 수동 추출 (L220-228)

포맷이 제각각이어서 로그 파싱이나 에러 집계가 어렵다.

### 15. 헤딩 레벨 자동 조정의 암묵적 규칙 (core.py L186-188)

```python
original_level = int(node.name[1])
adjusted_level = min(original_level + 1, 6)
```

Confluence의 h1을 h2로, h2를 h3로 자동 조정한다. MDX 파일의 `# title`이 h1을 차지하기 때문인데, 이 이유가 코드에 주석으로 설명되어 있지 않다.

---

### 16. 네임스페이스 접두사 제거가 텍스트를 손상시킴 (cli.py L171-173) — **해결됨**

```python
html_content = re.sub(r'\sac:', ' ', html_content)
html_content = re.sub(r'\sri:', ' ', html_content)
```

**문제**: BeautifulSoup 파싱 전에 정규식으로 XHTML 전체 문자열에서 `ac:`, `ri:` 접두사를 제거한다. 속성명뿐 아니라 텍스트 본문의 `ac:`, `ri:` 문자열까지 삭제하는 부작용이 있다.

**해결**: 정규식 기반 전처리를 제거하고, `ConfluenceToMarkdown.__init__()`에서 BeautifulSoup 파싱 후 DOM을 순회하며 속성명에서만 접두사를 제거하는 `_strip_namespace_prefixes()` 메서드를 도입했다. 태그명과 텍스트 내용은 변경하지 않는다.

---

## 유지할 좋은 패턴

- **파서 클래스 분리**: `SingleLineParser`(인라인)와 `MultiLineParser`(블록)의 역할 분담이 명확하다.
- **테이블 변환 이중 전략**: `TableToNativeMarkdown` → `TableToHtmlTable` 폴백 구조가 실용적이다.
- **Attachment 폴백**: 첨부파일이 없어도 `[filename]()`으로 폴백하여 변환 자체는 실패하지 않는다.
- **TypedDict 사용**: `PageV1`, `PageInfo`로 데이터 구조를 명시한다.
- **subprocess 격리**: 전역 상태 문제에도 불구하고, subprocess 호출이 프로세스 격리를 제공하여 실제로는 데이터 오염이 방지되고 있다.

---

## 개선 우선순위

| 우선순위 | 이슈 | 난이도 | 비고 |
|----------|------|--------|------|
| **P0** | #1 전역 상태 → ConvertContext 도입 | 높음 | 다른 개선의 전제조건 |
| **P0** | #2 언어 감지 → 명시적 전달 | 낮음 | |
| **P0** | #3 sidecar mapping 실패 처리 | 낮음 | |
| **P1** | #4 load_pages_yaml API 정리 | 중간 | |
| **P1** | #5 테이블 rowspan/colspan 수정 | 중간 | |
| **P1** | #7 경로 검증 추가 | 낮음 | |
| **P1** | #8 파서 인스턴스 재사용 | 낮음 | |
| **P2** | #6 URL 하드코딩 제거 | 낮음 | |
| **P2** | #13 subprocess → in-process | 높음 | #1 선행 필요 |
| **P3** | #9, #10, #11, #12 | 낮음 | |
