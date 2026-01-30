# EKS 설치 가이드 문서 개선 설계

## 개요

QueryPie ACP의 AWS EKS 설치 가이드 문서(`installing-on-aws-eks.mdx`)를 실제 테스트 결과(`tpm/aws/eks/` 리포트)를 기반으로 개선하는 설계 문서입니다.

**작성일:** 2026-01-30

## 배경

### 현재 문서의 문제점

1. **누락된 필수 AWS 설정**
   - EBS CSI Driver 설치 및 IAM 설정 없음
   - AWS Load Balancer Controller 설치 과정 없음
   - OIDC Provider 연결 과정 없음

2. **리소스 설정 오류**
   - 메모리 16Gi 요청 → m7i.xlarge 노드에서 `Insufficient memory` 에러
   - allocatable memory (~15Gi) 초과

3. **PersistentVolume 설정 문제**
   - hostPath 사용 (EKS에서 작동 안 함)
   - StorageClass 미지정

4. **Ingress 설정 누락**
   - ALB Controller annotation 없음
   - ACM 인증서 연동 없음

5. **Demo 모드 미활용**
   - Helm Chart 1.5.0의 `demo.enabled` 옵션 미언급
   - 불필요하게 복잡한 수동 MySQL/Redis 설정

### 실제 테스트 결과 (tpm/aws/eks/)

| 항목 | 결과 |
|------|------|
| Helm Chart 버전 | 1.5.0 |
| App 버전 | 11.5.1 |
| 전체 평가 | **PASSED** |
| 발견된 이슈 | EBS CSI Driver IAM, ALB Controller 권한, 메모리 설정 |

## 설계

### 문서 구조 변경

**기존:**
```
installation/
└── installation/
    └── installing-on-aws-eks.mdx (753줄, 모든 내용 포함)
```

**개선 후:**
```
installation/
└── installation/
    ├── installing-on-aws-eks.mdx (개요 + 빠른 시작)
    ├── installing-on-aws-eks-part1-aws-setup.mdx (AWS 환경 설정)
    └── installing-on-aws-eks-part2-helm-deployment.mdx (Helm 배포)
```

### 각 문서의 역할

#### installing-on-aws-eks.mdx (메인 페이지)

**목적:** 개요 제공 및 설치 방식 선택 가이드

**내용:**
1. 개요
   - 목적 및 대상 독자
   - 아키텍처 다이어그램
2. 설치 방식 선택
   - Demo 모드: 내장 MySQL/Redis, 빠른 PoC
   - Production 모드: 외부 관리형 DB
3. 사전 요구사항
   - EKS 클러스터 (K8s 1.24+, m7i.xlarge x 2)
   - 필수 도구 (AWS CLI, kubectl, Helm, eksctl)
4. 설치 가이드 링크
   - Part 1: AWS 환경 설정
   - Part 2: Helm 배포
5. 설치 후 설정
   - 라이선스 설치 (setup.v2.sh 문서와 동일한 형식)
   - Proxy 주소 설정

#### installing-on-aws-eks-part1-aws-setup.mdx (신규)

**목적:** EKS 외부 AWS 리소스 설정

**내용:**
1. OIDC Provider 연결
   ```bash
   eksctl utils associate-iam-oidc-provider --cluster <name> --approve
   ```

2. EBS CSI Driver 설치
   - IAM Role 생성 (`eksctl create iamserviceaccount`)
   - 애드온 설치 (`eksctl create addon`)

3. AWS Load Balancer Controller 설치
   - IAM Policy 생성/업데이트 (v2.11+ 권한 포함)
   - Service Account 생성
   - Helm 설치

4. ACM 인증서 생성
   - 인증서 요청
   - DNS 검증 (Route53)

5. 트러블슈팅
   - `sts:AssumeRoleWithWebIdentity` 에러 대응
   - `DescribeListenerAttributes` 권한 에러 대응

#### installing-on-aws-eks-part2-helm-deployment.mdx (신규)

**목적:** Kubernetes 리소스 및 QueryPie 배포

**내용:**
1. Namespace 생성

2. Secret 생성
   - querypie.env 파일 작성
   - `kubectl create secret`

3. Helm Repository 추가

4. Helm Values 설정
   - **Demo 모드 예시** (기본 권장)
     ```yaml
     querypie:
       resources:
         requests:
           memory: 8Gi
         limits:
           memory: 8Gi
       ingress:
         enabled: true
         ingressClassName: alb
         annotations:
           alb.ingress.kubernetes.io/scheme: internet-facing
           alb.ingress.kubernetes.io/certificate-arn: "${CERT_ARN}"
     demo:
       enabled: true
     ```
   - **Production 모드 예시** (외부 DB 사용 시)
     ```yaml
     demo:
       enabled: false
     config:
       secretName: "querypie-secret"
     ```

5. Helm 설치
   - `envsubst`를 사용한 인증서 ARN 주입

6. DB 마이그레이션
   - `migrate.sh runall` 실행 (필수)

7. Route53 DNS 설정
   - ALB DNS 확인
   - A 레코드 (Alias) 생성

8. 접속 확인
   - Health Check
   - 라이선스 활성화

9. 트러블슈팅
   - `Insufficient memory` 에러
   - `Table 'querypie.system_settings' doesn't exist` 에러

### 주요 변경 사항

#### 1. 리소스 설정 수정

**Before:**
```yaml
resources:
  requests:
    memory: 16Gi
  limits:
    memory: 16Gi
```

**After:**
```yaml
resources:
  requests:
    memory: 8Gi  # m7i.xlarge 노드에 적합
  limits:
    memory: 8Gi
# Note: m7i.xlarge (16GB)의 allocatable memory는 ~15Gi
# 16Gi 요청 시 Insufficient memory 에러 발생
# Production 환경에서는 m7i.2xlarge 이상 권장
```

#### 2. Ingress 설정 추가

**Before:** 빈 annotations

**After:**
```yaml
ingress:
  enabled: true
  ingressClassName: alb
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/certificate-arn: "${CERT_ARN}"
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80}, {"HTTPS": 443}]'
    alb.ingress.kubernetes.io/ssl-redirect: "443"
    alb.ingress.kubernetes.io/healthcheck-path: /api/health
  host: querypie.example.com
```

#### 3. Demo 모드 추가

**새로운 섹션:**
```yaml
# Demo 모드: MySQL과 Redis를 자동으로 배포
# PoC/Demo 환경에 권장
demo:
  enabled: true
  mysql:
    image: mysql:8.0
    rootPassword: "querypie"
    resources:
      limits:
        memory: 2Gi
    volumeClaimTemplate:
      spec:
        resources:
          requests:
            storage: 50Gi
  redis:
    image: redis:7.4
    password: "querypie"
```

#### 4. 수동 MySQL/Redis 설정 제거

현재 문서의 3.1, 3.2 섹션 (MySQL StatefulSet, Redis Deployment 수동 작성)을 제거하고 Demo 모드로 대체합니다.

수동 설정이 필요한 경우 Production 모드 가이드에서 외부 RDS/ElastiCache 사용을 안내합니다.

#### 5. hostPath PV 제거

**Before:**
```yaml
spec:
  hostPath:
    path: /var/lib/mysql
```

**After:**
Demo 모드 사용 시 Helm Chart가 EBS 기반 PVC를 자동 생성합니다.
EBS CSI Driver 설치가 필수 사전 요구사항입니다.

### 트러블슈팅 가이드 업데이트

실제 테스트에서 발견된 이슈를 문서에 반영합니다.

| 증상 | 원인 | 해결책 |
|------|------|--------|
| `0/2 nodes are available: 2 Insufficient memory` | 메모리 요청(16Gi)이 노드 allocatable memory(~15Gi) 초과 | 메모리를 8Gi로 조정 또는 m7i.2xlarge 노드 사용 |
| `failed to provision volume: AccessDeniedException: sts:AssumeRoleWithWebIdentity` | EBS CSI Driver의 OIDC Trust Policy 미설정 | Part 1의 EBS CSI Driver 설치 과정 수행 |
| `AccessDenied: elasticloadbalancing:DescribeListenerAttributes` | ALB Controller v2.11+에서 필요한 권한 누락 | 최신 IAM Policy 다운로드 후 업데이트 |
| `Table 'querypie.system_settings' doesn't exist` | DB 마이그레이션 미실행 | `migrate.sh runall` 명령 실행 |
| ALB가 생성되지 않음 | ALB Controller 미설치 또는 IAM 권한 부족 | Part 1의 ALB Controller 설치 과정 확인 |

### 다른 설치 가이드와의 일관성

**setup.v2.sh 문서 참조:**

현재 `installation-guide-setupv2sh.mdx`의 "기본 설정 절차" 섹션 구조를 EKS 가이드에도 적용합니다.

- 공통 설정: QueryPie Web Base URL 설정
- 제품별 설정: DAC/SAC Proxy 주소, KAC Proxy 주소, WAC Proxy 주소

이를 통해 Docker Compose 설치와 EKS 설치 문서의 일관성을 유지합니다.

## 구현 계획

### Phase 1: 메인 문서 재구조화
1. `installing-on-aws-eks.mdx` 개요로 단순화
2. 사전 요구사항 업데이트
3. 설치 방식 선택 가이드 추가

### Phase 2: Part 1 문서 작성
1. `installing-on-aws-eks-part1-aws-setup.mdx` 신규 생성
2. OIDC, EBS CSI, ALB Controller 설치 과정 작성
3. ACM 인증서 설정 추가

### Phase 3: Part 2 문서 작성
1. `installing-on-aws-eks-part2-helm-deployment.mdx` 신규 생성
2. Demo 모드 / Production 모드 분리
3. 실제 검증된 values.yaml 예시 제공

### Phase 4: 트러블슈팅 통합
1. 실제 테스트에서 발견된 이슈 반영
2. 각 문서 말미에 관련 트러블슈팅 추가

### Phase 5: 검토 및 마무리
1. 다른 설치 가이드와의 일관성 확인
2. 링크 및 참조 업데이트
3. installation.mdx의 EKS 관련 링크 업데이트

## 참고 자료

- `tpm/aws/eks/HELM_CHART_1.5.0_EVALUATION.md` - Helm Chart 평가 결과
- `tpm/aws/eks/SETUP_CLUSTER.md` - EKS 클러스터 구성 가이드
- `tpm/aws/eks/INSTALL_ACP_PART1_AWS.md` - AWS 환경 설정
- `tpm/aws/eks/INSTALL_ACP_PART2_HELM.md` - Helm 배포
- `querypie-docs/.../installation-guide-setupv2sh.mdx` - 기존 설치 가이드 참조
