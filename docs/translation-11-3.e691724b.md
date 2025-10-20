### 커밋 42e20714d08b7e5dc6596503d57d7df842e3d829 변경에 따른 번역 수행

1. 한국어 원문을 영어, 일본어로 번역하는 일반적인 가이드에 대해, [translation.md](translation.md) 문서를 참조하여 주세요.

2. 42e20714d08b7e5dc6596503d57d7df842e3d829 에서 다수의 한국어 문서가 업데이트되었습니다.
   이에 따른 변경을 src/content/en/ 디렉토리 아래의 영어 문서에 번역하여 반영하고자 합니다.
   이 문서에서, 한국어 원문 변경파일의 목록, 영어 문서의 TODO list 를 관리하고 있습니다.
   이미 번역된 것은 체크표시되어 있습니다.

3. 번역을 시작하기 전에, 이미 영어 번역된 파일이 존재하는지, 번역문이 올바르게 저장되어 있는지, 확인을 수행하여 주세요.
   42e20714d08b7e5dc6596503d57d7df842e3d829 의 commit 을 확인하여, 한국어 문서에서 변경된 부분을 확인하여 주세요.
   문서 전체가 아닌, 문서의 일부분 변경사항이 번역대상인 경우가 다수 있습니다. 한국의 문서의 부분적인 변경사항, 
   영어 문서의 번역결과물을 확인하여, 중복 번역을 방지하여야 합니다.
   이미 번역이 완벽하게 수행된 경우, TODO list 에서 완료표시를 위해 체크하여 주세요.

   * 문서의 일부분 변경사항 가운데, bullet list, numbered list 등 Markdown 스타일 변경, 강조표시 변경,
     공백 변경을 존중하여 주세요. 이러한 변경사항을 영어 번역문에 반영하여야 합니다.
   * 영어 번역된 문서의 범위를 확인하기 위해, main branch 이후 현재 branch 의 변경사항을 확인하여 주세요.
   * 한국어 원문의 변경사항 범위와 영어 번역된 문서의 변경사항 범위가 일치하여야 합니다.

4. npm run build 검증은 모든 번역이 완료된 후, 일괄적으로 한번에 수행하여 주세요.

5. 지시사항 - 제시된 번역 가이드에 맞추어, src/content/en 의 문서 업데이트를 수행하여 주세요. 최대한 많은 문서를 번역하여 주세요.

### 한국어 원문과 영어 번역문의 비교방법

1. 한국어 원문의 변경사항 범위를 확인하기 위해, 42e20714d08b7e5dc6596503d57d7df842e3d829 의 .mdx 파일목록, 
   각 파일에 대한 추가/삭제/대체된 라인수와 위치를 알아냅니다.
2. 영어 번역된 문서의 변경사항 범위를 확인하기 위해, main branch 이후의 .mdx 파일목록, 각 파일에 대한
   추가/삭제/대체된 라인수와 위치를 알아냅니다.
3. 위의 두 변경범위를 비교하여, 한국어 원문의 변경사항과 영어 번역된 문서의 변경사항이 일치하는지, 불일치한다면, 어느 정도로
   불일치하는지 알아냅니다. 불일치가 발생한 경우, 해당 부분이 올바르게 번역되었는지, 본문을 읽어 검증합니다.

## 한국어 원문 변경 파일(MDX, _meta.ts)

아래는 커밋에서 변경된 한국어 MDX 및 `_meta.ts` 파일 목록과, 대응하는 영어 문서 업데이트 체크리스트입니다.

- src/content/ko/administrator-manual/audit/general-logs/activity-logs.mdx (M)
- src/content/ko/administrator-manual/audit/reports/audit-log-export.mdx (M)
- src/content/ko/administrator-manual/audit/server-logs/command-audit.mdx (M)
- src/content/ko/administrator-manual/databases/connection-management/cloud-providers/synchronizing-db-resources-from-aws.mdx (M)
- src/content/ko/administrator-manual/databases/connection-management/cloud-providers/synchronizing-db-resources-from-google-cloud.mdx (M)
- src/content/ko/administrator-manual/databases/connection-management/cloud-providers/synchronizing-db-resources-from-ms-azure.mdx (M)
- src/content/ko/administrator-manual/databases/connection-management/db-connections.mdx (M)
- src/content/ko/administrator-manual/databases/dac-general-configurations.mdx (M)
- src/content/ko/administrator-manual/databases/new-policy-management/data-policies.mdx (M)
- src/content/ko/administrator-manual/databases/new-policy-management/exception-management.mdx (M)
- src/content/ko/administrator-manual/general/company-management/alerts.mdx (M)
- src/content/ko/administrator-manual/general/company-management/allowed-zones.mdx (M)
- src/content/ko/administrator-manual/general/company-management/general.mdx (M)
- src/content/ko/administrator-manual/general/company-management/licenses.mdx (M)
- src/content/ko/administrator-manual/general/company-management/security.mdx (M)
- src/content/ko/administrator-manual/general/system/_meta.ts (M)
- src/content/ko/administrator-manual/general/system/integrations/_meta.ts (M)
- src/content/ko/administrator-manual/general/system/integrations/identity-providers.mdx (A)
- src/content/ko/administrator-manual/general/system/integrations/identity-providers/integrating-with-aws-sso-saml-20.mdx (A)
- src/content/ko/administrator-manual/general/system/integrations/integrating-with-splunk.mdx (M)
- src/content/ko/administrator-manual/general/system/integrations/integrating-with-syslog.mdx (M)
- src/content/ko/administrator-manual/general/system/integrations/oauth-client-application.mdx (A)
- src/content/ko/administrator-manual/general/system/maintenance.mdx (A)
- src/content/ko/administrator-manual/general/user-management/authentication.mdx (M)
- src/content/ko/administrator-manual/general/user-management/groups.mdx (M)
- src/content/ko/administrator-manual/general/workflow-management/approval-rules.mdx (M)
- src/content/ko/administrator-manual/servers/connection-management/server-agents-for-rdp/installing-and-removing-server-agent.mdx (M)
- src/content/ko/administrator-manual/servers/connection-management/server-groups/managing-servers-as-groups.mdx (M)
- src/content/ko/release-notes/1130.mdx (A)
- src/content/ko/release-notes/_meta.ts (M)
- src/content/ko/user-manual/server-access-control/connecting-to-authorized-servers.mdx (M)
- src/content/ko/user-manual/web-access-control/accessing-web-applications-websites.mdx (M)
- src/content/ko/user-manual/workflow/requesting-db-access.mdx (M)
- src/content/ko/user-manual/workflow/requesting-db-policy-exception.mdx (M)
- src/content/ko/user-manual/workflow/requesting-restricted-data-access.mdx (M)
- src/content/ko/user-manual/workflow/requesting-unmasking-mask-removal-request.mdx (M)

## 영어 문서 업데이트 체크리스트 (src/content/en)

- [ ] src/content/en/administrator-manual/audit/general-logs/activity-logs.mdx
- [ ] src/content/en/administrator-manual/audit/reports/audit-log-export.mdx
- [ ] src/content/en/administrator-manual/audit/server-logs/command-audit.mdx
- [ ] src/content/en/administrator-manual/databases/connection-management/cloud-providers/synchronizing-db-resources-from-aws.mdx
- [ ] src/content/en/administrator-manual/databases/connection-management/cloud-providers/synchronizing-db-resources-from-google-cloud.mdx
- [ ] src/content/en/administrator-manual/databases/connection-management/cloud-providers/synchronizing-db-resources-from-ms-azure.mdx
- [ ] src/content/en/administrator-manual/databases/connection-management/db-connections.mdx
- [ ] src/content/en/administrator-manual/databases/dac-general-configurations.mdx
- [ ] src/content/en/administrator-manual/databases/new-policy-management/data-policies.mdx
- [ ] src/content/en/administrator-manual/databases/new-policy-management/exception-management.mdx
- [ ] src/content/en/administrator-manual/general/company-management/alerts.mdx
- [ ] src/content/en/administrator-manual/general/company-management/allowed-zones.mdx
- [ ] src/content/en/administrator-manual/general/company-management/general.mdx
- [ ] src/content/en/administrator-manual/general/company-management/licenses.mdx
- [ ] src/content/en/administrator-manual/general/company-management/security.mdx
- [ ] src/content/en/administrator-manual/general/system/_meta.ts
- [ ] src/content/en/administrator-manual/general/system/integrations/_meta.ts
- [ ] src/content/en/administrator-manual/general/system/integrations/identity-providers.mdx
- [ ] src/content/en/administrator-manual/general/system/integrations/identity-providers/integrating-with-aws-sso-saml-20.mdx
- [ ] src/content/en/administrator-manual/general/system/integrations/integrating-with-splunk.mdx
- [ ] src/content/en/administrator-manual/general/system/integrations/integrating-with-syslog.mdx
- [ ] src/content/en/administrator-manual/general/system/integrations/oauth-client-application.mdx
- [ ] src/content/en/administrator-manual/general/system/maintenance.mdx
- [ ] src/content/en/administrator-manual/general/user-management/authentication.mdx
- [ ] src/content/en/administrator-manual/general/user-management/groups.mdx
- [ ] src/content/en/administrator-manual/general/workflow-management/approval-rules.mdx
- [ ] src/content/en/administrator-manual/servers/connection-management/server-agents-for-rdp/installing-and-removing-server-agent.mdx
- [ ] src/content/en/administrator-manual/servers/connection-management/server-groups/managing-servers-as-groups.mdx
- [ ] src/content/en/release-notes/1130.mdx
- [ ] src/content/en/release-notes/_meta.ts
- [ ] src/content/en/user-manual/server-access-control/connecting-to-authorized-servers.mdx
- [ ] src/content/en/user-manual/web-access-control/accessing-web-applications-websites.mdx
- [ ] src/content/en/user-manual/workflow/requesting-db-access.mdx
- [ ] src/content/en/user-manual/workflow/requesting-db-policy-exception.mdx
- [ ] src/content/en/user-manual/workflow/requesting-restricted-data-access.mdx
- [ ] src/content/en/user-manual/workflow/requesting-unmasking-mask-removal-request.mdx

참고: 이미지 파일은 공통 자산으로 언어와 무관하게 공유됩니다. 캡션 등의 텍스트는 번역 대상입니다.


---

## 영문 번역 검증 결과 요약 (11.3.0)
- 본 문서는 체크리스트의 완료표시 여부와 무관하게, 한국어 원문과 영어 번역본의 전체 일치 여부를 우선순위 대상(신규 추가/시스템 통합/릴리스 노트)부터 점검한 결과입니다. npm run build 검증은 생략했습니다.

검증 기준
- 문서 존재 여부, 제목/헤딩 구조, 목록/표/강조(Callout) 및 그림/캡션의 보존 여부, 핵심 기술 용어의 일관성, 경로/메뉴 표기 및 링크/이미지 경로 확인

우선 검증 대상(신규 추가 및 System/Integrations 클러스터)
1) Administrator > General > System > Integrations > Identity Providers
   - KO: src/content/ko/administrator-manual/general/system/integrations/identity-providers.mdx
   - EN: src/content/en/administrator-manual/general/system/integrations/identity-providers.mdx
   - 결과: 구조/표/캡션/Callout/이미지 경로 모두 일치. 용어(IdP, MFA, SSO 등) 번역 적정. “동기화 후 삭제 불가” 경고도 반영 확인. [일치]

2) Identity Providers > Integrate AWS SSO (SAML 2.0)
   - KO: src/content/ko/.../identity-providers/integrating-with-aws-sso-saml-20.mdx
   - EN: src/content/en/.../identity-providers/integrating-with-aws-sso-saml-20.mdx
   - 결과: 단계별 절차/속성 매핑 표/화면 경로 및 캡션 일치. 스케줄 동기화 불가 주의사항도 반영. [일치]

3) OAuth Client Application
   - KO: src/content/ko/administrator-manual/general/system/integrations/oauth-client-application.mdx
   - EN: src/content/en/administrator-manual/general/system/integrations/oauth-client-application.mdx
   - 결과: 등록/수정/삭제 흐름, 필드 설명(Timeout 단위/최소값 등), Client ID/Secret 주의사항 캡션까지 일치. [일치]

4) Maintenance
   - KO: src/content/ko/administrator-manual/general/system/maintenance.mdx
   - EN: src/content/en/administrator-manual/general/system/maintenance.mdx
   - 결과: 이중화 환경 업그레이드 단계, Operation Mode 표(각 모드 설명/적용 불가 범위 주석) 일치. 기능 신설 버전(11.3.0) Callout 반영. [일치]

5) Integrations: Splunk
   - KO: src/content/ko/administrator-manual/general/system/integrations/integrating-with-splunk.mdx
   - EN: src/content/en/administrator-manual/general/system/integrations/integrating-with-splunk.mdx
   - 결과: 권장 아키텍처/프로토콜 및 HEC 설정/필드별 설명/전송 토글 동작/Timezone 추가(11.3.0) 공통 안내/라이선스별 이벤트 표/참고 문헌까지 일치. [일치]

6) Integrations: Syslog
   - KO: src/content/ko/administrator-manual/general/system/integrations/integrating-with-syslog.mdx
   - EN: src/content/en/administrator-manual/general/system/integrations/integrating-with-syslog.mdx
   - 결과: UDP→TCP 지원 이력/Legacy 안내(타임존 옵션)/설정 팝업 항목/토글 동작/Timezone 추가(11.3.0) 안내/이미지 경로 일치. [일치]

메뉴 메타(_meta.ts) 확인
- System (_meta.ts)
  - KO/EN 모두 integratons, api-token, jobs, maintenance 항목 일치. [일치]
- System/Integrations (_meta.ts)
  - KO/EN 모두 Syslog, Splunk, Secret Store, Email, Event Callback, Google Cloud API(OAuth 2.0), Slack DM, OAuth Client Application, Identity Providers 항목 구성/명칭 일치. [일치]
- Release Notes (_meta.ts)
  - KO/EN 모두 1130 항목 존재. [일치]

릴리스 노트 11.3.0
- KO: src/content/ko/release-notes/1130.mdx
- EN: src/content/en/release-notes/1130.mdx
- 결과: 날짜/섹션(New Feature/Improvement)/항목 수 및 의미 일치. 용어(기능명/모듈명) 대응 적정. [일치]

기타 참고 및 메모
- 일부 한국어 원문에 오타가 있으나(예: Athentication, Client Scret 등) 영어 번역본에는 반영되지 않았고, 의미 전달에는 영향 없음.
- 본 차수에서 변경(추가/수정)된 문서군에 대해 우선 검증을 완료했습니다. 나머지 수정 표기(M) 대상 문서군도 동일 기준으로 이상 여부를 지속 점검할 것을 권고합니다.

요약 결론
- 본 검증 범위 내에서 한국어 원문 대비 영어 번역본은 내용/구조/형식적으로 일치합니다. 별도의 수정 커밋이 필요한 항목은 발견하지 못했습니다.


---

## 한국어 원문 오타 내역 (11.3.0 관련)
- 아래 목록은 이번 차수에서 확인한 한국어 원문 내 오타/철자/띄어쓰기 오류와 잘못 표기된 영문 용어를 정리한 것입니다. 원문 수정은 본 이슈의 범위에 포함하지 않고, 참고용으로만 문서화합니다.

1) src/content/ko/administrator-manual/general/system/integrations/identity-providers.mdx
- 두가지 → 두 가지
- 여러개의 → 여러 개의
- 인증외에 → 인증 외에
- 삭제 할 수 없습니다 → 삭제할 수 없습니다
- (LDAP 추가 안내) “추가 할 수 있습니다” → “추가할 수 있습니다”
- “간주됩니다.예시:” → “간주됩니다. 예시:”
- “입력합니다.예시:” → “입력합니다. 예시:”
- QuerPie → QueryPie (제품명 오타)

2) src/content/ko/administrator-manual/general/system/integrations/identity-providers/integrating-with-aws-sso-saml-20.mdx
- 속상 → 속성
- Athentication → Authentication
- SML metadata XML → SAML metadata XML
- QueryPie 에서 → QueryPie에서 (띄어쓰기)
- 로그인 합니다 → 로그인합니다 (붙임표기)

3) src/content/ko/administrator-manual/general/system/integrations/oauth-client-application.mdx
- 어플리케이션 → 애플리케이션 (표준 표기, 다수 위치)
- 끝난후 → 끝난 후
- Client Scret → Client Secret

4) src/content/ko/administrator-manual/general/system/integrations/integrating-with-splunk.mdx
- 아키텍쳐 → 아키텍처 (이미지 캡션/본문 모두)
- 전송가능한 → 전송 가능한
- ip 주소 → IP 주소
- sylog server → syslog server
- 추가 되었습니다 → 추가되었습니다
- 전송기능 → 전송 기능
- 라이센스 → 라이선스

5) src/content/ko/administrator-manual/general/system/integrations/integrating-with-syslog.mdx
- 아래에 앴는 → 아래에 있는
- sylog server → syslog server
- 유지 보수 → 유지보수

6) src/content/ko/administrator-manual/general/system/maintenance.mdx
- 이중화 되어 → 이중화되어

7) src/content/ko/release-notes/1130.mdx
- SET STATISTCS PROFILE → SET STATISTICS PROFILE
- Sever Connection Attempt → Server Connection Attempt
- 라이센스 → 라이선스
- 행수 → 행 수
- Reviewer을 → Reviewer를
- (문장 다듬기 제안) “신정책에 이벤트에 대한” → “신정책의 이벤트에 대한” 또는 “신정책 이벤트에 대한”

참고
- 위 항목 중 일부는 맞춤법/띄어쓰기 통일(예: ‘유지보수’, ‘애플리케이션’, ‘라이선스’)과 영문 용어 표기 통일(예: IP, Syslog, Client Secret)에 해당합니다.
- 실제 원문 수정을 진행할 경우, 메뉴 캡처/이미지의 텍스트와도 일관되게 반영해야 합니다.