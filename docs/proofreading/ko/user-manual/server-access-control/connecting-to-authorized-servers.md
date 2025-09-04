# 교정/교열 결과: connecting-to-authorized-servers.mdx

**검토일시**: 2025-09-04  
**검토 수행 AI Agent**: Claude Sonnet 4

## 검토 결과

### 전체적인 평가
권한이 있는 서버에 접속하기 문서로, 서버 접속 과정을 단계별로 상세하게 안내하고 있습니다. Callout 컴포넌트와 이미지를 활용한 구성이 효과적입니다.

### 발견된 문제점 및 개선사항

#### 1. 문장 표현 개선
- **현재**: "사용자는 권한이 있는 서버의 목록을 서버, 서버 그룹 별로 또는 Cloud Provider 별로 정렬하여 한눈에 확인할 수 있습니다."
- **개선 제안**: "사용자는 권한이 있는 서버의 목록을 서버, 서버 그룹별 또는 Cloud Provider별로 정렬하여 한눈에 확인할 수 있습니다."
  - "그룹 별로" → "그룹별" (띄어쓰기 제거)
  - "Provider 별로" → "Provider별" (띄어쓰기 제거)

#### 2. 문장 표현 개선
- **현재**: "1. Servers 메뉴로 첫 접속시 표시되는 Role 선택 화면에서 접속을 위해 사용할 Role을 선택합니다."
- **개선 제안**: "1. Servers 메뉴로 첫 접속 시 표시되는 Role 선택 화면에서 접속을 위해 사용할 Role을 선택합니다."
  - "접속시" → "접속 시" (띄어쓰기 추가)

#### 3. 문장 표현 개선
- **현재**: "1. Role 선택 후에는 좌측의 패널에서 현재 사용자가 접근 가능한 서버 목록을 확인할 수 있습니다"
- **개선 제안**: "1. Role 선택 후에는 좌측의 패널에서 현재 사용자가 접근 가능한 서버 목록을 확인할 수 있습니다."
  - 마침표 추가

#### 4. 문장 표현 개선
- **현재**: "1. Sort by Server Group : . 서버 목록은 서버 그룹이 우선 정렬되며 하단에 개별 서버가 정렬됩니다."
- **개선 제안**: "1. Sort by Server Group: 서버 목록은 서버 그룹이 우선 정렬되며 하단에 개별 서버가 정렬됩니다."
  - "Group : ." → "Group:" (띄어쓰기 및 마침표 제거)

#### 5. 문장 표현 개선
- **현재**: "2. Time-limited items only : 시간단위로 권한을 부여받은 서버만 리스트에서 표시합니다."
- **개선 제안**: "2. Time-limited items only: 시간 단위로 권한을 부여받은 서버만 리스트에서 표시합니다."
  - "only :" → "only:" (띄어쓰기 제거)
  - "시간단위" → "시간 단위" (띄어쓰기 추가)

#### 6. 문장 표현 개선
- **현재**: "3. Search by Host : 서버 목록의 검색 기준이 기존 서버 이름에서 Host(IP 주소)로 변경됩니다."
- **개선 제안**: "3. Search by Host: 서버 목록의 검색 기준이 기존 서버 이름에서 Host(IP 주소)로 변경됩니다."
  - "Host :" → "Host:" (띄어쓰기 제거)

#### 7. 문장 표현 개선
- **현재**: "2. 서버 목록에서 서버를 선택하면 우측 페이지에서 서버 및 계정 정보를 확인할 수 있습니다."
- **개선 제안**: "2. 서버 목록에서 서버를 선택하면 우측 페이지에서 서버 및 계정 정보를 확인할 수 있습니다."
  - 표현은 적절함

#### 8. 문장 표현 개선
- **현재**: "1. **Server OS** : 해당 서버의 OS를 표시됩니다"
- **개선 제안**: "1. **Server OS**: 해당 서버의 OS가 표시됩니다."
  - "OS** :" → "OS**: " (띄어쓰기 제거)
  - "OS를 표시됩니다" → "OS가 표시됩니다" (조사 수정)
  - 마침표 추가

#### 9. 문장 표현 개선
- **현재**: "2. **Host** : 해당 서버의 호스트가 표시됩니다."
- **개선 제안**: "2. **Host**: 해당 서버의 호스트가 표시됩니다."
  - "Host** :" → "Host**: " (띄어쓰기 제거)

#### 10. 문장 표현 개선
- **현재**: "3. **Account** : 권한이 있는 계정 목록입니다."
- **개선 제안**: "3. **Account**: 권한이 있는 계정 목록입니다."
  - "Account** :" → "Account**: " (띄어쓰기 제거)

#### 11. 문장 표현 개선
- **현재**: "4. **Custom Account** : Account에서 카테고리가 QueryPie - Custom Account인 계정을 선택했을 때 표시됩니다."
- **개선 제안**: "4. **Custom Account**: Account에서 카테고리가 QueryPie - Custom Account인 계정을 선택했을 때 표시됩니다."
  - "Account** :" → "Account**: " (띄어쓰기 제거)

#### 12. 문장 표현 개선
- **현재**: "5. **View Detailed Policy Application** : 선택한 계정에 적용된 정책을 표시합니다."
- **개선 제안**: "5. **View Detailed Policy Application**: 선택한 계정에 적용된 정책을 표시합니다."
  - "Application** :" → "Application**: " (띄어쓰기 제거)

#### 13. 문장 표현 개선
- **현재**: "1. **Access Time** : 접속 가능 시간을 표시합니다."
- **개선 제안**: "1. **Access Time**: 접속 가능 시간을 표시합니다."
  - "Time** :" → "Time**: " (띄어쓰기 제거)

#### 14. 문장 표현 개선
- **현재**: "2. **Weekday Access Allowed** : 접속 가능 요일을 표시합니다."
- **개선 제안**: "2. **Weekday Access Allowed**: 접속 가능 요일을 표시합니다."
  - "Allowed** :" → "Allowed**: " (띄어쓰기 제거)

#### 15. 문장 표현 개선
- **현재**: "3. **Restrict Commands (SSH)** : SSH 접속시 차단 명령어를 표시합니다."
- **개선 제안**: "3. **Restrict Commands (SSH)**: SSH 접속 시 차단 명령어를 표시합니다."
  - "SSH)** :" → "SSH)**: " (띄어쓰기 제거)
  - "접속시" → "접속 시" (띄어쓰기 추가)

#### 16. 문장 표현 개선
- **현재**: "4. **Restrict Functions (SFTP)** : SFTP 접속시 차단 기능을 표시합니다."
- **개선 제안**: "4. **Restrict Functions (SFTP)**: SFTP 접속 시 차단 기능을 표시합니다."
  - "SFTP)** :" → "SFTP)**: " (띄어쓰기 제거)
  - "접속시" → "접속 시" (띄어쓰기 추가)

#### 17. 문장 표현 개선
- **현재**: "6. **Password** (또는 SSH Key) : 선택한 계정의 인증 방식이 Password 일 경우 Password를 입력할 수 있는 필드가 표시됩니다."
- **개선 제안**: "6. **Password** (또는 SSH Key): 선택한 계정의 인증 방식이 Password일 경우 Password를 입력할 수 있는 필드가 표시됩니다."
  - "SSH Key) :" → "SSH Key): " (띄어쓰기 제거)
  - "Password 일" → "Password일" (띄어쓰기 제거)

#### 18. 문장 표현 개선
- **현재**: "7. **Status** : 선택한 계정의 상태가 표시됩니다."
- **개선 제안**: "7. **Status**: 선택한 계정의 상태가 표시됩니다."
  - "Status** :" → "Status**: " (띄어쓰기 제거)

#### 19. 문장 표현 개선
- **현재**: "8. **Protocol** : SSH, SFTP 또는 RDP 를 선택하여 접속할 수 있습니다."
- **개선 제안**: "8. **Protocol**: SSH, SFTP 또는 RDP를 선택하여 접속할 수 있습니다."
  - "Protocol** :" → "Protocol**: " (띄어쓰기 제거)
  - "RDP 를" → "RDP를" (띄어쓰기 제거)

#### 20. 문장 표현 개선
- **현재**: "A. 권한의 상태가 변경되었거나 접속이 허용되지 않은 시간대, 요일에 접속을 시도한 경우 실패할 수 있습니다."
- **개선 제안**: "A. 권한의 상태가 변경되었거나 접속이 허용되지 않은 시간대, 요일에 접속을 시도한 경우 실패할 수 있습니다."
  - 표현은 적절함

#### 21. 문장 표현 개선
- **현재**: "A. QueryPie에서는 QueryPie User Agent를 통해서만 Windows Server에 접속이 가능합니다."
- **개선 제안**: "A. QueryPie에서는 QueryPie User Agent를 통해서만 Windows Server에 접속이 가능합니다."
  - 표현은 적절함

#### 22. 문장 표현 개선
- **현재**: "QueryPie User Agent 설치 후, 권한을 부여 받은 Windows Server를 우클릭, `Open Connection with` 메뉴를 클릭 후, PC에 설치된 RDP Client를 클릭하여 접속합니다."
- **개선 제안**: "QueryPie User Agent 설치 후, 권한을 부여받은 Windows Server를 우클릭, `Open Connection with` 메뉴를 클릭 후 PC에 설치된 RDP Client를 클릭하여 접속합니다."
  - "부여 받은" → "부여받은" (띄어쓰기 제거)
  - "클릭 후," → "클릭 후" (쉼표 제거)

#### 23. 문장 표현 개선
- **현재**: "A. 사용자의 PC가 macOS일 때, QueryPie User Agent를 통해서 macOS에 접속이 가능합니다."
- **개선 제안**: "A. 사용자의 PC가 macOS일 때, QueryPie User Agent를 통해서 macOS에 접속이 가능합니다."
  - 표현은 적절함

#### 24. 문장 표현 개선
- **현재**: "QueryPie User Agent 설치 후, 권한을 부여 받은 macOS를 우클릭, `Open Connection with` 메뉴를 클릭 후, macOS에 설치된 화면 공유.app을 클릭하여 접속합니다. 접속시, macOS의 계정 정보를 직접 입력해야합니다."
- **개선 제안**: "QueryPie User Agent 설치 후, 권한을 부여받은 macOS를 우클릭, `Open Connection with` 메뉴를 클릭 후 macOS에 설치된 화면 공유.app을 클릭하여 접속합니다. 접속 시, macOS의 계정 정보를 직접 입력해야 합니다."
  - "부여 받은" → "부여받은" (띄어쓰기 제거)
  - "클릭 후," → "클릭 후" (쉼표 제거)
  - "접속시," → "접속 시," (띄어쓰기 추가)
  - "해야합니다" → "해야 합니다" (띄어쓰기 추가)

### 권장 수정사항

1. **Overview 섹션 수정**:
   ```markdown
   사용자는 권한이 있는 서버의 목록을 서버, 서버 그룹별 또는 Cloud Provider별로 정렬하여 한눈에 확인할 수 있습니다. 접속할 서버를 선택 후 사용자는 운영체제와 상관없이 웹 브라우저를 통해 제공되는 웹 터미널과 웹 SFTP를 통해 명령어를 실행하고 작업을 수행할 수 있습니다.
   ```

2. **Role 선택하기 섹션 수정**:
   ```markdown
   1. Servers 메뉴로 첫 접속 시 표시되는 Role 선택 화면에서 접속을 위해 사용할 Role을 선택합니다.
   ```

3. **서버에 접속하기 섹션 수정**:
   ```markdown
   1. Role 선택 후에는 좌측의 패널에서 현재 사용자가 접근 가능한 서버 목록을 확인할 수 있습니다.
     1. Sort by Server Group: 서버 목록은 서버 그룹이 우선 정렬되며 하단에 개별 서버가 정렬됩니다. 만약 정렬 방식을 서버 그룹 없이 서버로만 표시하길 원한다면 좌측 상단에 있는 `Sort by Server Group` 버튼을 Off 상태로 변경하면 됩니다.
     2. Time-limited items only: 시간 단위로 권한을 부여받은 서버만 리스트에서 표시합니다.
     3. Search by Host: 서버 목록의 검색 기준이 기존 서버 이름에서 Host(IP 주소)로 변경됩니다. 동시에 서버 목록의 표기 방식도 Host로 전환되어 표시됩니다. 토글이 비활성화된 상태에서는 서버 이름으로만 검색할 수 있습니다.
   2. 서버 목록에서 서버를 선택하면 우측 페이지에서 서버 및 계정 정보를 확인할 수 있습니다.
     1. **Server OS**: 해당 서버의 OS가 표시됩니다.
     2. **Host**: 해당 서버의 호스트가 표시됩니다.
     3. **Account**: 권한이 있는 계정 목록입니다. 계정 뒤의 괄호 안에는 서버 및 계정이 속한 서버 그룹이 표시됩니다.
     4. **Custom Account**: Account에서 카테고리가 QueryPie - Custom Account인 계정을 선택했을 때 표시됩니다. 사전에 등록된 계정 외에 접속하려는 서버의 계정을 입력합니다. 해당 계정의 비밀번호는 Password 필드에 입력하면 됩니다.
     5. **View Detailed Policy Application**: 선택한 계정에 적용된 정책을 표시합니다.
        1. **Access Time**: 접속 가능 시간을 표시합니다.
        2. **Weekday Access Allowed**: 접속 가능 요일을 표시합니다.
        3. **Restrict Commands (SSH)**: SSH 접속 시 차단 명령어를 표시합니다.
        4. **Restrict Functions (SFTP)**: SFTP 접속 시 차단 기능을 표시합니다.
     6. **Password** (또는 SSH Key): 선택한 계정의 인증 방식이 Password일 경우 Password를 입력할 수 있는 필드가 표시됩니다. 만약 자동 로그인 설정이 되어있다면 Password 항목이 표시되지 않으며, 관리자가 설정한 패스워드 또는 SSH Key로 로그인을 하게 됩니다.
     7. **Status**: 선택한 계정의 상태가 표시됩니다.
     8. **Protocol**: SSH, SFTP 또는 RDP를 선택하여 접속할 수 있습니다.
   3. 하단의 `Connect` 버튼을 클릭하여 서버에 접속합니다.
   ```

4. **Callout 내용 수정**:
   ```markdown
   A. QueryPie에서는 QueryPie User Agent를 통해서만 Windows Server에 접속이 가능합니다. 접속 방법은 아래와 같습니다.
   
   QueryPie User Agent 설치 후, 권한을 부여받은 Windows Server를 우클릭, `Open Connection with` 메뉴를 클릭 후 PC에 설치된 RDP Client를 클릭하여 접속합니다.
   
   A. 사용자의 PC가 macOS일 때, QueryPie User Agent를 통해서 macOS에 접속이 가능합니다. 접속 방법은 아래와 같습니다.
   
   QueryPie User Agent 설치 후, 권한을 부여받은 macOS를 우클릭, `Open Connection with` 메뉴를 클릭 후 macOS에 설치된 화면 공유.app을 클릭하여 접속합니다. 접속 시, macOS의 계정 정보를 직접 입력해야 합니다.
   ```

### 기타 사항
- Callout 컴포넌트 사용이 적절합니다.
- 이미지 참조와 캡션이 적절하게 설정되어 있습니다.
- 전체적인 문서 구조는 체계적이고 사용자 친화적입니다.

### 최종 평가
문서의 구조와 내용은 우수하지만, 위에서 제시한 문장 표현 개선과 띄어쓰기 수정을 통해 더욱 완성도 높은 문서로 개선할 수 있습니다.
