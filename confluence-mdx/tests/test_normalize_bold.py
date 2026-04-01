"""normalize_bold 스크립트 회귀 테스트."""

from pathlib import Path

import normalize_bold


class TestApplyRules:
    def test_split_bold_merges_same_line_only(self):
        assert normalize_bold._protect_and_transform("**a** **b**") == "**a b**"

    def test_split_bold_does_not_merge_across_lines(self):
        text = "**a**\n**b**"
        assert normalize_bold._protect_and_transform(text) == text

    def test_bold_colon_space_merges_same_line_only(self):
        assert (
            normalize_bold._protect_and_transform("**label** : value")
            == "**label**: value"
        )

    def test_bold_colon_space_does_not_merge_across_lines(self):
        text = "**label**\n: value"
        assert normalize_bold._protect_and_transform(text) == text


class TestNormalizeFileDiff:
    def test_normalize_file_reports_inserted_lines(self, monkeypatch, tmp_path: Path):
        path = tmp_path / "sample.mdx"
        path.write_text("alpha\nbeta\ngamma\n", encoding="utf-8")

        monkeypatch.setattr(
            normalize_bold,
            "_protect_and_transform",
            lambda text, include_code=False: "alpha\ninserted\nbeta\ngamma\n",
        )

        assert normalize_bold.normalize_file(path) == [(2, "", "inserted")]

    def test_normalize_file_reports_deleted_lines(self, monkeypatch, tmp_path: Path):
        path = tmp_path / "sample.mdx"
        path.write_text("alpha\nbeta\ngamma\n", encoding="utf-8")

        monkeypatch.setattr(
            normalize_bold,
            "_protect_and_transform",
            lambda text, include_code=False: "alpha\ngamma\n",
        )

        assert normalize_bold.normalize_file(path) == [(2, "beta", "")]
