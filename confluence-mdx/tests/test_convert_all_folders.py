import subprocess
from argparse import Namespace
from datetime import date
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
from content_redirects import reconcile_content_redirects


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
            {
                "id": "draft-page",
                "type": "page",
                "status": "draft",
                "title": "Draft Page",
                "childPosition": 3,
            },
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
    assert "Draft Page" not in content
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
    assert manifest_path.stat().st_mode & 0o777 == 0o644


def test_manifest_records_route_move_with_eight_week_redirect(tmp_path):
    output_dir = tmp_path / "output"
    manifest_path = (
        tmp_path / "var" / "convert-manifests" / "convert-manifest.qm.yaml"
    )
    redirects_path = tmp_path / "content-redirects.yaml"
    old_output = output_dir / "support" / "old-title.mdx"
    new_output = output_dir / "support" / "new-title.mdx"
    old_output.parent.mkdir(parents=True)
    old_output.write_text("old", encoding="utf-8")
    new_output.write_text("new", encoding="utf-8")
    _write_yaml(manifest_path, {
        "version": 1,
        "sync_code": "qm",
        "outputs": [{
            "page_id": "page-1",
            "type": "page",
            "kind": "mdx",
            "path": "support/old-title.mdx",
        }],
    })
    _write_yaml(redirects_path, [])
    current_outputs = [{
        "page_id": "page-1",
        "type": "page",
        "kind": "mdx",
        "path": "support/new-title.mdx",
    }]

    finalize_manifest(
        manifest_path,
        "qm",
        current_outputs,
        output_dir,
        redirects_path,
        date(2026, 7, 28),
    )

    assert not old_output.exists()
    assert yaml.safe_load(redirects_path.read_text()) == [{
        "source": "/support/old-title",
        "destination": "/support/new-title",
        "created_on": "2026-07-28",
        "expires_on": "2026-09-22",
    }]


def test_manifest_prunes_expired_redirects(tmp_path):
    output_dir = tmp_path / "output"
    manifest_path = (
        tmp_path / "var" / "convert-manifests" / "convert-manifest.qm.yaml"
    )
    redirects_path = tmp_path / "content-redirects.yaml"
    current_output = output_dir / "current.mdx"
    current_output.parent.mkdir(parents=True)
    current_output.write_text("current", encoding="utf-8")
    output = {
        "page_id": "page-1",
        "type": "page",
        "kind": "mdx",
        "path": "current.mdx",
    }
    _write_yaml(manifest_path, {
        "version": 1,
        "sync_code": "qm",
        "outputs": [output],
    })
    _write_yaml(redirects_path, [
        {
            "source": "/expired",
            "destination": "/current",
            "created_on": "2026-05-01",
            "expires_on": "2026-06-26",
        },
        {
            "source": "/active",
            "destination": "/current",
            "created_on": "2026-07-01",
            "expires_on": "2026-08-26",
        },
    ])

    finalize_manifest(
        manifest_path,
        "qm",
        [output],
        output_dir,
        redirects_path,
        date(2026, 7, 28),
    )

    assert yaml.safe_load(redirects_path.read_text()) == [{
        "source": "/active",
        "destination": "/current",
        "created_on": "2026-07-01",
        "expires_on": "2026-08-26",
    }]


def test_consecutive_route_moves_collapse_redirect_chain():
    redirects = reconcile_content_redirects(
        [{
            "source": "/title-a",
            "destination": "/title-b",
            "created_on": "2026-07-01",
            "expires_on": "2026-08-26",
        }],
        [{
            "page_id": "page-1",
            "type": "page",
            "kind": "mdx",
            "path": "title-b.mdx",
        }],
        [{
            "page_id": "page-1",
            "type": "page",
            "kind": "mdx",
            "path": "title-c.mdx",
        }],
        date(2026, 7, 28),
    )

    assert redirects == [
        {
            "source": "/title-a",
            "destination": "/title-c",
            "created_on": "2026-07-01",
            "expires_on": "2026-08-26",
        },
        {
            "source": "/title-b",
            "destination": "/title-c",
            "created_on": "2026-07-28",
            "expires_on": "2026-09-22",
        },
    ]


@pytest.mark.parametrize(
    ("content_a_id", "content_b_id"),
    [
        ("page-1", "page-2"),
        ("page-2", "page-1"),
    ],
)
def test_route_reuse_preserves_redirect_created_in_same_pass(
    content_a_id,
    content_b_id,
):
    redirects = reconcile_content_redirects(
        [],
        [
            {
                "page_id": content_a_id,
                "type": "page",
                "kind": "mdx",
                "path": "title-a.mdx",
            },
            {
                "page_id": content_b_id,
                "type": "page",
                "kind": "mdx",
                "path": "title-b.mdx",
            },
        ],
        [
            {
                "page_id": content_a_id,
                "type": "page",
                "kind": "mdx",
                "path": "title-b.mdx",
            },
            {
                "page_id": content_b_id,
                "type": "page",
                "kind": "mdx",
                "path": "title-c.mdx",
            },
        ],
        date(2026, 7, 28),
    )

    assert redirects == [{
        "source": "/title-a",
        "destination": "/title-b",
        "created_on": "2026-07-28",
        "expires_on": "2026-09-22",
    }]


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


def test_convert_all_rejects_current_cross_profile_collision_before_write(
    tmp_path,
    capsys,
):
    var_dir = tmp_path / "var"
    output_dir = tmp_path / "output"
    public_dir = tmp_path / "public"
    manifest_dir = var_dir / "convert-manifests"
    qm_manifest = manifest_dir / "convert-manifest.qm.yaml"
    qcp_manifest = manifest_dir / "convert-manifest.qcp.yaml"
    qm_root = _node("qm-root", "page", "QM Root", ["qm-root"])
    qm_folder = _node(
        "qm-folder",
        "folder",
        "QM Folder",
        ["shared", "folder"],
    )
    qcp_pages = [
        _node("qcp-root", "folder", "QCP Root", ["qcp-root"]),
        _node(
            "qcp-folder",
            "folder",
            "QCP Folder",
            ["shared", "folder"],
        ),
    ]
    _write_yaml(var_dir / "pages.qcp.yaml", qcp_pages)
    _write_yaml(
        var_dir / "qm-folder" / "children.v2.yaml",
        {"results": []},
    )
    _write_yaml(
        var_dir / "qcp-folder" / "children.v2.yaml",
        {"results": []},
    )
    existing_output = output_dir / "shared" / "folder.mdx"
    existing_output.parent.mkdir(parents=True)
    existing_output.write_text("QCP output", encoding="utf-8")
    _write_yaml(qcp_manifest, {
        "version": 1,
        "sync_code": "qcp",
        "outputs": [{
            "page_id": "qcp-folder",
            "type": "folder",
            "kind": "mdx",
            "path": "shared/folder.mdx",
        }],
    })

    failures = convert_all(
        [qm_root, qm_folder],
        str(var_dir),
        str(output_dir),
        str(public_dir),
        "warning",
        manifest_path=str(qm_manifest),
        sync_code="qm",
    )

    assert failures == 1
    assert existing_output.read_text(encoding="utf-8") == "QCP output"
    assert not qm_manifest.exists()
    assert "Current output path collision" in capsys.readouterr().err


def test_convert_all_allows_ownership_transfer_after_sibling_catalog_update(
    tmp_path,
):
    var_dir = tmp_path / "var"
    output_dir = tmp_path / "output"
    public_dir = tmp_path / "public"
    manifest_dir = var_dir / "convert-manifests"
    qm_manifest = manifest_dir / "convert-manifest.qm.yaml"
    qcp_manifest = manifest_dir / "convert-manifest.qcp.yaml"
    qm_root = _node("qm-root", "page", "QM Root", ["qm-root"])
    qm_folder = _node(
        "qm-folder",
        "folder",
        "QM Folder",
        ["shared", "folder"],
    )
    _write_yaml(
        var_dir / "pages.qcp.yaml",
        [_node("qcp-root", "folder", "QCP Root", ["qcp-root"])],
    )
    _write_yaml(
        var_dir / "qm-folder" / "folder.v2.yaml",
        _folder_data("qm-folder", "QM Folder"),
    )
    _write_yaml(
        var_dir / "qm-folder" / "children.v2.yaml",
        {"results": []},
    )
    _write_yaml(qcp_manifest, {
        "version": 1,
        "sync_code": "qcp",
        "outputs": [{
            "page_id": "old-qcp-folder",
            "type": "folder",
            "kind": "mdx",
            "path": "shared/folder.mdx",
        }],
    })

    failures = convert_all(
        [qm_root, qm_folder],
        str(var_dir),
        str(output_dir),
        str(public_dir),
        "warning",
        manifest_path=str(qm_manifest),
        sync_code="qm",
    )

    assert failures == 0
    assert "# QM Folder" in (
        output_dir / "shared" / "folder.mdx"
    ).read_text(encoding="utf-8")
    assert {
        entry["path"]
        for entry in yaml.safe_load(qm_manifest.read_text())["outputs"]
    } == {"shared/folder.mdx"}


def test_full_all_fetches_all_catalogs_before_any_conversion(
    tmp_path,
    monkeypatch,
):
    project_dir = Path(__file__).resolve().parents[1]
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    container_workdir = tmp_path / "workdir"
    (container_workdir / "var").mkdir(parents=True)
    entrypoint_path = tmp_path / "entrypoint.sh"
    entrypoint_path.write_text(
        (project_dir / "scripts" / "entrypoint.sh")
        .read_text(encoding="utf-8")
        .replace("/workdir", str(container_workdir)),
        encoding="utf-8",
    )
    calls_path = tmp_path / "calls.log"
    for command, label in (
        ("fetch_cli.py", "fetch"),
        ("convert_all.py", "convert"),
    ):
        command_path = bin_dir / command
        command_path.write_text(
            "#!/bin/bash\n"
            f'echo "{label} $*" >> "$CALLS_PATH"\n',
            encoding="utf-8",
        )
        command_path.chmod(0o755)
    monkeypatch.setenv("CALLS_PATH", str(calls_path))

    subprocess.run(
        ["bash", str(entrypoint_path), "full-all"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )

    assert calls_path.read_text(encoding="utf-8").splitlines() == [
        "fetch --sync-code qm",
        "fetch --sync-code qcp",
        "convert --sync-code qm",
        "convert --sync-code qcp",
    ]


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
