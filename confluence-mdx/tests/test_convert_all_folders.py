from argparse import Namespace
from pathlib import Path

import pytest
import yaml

from convert_all import (
    ConversionError,
    convert_all,
    finalize_manifest,
    generate_folder_mdx,
    generate_navigation,
)


def _write_yaml(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def _node(page_id: str, content_type: str, title: str, path: list[str]) -> dict:
    return {
        "page_id": page_id,
        "type": content_type,
        "title": title,
        "title_orig": title,
        "breadcrumbs": [title],
        "breadcrumbs_en": [title],
        "path": path,
    }


def _folder_data(folder_id: str, title: str) -> dict:
    return {
        "id": folder_id,
        "type": "folder",
        "title": title,
        "_links": {
            "base": "https://querypie.atlassian.net/wiki",
        },
    }


def test_folder_mdx_contains_only_direct_supported_children_in_position_order(
    tmp_path,
    capsys,
):
    var_dir = tmp_path / "var"
    output_dir = tmp_path / "output"
    folder = _node("folder", "folder", "MCP Server", ["admin", "mcp-server"])
    page_a = _node("page-a", "page", "Page A", ["admin", "mcp-server", "page-a"])
    nested = _node(
        "nested",
        "folder",
        "Nested Folder",
        ["admin", "mcp-server", "nested-folder"],
    )
    descendant = _node(
        "descendant",
        "page",
        "Descendant",
        ["admin", "mcp-server", "nested-folder", "descendant"],
    )
    nodes = {
        node["page_id"]: node
        for node in (folder, page_a, nested, descendant)
    }
    _write_yaml(var_dir / "folder" / "folder.v2.yaml", _folder_data(
        "folder",
        "MCP Server",
    ))
    _write_yaml(var_dir / "folder" / "children.v2.yaml", {
        "results": [
            {
                "id": "page-a",
                "type": "page",
                "title": "stale title",
                "childPosition": 2,
            },
            {
                "id": "nested",
                "type": "folder",
                "title": "stale nested title",
                "childPosition": 1,
            },
            {
                "id": "whiteboard",
                "type": "whiteboard",
                "title": "Board",
                "childPosition": 3,
            },
        ],
    })
    _write_yaml(var_dir / "nested" / "folder.v2.yaml", _folder_data(
        "nested",
        "Nested Folder",
    ))
    _write_yaml(var_dir / "nested" / "children.v2.yaml", {
        "results": [{
            "id": "descendant",
            "type": "page",
            "title": "Descendant",
            "childPosition": 1,
        }],
    })

    relative_path = generate_folder_mdx(
        folder,
        nodes,
        var_dir,
        output_dir,
        "https://querypie.atlassian.net/wiki",
    )

    assert relative_path == Path("admin/mcp-server.mdx")
    content = (output_dir / relative_path).read_text()
    assert "title: 'MCP Server'" in content
    assert (
        "confluenceUrl: "
        "'https://querypie.atlassian.net/wiki/spaces/QM/folder/folder'"
    ) in content
    assert "# MCP Server" in content
    assert "## 하위 문서" in content
    assert content.index("Nested Folder") < content.index("Page A")
    assert (
        "- [Nested Folder](./mcp-server/nested-folder)"
        in content
    )
    assert "- [Page A](./mcp-server/page-a)" in content
    assert "Descendant" not in content
    assert "Board" not in content
    assert "type=whiteboard" in capsys.readouterr().err

    nested_relative_path = generate_folder_mdx(
        nested,
        nodes,
        var_dir,
        output_dir,
        "https://querypie.atlassian.net/wiki",
    )
    nested_content = (output_dir / nested_relative_path).read_text()
    assert "- [Descendant](./nested-folder/descendant)" in nested_content


def test_empty_folder_mdx_has_empty_state(tmp_path):
    var_dir = tmp_path / "var"
    output_dir = tmp_path / "output"
    folder = _node("empty", "folder", "Empty", ["empty"])
    _write_yaml(var_dir / "empty" / "folder.v2.yaml", _folder_data("empty", "Empty"))
    _write_yaml(var_dir / "empty" / "children.v2.yaml", {"results": []})

    generate_folder_mdx(
        folder,
        {"empty": folder},
        var_dir,
        output_dir,
        "https://querypie.atlassian.net/wiki",
    )

    assert "하위 문서가 없습니다." in (output_dir / "empty.mdx").read_text()


def test_navigation_is_generated_after_page_and_folder_mdx_exist(tmp_path):
    var_dir = tmp_path / "var"
    output_dir = tmp_path / "output"
    root = _node("root", "page", "Root", ["root"])
    parent = _node("parent", "page", "Parent", ["parent"])
    folder = _node("folder", "folder", "Folder", ["parent", "folder"])
    page = _node("page", "page", "Page", ["parent", "page"])
    pages = [root, parent, folder, page]

    _write_yaml(var_dir / "parent" / "children.v2.yaml", {
        "results": [
            {"id": "page", "type": "page", "childPosition": 2},
            {"id": "folder", "type": "folder", "childPosition": 1},
        ],
    })
    _write_yaml(var_dir / "folder" / "children.v2.yaml", {"results": []})
    _write_yaml(var_dir / "page" / "children.v2.yaml", {"results": []})
    for node in pages[1:]:
        path = Path(*node["path"][:-1], f"{node['path'][-1]}.mdx")
        (output_dir / path).parent.mkdir(parents=True, exist_ok=True)
        (output_dir / path).write_text("# generated\n")

    entries = generate_navigation(pages, var_dir, output_dir)

    meta_path = output_dir / "parent" / "_meta.ts"
    content = meta_path.read_text()
    assert content.index("'folder': 'Folder'") < content.index("'page': 'Page'")
    assert entries == [{
        "page_id": "parent",
        "type": "page",
        "kind": "navigation",
        "path": "parent/_meta.ts",
    }]
    assert not (output_dir / "root" / "_meta.ts").exists()


def test_manifest_removes_only_previous_owned_outputs(tmp_path):
    output_dir = tmp_path / "output"
    manifest_path = (
        tmp_path / "var" / "convert-manifests" / "convert-manifest.qm.yaml"
    )
    stale = output_dir / "old" / "folder.mdx"
    manual = output_dir / "old" / "manual.txt"
    current = output_dir / "new" / "folder.mdx"
    stale.parent.mkdir(parents=True)
    current.parent.mkdir(parents=True)
    stale.write_text("old")
    manual.write_text("manual")
    current.write_text("new")
    _write_yaml(manifest_path, {
        "version": 1,
        "sync_code": "qm",
        "outputs": [{
            "page_id": "folder",
            "type": "folder",
            "kind": "mdx",
            "path": "old/folder.mdx",
        }],
    })
    current_outputs = [{
        "page_id": "folder",
        "type": "folder",
        "kind": "mdx",
        "path": "new/folder.mdx",
    }]

    finalize_manifest(manifest_path, "qm", current_outputs, output_dir)

    assert not stale.exists()
    assert manual.read_text() == "manual"
    assert current.read_text() == "new"
    assert yaml.safe_load(manifest_path.read_text())["outputs"] == current_outputs


def test_manifest_preserves_stale_output_owned_by_another_profile(tmp_path):
    output_dir = tmp_path / "output"
    manifest_dir = tmp_path / "var" / "convert-manifests"
    qm_manifest = manifest_dir / "convert-manifest.qm.yaml"
    qcp_manifest = manifest_dir / "convert-manifest.qcp.yaml"
    shared_output = output_dir / "shared" / "folder.mdx"
    shared_output.parent.mkdir(parents=True)
    shared_output.write_text("fresh QM output")
    owned_output = {
        "page_id": "qm-folder",
        "type": "folder",
        "kind": "mdx",
        "path": "shared/folder.mdx",
    }
    _write_yaml(qm_manifest, {
        "version": 1,
        "sync_code": "qm",
        "outputs": [owned_output],
    })
    _write_yaml(qcp_manifest, {
        "version": 1,
        "sync_code": "qcp",
        "outputs": [{
            **owned_output,
            "page_id": "old-qcp-folder",
        }],
    })

    finalize_manifest(qcp_manifest, "qcp", [], output_dir)

    assert shared_output.read_text() == "fresh QM output"
    assert yaml.safe_load(qcp_manifest.read_text())["outputs"] == []


def test_first_manifest_does_not_delete_untracked_existing_mdx(tmp_path):
    output_dir = tmp_path / "output"
    existing = output_dir / "legacy.mdx"
    existing.parent.mkdir(parents=True)
    existing.write_text("legacy")
    manifest_path = (
        tmp_path / "var" / "convert-manifests" / "convert-manifest.qm.yaml"
    )

    finalize_manifest(manifest_path, "qm", [], output_dir)

    assert existing.read_text() == "legacy"
    assert yaml.safe_load(manifest_path.read_text())["outputs"] == []


def test_manifest_rejects_path_outside_output_root(tmp_path):
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    outside = tmp_path / "outside.mdx"
    outside.write_text("keep")
    manifest_path = (
        tmp_path / "var" / "convert-manifests" / "convert-manifest.qm.yaml"
    )
    _write_yaml(manifest_path, {
        "version": 1,
        "sync_code": "qm",
        "outputs": [{
            "page_id": "folder",
            "type": "folder",
            "kind": "mdx",
            "path": "../outside.mdx",
        }],
    })

    with pytest.raises(ConversionError, match="escapes output root"):
        finalize_manifest(manifest_path, "qm", [], output_dir)

    assert outside.read_text() == "keep"


def test_manifest_rejects_different_sync_profile(tmp_path):
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    manifest_path = (
        tmp_path / "var" / "convert-manifests" / "convert-manifest.qm.yaml"
    )
    _write_yaml(manifest_path, {
        "version": 1,
        "sync_code": "qcp",
        "outputs": [],
    })

    with pytest.raises(ConversionError, match="sync_code mismatch"):
        finalize_manifest(manifest_path, "qm", [], output_dir)


def test_compose_persists_manifest_directory_for_atomic_replace():
    project_dir = Path(__file__).resolve().parents[1]
    compose = yaml.safe_load((project_dir / "compose.yml").read_text())
    volumes = compose["services"]["confluence-mdx"]["volumes"]
    manifest_mount = (
        "./var/convert-manifests:/workdir/var/convert-manifests"
    )

    assert manifest_mount in volumes
    for sync_code in ("qm", "qcp"):
        relative_path = (
            Path("var")
            / "convert-manifests"
            / f"convert-manifest.{sync_code}.yaml"
        )
        manifest = yaml.safe_load((project_dir / relative_path).read_text())
        assert manifest["sync_code"] == sync_code


def test_conversion_failure_preserves_previous_output_and_manifest(tmp_path):
    var_dir = tmp_path / "var"
    output_dir = tmp_path / "output"
    public_dir = tmp_path / "public"
    manifest_path = (
        var_dir / "convert-manifests" / "convert-manifest.qm.yaml"
    )
    previous_output = output_dir / "old.mdx"
    previous_output.parent.mkdir(parents=True)
    previous_output.write_text("old")
    previous_manifest = {
        "version": 1,
        "sync_code": "qm",
        "outputs": [{
            "page_id": "old",
            "type": "page",
            "kind": "mdx",
            "path": "old.mdx",
        }],
    }
    _write_yaml(manifest_path, previous_manifest)
    pages = [
        _node("root", "page", "Root", ["root"]),
        _node("missing", "page", "Missing", ["missing"]),
    ]

    failures = convert_all(
        pages,
        str(var_dir),
        str(output_dir),
        str(public_dir),
        "warning",
        manifest_path=str(manifest_path),
    )

    assert failures == 1
    assert previous_output.read_text() == "old"
    assert yaml.safe_load(manifest_path.read_text()) == previous_manifest


def test_convert_all_generates_folder_and_manifest(tmp_path):
    var_dir = tmp_path / "var"
    output_dir = tmp_path / "output"
    public_dir = tmp_path / "public"
    manifest_path = (
        var_dir / "convert-manifests" / "convert-manifest.qm.yaml"
    )
    root = _node("root", "page", "Root", ["root"])
    folder = _node("folder", "folder", "Folder", ["folder"])
    _write_yaml(var_dir / "folder" / "folder.v2.yaml", _folder_data(
        "folder",
        "Folder",
    ))
    _write_yaml(var_dir / "folder" / "children.v2.yaml", {"results": []})

    failures = convert_all(
        [root, folder],
        str(var_dir),
        str(output_dir),
        str(public_dir),
        "warning",
        manifest_path=str(manifest_path),
        sync_code="qm",
    )

    assert failures == 0
    assert (output_dir / "folder.mdx").is_file()
    manifest = yaml.safe_load(manifest_path.read_text())
    assert manifest["outputs"] == [{
        "page_id": "folder",
        "type": "folder",
        "kind": "mdx",
        "path": "folder.mdx",
    }]


def test_convert_all_generates_page_folder_and_central_navigation(tmp_path):
    var_dir = tmp_path / "var"
    output_dir = tmp_path / "output"
    public_dir = tmp_path / "public"
    manifest_path = (
        var_dir / "convert-manifests" / "convert-manifest.qm.yaml"
    )
    pages_yaml = var_dir / "pages.qm.yaml"
    root = _node("root", "page", "Root", ["root"])
    parent = _node("parent", "page", "Parent", ["parent"])
    folder = _node("folder", "folder", "Folder", ["parent", "folder"])
    pages = [root, parent, folder]
    _write_yaml(pages_yaml, pages)
    _write_yaml(var_dir / "parent" / "page.v1.yaml", {
        "id": "parent",
        "type": "page",
        "title": "Parent",
        "ancestors": [],
        "body": {},
        "_links": {
            "base": "https://querypie.atlassian.net/wiki",
            "webui": "/spaces/QM/pages/parent",
        },
    })
    (var_dir / "parent" / "page.xhtml").write_text(
        "<p>Parent body</p>",
        encoding="utf-8",
    )
    _write_yaml(var_dir / "parent" / "children.v2.yaml", {
        "results": [{
            "id": "folder",
            "type": "folder",
            "title": "Folder",
            "childPosition": 1,
        }],
    })
    _write_yaml(var_dir / "folder" / "folder.v2.yaml", _folder_data(
        "folder",
        "Folder",
    ))
    _write_yaml(var_dir / "folder" / "children.v2.yaml", {"results": []})

    failures = convert_all(
        pages,
        str(var_dir),
        str(output_dir),
        str(public_dir),
        "warning",
        pages_yaml=str(pages_yaml),
        manifest_path=str(manifest_path),
        sync_code="qm",
    )

    assert failures == 0
    assert (output_dir / "parent.mdx").is_file()
    assert (output_dir / "parent" / "folder.mdx").is_file()
    assert "'folder': 'Folder'" in (
        output_dir / "parent" / "_meta.ts"
    ).read_text()
    output_paths = {
        entry["path"]
        for entry in yaml.safe_load(manifest_path.read_text())["outputs"]
    }
    assert output_paths == {
        "parent.mdx",
        "parent/folder.mdx",
        "parent/_meta.ts",
    }


def test_reverse_sync_rejects_generated_folder_landing_page(tmp_path, monkeypatch):
    import reverse_sync_cli

    monkeypatch.setattr(reverse_sync_cli, "_PROJECT_DIR", tmp_path)
    _write_yaml(tmp_path / "var" / "pages.qm.yaml", [{
        "page_id": "folder",
        "type": "folder",
        "path": ["admin", "folder"],
    }])

    with pytest.raises(ValueError, match="cannot be reverse-synced"):
        reverse_sync_cli._ensure_reverse_sync_page("folder")

    with pytest.raises(ValueError, match="cannot be reverse-synced"):
        reverse_sync_cli._resolve_page_id(
            "src/content/ko/admin/folder.mdx"
        )

    with pytest.raises(ValueError, match="cannot be reverse-synced"):
        reverse_sync_cli._do_verify(Namespace(
            improved_mdx="unused.mdx",
            original_mdx=None,
            page_id="folder",
            page_dir=None,
            lenient=False,
            no_normalize=False,
        ))
