"""Confluence API 클라이언트 — 일관된 snapshot과 version-bound update."""
from pathlib import Path

import requests
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Any, Tuple

from reverse_sync.models import PageSnapshot, ReasonCode

CONFIG_FILE = Path.home() / '.config' / 'atlassian' / 'confluence.conf'


def _load_credentials() -> Tuple[str, str]:
    """~/.config/atlassian/confluence.conf 에서 인증 정보를 로드한다."""
    if CONFIG_FILE.exists():
        line = CONFIG_FILE.read_text().strip().split('\n')[0]
        if ':' in line:
            email, token = line.split(':', 1)
            return email, token
    return '', ''


@dataclass
class ConfluenceConfig:
    base_url: str = "https://querypie.atlassian.net/wiki"
    email: str = ''
    api_token: str = ''
    timeout_seconds: float = 30.0

    def __post_init__(self):
        if not self.email or not self.api_token:
            self.email, self.api_token = _load_credentials()


class ConfluenceClientError(RuntimeError):
    """Confluence provider error의 공통 기반."""

    reason_code = ReasonCode.NETWORK_ERROR.value


class InvalidPageSnapshotError(ConfluenceClientError):
    reason_code = ReasonCode.INVALID_PAGE_SNAPSHOT.value


class VersionConflictError(ConfluenceClientError):
    reason_code = ReasonCode.VERSION_CONFLICT.value


class PermissionDeniedError(ConfluenceClientError):
    reason_code = ReasonCode.PERMISSION_DENIED.value


class NetworkError(ConfluenceClientError):
    reason_code = ReasonCode.NETWORK_ERROR.value


def _raise_mapped_http_error(exc: requests.HTTPError, *, update: bool = False) -> None:
    status = exc.response.status_code if exc.response is not None else None
    if status == 409 or (update and status == 400):
        raise VersionConflictError("Confluence page version conflict") from exc
    if status in (401, 403):
        raise PermissionDeniedError("Confluence page 접근 권한이 없습니다") from exc
    raise NetworkError(f"Confluence API 요청이 실패했습니다 (HTTP {status})") from exc


def _request_json(method: str, url: str, config: ConfluenceConfig, **kwargs) -> Dict[str, Any]:
    try:
        kwargs.setdefault("timeout", config.timeout_seconds)
        response = requests.request(
            method,
            url,
            auth=(config.email, config.api_token),
            headers={
                "Accept": "application/json",
                **kwargs.pop("headers", {}),
            },
            **kwargs,
        )
        response.raise_for_status()
        return response.json()
    except requests.HTTPError as exc:
        _raise_mapped_http_error(exc, update=method.upper() == "PUT")
    except (requests.RequestException, ValueError) as exc:
        raise NetworkError("Confluence API 응답을 읽지 못했습니다") from exc


def _parse_page_snapshot(
    data: Dict[str, Any],
    page_id: str,
    *,
    expected_status: str,
    fetched_at: datetime,
) -> PageSnapshot:
    try:
        response_page_id = str(data["id"])
        status = data["status"]
        title = data["title"]
        version = data["version"]["number"]
        storage = data["body"]["storage"]
        representation = storage["representation"]
        storage_xhtml = storage["value"]
    except (KeyError, TypeError) as exc:
        raise InvalidPageSnapshotError(
            f"페이지 {page_id} snapshot의 필수 field가 없습니다"
        ) from exc

    invalid = (
        response_page_id != str(page_id)
        or status != expected_status
        or representation != "storage"
        or not isinstance(title, str)
        or not title
        or not isinstance(version, int)
        or version < 1
        or not isinstance(storage_xhtml, str)
    )
    if invalid:
        raise InvalidPageSnapshotError(
            f"페이지 {page_id} snapshot identity/representation이 올바르지 않습니다"
        )

    return PageSnapshot(
        page_id=response_page_id,
        status=status,
        title=title,
        version=version,
        storage_xhtml=storage_xhtml,
        fetched_at=fetched_at.astimezone(timezone.utc).isoformat(),
        api="confluence-v2",
    )


def get_page_snapshot(
    config: ConfluenceConfig,
    page_id: str,
    *,
    fetched_at: datetime | None = None,
) -> PageSnapshot:
    """version/title/Storage body를 하나의 v2 response에서 획득한다."""
    url = f"{config.base_url}/api/v2/pages/{page_id}"
    captured_at = fetched_at or datetime.now(timezone.utc)
    try:
        response = requests.get(
            url,
            params={
                "body-format": "storage",
                "status": ["current"],
                "include-version": True,
            },
            auth=(config.email, config.api_token),
            headers={"Accept": "application/json"},
            timeout=config.timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
    except requests.HTTPError as exc:
        _raise_mapped_http_error(exc)
    except (requests.RequestException, ValueError) as exc:
        raise NetworkError("Confluence page snapshot을 읽지 못했습니다") from exc
    return _parse_page_snapshot(
        data,
        page_id,
        expected_status="current",
        fetched_at=captured_at,
    )


def get_active_draft(
    config: ConfluenceConfig,
    page_id: str,
    *,
    fetched_at: datetime | None = None,
) -> PageSnapshot | None:
    """active draft가 있으면 draft snapshot을 반환하고, 없으면 None을 반환한다."""
    url = f"{config.base_url}/api/v2/pages/{page_id}"
    captured_at = fetched_at or datetime.now(timezone.utc)
    try:
        response = requests.get(
            url,
            params={
                "body-format": "storage",
                "get-draft": True,
                "status": ["draft"],
                "include-version": True,
            },
            auth=(config.email, config.api_token),
            headers={"Accept": "application/json"},
            timeout=config.timeout_seconds,
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json()
    except requests.HTTPError as exc:
        _raise_mapped_http_error(exc)
    except (requests.RequestException, ValueError) as exc:
        raise NetworkError("Confluence draft snapshot을 읽지 못했습니다") from exc

    if data.get("status") != "draft":
        return None
    return _parse_page_snapshot(
        data,
        page_id,
        expected_status="draft",
        fetched_at=captured_at,
    )


def update_page(
    config: ConfluenceConfig,
    page_id: str,
    *,
    title: str,
    version: int,
    xhtml_body: str,
) -> Dict[str, Any]:
    """base version + 1로 Storage body를 한 번만 갱신한다."""
    url = f"{config.base_url}/api/v2/pages/{page_id}"
    payload = {
        "id": str(page_id),
        "status": "current",
        "title": title,
        "body": {
            "representation": "storage",
            "value": xhtml_body,
        },
        "version": {"number": version},
    }
    return _request_json(
        "PUT",
        url,
        config,
        json=payload,
        headers={"Content-Type": "application/json"},
    )


class ConfluenceGateway:
    """publisher가 사용하는 Confluence adapter."""

    def __init__(self, config: ConfluenceConfig):
        self.config = config

    def get_current_page(self, page_id: str) -> PageSnapshot:
        return get_page_snapshot(self.config, page_id)

    def get_active_draft(self, page_id: str) -> PageSnapshot | None:
        return get_active_draft(self.config, page_id)

    def update_page(
        self,
        page_id: str,
        *,
        title: str,
        version: int,
        xhtml_body: str,
    ) -> Dict[str, Any]:
        return update_page(
            self.config,
            page_id,
            title=title,
            version=version,
            xhtml_body=xhtml_body,
        )
