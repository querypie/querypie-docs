from pathlib import Path

from mdx_to_storage.link_resolver import LinkResolver, load_pages_yaml


def test_resolve_relative_path_to_title(tmp_path: Path):
    pages_yaml = tmp_path / "pages.yaml"
    pages_yaml.write_text(
        """
- page_id: "1"
  title_orig: "My Dashboard"
  path: ["user-manual", "my-dashboard"]
""".strip(),
        encoding="utf-8",
    )
    resolver = LinkResolver(pages_yaml)

    title, anchor = resolver.resolve("user-manual/my-dashboard", link_text="My Dashboard")
    assert title == "My Dashboard"
    assert anchor is None


def test_resolve_relative_path_with_dotdot_and_anchor(tmp_path: Path):
    pages_yaml = tmp_path / "pages.yaml"
    pages_yaml.write_text(
        """
- page_id: "1"
  title_orig: "My Dashboard"
  path: ["user-manual", "my-dashboard"]
""".strip(),
        encoding="utf-8",
    )
    resolver = LinkResolver(pages_yaml)

    title, anchor = resolver.resolve(
        "../../user-manual/my-dashboard#querypie-web%EC%97%90",
        link_text="My Dashboard",
    )
    assert title == "My Dashboard"
    assert anchor == "querypie-web%EC%97%90"


def test_resolve_dot_path_by_link_text(tmp_path: Path):
    pages_yaml = tmp_path / "pages.yaml"
    pages_yaml.write_text(
        """
- page_id: "1"
  title_orig: "SQL Request 요청하기"
  path: ["user-manual", "workflow", "requesting-sql"]
""".strip(),
        encoding="utf-8",
    )
    resolver = LinkResolver(pages_yaml)

    title, anchor = resolver.resolve(".", link_text="SQL Request 요청하기")
    assert title == "SQL Request 요청하기"
    assert anchor is None


def test_external_and_hash_links_are_not_resolved(tmp_path: Path):
    pages_yaml = tmp_path / "pages.yaml"
    pages_yaml.write_text("[]", encoding="utf-8")
    resolver = LinkResolver(pages_yaml)

    assert resolver.resolve("https://example.com", link_text="x") == (None, None)
    assert resolver.resolve("mailto:test@example.com", link_text="x") == (None, None)
    assert resolver.resolve("#section", link_text="x") == (None, None)


def test_load_pages_yaml_returns_page_entries(tmp_path: Path):
    pages_yaml = tmp_path / "pages.yaml"
    pages_yaml.write_text(
        """
- page_id: "100"
  title_orig: "Overview"
  path: ["overview"]
""".strip(),
        encoding="utf-8",
    )
    pages = load_pages_yaml(pages_yaml)
    assert len(pages) == 1
    assert pages[0].page_id == "100"
    assert pages[0].title_orig == "Overview"
    assert pages[0].path == ["overview"]


def test_resolve_relative_dotdot_with_current_page(tmp_path: Path):
    pages_yaml = tmp_path / "pages.yaml"
    pages_yaml.write_text(
        """
- page_id: "200"
  title_orig: "Child"
  path: ["docs", "section", "child"]
- page_id: "201"
  title_orig: "Sibling"
  path: ["docs", "sibling"]
""".strip(),
        encoding="utf-8",
    )
    resolver = LinkResolver(pages_yaml)
    resolver.set_current_page("200")
    title, anchor = resolver.resolve("../sibling", link_text="Sibling")
    assert title == "Sibling"
    assert anchor is None
