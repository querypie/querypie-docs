# QueryPie 제품 및 API 명칭 지침

이 문서는 QueryPie 제품 및 QueryPie ACP External API 문서 작성 시 사용할 명칭 및 지칭에 대한 가이드입니다.

## 개요

제품명이 QueryPie에서 QueryPie ACP (Access Control Platform)로 변경됨에 따라, 문서에서 사용하는 명칭도 일관되게 유지해야 합니다.
이 가이드는 제품명과 API 명칭에 대한 일관된 사용을 위한 기준을 제공합니다.

## QueryPie 제품명 가이드

### 1. 공식 제품명

**"QueryPie ACP"** (권장)
- 현재 공식 제품명
- 모든 문서에서 제품을 지칭할 때 사용
- 사용 예시:
  - "QueryPie ACP는 통합 액세스 제어 솔루션입니다."
  - "QueryPie ACP 관리자 매뉴얼"

**"QueryPie Access Control Platform"** (전체명)
- 첫 언급 시 또는 공식적인 맥락에서 사용
- 약어 (ACP)를 함께 표기하는 것을 권장
- 사용 예시:
  - "QueryPie Access Control Platform (ACP)은..."
  - 이후에는 "QueryPie ACP"로 간략히 사용 가능

### 2. 제품 구성 요소

QueryPie ACP는 다음 4가지 핵심 구성 요소로 이루어져 있습니다:

- **DAC (Database Access Controller)**: 데이터베이스 액세스 제어 및 감사
- **SAC (System Access Controller)**: 시스템 및 서버 액세스 제어
- **KAC (Kubernetes Access Controller)**: Kubernetes 클러스터 액세스 제어
- **WAC (Web Access Controller)**: 웹 애플리케이션 액세스 제어

**사용 가이드:**
- 구성 요소를 언급할 때는 약어와 전체명을 함께 표기
- 예시: "DAC (Database Access Controller)", "SAC (System Access Controller)"
- 반복 사용 시에는 약어만 사용 가능: "DAC", "SAC", "KAC", "WAC"

### 3. 제품명 사용 규칙

| 상황 | 권장 명칭 | 예시 |
|------|----------|------|
| 문서 제목 | QueryPie ACP | "QueryPie ACP 제품 문서" |
| 첫 언급 | QueryPie Access Control Platform (ACP) | "QueryPie Access Control Platform (ACP)은..." |
| 일반 언급 | QueryPie ACP | "QueryPie ACP의 기능" |
| 구성 요소 | DAC (Database Access Controller) | "DAC (Database Access Controller)는..." |

### 4. 레거시 명칭 처리

**"QueryPie"** (단독 사용)
- 레거시 명칭으로, 현재는 사용하지 않음
- 기존 문서나 레거시 참조에서만 사용
- 새로운 문서 작성 시에는 "QueryPie ACP" 사용

**주의사항:**
- 기존 문서에서 "QueryPie"를 발견하면 "QueryPie ACP"로 업데이트 권장
- API 문서에서는 "QueryPie ACP External API" 사용

## QueryPie ACP External API 명칭 가이드

### API 명칭 체계

#### 1. 공식 명칭 (문서 제목, 주요 섹션)

**"QueryPie ACP External API"** (권장)
- 제품명을 포함하여 명확함
- "External"을 포함하여 웹 콘솔 외부에서 사용하는 API임을 구분
- 사용 예시:
  - 문서 제목: "QueryPie ACP External API 레퍼런스"
  - 주요 섹션: "QueryPie ACP External API 소개"

**"QueryPie ACP API"** (대안)
- 더 간결한 표현
- "External"이 생략되어도 문맥상 명확한 경우 사용 가능

#### 2. 간략 명칭 (본문 내 반복 사용)

**"ACP External API"** 또는 **"ACP API"**
- 제품명이 이미 언급된 후 반복 사용 시
- 사용 예시:
  - "QueryPie ACP External API는 RESTful API 방식으로 구현된 API입니다."
  - "ACP External API를 사용하면 다음을 수행할 수 있습니다:"

#### 3. 버전별 명칭

**전체 명칭:**
- "QueryPie ACP External API V2" / "ACP External API V2"
- "QueryPie ACP External API V0.9" / "ACP External API V0.9"

**간략 명칭:**
- "V2 API"
- "V0.9 API"

#### 4. API와 제품명의 관계

- API 문서에서 제품명을 언급할 때는 "QueryPie ACP" 사용
- API는 제품의 기능이므로 "QueryPie ACP의 External API" 또는 "QueryPie ACP External API"로 표현

### API 명칭 사용 가이드

| 상황 | 권장 명칭 | 예시 |
|------|----------|------|
| 문서 제목 | QueryPie ACP External API | "QueryPie ACP External API 레퍼런스" |
| 첫 언급 | QueryPie ACP External API | "QueryPie ACP External API는..." |
| 반복 사용 | ACP External API | "ACP External API를 사용하면..." |
| 버전 구분 | ACP External API V2 | "ACP External API V2는..." |
| 간략 표현 | ACP API | 문맥상 명확한 경우 |

### API 명칭 선택 기준

1. **문서 제목/주요 섹션**: "QueryPie ACP External API" 사용
2. **첫 언급**: "QueryPie ACP External API" 사용
3. **반복 사용**: "ACP External API" 또는 "ACP API" 사용
4. **버전 구분**: "ACP External API V2" 또는 "V2 API" 사용
5. **제품명과의 구분**: 제품명은 "QueryPie ACP", API는 "External API"로 구분

## 통합 명칭 체계 요약

### 제품명

1. **공식 제품명**: "QueryPie ACP"
2. **전체명**: "QueryPie Access Control Platform (ACP)" (첫 언급 시)
3. **구성 요소**: "DAC (Database Access Controller)", "SAC (System Access Controller)", "KAC (Kubernetes Access Controller)", "WAC (Web Access Controller)"

### API 명칭

1. **공식 명칭**: "QueryPie ACP External API"
2. **간략 명칭**: "ACP External API" 또는 "ACP API"
3. **버전별**: "ACP External API V2", "ACP External API V0.9"

## 사용 예시

### 제품명 사용 예시

```markdown
# QueryPie ACP 제품 문서

## QueryPie Access Control Platform (ACP)이란?

QueryPie Access Control Platform (ACP)은 통합 액세스 제어 솔루션입니다.
QueryPie ACP는 DAC, SAC, KAC, WAC를 단일 플랫폼으로 제공합니다.

### 핵심 구성 요소

- **DAC (Database Access Controller)**: 데이터베이스 액세스 제어 및 감사
- **SAC (System Access Controller)**: 시스템 및 서버 액세스 제어
- **KAC (Kubernetes Access Controller)**: Kubernetes 클러스터 액세스 제어
- **WAC (Web Access Controller)**: 웹 애플리케이션 액세스 제어
```

### API 문서 제목 및 소개

```markdown
# QueryPie ACP External API 레퍼런스

QueryPie ACP External API 레퍼런스 문서에 오신 것을 환영합니다.
이 문서는 QueryPie Access Control Platform (ACP)과 프로그래밍 방식으로 상호작용할 수 있는 RESTful API에 대한 종합적인 가이드를 제공합니다.

## API 소개

QueryPie ACP External API는 RESTful API 방식으로 구현된 API입니다.
ACP External API를 사용하면 다음을 수행할 수 있습니다:
```

### 버전 정보

```markdown
## API 버전

QueryPie ACP External API는 두 가지 버전을 지원합니다:

### V2 API

- **현재 권장되는 API 버전**입니다.
- QueryPie ACP 버전 9.16.1부터 지원됩니다.
- 호출 경로: `{querypie url}/api/external/v2/`
- 기존 V0.9 API와 호환되지 않습니다.
- V0.9 API와는 다른 엔드포인트 구조와 요청/응답 형식을 사용합니다.

### V0.9 API

- **레거시 API 버전**으로, Version 9.16 이전에 제공하던 API입니다.
- **2026년 상반기 릴리즈에서 Deprecate 예정**입니다.
- **2026년 하반기 릴리즈에서 제거 예정**입니다.
```

### 상세 문서 링크

```markdown
### 버전 11.4.1

- [ACP External API V2](api-reference/11.4.1/v2) - 현행 API (권장)
- [ACP External API V0.9](api-reference/11.4.1/v0.9) - 레거시 API (Deprecate 예정)
```

## 주의사항

### 제품명 관련

1. **일관성 유지**: 모든 문서에서 "QueryPie ACP"를 제품명으로 일관되게 사용해야 합니다.
2. **레거시 명칭**: "QueryPie" 단독 사용은 피하고, "QueryPie ACP"로 통일합니다.
3. **구성 요소**: DAC, SAC, KAC, WAC 언급 시 첫 사용 시에는 전체명과 함께 표기합니다.
4. **약어 사용**: "ACP"는 "Access Control Platform"의 약어임을 명확히 합니다.

### API 명칭 관련

1. **제품명과의 구분**: "QueryPie ACP"는 제품명, "External API"는 API 기능을 지칭합니다.
2. **첫 언급 시**: "QueryPie ACP External API" 전체 명칭을 사용하고, 이후에는 "ACP External API"로 간략히 사용할 수 있습니다.
3. **버전 정보**: V0.9 API는 Deprecate 예정이므로 이를 명시해야 합니다.
4. **일관성**: 문서 전체에서 API 명칭을 일관되게 사용해야 합니다.

## 체크리스트

문서 작성 시 다음 사항을 확인하세요:

### 제품명 체크리스트

- [ ] 제품명이 "QueryPie ACP"로 통일되어 있는가?
- [ ] 첫 언급 시 "QueryPie Access Control Platform (ACP)"로 표기했는가?
- [ ] 구성 요소(DAC, SAC, KAC, WAC) 첫 언급 시 전체명을 함께 표기했는가?
- [ ] 레거시 "QueryPie" 단독 사용이 없는가?

### API 명칭 체크리스트

- [ ] 문서 제목에 "QueryPie ACP External API"를 사용했는가?
- [ ] 첫 언급 시 전체 명칭을 사용했는가?
- [ ] 반복 사용 시 간략 명칭("ACP External API")을 적절히 사용했는가?
- [ ] 버전 정보가 명확히 표기되어 있는가?
- [ ] V0.9 API Deprecate 정보가 포함되어 있는가?

## 참고

- 이 가이드는 QueryPie ACP 제품명 변경에 따라 작성되었습니다.
- 모든 문서 작성 시 이 가이드를 참조하여 일관된 명칭을 사용해주세요.
- 명칭 관련 문의사항이 있으면 문서 팀에 문의해주세요.
- 이 가이드는 필요에 따라 업데이트될 수 있습니다.

