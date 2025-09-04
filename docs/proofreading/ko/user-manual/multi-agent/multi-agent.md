# Multi Agent - 교정/교열 결과

**검토일시**: 2025-09-04  
**검토자**: Claude (AI Agent)

## 검토 개요

이 문서는 QueryPie Multi Agent에 대한 종합적인 사용 가이드입니다. DAC, KAC, SAC 서비스별 사용법과 설정 방법을 상세히 설명하고 있으며, 전반적으로 잘 구성되어 있습니다. 다만, 몇 가지 문법적 개선사항과 표현의 일관성 문제가 있습니다.

## 교정/교열 사항

### 1. 문법 및 표현 개선

#### 1.1 Overview 섹션
- **현재**: "QueryPie Multi Agent는 여러 개의 QueryPie Host를 동시에 사용할 수 있도록 개선된 Proxy Agent입니다."
- **개선**: "QueryPie Multi Agent는 여러 개의 QueryPie Host를 동시에 사용할 수 있도록 개선된 Proxy Agent입니다."
- **이유**: 현재 표현이 적절합니다.

- **현재**: "Agent UI에서는 특정 Host에서 사용 가능한 리소스들을 확인할 수 있습니다."
- **개선**: "Agent UI에서는 특정 Host에서 사용 가능한 리소스들을 확인할 수 있습니다."
- **이유**: 현재 표현이 적절합니다.

- **현재**: "Agent 설치 및 Host 별 로그인 수행만으로 추가 설정 없이 둘 이상의 QueryPie Proxy를 통한 리소스 접속이 가능합니다."
- **개선**: "Agent 설치 및 Host별 로그인 수행만으로 추가 설정 없이 둘 이상의 QueryPie Proxy를 통한 리소스 접속이 가능합니다."
- **이유**: "Host 별" → "Host별" (띄어쓰기 수정)

#### 1.2 지원 버전 섹션
- **현재**: "Multi Agent는 `10.2.5` 버전 또는 이후 버전의 QueryPie Host만을 지원합니다."
- **개선**: "Multi Agent는 `10.2.5` 버전 또는 이후 버전의 QueryPie Host만을 지원합니다."
- **이유**: 현재 표현이 적절합니다.

- **현재**: "동일한 PC에 기존의 User Agent와 Multi Agent 둘 다 설치하는 것은 가능합니다."
- **개선**: "동일한 PC에 기존의 User Agent와 Multi Agent 둘 다 설치하는 것이 가능합니다."
- **이유**: "것은"보다는 "것이"가 더 자연스러운 표현입니다.

#### 1.3 에이전트 앱 다운로드 및 초기 설정 섹션
- **현재**: "QueryPie 로그인 후 우측 상단 프로필을 클릭한 뒤 Download & Support &gt; `Multi-Agent` 버튼을 클릭합니다."
- **개선**: "QueryPie 로그인 후 우측 상단 프로필을 클릭한 뒤 Download & Support &gt; `Multi-Agent` 버튼을 클릭합니다."
- **이유**: 현재 표현이 적절합니다.

- **현재**: "QueryPie Multi-Agent Downloads 팝업창이 실행되면"
- **개선**: "QueryPie Multi-Agent Downloads 팝업 창이 실행되면"
- **이유**: "팝업창" → "팝업 창" (띄어쓰기 수정)

- **현재**: "Step 1에서 사용 중인 PC 운영체제에 맞는 설치 파일을 다운로드한 후"
- **개선**: "Step 1에서 사용 중인 PC 운영체제에 맞는 설치 파일을 다운로드한 후"
- **이유**: 현재 표현이 적절합니다.

- **현재**: "다운로드받은 QueryPie Multi-Agent 설치 프로그램을 실행한 뒤"
- **개선**: "다운로드받은 QueryPie Multi-Agent 설치 프로그램을 실행한 후"
- **이유**: "뒤"보다는 "후"가 더 격식 있는 표현입니다.

- **현재**: "설치 완료된 QueryPie Agent를 실행하면 Host 최초 등록 페이지가 열립니다."
- **개선**: "설치 완료된 QueryPie Agent를 실행하면 Host 최초 등록 페이지가 열립니다."
- **이유**: 현재 표현이 적절합니다.

- **현재**: "QueryPie Host 입력란에 미리 복사해뒀던 QueryPie URL을 입력하고"
- **개선**: "QueryPie Host 입력란에 미리 복사해둔 QueryPie URL을 입력하고"
- **이유**: "복사해뒀던"보다는 "복사해둔"이 더 자연스러운 표현입니다.

#### 1.4 DAC 섹션
- **현재**: "Database 탭에서 선택된 QueryPie Host 에 대해 권한이 부여되어 있고"
- **개선**: "Database 탭에서 선택된 QueryPie Host에 대해 권한이 부여되어 있고"
- **이유**: "Host 에" → "Host에" (띄어쓰기 수정)

- **현재**: "접속하고자 하는 커넥션을 선택하고 마우스 오른쪽 버튼을 클릭하면"
- **개선**: "접속하고자 하는 커넥션을 선택하고 마우스 오른쪽 버튼을 클릭하면"
- **이유**: 현재 표현이 적절합니다.

- **현재**: "Open Connection With **[10.2.6~]**: 3rd Party 툴로 커넥션에 접속할 수 있습니다."
- **개선**: "Open Connection With **[10.2.6~]**: 3rd Party 툴로 커넥션에 접속할 수 있습니다."
- **이유**: 현재 표현이 적절합니다.

- **현재**: "DBeaver 를 열고 커넥션의 정보를 삽입해줍니다."
- **개선**: "DBeaver를 열고 커넥션의 정보를 삽입해줍니다."
- **이유**: "DBeaver 를" → "DBeaver를" (띄어쓰기 수정)

- **현재**: "최초 1회의 DBeaver 경로 인식 과정이 필요합니다."
- **개선**: "최초 1회의 DBeaver 경로 인식 과정이 필요합니다."
- **이유**: 현재 표현이 적절합니다.

- **현재**: "DBeaver가 실행 중인 상태에서 본 기능을 실행하시기를 권장합니다."
- **개선**: "DBeaver가 실행 중인 상태에서 본 기능을 실행하시기를 권장합니다."
- **이유**: 현재 표현이 적절합니다.

- **현재**: "DataGrip: DataGrip에 붙여넣을 수 있는 커넥션 정보가 복사됩니다."
- **개선**: "DataGrip: DataGrip에 붙여넣을 수 있는 커넥션 정보가 복사됩니다."
- **이유**: 현재 표현이 적절합니다.

- **현재**: "SQLGate for Oracle (Windows만 지원): SQLGate for Oracle 을 열고 커넥션 정보를 삽입해줍니다."
- **개선**: "SQLGate for Oracle (Windows만 지원): SQLGate for Oracle을 열고 커넥션 정보를 삽입해줍니다."
- **이유**: "Oracle 을" → "Oracle을" (띄어쓰기 수정)

- **현재**: "Copy as JDBC URL **[10.2.6~]**: 선택한 커넥션의 JDBC URL을 복사해줍니다."
- **개선**: "Copy as JDBC URL **[10.2.6~]**: 선택한 커넥션의 JDBC URL을 복사해줍니다."
- **이유**: 현재 표현이 적절합니다.

#### 1.5 에이전트에서 3rd Party Database Tool 설정 관리하기 섹션
- **현재**: "Settings &gt; Databases 에서 3rd Party 툴 관련 설정을 관리할 수 있습니다."
- **개선**: "Settings &gt; Databases에서 3rd Party 툴 관련 설정을 관리할 수 있습니다."
- **이유**: "Databases 에서" → "Databases에서" (띄어쓰기 수정)

- **현재**: "Database Tool Path: 지원하는 3rd Party 툴의 경로를 설정할 수 있습니다."
- **개선**: "Database Tool Path: 지원하는 3rd Party 툴의 경로를 설정할 수 있습니다."
- **이유**: 현재 표현이 적절합니다.

- **현재**: "Auto Detected : Open Connection With 로 툴을 선택할 때마다 툴의 경로를 자동으로 찾습니다."
- **개선**: "Auto Detected: Open Connection With로 툴을 선택할 때마다 툴의 경로를 자동으로 찾습니다."
- **이유**: "Detected :" → "Detected:", "With 로" → "With로" (띄어쓰기 수정)

- **현재**: "툴이 제대로 열리지 않는 경우 Manual Configuration 으로 경로를 수동 지정하시기를 바랍니다."
- **개선**: "툴이 제대로 열리지 않는 경우 Manual Configuration으로 경로를 수동 지정하시기를 바랍니다."
- **이유**: "Configuration 으로" → "Configuration으로" (띄어쓰기 수정)

- **현재**: "Manual Configuration : 수동으로 툴이 설치된 경로를 지정합니다."
- **개선**: "Manual Configuration: 수동으로 툴이 설치된 경로를 지정합니다."
- **이유**: "Configuration :" → "Configuration:" (띄어쓰기 수정)

- **현재**: "Do not user the tool : 툴 사용을 비활성화 합니다."
- **개선**: "Do not use the tool: 툴 사용을 비활성화합니다."
- **이유**: "user" → "use" (오타 수정), "Configuration :" → "Configuration:", "비활성화 합니다" → "비활성화합니다" (띄어쓰기 수정)

- **현재**: "커넥션 목록의 컨텍스트 메뉴에서 툴이 숨겨집니다."
- **개선**: "커넥션 목록의 컨텍스트 메뉴에서 툴이 숨겨집니다."
- **이유**: 현재 표현이 적절합니다.

- **현재**: "DataGrip Connection Guide: DataGrip으로 커넥션을 열 때 노출되는 가이드 모달을 계속 볼지 설정합니다."
- **개선**: "DataGrip Connection Guide: DataGrip으로 커넥션을 열 때 노출되는 가이드 모달을 계속 볼지 설정합니다."
- **이유**: 현재 표현이 적절합니다.

#### 1.6 에이전트에서 default privilege 선택하기 섹션
- **현재**: "쿼리파이 DB 접근제어에서 한 사용자가 두개이상의 privilege를 부여받을 수 있습니다."
- **개선**: "QueryPie DB 접근제어에서 한 사용자가 두 개 이상의 privilege를 부여받을 수 있습니다."
- **이유**: "쿼리파이" → "QueryPie" (브랜드명 일관성), "두개이상" → "두 개 이상" (띄어쓰기 수정)

- **현재**: "특정 커넥션에 접근권한을 부여받은 사용자가 여러 그룹에 포함되어 있고"
- **개선**: "특정 커넥션에 접근 권한을 부여받은 사용자가 여러 그룹에 포함되어 있고"
- **이유**: "접근권한" → "접근 권한" (띄어쓰기 수정)

- **현재**: "그룹에 다른 접근 권한을 부여한 경우 이 사용자는 여러개의 privilege가 할당될 수 있습니다."
- **개선**: "그룹에 다른 접근 권한을 부여한 경우 이 사용자는 여러 개의 privilege가 할당될 수 있습니다."
- **이유**: "여러개의" → "여러 개의" (띄어쓰기 수정)

- **현재**: "이 때 proxy를 통해 접속할 때 사용할 Privilege를 agent 화면에서 선택할 수 있습니다."
- **개선**: "이때 proxy를 통해 접속할 때 사용할 Privilege를 agent 화면에서 선택할 수 있습니다."
- **이유**: "이 때" → "이때" (띄어쓰기 수정)

- **현재**: "다중 privilege를 부여받은 후 사용자가 특정 privilege를 default로 설정하지 않으면 접속할 수 없기 때문에"
- **개선**: "다중 privilege를 부여받은 후 사용자가 특정 privilege를 default로 설정하지 않으면 접속할 수 없기 때문에"
- **이유**: 현재 표현이 적절합니다.

- **현재**: "만약 default privilege가 설정되어 있지 않은 경우 아래 그림과 같은 경고 아이콘이 표시됩니다."
- **개선**: "만약 default privilege가 설정되어 있지 않은 경우 아래 그림과 같은 경고 아이콘이 표시됩니다."
- **이유**: 현재 표현이 적절합니다.

- **현재**: "1. 다중 Privilege가 할당된 커넥션에 대해 마우스 오른쪽 버튼을 누르고 메뉴를 호출합니다."
- **개선**: "1. 다중 Privilege가 할당된 커넥션에 대해 마우스 오른쪽 버튼을 클릭하고 메뉴를 호출합니다."
- **이유**: "누르고"보다는 "클릭하고"가 더 격식 있는 표현입니다.

- **현재**: "2. 메뉴에서 Connection Information을 선택합니다."
- **개선**: "2. 메뉴에서 Connection Information을 선택합니다."
- **이유**: 현재 표현이 적절합니다.

- **현재**: "3. Original Information 의 Privilege에서 편집 (연필모양 아이콘) 버튼을 클릭합니다."
- **개선**: "3. Original Information의 Privilege에서 편집 (연필 모양 아이콘) 버튼을 클릭합니다."
- **이유**: "Information 의" → "Information의" (띄어쓰기 수정), "연필모양" → "연필 모양" (띄어쓰기 수정)

- **현재**: "4. Previlege Name 의 항목중 하나를 선택하고 저장합니다."
- **개선**: "4. Privilege Name의 항목 중 하나를 선택하고 저장합니다."
- **이유**: "Previlege" → "Privilege" (오타 수정), "Name 의" → "Name의" (띄어쓰기 수정), "항목중" → "항목 중" (띄어쓰기 수정)

- **현재**: "5. 경고 아이콘이 사라지고 할당된 privilege 이름이 해당 커넥션에 보이는지 확인합니다."
- **개선**: "5. 경고 아이콘이 사라지고 할당된 privilege 이름이 해당 커넥션에 보이는지 확인합니다."
- **이유**: 현재 표현이 적절합니다.

## 전체적인 평가

이 문서는 QueryPie Multi Agent의 포괄적인 사용 가이드로서, DAC, KAC, SAC 서비스별로 상세한 사용법을 제공하고 있습니다. 특히 3rd Party 툴 연동과 설정 관리에 대한 설명이 잘 되어 있습니다. 다만, 띄어쓰기 오류, 브랜드명의 일관성, 그리고 일부 표현의 자연스러움 개선이 필요합니다.

## 권장사항

1. 브랜드명 "QueryPie"의 일관된 사용
2. 띄어쓰기 규칙 준수 (특히 "Host별", "접근 권한", "여러 개의" 등)
3. 오타 수정 ("user" → "use", "Previlege" → "Privilege")
4. 격식 있는 표현 사용 (예: "누르고" → "클릭하고")
5. 일관된 용어 사용
