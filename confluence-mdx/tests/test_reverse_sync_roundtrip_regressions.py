import shutil
from pathlib import Path

import pytest

from reverse_sync_cli import MdxSource, run_verify


THIS_FILE = Path(__file__).resolve()
CONFLUENCE_DIR = THIS_FILE.parents[1]
REPO_ROOT = THIS_FILE.parents[2]


def _prepare_real_roundtrip_env(monkeypatch, tmp_path, page_id: str) -> Path:
    """실제 var/<page_id> + pages.yaml을 tmp_path로 복사한다."""
    src_var_page = CONFLUENCE_DIR / "var" / page_id
    src_pages_yaml = CONFLUENCE_DIR / "var" / "pages.yaml"
    if not src_var_page.exists():
        pytest.skip(f"var/{page_id} not found")
    if not src_pages_yaml.exists():
        pytest.skip("var/pages.yaml not found")

    monkeypatch.chdir(tmp_path)
    dest_var_root = tmp_path / "var"
    dest_var_root.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_pages_yaml, dest_var_root / "pages.yaml")
    shutil.copytree(src_var_page, dest_var_root / page_id)

    # run_verify가 tmp_path/var를 사용하도록 강제
    monkeypatch.setattr("reverse_sync_cli._PROJECT_DIR", tmp_path)
    return dest_var_root / page_id


def _load_repo_mdx(rel_path: str) -> str:
    path = REPO_ROOT / rel_path
    if not path.exists():
        pytest.skip(f"MDX not found: {rel_path}")
    return path.read_text()


CASES = [
    {
        "type": "type4_empty_strong",
        "page_id": "543948978",
        "mdx_path": "src/content/ko/administrator-manual/general/company-management.mdx",
        "old": (
            "* [ **General** ](company-management/general) **:** 쿼리파이의 기본 시스템 설정을 적용하는 메뉴입니다. \n"
            "* [ **Security** ](company-management/security) : 쿼리파이의 보안 설정을 적용하는 메뉴입니다. \n"
            "* [ **Allowed Zones** ](company-management/allowed-zones) **** : 쿼리파이의 허용 네트워크 존 설정을 구성하는 메뉴입니다. \n"
            "* [ **Channels** ](company-management/channels) : 쿼리파이의 알림을 받을 채널을 구성하는 메뉴입니다.\n"
            "* [ **Alerts** ](company-management/alerts) : 쿼리파이 알림을 설정하는 메뉴입니다. \n"
        ),
        "new": (
            "* [ **General** ](company-management/general) **:** 쿼리파이의 기본 시스템 설정을 적용하는 메뉴입니다. \n"
            "* [ **Security** ](company-management/security) : 쿼리파이의 보안 설정을 적용하는 메뉴입니다. \n"
            "* [ **Allowed Zones** ](company-management/allowed-zones) : 쿼리파이의 허용 네트워크 존 설정을 구성하는 메뉴입니다. \n"
            "* [ **Channels** ](company-management/channels) : 쿼리파이의 알림을 받을 채널을 구성하는 메뉴입니다.\n"
            "* [ **Alerts** ](company-management/alerts) : 쿼리파이 알림을 설정하는 메뉴입니다. \n"
        ),
        "markers": ["Allowed Zones", "****"],
        "status": "fail",
    },
    {
        "type": "type5_nested_list_break",
        "page_id": "544383693",
        "mdx_path": "src/content/ko/administrator-manual/audit/kubernetes-logs/pod-session-recordings.mdx",
        "old": (
            "3. 녹화된 파일의 크기가 700MB를 초과 여부에 따라 재생화면을 노출하거나 다운로드 버튼을 노출합니다. \n"
            "    1.  **700MB 미만**  \n"
            "      <figure data-layout=\"center\" data-align=\"center\">\n"
            "      <img src=\"/administrator-manual/audit/kubernetes-logs/pod-session-recordings/image-20240721-082651.png\" alt=\"image-20240721-082651.png\" width=\"440\" />\n"
            "      </figure>\n"
        ),
        "new": (
            "3. 녹화된 파일의 크기가 700MB를 초과 여부에 따라 재생화면을 노출하거나 다운로드 버튼을 노출합니다. \n"
            "    1.  **700MB 미만 (권장)**  \n"
            "      <figure data-layout=\"center\" data-align=\"center\">\n"
            "      <img src=\"/administrator-manual/audit/kubernetes-logs/pod-session-recordings/image-20240721-082651.png\" alt=\"image-20240721-082651.png\" width=\"440\" />\n"
            "      </figure>\n"
        ),
        "markers": ["700MB", "****"],
        "status": "fail",
    },
    {
        "type": "type6_callout_parser_error",
        "page_id": "571277650",
        "mdx_path": "src/content/ko/administrator-manual/databases/ledger-management/ledger-approval-rules.mdx",
        "old": (
            "### Overview\n\n"
            "관리자는 원장 테이블에 맵핑할 ‘원장 전용 승인 규칙(Ledger Approval Rule)’을 정의할 수 있습니다.\n\n"
            "### 원장 테이블에 승인 규칙 생성하기\n\n"
            "원장 테이블 정책 적용 시 강제화할 승인 규칙을 별도로 생성하고 관리할 수 있습니다.\n"
        ),
        "new": (
            "### Overview\n\n"
            "관리자는 원장 테이블에 맵핑할 ‘원장 전용 승인 규칙(Ledger Approval Rule)’을 정의하고 운영할 수 있습니다.\n\n"
            "### 원장 테이블에 승인 규칙 생성하기\n\n"
            "원장 테이블 정책 적용 시 강제화할 승인 규칙을 별도로 생성하고 관리할 수 있습니다.\n"
        ),
        "markers": [],
        "status": "pass",
    },
    {
        "type": "type7_callout_deleted",
        "page_id": "544080097",
        "mdx_path": "src/content/ko/administrator-manual/general/system/integrations.mdx",
        "old": (
            "<Callout type=\"important\">\n"
            "Integration 설정을 위해서는 System admin 권한이 필요합니다.\n"
            "</Callout>\n\n"
            "### 제공하는 기능\n\n"
            "* [Syslog 연동](integrations/integrating-with-syslog)\n"
        ),
        "new": (
            "<Callout type=\"important\">\n"
            "Integration 설정을 위해서는 System admin 권한이 필요합니다.\n"
            "</Callout>\n\n"
            "### 제공하는 기능\n\n"
            "* [Syslog 연동](integrations/integrating-with-syslog)\n"
            "* [PagerDuty 연동](integrations/integrating-with-pagerduty)\n"
        ),
        "markers": ["Syslog 연동 PagerDuty 연동"],
        "status": "fail",
    },
    {
        "type": "type10_unsupported_node_dup",
        "page_id": "544376236",
        "mdx_path": "src/content/ko/administrator-manual/general/user-management/provisioning.mdx",
        "old": (
            "### SCIM 계정 시스템 연동 가이드 바로가기\n\n"
            "* [Provisioning 활성화 하기](provisioning/activating-provisioning)\n"
            "* [[Okta] 프로비저닝 연동 가이드](provisioning/okta-provisioning-integration-guide)\n"
        ),
        "new": (
            "### SCIM 계정 시스템 연동 가이드 바로가기\n\n"
            "* [Provisioning 활성화 하기](provisioning/activating-provisioning)\n"
            "* [[Okta] 프로비저닝 연동 가이드](provisioning/okta-provisioning-integration-guide)\n"
            "* [SCIM API 참고](provisioning/scim-api-reference)\n"
        ),
        "markers": ["SCIM API 참고"],
        "status": "fail",
    },
    {
        "type": "type12_backtick_break",
        "page_id": "565575990",
        "mdx_path": "src/content/ko/administrator-manual/servers/connection-management/server-agents-for-rdp/installing-and-removing-server-agent.mdx",
        "old": (
            "1. Administrator &gt; Servers &gt; Connection Management &gt; Server Agents for RDP 페이지로 접속합니다.\n"
            "2. 우측 상단은 `Verify Deletion Key 버튼을 클릭합니다.`\n"
            "3. 확인된 Deletion Key를 기록합니다.\n"
            "4. Windows Server 콘솔에 접속합니다.\n"
            "5. 제어판 &gt; 프로그램 추가/제거 메뉴 접속 후 QueryPie Server Agent를 삭제합니다.\n"
        ),
        "new": (
            "1. Administrator &gt; Servers &gt; Connection Management &gt; Server Agents for RDP 페이지로 접속합니다.\n"
            "2. 우측 상단의 `Verify Deletion Key` 버튼을 클릭합니다.\n"
            "3. 확인된 Deletion Key를 기록합니다.\n"
            "4. Windows Server 콘솔에 접속합니다.\n"
            "5. 제어판 &gt; 프로그램 추가/제거 메뉴 접속 후 QueryPie Server Agent를 삭제합니다.\n"
        ),
        "markers": ["Verify Deletion Key", "`Verify Deletion Key"],
        "status": "fail",
    },
    {
        "type": "type11_proofread_revert",
        "page_id": "544380381",
        "mdx_path": "src/content/ko/administrator-manual/databases/connection-management/db-connections/mongodb-specific-guide.mdx",
        "old": (
            "### Proxy를 사용하는 경우 TLS(SSL) 설정\n\n"
            "위에서 안내된 바와 같이 QueryPie의 SQL editor를 사용하여 접속하는 경우 커넥션 스트링에 tls=true가 필요합니다.\n\n"
            "> +srv 스킴은 TLS 옵션이 자동으로 true이므로 standard string으로 변환하면  **tls=true** 를 수동으로 입력해줘야 합니다.> (TXT 레코드에 TLS 옵션이 없기 때문입니다.) 따라서 Other options 항목에 위 그림과 같이  **&tls=true** 를 입력합니다.\n"
            "Proxy를 사용하는 경우 DataGrip등의 SQL Client에서 TLS 설정과 별개로 QueryPie에서도 SSL 설정이 필요합니다.<br/>[SSL Configurations](../ssl-configurations)를 참고하여 설정 후 커넥션의 SSL 설정에 반영해야 합니다.<br/>\n"
        ),
        "new": (
            "### Proxy를 사용하는 경우 TLS(SSL) 설정\n\n"
            "위에서 안내된 바와 같이 QueryPie의 SQL editor를 사용하여 접속하는 경우 커넥션 스트링에 tls=true가 필요합니다.\n\n"
            "> +srv 스킴은 TLS 옵션이 자동으로 true이므로 standard string으로 변환하면  **tls=true** 를 수동으로 입력해줘야 합니다.> (TXT 레코드에 TLS 옵션이 없기 때문입니다.) 따라서 Other options 항목에 위 그림과 같이  **&tls=true** 를 입력합니다.\n"
            "Proxy를 사용하는 경우 DataGrip 등의 SQL Client에서 TLS 설정과 별개로 QueryPie에서도 SSL 설정이 필요합니다.<br/>[SSL Configurations](../ssl-configurations)를 참고하여 설정 후 커넥션의 SSL 설정에 반영해야 합니다.<br/>\n"
        ),
        "markers": ["DataGrip등", "DataGrip 등"],
        "status": "fail",
    },
]


@pytest.mark.parametrize("case", CASES, ids=[c["type"] for c in CASES])
def test_roundtrip_real_cases_reproduce_failures(monkeypatch, tmp_path, case):
    """모든 케이스를 실제 roundtrip 경로로 실행하고 실패 시그널을 검증한다."""
    page_id = case["page_id"]
    mdx_path = case["mdx_path"]

    var_dir = _prepare_real_roundtrip_env(monkeypatch, tmp_path, page_id)
    original_mdx = _load_repo_mdx(mdx_path)
    assert case["old"] in original_mdx, f"old snippet not found for {case['type']}"

    improved_mdx = original_mdx.replace(case["old"], case["new"], 1)
    assert improved_mdx != original_mdx, f"no mutation for {case['type']}"

    result = run_verify(
        page_id=page_id,
        original_src=MdxSource(content=original_mdx, descriptor=mdx_path),
        improved_src=MdxSource(content=improved_mdx, descriptor=f"{mdx_path}#improved"),
    )

    assert (var_dir / "reverse-sync.patched.xhtml").exists()
    assert (var_dir / "verify.mdx").exists()
    assert result["changes_count"] > 0
    assert result["status"] == case["status"]

    diff_text = result["verification"]["diff_report"]
    if case["markers"]:
        assert any(marker in diff_text for marker in case["markers"])
