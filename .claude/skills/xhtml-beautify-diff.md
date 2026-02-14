# XHTML Beautify-Diff Viewer 사용 가이드

## 개요

`xhtml_beautify_diff.py`는 두 Confluence XHTML 파일의 **의미적 차이**만 비교하는 도구다.
XML serializer 부산물(속성 순서, self-closing 태그, entity 인코딩)을 정규화하여 소거하고,
실제 구조/텍스트 변경만 unified diff로 출력한다.

## 사용법

```bash
cd confluence-mdx
python3 bin/xhtml_beautify_diff.py <file_a> <file_b>
```

### Exit codes

| Code | 의미 |
|------|------|
| 0 | 차이 없음 |
| 1 | 차이 있음 (diff 출력) |
| 2 | 오류 (파일 없음 등) |

## 주요 활용 시나리오

### 1. reverse-sync 패치 결과 검증

reverse-sync가 XHTML에 적용한 패치를 원본과 비교:

```bash
python3 bin/xhtml_beautify_diff.py \
  var/<page_id>/page.xhtml \
  var/<page_id>/reverse-sync.patched.xhtml
```

### 2. Confluence 원본 vs 패치된 XHTML 비교

특정 페이지의 원본과 패치 결과를 비교하여 의도한 변경만 적용되었는지 확인:

```bash
# 예: administrator-manual 페이지
python3 bin/xhtml_beautify_diff.py \
  var/544178405/page.xhtml \
  var/544178405/reverse-sync.patched.xhtml
```

### 3. 테스트케이스의 expected diff 확인

각 테스트케이스 디렉토리에는 `expected.beautify-diff` 파일이 있다.
이 파일은 `page.xhtml`과 `expected.reverse-sync.patched.xhtml` 간의 기대 diff를 담고 있다:

```bash
# 테스트케이스의 실제 diff와 기대 diff 비교
python3 bin/xhtml_beautify_diff.py \
  tests/testcases/<page_id>/page.xhtml \
  tests/testcases/<page_id>/expected.reverse-sync.patched.xhtml
```

## 실전 예시: reverse-sync verify 후 패치 분석

`reverse-sync verify`를 실행하면 `var/<page_id>/` 에 중간 산출물이 생성된다.
이 중 `page.xhtml`(원본)과 `reverse-sync.patched.xhtml`(패치 결과)를 비교하면
XHTML 레벨에서 어떤 텍스트가 변경되었는지 직접 확인할 수 있다.

### Step 1: verify 실행

```bash
cd confluence-mdx
python3 bin/reverse_sync_cli.py verify \
  "jk/fix-typo-and-grammar:src/content/ko/administrator-manual.mdx"
```

이 명령은 `var/544178405/` 디렉토리에 다음 파일들을 생성한다:

```
var/544178405/
├── page.xhtml                          # Confluence 원본 XHTML
├── reverse-sync.diff.yaml             # MDX 블록 변경 목록
├── reverse-sync.mapping.original.yaml # 원본 XHTML 블록 매핑
├── reverse-sync.patched.xhtml         # 패치된 XHTML  ← 비교 대상
├── reverse-sync.mapping.patched.yaml  # 패치 후 매핑
├── reverse-sync.result.yaml           # 검증 결과
└── verify.mdx                         # 패치된 XHTML → MDX 재변환 결과
```

### Step 2: beautify-diff로 XHTML 변경 확인

```bash
python3 bin/xhtml_beautify_diff.py \
  var/544178405/page.xhtml \
  var/544178405/reverse-sync.patched.xhtml
```

### Step 3: 출력 읽기

```diff
@@ -2,7 +2,7 @@
  환영합니다.
 </h2>
 <p>
- QueryPie의 관리자는 QueryPie Web 또는 API를 통하여 리소스 및 권한, ...
+ QueryPie의 관리자는 QueryPie Web 또는 API를 통해 리소스 및 권한, ...
 </p>
@@ -28,7 +28,7 @@
 <p>
- ... 설정해야하는 항목들이 있습니다. ... 설정하시는 것을 권장해 드립니다.
+ ... 설정해야 하는 항목들이 있습니다. ... 설정하는 것을 권장합니다.
 </p>
```

이 diff를 통해 확인할 수 있는 것:

- **패치가 올바른 위치에 적용되었는지**: `<p>` 태그 내의 정확한 텍스트가 변경됨
- **의도하지 않은 변경이 없는지**: diff에 나타나지 않은 부분은 원본 그대로 보존됨
- **인라인 구조가 보존되었는지**: `<code>`, `<strong>` 등 인라인 태그가 유지됨

### verify 결과가 FAIL인 경우

verify가 FAIL이면 `reverse-sync.result.yaml`의 diff_report와 beautify-diff 출력을 함께 분석한다:

1. **result.yaml의 diff_report** → MDX 레벨에서 어떤 텍스트가 기대와 다른지 확인
2. **beautify-diff** → XHTML 레벨에서 패치가 실제로 어떻게 적용되었는지 확인
3. 두 결과를 대조하여 패치 누락/오적용 원인을 특정

## 정규화 동작

이 도구가 자동으로 소거하는 serializer 부산물:

- **속성 순서 차이**: `ac:align="center" ac:layout="center"` vs `ac:layout="center" ac:align="center"` → 동일
- **Self-closing 태그**: `<ri:attachment ... />` vs `<ri:attachment ...></ri:attachment>` → 동일
- **Entity 인코딩**: `&amp;`, `&lt;`, `&gt;`는 보존, `&quot;` 등은 유니코드로 디코딩

## 출력 예시

```diff
--- var/544112828/page.xhtml
+++ var/544112828/reverse-sync.patched.xhtml
@@ -5,7 +5,7 @@
     Overview
    </h2>
    <p>
-    QueryPie Agent를 설치하면, DataGrip, DBeaver와 같은 SQL Client...
+    QueryPie Agent를 설정하면, DataGrip, DBeaver와 같은 SQL Client...
    </p>
```

## Python API

스크립트 내에서 직접 사용할 수도 있다:

```python
from xhtml_beautify_diff import beautify_xhtml, xhtml_diff

# 단일 XHTML 정규화
pretty = beautify_xhtml(xhtml_string)

# 두 XHTML 비교 (차이 없으면 빈 리스트)
diff_lines = xhtml_diff(text_a, text_b, label_a="original", label_b="patched")
```

## 관련 Skill

- [reverse-sync.md](reverse-sync.md) — 이 도구의 주요 사용 워크플로우 (MDX → Confluence XHTML 역반영)
- [confluence-mdx.md](confluence-mdx.md) — Confluence에서 MDX로의 forward 변환 워크플로우
