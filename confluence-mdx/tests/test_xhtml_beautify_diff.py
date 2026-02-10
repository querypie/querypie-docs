"""xhtml_beautify_diff 모듈 단위 테스트."""

import subprocess
import sys
from pathlib import Path

import pytest

from xhtml_beautify_diff import beautify_xhtml, xhtml_diff


# ---------------------------------------------------------------------------
# beautify_xhtml: 정규화 동작 검증
# ---------------------------------------------------------------------------


class TestBeautifyXhtml:
    """beautify_xhtml() 정규화 동작 테스트."""

    def test_node_per_line(self):
        """각 노드가 별도 줄로 분리된다."""
        html = "<h2>Title</h2><p>Text</p>"
        result = beautify_xhtml(html)
        assert "<h2>\n" in result
        assert "</h2>\n" in result
        assert "<p>\n" in result

    def test_self_closing_normalized(self):
        """<p /> 과 <p></p> 가 동일하게 정규화된다."""
        a = beautify_xhtml("<p />")
        b = beautify_xhtml("<p></p>")
        assert a == b

    def test_self_closing_ri_attachment(self):
        """<ri:attachment ... /> 과 명시적 닫기가 동일하게 정규화된다."""
        a = beautify_xhtml('<ri:attachment ri:filename="t.png" />')
        b = beautify_xhtml('<ri:attachment ri:filename="t.png"></ri:attachment>')
        assert a == b

    def test_attribute_order_preserved(self):
        """속성 순서가 원문 그대로 유지된다."""
        html = '<ac:image ac:align="center" ac:layout="center" ac:width="760">'
        result = beautify_xhtml(html)
        # align이 layout보다 먼저 나와야 함
        assert result.index("ac:align") < result.index("ac:layout")
        assert result.index("ac:layout") < result.index("ac:width")

    def test_amp_lt_gt_preserved(self):
        """&amp; &lt; &gt; 가 entity로 보존된다."""
        html = "<p>A &amp; B &lt; C &gt; D</p>"
        result = beautify_xhtml(html)
        assert "&amp;" in result
        assert "&lt;" in result
        assert "&gt;" in result

    def test_quot_decoded(self):
        """&quot; 는 유니코드 문자로 디코딩된다 (html.parser 특성)."""
        html = '<p>&quot;hello&quot;</p>'
        result = beautify_xhtml(html)
        assert '"hello"' in result
        assert "&quot;" not in result

    def test_empty_input(self):
        """빈 문자열은 빈 결과를 반환한다."""
        assert beautify_xhtml("").strip() == ""

    def test_nested_structure(self):
        """중첩 구조가 들여쓰기로 표현된다."""
        html = "<ol><li><p>Item</p></li></ol>"
        result = beautify_xhtml(html)
        lines = result.splitlines()
        # li는 ol보다 깊은 들여쓰기
        ol_indent = len(lines[0]) - len(lines[0].lstrip())
        li_line = [l for l in lines if "<li>" in l][0]
        li_indent = len(li_line) - len(li_line.lstrip())
        assert li_indent > ol_indent


# ---------------------------------------------------------------------------
# xhtml_diff: diff 출력 검증
# ---------------------------------------------------------------------------


class TestXhtmlDiff:
    """xhtml_diff() diff 검증 테스트."""

    def test_identical_no_diff(self):
        """동일한 XHTML은 빈 diff를 반환한다."""
        html = "<h2>Title</h2><p>Content</p>"
        assert xhtml_diff(html, html) == []

    def test_serialization_artifacts_ignored(self):
        """속성 순서/self-closing 차이는 diff에 나타나지 않는다."""
        a = '<ac:image ac:align="center" ac:layout="center"><ri:attachment ri:filename="t.png" /></ac:image>'
        b = '<ac:image ac:layout="center" ac:align="center"><ri:attachment ri:filename="t.png"></ri:attachment></ac:image>'
        assert xhtml_diff(a, b) == []

    def test_text_change_detected(self):
        """텍스트 변경이 감지된다."""
        a = "<h2>활성화</h2><p>Content</p>"
        b = "<h2>사용</h2><p>Content</p>"
        diff = xhtml_diff(a, b)
        assert len(diff) > 0
        minus = [l for l in diff if l.startswith("-") and not l.startswith("---")]
        plus = [l for l in diff if l.startswith("+") and not l.startswith("+++")]
        assert any("활성화" in l for l in minus)
        assert any("사용" in l for l in plus)

    def test_attribute_deletion_detected(self):
        """속성 삭제가 감지된다."""
        a = '<ac:image ac:align="center" ac:width="760"></ac:image>'
        b = '<ac:image ac:align="center"></ac:image>'
        diff = xhtml_diff(a, b)
        assert len(diff) > 0
        assert any('ac:width="760"' in l for l in diff)

    def test_attribute_value_change_detected(self):
        """속성 값 변경이 감지된다."""
        a = '<ac:image ac:width="760"></ac:image>'
        b = '<ac:image ac:width="800"></ac:image>'
        diff = xhtml_diff(a, b)
        assert len(diff) > 0
        assert any("760" in l for l in diff)
        assert any("800" in l for l in diff)

    def test_node_deletion_detected(self):
        """노드 삭제가 감지된다."""
        a = "<p>Text</p><p>Extra</p>"
        b = "<p>Text</p>"
        diff = xhtml_diff(a, b)
        assert len(diff) > 0
        assert any("Extra" in l for l in diff)

    def test_node_addition_detected(self):
        """노드 추가가 감지된다."""
        a = "<p>Text</p>"
        b = "<p>Text</p><p>Added</p>"
        diff = xhtml_diff(a, b)
        assert len(diff) > 0
        assert any("Added" in l for l in diff)

    def test_tag_name_change_detected(self):
        """태그 이름 변경이 감지된다."""
        a = "<h2>Title</h2>"
        b = "<h3>Title</h3>"
        diff = xhtml_diff(a, b)
        assert len(diff) > 0
        assert any("<h2>" in l for l in diff)
        assert any("<h3>" in l for l in diff)

    def test_node_insertion_detected(self):
        """노드 삽입(br 등)이 감지된다."""
        a = "<p>Text</p>"
        b = "<p><br/>Text</p>"
        diff = xhtml_diff(a, b)
        assert len(diff) > 0
        assert any("br" in l.lower() for l in diff)

    def test_labels_in_output(self):
        """fromfile/tofile 레이블이 diff 헤더에 포함된다."""
        a = "<p>Old</p>"
        b = "<p>New</p>"
        diff = xhtml_diff(a, b, label_a="page.xhtml", label_b="patched.xhtml")
        assert any("page.xhtml" in l for l in diff)
        assert any("patched.xhtml" in l for l in diff)

    def test_confluence_macro_change_detected(self):
        """Confluence 매크로 속성 변경이 감지된다."""
        a = '<ac:structured-macro ac:name="info" ac:schema-version="1"></ac:structured-macro>'
        b = '<ac:structured-macro ac:name="warning" ac:schema-version="1"></ac:structured-macro>'
        diff = xhtml_diff(a, b)
        assert len(diff) > 0
        assert any("info" in l for l in diff)
        assert any("warning" in l for l in diff)


# ---------------------------------------------------------------------------
# CLI 통합 테스트
# ---------------------------------------------------------------------------


class TestCli:
    """CLI(main) 통합 테스트."""

    def test_identical_files_exit_0(self, tmp_path):
        """동일한 파일 비교 시 exit code 0."""
        content = "<h2>Title</h2><p>Content</p>"
        file_a = tmp_path / "a.xhtml"
        file_b = tmp_path / "b.xhtml"
        file_a.write_text(content)
        file_b.write_text(content)

        result = subprocess.run(
            [sys.executable, "bin/xhtml_beautify_diff.py", str(file_a), str(file_b)],
            capture_output=True, text=True,
            cwd="/Users/jk/workspace/querypie-docs/confluence-mdx",
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_different_files_exit_1(self, tmp_path):
        """다른 파일 비교 시 exit code 1 + diff 출력."""
        file_a = tmp_path / "a.xhtml"
        file_b = tmp_path / "b.xhtml"
        file_a.write_text("<p>Old</p>")
        file_b.write_text("<p>New</p>")

        result = subprocess.run(
            [sys.executable, "bin/xhtml_beautify_diff.py", str(file_a), str(file_b)],
            capture_output=True, text=True,
            cwd="/Users/jk/workspace/querypie-docs/confluence-mdx",
        )
        assert result.returncode == 1
        assert "Old" in result.stdout
        assert "New" in result.stdout

    def test_missing_file_exit_2(self, tmp_path):
        """존재하지 않는 파일 시 exit code 2."""
        file_a = tmp_path / "a.xhtml"
        file_a.write_text("<p>Text</p>")

        result = subprocess.run(
            [sys.executable, "bin/xhtml_beautify_diff.py",
             str(file_a), str(tmp_path / "nonexistent.xhtml")],
            capture_output=True, text=True,
            cwd="/Users/jk/workspace/querypie-docs/confluence-mdx",
        )
        assert result.returncode == 2
        assert "not found" in result.stderr

    def test_serialization_only_diff_exit_0(self, tmp_path):
        """serializer 부산물만 다른 파일은 exit code 0."""
        file_a = tmp_path / "a.xhtml"
        file_b = tmp_path / "b.xhtml"
        file_a.write_text('<ac:image ac:align="center" ac:layout="center"><ri:attachment ri:filename="t.png" /></ac:image>')
        file_b.write_text('<ac:image ac:layout="center" ac:align="center"><ri:attachment ri:filename="t.png"></ri:attachment></ac:image>')

        result = subprocess.run(
            [sys.executable, "bin/xhtml_beautify_diff.py", str(file_a), str(file_b)],
            capture_output=True, text=True,
            cwd="/Users/jk/workspace/querypie-docs/confluence-mdx",
        )
        assert result.returncode == 0
