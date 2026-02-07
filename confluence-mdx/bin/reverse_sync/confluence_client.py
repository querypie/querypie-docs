"""Confluence API 클라이언트 — reverse sync push용."""
import os

import requests
from dataclasses import dataclass, field
from typing import Dict, Any


def _env(key: str) -> str:
    return os.environ.get(key, '')


@dataclass
class ConfluenceConfig:
    base_url: str = "https://querypie.atlassian.net/wiki"
    email: str = field(default_factory=lambda: _env('ATLASSIAN_USERNAME'))
    api_token: str = field(default_factory=lambda: _env('ATLASSIAN_API_TOKEN'))


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
