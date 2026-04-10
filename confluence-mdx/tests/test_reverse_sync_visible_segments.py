"""Visible segment extraction tests for reverse sync list phase 1."""

from reverse_sync.visible_segments import (
    extract_list_model_from_mdx,
    extract_list_model_from_xhtml,
)


class TestExtractListModelFromMdx:
    def test_preserves_marker_post_space_and_item_edge_space(self):
        model = extract_list_model_from_mdx(
            "*  [Okta 연동하기 ](url)\n"
            "* LDAP\n"
        )

        assert model.visible_text == "Okta 연동하기 LDAP"
        assert [segment.kind for segment in model.segments[:3]] == [
            "list_marker", "ws", "text",
        ]
        assert model.segments[1].text == "  "
        assert model.segments[1].visible is False

    def test_continuation_line_reflow_canonicalizes_to_same_visible_text(self):
        single = extract_list_model_from_mdx("* hello world\n")
        reflow = extract_list_model_from_mdx("* hello\n  world\n")

        assert single.visible_text == reflow.visible_text
        assert single.structural_fingerprint == reflow.structural_fingerprint

    def test_strips_non_visible_trailing_space_before_br_followed_by_figure(self):
        model = extract_list_model_from_mdx(
            "4. 목록 좌측 상단에서 `Delete`버튼을 클릭합니다 <br/>\n"
            "  <figure data-layout=\"center\" data-align=\"center\">\n"
            "  <img src=\"/x.png\" alt=\"img\" width=\"736\" />\n"
            "  </figure>\n"
            "5. 확인 창이 나타나면 삭제하여 설정을 제거합니다.\n"
        )

        assert "클릭합니다 확인" not in model.visible_text
        assert "클릭합니다확인" in model.visible_text

    def test_canonicalizes_figure_only_pseudo_item_into_previous_item(self):
        old = extract_list_model_from_mdx(
            "4. SMTP 설정을 생성합니다.\n"
            "    11. **Test 버튼** : SMTP 설정이 접속에 문제 없는지 확인합니다.<br/>\n"
            "    12.\n"
            "      <figure data-layout=\"center\" data-align=\"center\">\n"
            "      <img src=\"/x.png\" alt=\"SMTP 설정 팝업 다이얼로그\" width=\"402\" />\n"
            "      <figcaption>\n"
            "      SMTP 설정 팝업 다이얼로그\n"
            "      </figcaption>\n"
            "      </figure>\n"
            "5. `OK` 버튼을 누르고 설정을 저장합니다.\n"
        )
        new = extract_list_model_from_mdx(
            "4. SMTP 설정을 생성합니다.\n"
            "    11. **Test 버튼** : SMTP 설정이 접속에 문제 없는지 확인합니다.<br/>\n"
            "      <figure data-layout=\"center\" data-align=\"center\">\n"
            "      <img src=\"/x.png\" alt=\"SMTP 설정 팝업 다이얼로그\" width=\"402\" />\n"
            "      <figcaption>\n"
            "      SMTP 설정 팝업 다이얼로그\n"
            "      </figcaption>\n"
            "      </figure>\n"
            "5. `OK` 버튼을 누르고 설정을 저장합니다.\n"
        )

        assert old.visible_text == new.visible_text
        assert old.structural_fingerprint == new.structural_fingerprint


class TestExtractListModelFromXhtml:
    def test_preserves_dom_whitespace_and_tracks_structure(self):
        model = extract_list_model_from_xhtml(
            "<ul><li><p>앞 "
            "<ac:link><ri:page ri:content-title=\"링크\"/>"
            "<ac:link-body>링크</ac:link-body></ac:link> 뒤</p></li></ul>"
        )

        assert model.visible_text == "앞 링크 뒤"
        assert any(segment.kind == "anchor" for segment in model.segments)
        assert model.structural_fingerprint[0] == "ul"

    def test_includes_image_caption_text_in_visible_text(self):
        model = extract_list_model_from_xhtml(
            "<ul><li><p>항목</p>"
            "<ac:image ac:align=\"center\">"
            "<ri:attachment ri:filename=\"x.png\"/>"
            "<ac:caption><p>캡션 텍스트</p></ac:caption>"
            "</ac:image></li></ul>"
        )

        assert model.visible_text == "항목캡션 텍스트"

    def test_ignores_whitespace_only_paragraph_after_image(self):
        model = extract_list_model_from_xhtml(
            "<ol><li><p>목록 좌측 상단에서 <code>Delete</code>버튼을 클릭합니다</p>"
            "<ac:image ac:align=\"center\">"
            "<ri:attachment ri:filename=\"x.png\"/>"
            "</ac:image><p> </p></li></ol>"
        )

        assert model.visible_text == "목록 좌측 상단에서 Delete버튼을 클릭합니다"

    def test_preserves_separator_space_from_whitespace_only_paragraph_between_items(self):
        model = extract_list_model_from_xhtml(
            "<ol><li><p>before old</p>"
            "<ac:image ac:align=\"center\">"
            "<ri:attachment ri:filename=\"x.png\"/>"
            "<ac:caption><p>Cap</p></ac:caption>"
            "</ac:image><p> </p></li><li><p>next</p></li></ol>"
        )

        assert model.visible_text == "before oldCap next"
