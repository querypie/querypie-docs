"""unused_attachments.py 단위 테스트."""

import json
import textwrap
from pathlib import Path

import pytest
import yaml

from unused_attachments import (
    extract_referenced_filenames,
    find_unused_attachments,
    format_size,
    load_attachments,
    normalize_filename,
)


@pytest.fixture
def tmp_var(tmp_path):
    """테스트용 var/ 디렉토리 구조를 생성합니다."""
    var_dir = tmp_path / "var"
    var_dir.mkdir()
    return var_dir


def make_page(var_dir: Path, page_id: str, attachments: list[dict], xhtml: str):
    """테스트용 페이지 디렉토리를 생성합니다."""
    page_dir = var_dir / page_id
    page_dir.mkdir(exist_ok=True)

    # attachments.v1.yaml
    att_data = {"results": attachments}
    with open(page_dir / "attachments.v1.yaml", "w", encoding="utf-8") as f:
        yaml.dump(att_data, f, allow_unicode=True)

    # page.xhtml
    (page_dir / "page.xhtml").write_text(xhtml, encoding="utf-8")


def make_pages_yaml(var_dir: Path, page_ids: list[str]):
    """테스트용 pages.yaml을 생성합니다."""
    pages = [{"page_id": pid, "title": f"Page {pid}", "path": [f"page-{pid}"]} for pid in page_ids]
    with open(var_dir / "pages.yaml", "w", encoding="utf-8") as f:
        yaml.dump(pages, f, allow_unicode=True)


def make_attachment(att_id: str, title: str, file_size: int = 1000,
                    media_type: str = "image/png") -> dict:
    """테스트용 첨부파일 메타데이터를 생성합니다."""
    return {
        "id": att_id,
        "type": "attachment",
        "status": "current",
        "title": title,
        "extensions": {
            "mediaType": media_type,
            "fileSize": file_size,
        },
    }


class TestNormalizeFilename:
    def test_nfc_normalization(self):
        import unicodedata
        # "스크린샷" 의 NFD 분해 형태
        nfd = unicodedata.normalize('NFD', "스크린샷")
        nfc = normalize_filename(nfd)
        assert nfc == "스크린샷"  # NFC 정규화됨
        assert nfc == unicodedata.normalize('NFC', nfd)

    def test_ascii_unchanged(self):
        assert normalize_filename("image.png") == "image.png"


class TestExtractReferencedFilenames:
    def test_basic_reference(self):
        xhtml = '<ac:image><ri:attachment ri:filename="test.png" /></ac:image>'
        result = extract_referenced_filenames(xhtml)
        assert result == {"test.png"}

    def test_multiple_references(self):
        xhtml = (
            '<ac:image><ri:attachment ri:filename="a.png" /></ac:image>'
            '<ac:image><ri:attachment ri:filename="b.png" /></ac:image>'
        )
        result = extract_referenced_filenames(xhtml)
        assert result == {"a.png", "b.png"}

    def test_korean_filename(self):
        xhtml = '<ac:image><ri:attachment ri:filename="스크린샷 2024-07-24.png" /></ac:image>'
        result = extract_referenced_filenames(xhtml)
        assert "스크린샷 2024-07-24.png" in result

    def test_no_references(self):
        xhtml = "<p>Hello world</p>"
        result = extract_referenced_filenames(xhtml)
        assert result == set()

    def test_duplicate_references(self):
        xhtml = (
            '<ac:image><ri:attachment ri:filename="same.png" /></ac:image>'
            '<ac:image><ri:attachment ri:filename="same.png" /></ac:image>'
        )
        result = extract_referenced_filenames(xhtml)
        assert result == {"same.png"}


class TestFormatSize:
    def test_bytes(self):
        assert format_size(500) == "500 B"

    def test_kilobytes(self):
        assert format_size(2048) == "2.0 KB"

    def test_megabytes(self):
        assert format_size(5 * 1024 * 1024) == "5.0 MB"


class TestFindUnusedAttachments:
    def test_all_used(self, tmp_var):
        """모든 첨부파일이 사용되는 경우."""
        make_pages_yaml(tmp_var, ["100"])
        make_page(
            tmp_var, "100",
            attachments=[make_attachment("att1", "used.png")],
            xhtml='<ac:image><ri:attachment ri:filename="used.png" /></ac:image>',
        )
        unused = find_unused_attachments(tmp_var)
        assert len(unused) == 0

    def test_one_unused(self, tmp_var):
        """하나의 첨부파일이 사용되지 않는 경우."""
        make_pages_yaml(tmp_var, ["100"])
        make_page(
            tmp_var, "100",
            attachments=[
                make_attachment("att1", "used.png"),
                make_attachment("att2", "unused.png", file_size=5000),
            ],
            xhtml='<ac:image><ri:attachment ri:filename="used.png" /></ac:image>',
        )
        unused = find_unused_attachments(tmp_var)
        assert len(unused) == 1
        assert unused[0]["title"] == "unused.png"
        assert unused[0]["attachment_id"] == "att2"
        assert unused[0]["file_size"] == 5000

    def test_no_attachments(self, tmp_var):
        """첨부파일이 없는 페이지."""
        make_pages_yaml(tmp_var, ["100"])
        page_dir = tmp_var / "100"
        page_dir.mkdir()
        (page_dir / "page.xhtml").write_text("<p>Hello</p>")
        unused = find_unused_attachments(tmp_var)
        assert len(unused) == 0

    def test_page_filter(self, tmp_var):
        """특정 페이지만 검사."""
        make_pages_yaml(tmp_var, ["100", "200"])
        make_page(
            tmp_var, "100",
            attachments=[make_attachment("att1", "unused1.png")],
            xhtml="<p>No refs</p>",
        )
        make_page(
            tmp_var, "200",
            attachments=[make_attachment("att2", "unused2.png")],
            xhtml="<p>No refs</p>",
        )
        unused = find_unused_attachments(tmp_var, page_ids=["100"])
        assert len(unused) == 1
        assert unused[0]["page_id"] == "100"

    def test_cross_reference(self, tmp_var):
        """다른 페이지에서 교차 참조하는 경우 미사용으로 판정하지 않습니다."""
        make_pages_yaml(tmp_var, ["100", "200"])
        # Page 100: attachment "shared.png" is not referenced in its own XHTML
        make_page(
            tmp_var, "100",
            attachments=[make_attachment("att1", "shared.png")],
            xhtml="<p>No local refs</p>",
        )
        # Page 200: references "shared.png" (cross-reference)
        make_page(
            tmp_var, "200",
            attachments=[],
            xhtml='<ac:image><ri:attachment ri:filename="shared.png" /></ac:image>',
        )
        unused = find_unused_attachments(tmp_var)
        assert len(unused) == 0

    def test_multiple_pages(self, tmp_var):
        """여러 페이지에서 미사용 첨부파일 검출."""
        make_pages_yaml(tmp_var, ["100", "200"])
        make_page(
            tmp_var, "100",
            attachments=[
                make_attachment("att1", "used.png"),
                make_attachment("att2", "unused1.png"),
            ],
            xhtml='<ac:image><ri:attachment ri:filename="used.png" /></ac:image>',
        )
        make_page(
            tmp_var, "200",
            attachments=[
                make_attachment("att3", "unused2.png"),
            ],
            xhtml="<p>No refs</p>",
        )
        unused = find_unused_attachments(tmp_var)
        assert len(unused) == 2
        titles = {u["title"] for u in unused}
        assert titles == {"unused1.png", "unused2.png"}

    def test_unicode_normalization_match(self, tmp_var):
        """Unicode NFC 정규화로 파일명이 일치하는 경우."""
        # NFD 형태의 한글 파일명을 첨부파일로, NFC 형태를 XHTML에서 사용
        nfd_name = "스크린샷.png"  # Python 소스는 NFC이지만, YAML에서 NFD가 올 수 있음
        nfc_name = "스크린샷.png"

        make_pages_yaml(tmp_var, ["100"])
        make_page(
            tmp_var, "100",
            attachments=[make_attachment("att1", nfd_name)],
            xhtml=f'<ac:image><ri:attachment ri:filename="{nfc_name}" /></ac:image>',
        )
        unused = find_unused_attachments(tmp_var)
        assert len(unused) == 0


class TestLoadAttachments:
    def test_missing_file(self, tmp_path):
        """attachments.v1.yaml이 없는 경우."""
        result = load_attachments(tmp_path)
        assert result == []

    def test_empty_file(self, tmp_path):
        """빈 YAML 파일."""
        (tmp_path / "attachments.v1.yaml").write_text("")
        result = load_attachments(tmp_path)
        assert result == []

    def test_valid_file(self, tmp_path):
        """정상적인 첨부파일 메타데이터."""
        data = {"results": [{"id": "att1", "title": "test.png"}]}
        with open(tmp_path / "attachments.v1.yaml", "w") as f:
            yaml.dump(data, f)
        result = load_attachments(tmp_path)
        assert len(result) == 1
        assert result[0]["title"] == "test.png"


class TestRealData:
    """실제 var/ 데이터를 사용한 통합 테스트."""

    VAR_DIR = Path(__file__).resolve().parent.parent / "var"
    SAMPLE_PAGE_ID = "1060306945"

    @pytest.mark.skipif(
        not (VAR_DIR / SAMPLE_PAGE_ID).is_dir(),
        reason="var/ 실제 데이터가 없습니다"
    )
    def test_sample_page(self):
        """실제 페이지 데이터로 미사용 첨부파일을 검출합니다."""
        unused = find_unused_attachments(self.VAR_DIR, page_ids=[self.SAMPLE_PAGE_ID])
        # 이 페이지는 10개 첨부파일 중 5개가 미사용
        assert len(unused) == 5
        unused_titles = {u["title"] for u in unused}
        assert "image-20240801-074431.png" in unused_titles
        assert "image-20241103-071004.png" in unused_titles

    @pytest.mark.skipif(
        not (VAR_DIR / SAMPLE_PAGE_ID).is_dir(),
        reason="var/ 실제 데이터가 없습니다"
    )
    def test_full_scan(self):
        """전체 스캔이 정상적으로 완료됩니다."""
        unused = find_unused_attachments(self.VAR_DIR)
        # 미사용 첨부파일이 존재해야 함
        assert len(unused) > 0
        # 각 항목에 필수 필드가 있어야 함
        for item in unused:
            assert "page_id" in item
            assert "attachment_id" in item
            assert "title" in item
