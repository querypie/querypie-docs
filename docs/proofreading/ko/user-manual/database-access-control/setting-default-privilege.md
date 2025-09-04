# Default Privilege 설정하기 - 교정/교열 결과

**검토일시**: 2025-09-04  
**검토자**: Claude (AI Agent)

## 검토 개요

이 문서는 QueryPie의 Database Access Control에서 Default Privilege를 설정하는 방법에 대한 가이드입니다. 단일 DB 커넥션에 다수의 Privilege 권한이 부여된 경우의 기본 접속 권한 설정 방법을 설명하고 있습니다. 전반적으로 잘 구성되어 있으나, 몇 가지 문법적 개선사항과 표현의 일관성 문제가 있습니다.

## 교정/교열 사항

### 1. 문법 및 표현 개선

#### 1.1 Overview 섹션
- **현재**: "단일 DB 커넥션에 다수의 Privilege 권한이 부여된 경우에 기본으로 접속하는 Default Privilege 를 설정하는 기능입니다."
- **개선**: "단일 DB 커넥션에 다수의 Privilege 권한이 부여된 경우에 기본으로 접속하는 Default Privilege를 설정하는 기능입니다."
- **이유**: "Default Privilege 를" → "Default Privilege를" (띄어쓰기 수정)

#### 1.2 Default Privilege 설정하기 섹션
- **현재**: "1. 부여받은 권한이 1개일 경우, 웹, 프록시, SQL Request, Export Request, SQL Jobs 모두 해당 권한으로 접속하며 별도의 Default Privilege 설정을 하지 않습니다."
- **개선**: "1. 부여받은 권한이 1개일 경우 웹, 프록시, SQL Request, Export Request, SQL Jobs 모두 해당 권한으로 접속하며 별도의 Default Privilege 설정을 하지 않습니다."
- **이유**: 불필요한 쉼표 제거

- **현재**: "2. 부여받은 권한이 2개 이상인 경우, 사용자는 별도로 Default Privilege 설정을 해야합니다."
- **개선**: "2. 부여받은 권한이 2개 이상인 경우 사용자는 별도로 Default Privilege 설정을 해야 합니다."
- **이유**: 불필요한 쉼표 제거, "해야합니다" → "해야 합니다" (띄어쓰기 수정)

- **현재**: "1. Privileges 우측에 `Edit` 버튼 또는 `&gt; Go to Settings` 링크를 클릭합니다."
- **개선**: "1. Privileges 우측에 `Edit` 버튼 또는 `&gt; Go to Settings` 링크를 클릭합니다."
- **이유**: 현재 표현이 적절합니다.

- **현재**: "2. Privilege 항목에서 부여받은 권한 중 기본 값으로 사용할 Privilege 를 선택합니다."
- **개선**: "2. Privilege 항목에서 부여받은 권한 중 기본값으로 사용할 Privilege를 선택합니다."
- **이유**: "기본 값" → "기본값" (띄어쓰기 수정), "Privilege 를" → "Privilege를" (띄어쓰기 수정)

- **현재**: "3. Save 버튼을 클릭하여 Default Privilege 설정을 완료합니다."
- **개선**: "3. Save 버튼을 클릭하여 Default Privilege 설정을 완료합니다."
- **이유**: 현재 표현이 적절합니다.

#### 1.3 Callout 섹션
- **현재**: "* 부여받은 권한이 2개 이상이지만 Default Privilege 설정이 안되어 있는 경우에는 가장 먼저 grant된 privilege가 default privilege가 됩니다."
- **개선**: "* 부여받은 권한이 2개 이상이지만 Default Privilege 설정이 안 되어 있는 경우에는 가장 먼저 grant된 privilege가 default privilege가 됩니다."
- **이유**: "안되어" → "안 되어" (띄어쓰기 수정)

- **현재**: "에이전트 프록시, SQL Request, Export Request 에서 접속시 Default Privilege 로 선택된 권한으로 DB 에 접속합니다."
- **개선**: "에이전트 프록시, SQL Request, Export Request에서 접속 시 Default Privilege로 선택된 권한으로 DB에 접속합니다."
- **이유**: "Request 에서" → "Request에서" (띄어쓰기 수정), "접속시" → "접속 시" (띄어쓰기 수정), "Privilege 로" → "Privilege로" (띄어쓰기 수정), "DB 에" → "DB에" (띄어쓰기 수정)

- **현재**: "* Default Privilege 변경은 웹과 Multi-Agent에서 제공합니다."
- **개선**: "* Default Privilege 변경은 웹과 Multi-Agent에서 제공합니다."
- **이유**: 현재 표현이 적절합니다.

- **현재**: "User Agent에서는 Default Privilege 변경 기능은 제공하지 않으며, 사용자는 접속할 Privilege 를 변경하고자 하는 경우 웹페이지에서 변경하여야 합니다."
- **개선**: "User Agent에서는 Default Privilege 변경 기능을 제공하지 않으며 사용자는 접속할 Privilege를 변경하고자 하는 경우 웹페이지에서 변경하여야 합니다."
- **이유**: "기능은 제공하지 않으며," → "기능을 제공하지 않으며" (문법 수정), "Privilege 를" → "Privilege를" (띄어쓰기 수정), 불필요한 쉼표 제거

- **현재**: "* Default Privilege 로 커넥션에 이미 접속되어 있는 상태에서 Default Privilege 를 변경한 경우 또는 해당 권한을 회수한 경우, 기존 세션은 Disconnect 처리하고 새로운 Default 권한으로 새로 Connect 처리합니다."
- **개선**: "* Default Privilege로 커넥션에 이미 접속되어 있는 상태에서 Default Privilege를 변경한 경우 또는 해당 권한을 회수한 경우 기존 세션은 Disconnect 처리하고 새로운 Default 권한으로 새로 Connect 처리합니다."
- **이유**: "Privilege 로" → "Privilege로" (띄어쓰기 수정), "Privilege 를" → "Privilege를" (띄어쓰기 수정), 불필요한 쉼표 제거

- **현재**: "*  부여받은 권한이 2개 이상인 경우 Default privilege 설정이 되어 있지 않고 privilege deactivation period 초과로 inactive 상태가 된 경우 agent를 통해 접속할 수 없습니다."
- **개선**: "* 부여받은 권한이 2개 이상인 경우 Default privilege 설정이 되어 있지 않고 privilege deactivation period 초과로 inactive 상태가 된 경우 agent를 통해 접속할 수 없습니다."
- **이유**: 불필요한 공백 제거

- **현재**: "Default privilege가 설정 되어 있어도 상태가 privilege deactivation period 초과로 inactive 인 경우 접속할 수 없습니다."
- **개선**: "Default privilege가 설정되어 있어도 상태가 privilege deactivation period 초과로 inactive인 경우 접속할 수 없습니다."
- **이유**: "설정 되어" → "설정되어" (띄어쓰기 수정), "inactive 인" → "inactive인" (띄어쓰기 수정)

## 전체적인 평가

이 문서는 QueryPie의 Database Access Control에서 Default Privilege 설정 방법에 대한 명확한 가이드를 제공하고 있습니다. 단일 권한과 다중 권한 상황을 구분하여 설명하고 있으며, 중요한 주의사항들을 Callout으로 잘 정리하고 있습니다. 다만, 띄어쓰기 오류, 문법적 오류, 그리고 일부 표현의 자연스러움 개선이 필요합니다.

## 권장사항

1. 띄어쓰기 규칙 준수 (특히 조사와의 띄어쓰기)
2. 문법적 오류 수정 (예: "기능은 제공하지 않으며" → "기능을 제공하지 않으며")
3. 불필요한 쉼표 제거
4. 일관된 용어 사용 (예: "기본값", "접속 시")
5. 불필요한 공백 제거
