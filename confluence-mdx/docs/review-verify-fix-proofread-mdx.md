# reverse-sync verify 리뷰: `fix/proofread-mdx` 브랜치

> **실행일:** 2026-02-14 07:28
> **명령어:** `bin/reverse_sync_cli.py verify --branch fix/proofread-mdx`
> **로그 파일:** `reverse_sync_verify_fix_proofread-mdx.02140728.log`

## 결과 요약

| 상태 | 건수 | 비율 |
|------|-----:|-----:|
| pass | 158 | 74.9% |
| fail | 52 | 24.6% |
| error | 1 | 0.5% |
| **합계** | **211** | |

## 실패 유형 분류

52건의 fail을 원인별로 분류했습니다. 하나의 파일이 여러 유형에 해당할 수 있습니다.

### 심각도별 분류

```
[Critical]  데이터 손실·구조 파괴     — 유형 5, 6, 7, 12, 13
[Medium]    교정 내용 원복             — 유형 11
[Low]       코스메틱 차이 (자동화 가능) — 유형 1, 2, 3, 4, 8, 9, 10, 14
```

---

### 유형 1: Trailing Whitespace 추가 (29건)

XHTML 라운드트립 후 줄 끝에 공백이 추가됩니다.

```diff
-    1. 조회 기간 변경을 위해서는 필터 패널을 열고, **Action At**에서 조회 기준일을 변경하시기 바랍니다.
+    1. 조회 기간 변경을 위해서는 필터 패널을 열고,  **Action At**  에서 조회 기준일을 변경하시기 바랍니다.
```

<details>
<summary>해당 파일 목록 (29건)</summary>

1. `administrator-manual/audit/general-logs/activity-logs.mdx`
2. `administrator-manual/audit/reports/audit-log-export.mdx`
3. `administrator-manual/databases/connection-management/cloud-providers/synchronizing-db-resources-from-aws.mdx`
4. `administrator-manual/databases/connection-management/cloud-providers/synchronizing-db-resources-from-ms-azure.mdx`
5. `administrator-manual/databases/connection-management/db-connections.mdx`
6. `administrator-manual/databases/connection-management/db-connections/documentdb-specific-guide.mdx`
7. `administrator-manual/databases/connection-management/db-connections/mongodb-specific-guide.mdx`
8. `administrator-manual/databases/db-access-control/access-control.mdx`
9. `administrator-manual/databases/new-policy-management/data-paths.mdx`
10. `administrator-manual/general/company-management/channels.mdx`
11. `administrator-manual/general/company-management/licenses.mdx`
12. `administrator-manual/general/system/api-token.mdx`
13. `administrator-manual/general/system/integrations/integrating-with-secret-store.mdx`
14. `administrator-manual/general/user-management/authentication/integrating-with-okta.mdx`
15. `administrator-manual/general/user-management/users/password-change-enforcement-and-account-deletion-feature-for-qp-admin-default-account.mdx`
16. `administrator-manual/general/workflow-management/approval-rules.mdx`
17. `administrator-manual/servers/session-monitoring.mdx`
18. `installation/post-installation-setup.mdx`
19. `overview.mdx`
20. `support.mdx`
21. `support/premium-support.mdx`
22. `user-manual/database-access-control.mdx`
23. `user-manual/database-access-control/connecting-to-proxy-without-agent.mdx`
24. `user-manual/multi-agent/multi-agent-3rd-party-tool-support-list-by-os.mdx`
25. `user-manual/multi-agent/multi-agent-linux-installation-and-usage-guide.mdx`
26. `user-manual/multi-agent/multi-agent-seamless-ssh-usage-guide.mdx`
27. `user-manual/preferences.mdx`
28. `user-manual/server-access-control/using-web-terminal.mdx`
29. `user-manual/user-agent.mdx`

</details>

---

### 유형 2: Bold 마크업 주변 공백 차이 (18건)

`**text**` ↔ ` **text** ` — Confluence `<strong>` 태그의 변환 특성으로 bold 마크업 앞뒤에 공백이 삽입됩니다.

```diff
-현재 QueryPie ACP는 **데이터베이스, 시스템, 쿠버네티스 접근제어와 감사 기능**을 핵심으로
+현재 QueryPie ACP는  **데이터베이스, 시스템, 쿠버네티스 접근제어와 감사 기능** 을 핵심으로
```

<details>
<summary>해당 파일 목록 (18건)</summary>

1. `administrator-manual/audit/general-logs/activity-logs.mdx`
2. `administrator-manual/audit/reports/audit-log-export.mdx`
3. `administrator-manual/databases/connection-management/cloud-providers/synchronizing-db-resources-from-ms-azure.mdx`
4. `administrator-manual/databases/connection-management/db-connections.mdx`
5. `administrator-manual/databases/connection-management/db-connections/documentdb-specific-guide.mdx`
6. `administrator-manual/databases/connection-management/db-connections/mongodb-specific-guide.mdx`
7. `administrator-manual/databases/new-policy-management/data-paths.mdx`
8. `administrator-manual/general/workflow-management/approval-rules.mdx`
9. `overview.mdx`
10. `support/standard-edition-license-policy.mdx`
11. `support/standard-edition.mdx`
12. `user-manual/database-access-control.mdx`
13. `user-manual/database-access-control/connecting-to-proxy-without-agent.mdx`
14. `user-manual/multi-agent/multi-agent-3rd-party-tool-support-list-by-os.mdx`
15. `user-manual/multi-agent/multi-agent-seamless-ssh-usage-guide.mdx`
16. `user-manual/server-access-control/using-web-terminal.mdx`
17. `user-manual/preferences.mdx`
18. `user-manual/user-agent.mdx`

</details>

---

### 유형 3: 백틱 코드 스팬 주변 공백 차이 (11건)

`` `text` `` ↔ `` `text` `` — 인라인 코드 블록 앞뒤에도 동일한 공백 삽입 현상이 발생합니다.

```diff
-2. `Test Connection`을 통해 실제로 접속 가능한 계정인지 테스트할 수 있습니다.
+2. `Test Connection` 을 통해 실제로 접속 가능한 계정인지 테스트할 수 있습니다.
```

<details>
<summary>해당 파일 목록 (11건)</summary>

1. `administrator-manual/databases/connection-management/db-connections.mdx`
2. `administrator-manual/general/company-management/channels.mdx`
3. `administrator-manual/general/system/api-token.mdx`
4. `installation/installation/installation-guide-setupv2sh.mdx`
5. `installation/post-installation-setup.mdx`
6. `support.mdx`
7. `support/premium-support.mdx`
8. `user-manual/multi-agent/multi-agent-linux-installation-and-usage-guide.mdx`
9. `user-manual/multi-agent/multi-agent-seamless-ssh-usage-guide.mdx`
10. `user-manual/preferences.mdx`
11. `user-manual/user-agent.mdx`

</details>

---

### 유형 4: 빈 Bold 태그 `****` 삽입 (5건)

Confluence `<strong></strong>` 빈 태그가 MDX로 변환될 때 무의미한 `****`로 나타납니다.

```diff
-* [ **Allowed Zones** ](company-management/allowed-zones) : 쿼리파이의 허용 네트워크 존 설정을 구성하는 메뉴입니다.
+* [ **Allowed Zones** ](company-management/allowed-zones) **** : 쿼리파이의 허용 네트워크 존 설정을 구성하는 메뉴입니다.
```

<details>
<summary>해당 파일 목록 (5건)</summary>

1. `administrator-manual/databases/connection-management/cloud-providers/synchronizing-db-resources-from-aws.mdx`
2. `administrator-manual/databases/connection-management/db-connections/custom-data-source-configuration-and-log-verification.mdx`
3. `administrator-manual/databases/db-access-control/access-control.mdx`
4. `administrator-manual/general/company-management.mdx`
5. `administrator-manual/general/company-management/licenses.mdx`

</details>

---

### 유형 5: 중첩 리스트 내용 소실 [Critical] (1건)

깊은 중첩 번호 목록의 텍스트가 부모 항목으로 병합되고, 하위 항목은 빈 줄이 됩니다.

```diff
-3. 녹화된 파일의 크기가 700MB 초과 여부에 따라 재생 화면을 노출하거나 다운로드 버튼을 노출합니다.
-    1.  **700MB 미만**
+3. 녹화된 파일의 크기가 700MB 초과 여부에 따라... 700MB 미만 상단에 기본 정보가... (전체 병합)
+    1.  ****
```

- `administrator-manual/audit/kubernetes-logs/pod-session-recordings.mdx`

---

### 유형 6: Callout 파서 에러 삽입 [Critical] (1건)

`<callout>` 요소 처리 실패로 `MultiLineParser` 에러 메시지가 본문에 삽입됩니다.

```diff
+[callout]
+MultiLineParser: Unexpected NavigableString '원장 테이블 정책은...' of from <[document]>...
```

- `administrator-manual/databases/ledger-management/ledger-approval-rules.mdx`

---

### 유형 7: Callout 블록 삭제 [Critical] (1건)

`<Callout>` 컴포넌트 전체가 라운드트립 후 소실됩니다.

```diff
-<Callout type="important">
-Integration 설정을 위해서는 System admin 권한이 필요합니다.
-</Callout>
```

- `administrator-manual/general/system/integrations.mdx`

---

### 유형 8: 테이블 컬럼 폭 변동 (2건)

테이블 구분선(`---`)의 대시 수가 달라지는 순수 포맷팅 차이입니다. 내용에는 영향 없습니다.

- `administrator-manual/general/system/maintenance.mdx`
- `installation/container-environment-variables.mdx`

---

### 유형 9: 줄바꿈·문단 병합 차이 (3건)

여러 줄로 분리된 텍스트가 한 줄로 병합되거나, 반대로 한 줄이 분리됩니다.

```diff
-기존 QueryPie DAC은 Data Access, Data Masking, Sensitive Data,
-Ledger Table Management와 같은 데이터 정책을 제공하고 있습니다.
+기존 QueryPie DAC은 Data Access, Data Masking, Sensitive Data, Ledger Table Management와 같은 데이터 정책을 제공하고 있습니다.
```

- `administrator-manual/databases/new-policy-management.mdx`
- `administrator-manual/databases/new-policy-management/exception-management.mdx`
- `administrator-manual/servers/session-monitoring.mdx`

---

### 유형 10: Unsupported XHTML Node 중복 (2건)

`(Unsupported xhtml node: ...)` 플레이스홀더가 라운드트립 후 중복 출력됩니다.

- `administrator-manual/general/user-management/provisioning.mdx`
- `administrator-manual/kubernetes/connection-management.mdx`

---

### 유형 11: 교정 내용 원복 [Medium] (9건+)

MDX에서 의도적으로 수정한 교정 사항이 XHTML 원본 기준으로 되돌아갑니다.

| 파일 | 교정 전 (XHTML 원본) | 교정 후 (MDX 수정) |
|------|----------------------|-------------------|
| `mongodb-specific-guide.mdx` | `DataGrip등` | `DataGrip 등` |
| `running-queries.mdx` | `**Client**   **Name**` | `**Client Name**` |
| `security.mdx` | `다중 설정이 가능하도록` | `다중으로 구성할 수 있도록` |
| `integrating-with-okta.mdx` | `진행하여 주시기 바랍니다` | `진행하기 바랍니다` |
| `user-profile.mdx` | `Static IP삭제하기` | `Static IP 삭제하기` |
| `installation-guide-simple-configuration.mdx` | `참조하여 주세요` | `참조해 주세요` |
| `installing-on-aws-eks.mdx` | `QueryPie ACP 를` | `QueryPie ACP를` |
| `post-installation-setup.mdx` | `갈음하여` | `대체하여` |
| `linux-distribution-and-docker-podman-support-status.mdx` | `Aug 29, 2025` | `2025년 08월 29일` |

---

### 유형 12: 백틱 포맷 깨짐 [Critical] (1건)

닫는 백틱 위치가 이동하여 코드 스팬이 깨집니다.

```diff
-2. 우측 상단의 `Verify Deletion Key` 버튼을 클릭합니다.
+2. 우측 상단의 `Verify Deletion Key 버튼을 클릭합니다.`
```

- `administrator-manual/servers/connection-management/server-agents-for-rdp/installing-and-removing-server-agent.mdx`

---

### 유형 13: 링크·URL 변경 [Critical] (2건)

라운드트립 후 URL이나 링크 대상이 변경됩니다.

```diff
-* [릴리스 버전별 문서](https://querypie.atlassian.net/wiki/spaces/QCP/pages/841351486)
+* [릴리스 버전별 문서](https://querypie.atlassian.net/wiki/spaces/QCP/overview)
```

- `administrator-manual/databases/new-policy-management.mdx` (이중 슬래시 삽입)
- `support.mdx` (링크 대상 변경)

---

### 유형 14: 테이블 셀 내 Bold 스타일 차이 (1건)

테이블 셀 내 bold 마크업의 공백 컨벤션 차이입니다.

- `support/standard-edition.mdx`

---

## Error (1건)

| 파일 | 원인 |
|------|------|
| `index.mdx` | `var/pages.yaml`에 page-id 매핑 없음 |

---

## 개선 권고

### verifier 정규화 개선 (유형 1, 2, 3 해소)

- bold(`**`), 백틱(`` ` ``) 마크업 주변 공백과 trailing whitespace는 라운드트립에서 구조적으로 발생합니다.
- `roundtrip_verifier.py`의 정규화 로직에 이 패턴들을 추가하면 **29건 이상의 false-positive를 제거**할 수 있습니다.

### XHTML 패처 버그 수정 (유형 4, 5, 6, 7, 10, 12)

- 빈 `<strong>` 태그 삽입, 중첩 리스트 구조 파괴, callout 처리 실패 등은 `xhtml_patcher.py` 또는 순변환 로직의 버그입니다.
- 특히 유형 5(중첩 리스트 소실)와 유형 6(파서 에러 본문 삽입)은 데이터 무결성을 해치므로 우선 수정이 필요합니다.

### 교정 내용 보존 전략 (유형 11)

- 띄어쓰기, 어미, 날짜 형식 등 텍스트 레벨 교정이 XHTML 패치 과정에서 손실됩니다.
- 블록 diff 적용 시 텍스트 변경 단위의 세밀한 패치가 필요하거나, 교정 내용이 Confluence 원본에도 반영되어야 합니다.
