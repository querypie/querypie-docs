import logging
from pathlib import Path

import pytest
import yaml

from fetch.api_client import ApiClient
from fetch.config import Config
from fetch.exceptions import ApiError
from fetch.file_manager import FileManager
from fetch.processor import ConfluencePageProcessor
from fetch.stages import Stage1Processor


def _config(tmp_path: Path, *, mode: str = "local", root_type: str = "page") -> Config:
    return Config(
        base_url="https://example.atlassian.net/wiki",
        default_output_dir=str(tmp_path / "var"),
        cache_dir=str(tmp_path / "cache"),
        translations_file=str(tmp_path / "translations.txt"),
        default_start_page_id="root",
        root_content_type=root_type,
        mode=mode,
    )


def _write_yaml(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def _page_data(page_id: str, title: str) -> dict:
    return {
        "id": page_id,
        "type": "page",
        "title": title,
        "ancestors": [],
        "body": {},
    }


def test_make_request_normalizes_link_header_next_into_response_body(
    tmp_path,
    monkeypatch,
):
    client = ApiClient(_config(tmp_path), logging.getLogger(__name__))

    class FakeResponse:
        links = {
            "next": {
                "url": (
                    "https://example.atlassian.net/wiki/api/v2/pages/root/"
                    "direct-children?cursor=next"
                ),
            },
        }

        def raise_for_status(self):
            return None

        def json(self):
            return {"results": [], "_links": {}}

    monkeypatch.setattr("fetch.api_client.requests.get", lambda *args, **kwargs: FakeResponse())

    result = client.make_request("https://example.test", "test")

    assert result["_links"]["next"].endswith("cursor=next")


def test_direct_children_uses_page_endpoint_and_merges_cursor_pages(
    tmp_path,
    monkeypatch,
):
    client = ApiClient(_config(tmp_path), logging.getLogger(__name__))
    requested_urls = []
    responses = [
        {
            "results": [{"id": "a", "type": "page"}],
            "_links": {"next": "/wiki/api/v2/pages/root/direct-children?cursor=next"},
        },
        {
            "results": [{"id": "b", "type": "folder"}],
            "_links": {},
        },
    ]

    def fake_request(url, description):
        requested_urls.append((url, description))
        return responses.pop(0)

    monkeypatch.setattr(client, "make_request", fake_request)

    result = client.get_direct_children("root", "page")

    assert [item["id"] for item in result["results"]] == ["a", "b"]
    assert "next" not in result["_links"]
    assert requested_urls == [
        (
            "https://example.atlassian.net/wiki/api/v2/pages/root/direct-children?limit=100",
            "V2 API direct children",
        ),
        (
            "https://example.atlassian.net/wiki/api/v2/pages/root/direct-children?cursor=next",
            "V2 API direct children",
        ),
    ]


def test_direct_children_uses_folder_endpoint(tmp_path, monkeypatch):
    client = ApiClient(_config(tmp_path), logging.getLogger(__name__))
    requested_urls = []

    def fake_request(url, description):
        requested_urls.append(url)
        return {"results": [], "_links": {}}

    monkeypatch.setattr(client, "make_request", fake_request)

    assert client.get_direct_children("folder-1", "folder")["results"] == []
    assert requested_urls == [
        "https://example.atlassian.net/wiki/api/v2/folders/folder-1/direct-children?limit=100"
    ]


class _FolderApi:
    def __init__(self, *, fail_children: bool = False):
        self.fail_children = fail_children
        self.direct_children_calls = 0

    def get_page_data_v2(self, page_id, content_type="page"):
        assert content_type == "folder"
        return {
            "id": page_id,
            "type": "folder",
            "title": "Folder",
            "_links": {"webui": f"/spaces/QM/folder/{page_id}"},
        }

    def get_direct_children(self, page_id, content_type="page"):
        self.direct_children_calls += 1
        if self.fail_children:
            raise ApiError("pagination failed")
        return {"results": [], "_links": {}}


def test_stage1_folder_writes_only_folder_metadata_and_children(tmp_path):
    config = _config(tmp_path, mode="remote", root_type="folder")
    api = _FolderApi()
    stage = Stage1Processor(
        config,
        api,
        FileManager(logging.getLogger(__name__)),
        logging.getLogger(__name__),
    )

    stage.process("folder-1", "folder")

    folder_dir = Path(config.default_output_dir) / "folder-1"
    assert sorted(path.name for path in folder_dir.iterdir()) == [
        "children.v2.yaml",
        "folder.v2.yaml",
    ]


def test_stage1_preserves_previous_children_when_pagination_fails(tmp_path):
    config = _config(tmp_path, mode="remote", root_type="folder")
    folder_dir = Path(config.default_output_dir) / "folder-1"
    previous = {"results": [{"id": "old", "type": "page"}]}
    _write_yaml(folder_dir / "children.v2.yaml", previous)
    stage = Stage1Processor(
        config,
        _FolderApi(fail_children=True),
        FileManager(logging.getLogger(__name__)),
        logging.getLogger(__name__),
    )

    with pytest.raises(ApiError, match="pagination failed"):
        stage.process("folder-1", "folder")

    assert yaml.safe_load((folder_dir / "children.v2.yaml").read_text()) == previous


class _RecentPageApi:
    def __init__(self):
        self.direct_children_calls = 0

    def get_page_data_v1(self, page_id):
        return _page_data(page_id, "Page")

    def get_page_data_v2(self, page_id, content_type="page"):
        return {"id": page_id, "type": "page", "title": "Page"}

    def get_attachments(self, page_id):
        return {"results": []}

    def get_direct_children(self, page_id, content_type="page"):
        self.direct_children_calls += 1
        return {"results": []}


def test_recent_page_fetch_does_not_refresh_children_snapshot(tmp_path):
    config = _config(tmp_path, mode="recent")
    api = _RecentPageApi()
    page_dir = Path(config.default_output_dir) / "page-1"
    previous = {"results": [{"id": "cached-child"}]}
    _write_yaml(page_dir / "children.v2.yaml", previous)
    stage = Stage1Processor(
        config,
        api,
        FileManager(logging.getLogger(__name__)),
        logging.getLogger(__name__),
    )

    stage.process("page-1", "page", include_children=False)

    assert api.direct_children_calls == 0
    assert yaml.safe_load((page_dir / "children.v2.yaml").read_text()) == previous


def test_local_mixed_tree_preserves_types_paths_order_and_warns(
    tmp_path,
    caplog,
):
    config = _config(tmp_path, mode="local")
    var_dir = Path(config.default_output_dir)

    _write_yaml(var_dir / "root" / "page.v1.yaml", _page_data("root", "Root"))
    _write_yaml(var_dir / "root" / "page.v2.yaml", {"id": "root", "title": "Root"})
    _write_yaml(var_dir / "root" / "children.v2.yaml", {
        "results": [
            {
                "id": "folder",
                "type": "folder",
                "title": "Folder",
                "childPosition": 1,
            },
        ],
    })

    _write_yaml(var_dir / "folder" / "folder.v2.yaml", {
        "id": "folder",
        "type": "folder",
        "title": "Folder",
    })
    _write_yaml(var_dir / "folder" / "children.v2.yaml", {
        "results": [
            {
                "id": "page-a",
                "type": "page",
                "title": "Page A",
                "childPosition": 2,
            },
            {
                "id": "nested",
                "type": "folder",
                "title": "Nested",
                "childPosition": 1,
            },
            {
                "id": "board",
                "type": "whiteboard",
                "title": "Board",
                "childPosition": 3,
            },
            {
                "id": "database",
                "type": "database",
                "title": "Database",
                "childPosition": 4,
            },
            {
                "id": "embed",
                "type": "embed",
                "title": "Embed",
                "childPosition": 5,
            },
        ],
    })

    _write_yaml(var_dir / "nested" / "folder.v2.yaml", {
        "id": "nested",
        "type": "folder",
        "title": "Nested",
    })
    _write_yaml(var_dir / "nested" / "children.v2.yaml", {
        "results": [
            {
                "id": "page-b",
                "type": "page",
                "title": "Page B",
                "childPosition": 1,
            },
        ],
    })

    for page_id, title in (("page-a", "Page A"), ("page-b", "Page B")):
        _write_yaml(var_dir / page_id / "page.v1.yaml", _page_data(page_id, title))
        _write_yaml(var_dir / page_id / "page.v2.yaml", {
            "id": page_id,
            "type": "page",
            "title": title,
        })
        _write_yaml(var_dir / page_id / "children.v2.yaml", {"results": []})

    processor = ConfluencePageProcessor(config, logging.getLogger(__name__))
    with caplog.at_level(logging.WARNING):
        nodes = list(processor.fetch_page_tree_recursive(
            "root",
            "root",
            use_local=True,
            content_type="page",
        ))

    assert [node.page_id for node in nodes] == [
        "root",
        "folder",
        "nested",
        "page-b",
        "page-a",
    ]
    assert [node.content_type for node in nodes] == [
        "page",
        "folder",
        "folder",
        "page",
        "page",
    ]
    assert nodes[1].breadcrumbs == ["Folder"]
    assert nodes[2].breadcrumbs == ["Folder", "Nested"]
    assert nodes[3].path == ["folder", "nested", "page-b"]
    assert "type=whiteboard" in caplog.text
    assert "type=database" in caplog.text
    assert "type=embed" in caplog.text


class _RemoteTreeApi:
    def __init__(self):
        self.v2_calls = []
        self.children_calls = []

    def get_page_data_v1(self, page_id):
        return _page_data(page_id, {"root": "Root", "page": "Page"}[page_id])

    def get_page_data_v2(self, page_id, content_type="page"):
        self.v2_calls.append((page_id, content_type))
        if content_type == "folder":
            return {
                "id": page_id,
                "type": "folder",
                "title": "Folder",
                "_links": {"webui": f"/spaces/QM/folder/{page_id}"},
            }
        return {
            "id": page_id,
            "type": "page",
            "title": {"root": "Root", "page": "Page"}[page_id],
        }

    def get_attachments(self, page_id):
        return {"results": []}

    def get_direct_children(self, page_id, content_type="page"):
        self.children_calls.append((page_id, content_type))
        if page_id == "root":
            return {"results": [{
                "id": "folder",
                "type": "folder",
                "title": "Folder",
                "childPosition": 1,
            }]}
        if page_id == "folder":
            return {"results": [{
                "id": "page",
                "type": "page",
                "title": "Page",
                "childPosition": 1,
            }]}
        return {"results": []}


def test_remote_tree_routes_new_non_root_folder_to_folder_api(tmp_path):
    config = _config(tmp_path, mode="remote")
    processor = ConfluencePageProcessor(config, logging.getLogger(__name__))
    api = _RemoteTreeApi()
    processor.api_client = api
    for stage in (
        processor.stage1,
        processor.stage2,
        processor.stage3,
        processor.stage4,
    ):
        stage.api_client = api

    nodes = list(processor.fetch_page_tree_recursive(
        "root",
        "root",
        use_local=False,
        content_type="page",
    ))

    assert [node.page_id for node in nodes] == ["root", "folder", "page"]
    assert ("folder", "folder") in api.v2_calls
    assert api.children_calls == [
        ("root", "page"),
        ("folder", "folder"),
        ("page", "page"),
    ]
    folder_dir = Path(config.default_output_dir) / "folder"
    assert (folder_dir / "folder.v2.yaml").is_file()
    assert (folder_dir / "children.v2.yaml").is_file()
    assert not (folder_dir / "page.v1.yaml").exists()
