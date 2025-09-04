# 교정/교열 결과: requesting-server-access.mdx

**검토일시**: 2025-09-04  
**검토 수행 AI Agent**: Claude Sonnet 4

## 검토 결과

### 전체적인 평가
Server Access Request 요청하기 문서로, 서버 접근 권한 요청의 전체 프로세스를 단계별로 상세하게 안내하고 있습니다. Callout 컴포넌트와 이미지를 활용한 구성이 효과적입니다.

### 발견된 문제점 및 개선사항

#### 1. 문장 표현 개선
- **현재**: "Approval Expiration Date은 Access Expiration Date을 초과할 수 없습니다."
- **개선 제안**: "Approval Expiration Date는 Access Expiration Date를 초과할 수 없습니다."
  - "Date은" → "Date는" (조사 수정)
  - "Date을" → "Date를" (조사 수정)

#### 2. 문장 표현 개선
- **현재**: "초과한 경우, 상신 할 수 없습니다."
- **개선 제안**: "초과한 경우 상신할 수 없습니다."
  - "상신 할 수" → "상신할 수" (띄어쓰기 제거)

#### 3. 문장 표현 개선
- **현재**: "Urgent mode = On 으로 설정 후 결재 요청을 등록하면 즉시 권한을 부여받거나 작업을 수행할 수 있습니다."
- **개선 제안**: "Urgent mode = On으로 설정 후 결재 요청을 등록하면 즉시 권한을 부여받거나 작업을 수행할 수 있습니다."
  - "On 으로" → "On으로" (띄어쓰기 제거)

#### 4. 문장 표현 개선
- **현재**: "오른쪽의 Servers 목록에서 요청 대상 서버를 선택합니다.(다중 선택 가능, 선택한 서버 개수가 우측 상단에 표시됨)"
- **개선 제안**: "오른쪽의 Servers 목록에서 요청 대상 서버를 선택합니다. (다중 선택 가능, 선택한 서버 개수가 우측 상단에 표시됨)"
  - "선택합니다.(" → "선택합니다. (" (띄어쓰기 추가)

#### 5. 문장 표현 개선
- **현재**: "Accounts에서 권한을 요청하고자 하는 계정을 선택합니다. (다중 선택 가능)"
- **개선 제안**: "Accounts에서 권한을 요청하고자 하는 계정을 선택합니다. (다중 선택 가능)"
  - 표현은 적절함

#### 6. 문장 표현 개선
- **현재**: "Start Trigger : 권한 부여 시작 조건을 선택합니다."
- **개선 제안**: "Start Trigger: 권한 부여 시작 조건을 선택합니다."
  - "Start Trigger :" → "Start Trigger:" (띄어쓰기 제거)

#### 7. 문장 표현 개선
- **현재**: "Access to the Server : 사용자가 서버에 접근할 때 즉시 권한이 활성화됩니다."
- **개선 제안**: "Access to the Server: 사용자가 서버에 접근할 때 즉시 권한이 활성화됩니다."
  - "Server :" → "Server:" (띄어쓰기 제거)

#### 8. 문장 표현 개선
- **현재**: "Grant : 권한 부여 즉시 타이머가 시작되며, 사용자의 실제 접속 여부와 관계없이 지정된 기간 동안만 권한이 유효합니다."
- **개선 제안**: "Grant: 권한 부여 즉시 타이머가 시작되며, 사용자의 실제 접속 여부와 관계없이 지정된 기간 동안만 권한이 유효합니다."
  - "Grant :" → "Grant:" (띄어쓰기 제거)

#### 9. 문장 표현 개선
- **현재**: "Duration(Minutes) : 서버 접근 권한이 유효한 시간을 분 단위로 입력합니다."
- **개선 제안**: "Duration(Minutes): 서버 접근 권한이 유효한 시간을 분 단위로 입력합니다."
  - "Duration(Minutes) :" → "Duration(Minutes):" (띄어쓰기 제거)

#### 10. 문장 표현 개선
- **현재**: "Access Expiration Date : 요청 권한의 만료일자를 입력합니다."
- **개선 제안**: "Access Expiration Date: 요청 권한의 만료일을 입력합니다."
  - "Date :" → "Date:" (띄어쓰기 제거)
  - "만료일자" → "만료일" (더 자연스러운 표현)

#### 11. 문장 표현 개선
- **현재**: "요청을 모두 작성하였다면 `Submit` 버튼을 눌러 상신을 완료합니다."
- **개선 제안**: "요청을 모두 작성했다면 `Submit` 버튼을 눌러 상신을 완료합니다."
  - "작성하였다면" → "작성했다면" (더 간결한 표현)

#### 12. 문장 표현 개선
- **현재**: "Direct Permission으로 부여된 권한은 서버 목록에서 **Default Role** 을 선택할 경우에 적용됩니다."
- **개선 제안**: "Direct Permission으로 부여된 권한은 서버 목록에서 **Default Role**을 선택할 경우에 적용됩니다."
  - "**Default Role** 을" → "**Default Role**을" (띄어쓰기 제거)

### 권장 수정사항

1. **결재 규칙 선택하기 섹션 수정**:
   ```markdown
   * **Approval Expiration Date**: 승인 만료일을 입력합니다. Maximum Approval Duration을 통해 최대값을 설정할 수 있습니다. Approval Expiration Date는 Access Expiration Date를 초과할 수 없습니다. 초과한 경우 상신할 수 없습니다. Maximum Approval Duration > Maximum Access Duration인 경우, Maximum Approval Duration의 값이 Maximum Access Duration의 값과 동일하게 적용됩니다. 예) Maximum Approval Duration은 14일이고 Maximum Access Duration은 5일인 경우, Maximum Approval Duration의 값도 5일로 적용됩니다.
   ```

2. **사후 승인으로 요청 보내기 섹션 수정**:
   ```markdown
   * Urgent mode = On으로 설정 후 결재 요청을 등록하면 즉시 권한을 부여받거나 작업을 수행할 수 있습니다.
   ```

3. **요청 대상 서버 추가하기 섹션 수정**:
   ```markdown
   * 오른쪽의 Servers 목록에서 요청 대상 서버를 선택합니다. (다중 선택 가능, 선택한 서버 개수가 우측 상단에 표시됨)
   ```

4. **Require Minute-Based RequestsOn인 경우 섹션 수정**:
   ```markdown
   * **Start Trigger**: 권한 부여 시작 조건을 선택합니다.
     * Access to the Server: 사용자가 서버에 접근할 때 즉시 권한이 활성화됩니다. 서버 세션 유지 여부와 상관없이, 활성화 시점부터 지정된 기간 동안 서버 접속이 가능합니다.
     * Grant: 권한 부여 즉시 타이머가 시작되며, 사용자의 실제 접속 여부와 관계없이 지정된 기간 동안만 권한이 유효합니다.
   * **Duration(Minutes)**: 서버 접근 권한이 유효한 시간을 분 단위로 입력합니다. 1분부터 최대 허용 시간까지 설정할 수 있으며, 지정된 시간이 경과하면 자동으로 접근 권한이 만료됩니다.
   ```

5. **Require Minute-Based RequestsOff인 경우 섹션 수정**:
   ```markdown
   * **Access Expiration Date**: 요청 권한의 만료일을 입력합니다. 기본값은 관리자 페이지에서 SAC configurations > Server Access Request Default Settings의 Maximum Access Duration 값을 따릅니다.
   ```

6. **요청 정보 입력하기 섹션 수정**:
   ```markdown
   * **Submit**: 요청을 모두 작성했다면 `Submit` 버튼을 눌러 상신을 완료합니다.
   ```

7. **Callout 내용 수정**:
   ```markdown
   Direct Permission으로 부여된 권한은 서버 목록에서 **Default Role**을 선택할 경우에 적용됩니다. 접근 권한 정책은 Server Access Request 신청 시점에 설정된 기본 서버 접근 정책을 적용받습니다.
   ```

### 기타 사항
- Callout 컴포넌트 사용이 적절합니다.
- 이미지 참조와 캡션이 적절하게 설정되어 있습니다.
- 전체적인 문서 구조는 체계적이고 사용자 친화적입니다.

### 최종 평가
문서의 구조와 내용은 우수하지만, 위에서 제시한 문장 표현 개선과 띄어쓰기 수정을 통해 더욱 완성도 높은 문서로 개선할 수 있습니다.
