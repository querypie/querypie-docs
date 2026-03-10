# Reverse-Sync 테스트 가이드

## 디렉토리 구조

각 테스트케이스는 Confluence 페이지 ID 이름의 디렉토리로 구성됩니다.

```
tests/reverse-sync/
├── pages.yaml          # 페이지 카탈로그 + 테스트케이스 매니페스트
├── README.md           # 이 파일
└── {page_id}/
    ├── page.xhtml      # Confluence 원본 XHTML (소스)
    ├── page.v1.yaml    # Confluence 페이지 메타데이터 (frontmatter/h1 생성용)
    ├── original.mdx    # page.xhtml → forward 변환 결과
    └── improved.mdx    # original.mdx 에 교정을 가한 버전
```

## pages.yaml 의 구조와 역할

`tests/reverse-sync/pages.yaml` 은 list 형식이며 두 가지 역할을 합니다.

### 역할 1: forward converter 페이지 카탈로그

converter 가 `original.mdx` 를 생성할 때 이 파일을 자동으로 로드합니다.

- **cross-page 링크 해소**: `<ac:link>` 요소의 타겟 페이지를 MDX 상대경로로 변환
- **포함 범위**: 테스트케이스 페이지 + 테스트케이스에서 링크되는 대상 페이지

각 항목의 기본 필드 (`var/pages.yaml` 과 동일):

```yaml
- page_id: '543948978'
  title: Company Management
  title_orig: Company Management
  breadcrumbs: [관리자 매뉴얼, General, Company Management]
  breadcrumbs_en: [Administrator Manual, General, Company Management]
  path: [administrator-manual, general, company-management]
```

### 역할 2: 테스트케이스 매니페스트

`failure_type` 필드가 있는 항목이 테스트케이스입니다.
테스트케이스 항목에는 기본 필드 외에 아래 필드가 추가됩니다.

```yaml
- page_id: '543948978'
  title: Company Management
  title_orig: Company Management
  breadcrumbs: [...]
  breadcrumbs_en: [...]
  path: [administrator-manual, general, company-management]
  # 아래는 테스트케이스 전용 필드
  failure_type: 4
  severity: low
  label: "빈 Bold 태그 삽입 (링크 뒤)"
  description: >
    링크 요소 뒤에 빈 <strong></strong>가 위치하여 **** 가 삽입됨.
  mdx_path: administrator-manual/general/company-management.mdx
  page_title: 'Company Management'
  page_confluenceUrl: 'https://querypie.atlassian.net/wiki/spaces/QM/pages/543948978/...'
  expected_status: fail
```

| 필드 | 설명 |
|------|------|
| `failure_type` | 버그 유형 번호 (4~17) |
| `severity` | `low` / `critical` |
| `label` | 한 줄 버그 요약 |
| `description` | 상세 설명 |
| `mdx_path` | `src/content/ko/` 기준 상대경로 (이미지 경로 계산에 사용) |
| `page_title` | Confluence 페이지 제목 (frontmatter `title:` 값) |
| `page_confluenceUrl` | Confluence 페이지 URL |
| `expected_status` | `fail` (버그 재현) 또는 `pass` (이미 수정됨) |

## pages.yaml 에 엔트리 추가하기

### 새 테스트케이스 추가

1. **테스트케이스 파일 준비**

   ```bash
   PAGE_ID=544379719
   mkdir -p tests/reverse-sync/$PAGE_ID

   # page.xhtml: var/ 에서 복사
   cp var/$PAGE_ID/page.xhtml tests/reverse-sync/$PAGE_ID/page.xhtml

   # page.v1.yaml: var/ 에서 복사 (frontmatter/h1 생성에 필요)
   cp var/$PAGE_ID/page.v1.yaml tests/reverse-sync/$PAGE_ID/page.v1.yaml

   # improved.mdx: 교정된 MDX 파일을 가져옴 (예: 브랜치에서)
   git show <branch>:src/content/ko/<mdx_path> > tests/reverse-sync/$PAGE_ID/improved.mdx
   ```

2. **`pages.yaml` 에 테스트케이스 항목 추가**

   `var/pages.yaml` 에서 해당 페이지 항목을 찾아 복사하고 테스트케이스 필드를 추가합니다.

   ```bash
   # var/pages.yaml 에서 해당 페이지 항목 조회
   python3 -c "
   import yaml
   pages = yaml.safe_load(open('var/pages.yaml'))
   for p in pages:
       if p['page_id'] == '$PAGE_ID':
           print(yaml.dump([p], allow_unicode=True))
           break
   "
   ```

   출력된 항목을 `tests/reverse-sync/pages.yaml` 에 추가하고 테스트케이스 필드를 붙입니다.

   ```yaml
   - page_id: '544379719'
     title: AWS에서 DB 리소스 동기화
     title_orig: AWS에서 DB 리소스 동기화
     breadcrumbs: [...]
     breadcrumbs_en: [...]
     path: [administrator-manual, databases, ...]
     # 테스트케이스 필드 추가
     failure_type: 4
     severity: low
     label: "빈 Bold 태그 삽입"
     description: >
       설명...
     mdx_path: administrator-manual/databases/.../file.mdx
     page_title: 'AWS에서 DB 리소스 동기화'
     page_confluenceUrl: 'https://querypie.atlassian.net/wiki/spaces/QM/pages/544379719/...'
     expected_status: fail
   ```

   > **`mdx_path` 계산**: `var/pages.yaml` 의 `path` 배열을 `/` 로 조인하고 `.mdx` 를 붙입니다.
   > 예: `path: [administrator-manual, databases, file]` → `administrator-manual/databases/file.mdx`

3. **cross-page 링크 대상 페이지 추가 (필요 시)**

   새 테스트케이스 `page.xhtml` 에 다른 페이지로의 `<ac:link>` 가 있다면,
   해당 대상 페이지도 `pages.yaml` 에 있어야 링크가 올바르게 해소됩니다.

   ```bash
   # 새 page.xhtml 에서 참조하는 페이지 제목 확인
   python3 -c "
   from bs4 import BeautifulSoup
   import yaml

   soup = BeautifulSoup(open('tests/reverse-sync/$PAGE_ID/page.xhtml').read(), 'html.parser')
   titles = {l.find('ri:page').get('ri:content-title', '')
             for l in soup.find_all('ac:link')
             if l.find('ri:page')}

   # pages.yaml 에 없는 항목 확인
   existing = {p['title_orig'] for p in yaml.safe_load(open('tests/reverse-sync/pages.yaml'))}
   missing = titles - existing
   if missing:
       print('pages.yaml 에 추가 필요:', missing)
   else:
       print('모두 포함됨')
   "
   ```

   누락된 항목이 있으면 `var/pages.yaml` 에서 찾아 **기본 필드만** 추가합니다 (테스트케이스 필드 불필요).

4. **`original.mdx` 생성**

   ```bash
   # confluence-mdx/ 디렉토리에서
   MDX_PATH=administrator-manual/databases/.../file.mdx
   python3 bin/converter/cli.py \
     --skip-image-copy \
     --language ko \
     --attachment-dir "/${MDX_PATH%.mdx}" \
     "tests/reverse-sync/$PAGE_ID/page.xhtml" \
     "tests/reverse-sync/$PAGE_ID/original.mdx"
   ```

## original.mdx 전체 재생성

`pages.yaml` 을 업데이트한 후 모든 테스트케이스의 `original.mdx` 를 재생성합니다.

```bash
# confluence-mdx/ 디렉토리에서 실행
tests/reverse-sync/regen-original.py
```

## 왜 page.v1.yaml 이 필요한가?

converter 는 `page.v1.yaml` 에서 페이지 제목과 Confluence URL 을 읽어
`original.mdx` 상단의 frontmatter 와 `# h1 제목` 을 자동으로 생성합니다.

```
---
title: 'Company Management'
confluenceUrl: 'https://...'
---

# Company Management
```

이 파일이 없으면 frontmatter 와 h1 제목이 생성되지 않습니다.

## original.mdx 생성 결과 검증

`original.mdx` 를 재생성한 후 아래 항목을 확인합니다.

### 1. `#link-error` 없는지 확인

```bash
# confluence-mdx/ 디렉토리에서
grep -rl '#link-error' tests/reverse-sync/*/original.mdx
# 출력이 없으면 정상
```

원인: `pages.yaml` 에 링크 대상 페이지가 누락된 경우 발생합니다.
해결: 위 "cross-page 링크 대상 페이지 추가" 절차를 따릅니다.

### 2. frontmatter 생성 확인

```bash
head -5 tests/reverse-sync/<page_id>/original.mdx
```

정상 출력:
```
---
title: 'Company Management'
confluenceUrl: 'https://querypie.atlassian.net/wiki/spaces/QM/pages/...'
---
```

원인: `page.v1.yaml` 이 없으면 frontmatter 가 생성되지 않습니다.
해결: `cp var/<page_id>/page.v1.yaml tests/reverse-sync/<page_id>/page.v1.yaml`

### 3. h1 제목 생성 확인

```bash
grep -m1 '^# ' tests/reverse-sync/<page_id>/original.mdx
```

정상 출력: `# Company Management` (페이지 제목)

원인: `page.v1.yaml` 이 없거나 `title` 필드가 없으면 h1 이 생성되지 않습니다.

### 전체 일괄 검증

```bash
python3 - <<'PYEOF'
import yaml, os, re

with open('tests/reverse-sync/pages.yaml') as f:
    pages = yaml.safe_load(f)

errors = []
for page in pages:
    if 'failure_type' not in page:
        continue
    pid = page['page_id']
    path = f"tests/reverse-sync/{pid}/original.mdx"
    if not os.path.exists(path):
        errors.append(f"[MISSING] {pid}: original.mdx 없음")
        continue
    content = open(path).read()
    if '#link-error' in content:
        count = content.count('#link-error')
        errors.append(f"[LINK-ERR] {pid}: #link-error {count}건")
    if not content.startswith('---'):
        errors.append(f"[NO-FRONT] {pid}: frontmatter 없음")
    if not re.search(r'^# .+', content, re.MULTILINE):
        errors.append(f"[NO-H1]    {pid}: h1 제목 없음")

if errors:
    print("검증 실패:")
    for e in errors:
        print(f"  {e}")
else:
    print(f"검증 통과: {sum(1 for p in pages if 'failure_type' in p)}개 테스트케이스 모두 정상")
PYEOF
```

## 테스트 실행

### make test-reverse-sync-bugs

`tests/reverse-sync/` 아래 모든 테스트케이스에 대해 `reverse_sync_cli.py verify` 를 실행합니다.

```bash
# confluence-mdx/tests/ 디렉토리에서
make test-reverse-sync-bugs
```

**결과 해석:**

- **PASS** (녹색): `expected_status: fail` 인 케이스가 pass 로 전환된 경우 = 해당 버그가 수정됨
- **FAIL** (적색): `expected_status: fail` 인 케이스가 여전히 fail = 버그가 아직 존재함 (예상된 실패)
- **PASS** (녹색): `expected_status: pass` 인 케이스가 pass = 정상 작동 확인

> **Note:** `make test-reverse-sync-bugs` 의 실패는 대부분 **예상된 실패**입니다.
> 이 명령은 "현재 수정된 버그 수 / 전체 버그 수" 를 파악하는 용도로 사용합니다.
> `expected_status: fail` 인 케이스가 모두 PASS 로 전환되면, 해당 버그 유형은 모두 수정된 것입니다.

**단일 케이스 실행:**

```bash
make test-reverse-sync-bugs-one TEST_ID=<page_id>
```

**출력 파일:**

실행 후 각 테스트케이스 디렉토리에 다음 파일이 생성됩니다:

| 파일 | 내용 |
|------|------|
| `output.verify.log` | `reverse_sync_cli.py verify` 의 전체 출력 |
| `output.verify.cmd` | 실행된 정확한 CLI 명령 |
| `output.reverse-sync.result.yaml` | verify 결과 YAML (status, diff 포함) |

결과 로그 확인:
```bash
cat reverse-sync/<page_id>/output.verify.log
```

실행된 명령 확인:
```bash
cat reverse-sync/<page_id>/output.verify.cmd
```

**버그 수정 확인 워크플로우:**

버그를 수정한 후, 해당 테스트케이스가 PASS 로 전환되었는지 확인합니다:

```bash
# 1. 단일 케이스로 빠르게 확인
make test-reverse-sync-bugs-one TEST_ID=<page_id>

# 2. 전체 케이스 실행하여 기존 버그 케이스가 깨지지 않았는지 확인
make test-reverse-sync-bugs
```

버그가 수정되었다면 해당 케이스의 `pages.yaml` 항목에서 `expected_status: fail` → `expected_status: pass` 로 변경합니다.
