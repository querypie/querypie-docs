# XHTML Beautify-Diff Viewer 사용 가이드

## 개요

`xhtml_beautify_diff.py`는 두 Confluence XHTML 파일의 **의미적 차이**만 비교하는 도구다.
XML serializer 부산물(속성 순서, self-closing 태그, entity 인코딩)을 정규화하여 소거하고,
실제 구조/텍스트 변경만 unified diff로 출력한다.

## 사용법

```bash
cd confluence-mdx
python bin/xhtml_beautify_diff.py <file_a> <file_b>
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
python bin/xhtml_beautify_diff.py \
  var/<page_id>/page.xhtml \
  var/<page_id>/reverse-sync.patched.xhtml
```

### 2. Confluence 원본 vs 패치된 XHTML 비교

특정 페이지의 원본과 패치 결과를 비교하여 의도한 변경만 적용되었는지 확인:

```bash
# 예: administrator-manual 페이지
python bin/xhtml_beautify_diff.py \
  var/544178405/page.xhtml \
  var/544178405/reverse-sync.patched.xhtml
```

### 3. 테스트케이스의 expected diff 확인

각 테스트케이스 디렉토리에는 `expected.beautify-diff` 파일이 있다.
이 파일은 `page.xhtml`과 `expected.reverse-sync.patched.xhtml` 간의 기대 diff를 담고 있다:

```bash
# 테스트케이스의 실제 diff와 기대 diff 비교
python bin/xhtml_beautify_diff.py \
  tests/testcases/<page_id>/page.xhtml \
  tests/testcases/<page_id>/expected.reverse-sync.patched.xhtml
```

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
