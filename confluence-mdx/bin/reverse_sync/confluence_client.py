"""Confluence API 클라이언트 — reverse sync push용."""
from pathlib import Path

import requests
from dataclasses import dataclass
from typing import Dict, Any, Tuple

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

    def __post_init__(self):
        if not self.email or not self.api_token:
            self.email, self.api_token = _load_credentials()


def get_page_version(config: ConfluenceConfig, page_id: str) -> Dict[str, Any]:
    """페이지의 현재 version number와 title을 조회한다."""
    url = f"{config.base_url}/rest/api/content/{page_id}?expand=version"
    resp = requests.get(url, auth=(config.email, config.api_token),
                        headers={"Accept": "application/json"})
    resp.raise_for_status()
    data = resp.json()
    return {
        'version': data['version']['number'],
        'title': data['title'],
    }


def update_page_body(config: ConfluenceConfig, page_id: str,
                     title: str, version: int, xhtml_body: str) -> Dict[str, Any]:
    """페이지의 body를 업데이트한다."""
    url = f"{config.base_url}/rest/api/content/{page_id}"
    payload = {
        "type": "page",
        "title": title,
        "version": {"number": version},
        "body": {
            "storage": {
                "value": xhtml_body,
                "representation": "storage",
            }
        },
    }
    resp = requests.put(url, json=payload, auth=(config.email, config.api_token),
                        headers={"Content-Type": "application/json",
                                 "Accept": "application/json"})
    resp.raise_for_status()
    return resp.json()
