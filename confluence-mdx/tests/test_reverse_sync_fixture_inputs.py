import yaml
from pathlib import Path

from converter.context import build_link_mapping


def test_862093313_page_v1_contains_external_page_link_mapping():
    fixture = (
        Path(__file__).resolve().parent
        / "reverse-sync"
        / "862093313"
        / "page.v1.yaml"
    )
    page_v1 = yaml.safe_load(fixture.read_text(encoding="utf-8"))

    link_map = build_link_mapping(page_v1)

    assert link_map["Supported 3rd Party Tools (KO)"] == "919404587"
