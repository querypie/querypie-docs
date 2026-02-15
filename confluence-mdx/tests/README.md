# Confluence XHTML to Markdown 변환기 테스트

이 디렉토리는 Confluence XHTML 내보내기를 Markdown 형식으로 변환하는 `converter/cli.py` 스크립트의 테스트 케이스를 포함합니다.

## 디렉토리 구조

```
confluence-mdx/tests/
├── README.md                 # 이 파일
├── Makefile                  # 테스트 실행기
├── copy-files-to-testcases.sh
├── update-expected-mdx.sh
└── testcases/                # 테스트 케이스 디렉토리
    └── 568918170/            # 테스트 케이스 ID (Confluence 페이지 ID)
        ├── page.xhtml        # 입력 XHTML 파일
        ├── expected.mdx      # 예상 출력 MDX 파일
        └── output.mdx        # 실제 출력 MDX 파일 (테스트 실행 시 생성)
```

## 새 테스트 케이스 추가

새 테스트 케이스를 추가하려면:

1. `testcases/` 아래에 Confluence 페이지 ID 또는 설명적인 이름으로 새 디렉토리를 생성합니다.
2. `testcases/<page-id>`에 입력 파일을 추가합니다.
   - 방법 A: `./copy-files-to-testcases.sh`를 실행하여 `../../docs/latest-ko-confluence/<page-id>/`의 파일을 `testcases/<page-id>/`로 복사합니다.
   - 방법 B: `page.xhtml` (및 관련 에셋)을 `testcases/<page-id>/` 아래에 수동으로 배치합니다.
3. 다음 명령을 실행하여 예상 출력을 생성합니다:
   ```
   source ../../venv/bin/activate
   python ../../scripts/converter/cli.py testcases/<page-id>/page.xhtml testcases/<page-id>/expected.mdx
   ```
   위 명령은 이 디렉토리(confluence-mdx/tests)에서 실행합니다.
4. 적절한 경우 새로 생성된 `output.mdx`를 기준 예상 출력으로 사용합니다.
   - `./update-expected-mdx.sh`를 실행하여 해당 테스트 케이스의 `output.mdx`를 `expected.mdx`로 복사합니다.


## 테스트 실행

테스트는 이 디렉토리의 Makefile을 사용하여 실행합니다.

### 모든 테스트 실행

```bash
cd confluence-mdx/tests
make test
```

### 특정 테스트 실행

```bash
cd confluence-mdx/tests
make test-one TEST_ID=568918170
```

### expected.mdx -> page.xhtml 동등성 검증

`expected.mdx`로부터 XHTML fragment를 생성한 뒤 `page.xhtml`과 구조 차이를 비교합니다.
비교는 `bin/xhtml_beautify_diff.py` 정규화 규칙을 사용합니다.

```bash
cd confluence-mdx
./bin/mdx_to_storage_xhtml_verify_cli.py --testcases-dir tests/testcases --diff-engine external --write-generated --show-diff-limit 3
```

### 출력 파일 정리

```bash
cd confluence-mdx/tests
make clean
```

## 입력 파일 및 예상 출력 업데이트

입력 파일 업데이트 방법
- `confluence-mdx/var/<page-id>/` 아래의 Confluence 데이터가 새로고침되었는지 확인합니다.
- 이 디렉토리에서 다음을 실행합니다:
  ```bash
  ./copy-files-to-testcases.sh
  ```
  이 명령은 각 `<page-id>`의 최신 파일(예: `page.xhtml`, `page.yaml`, 첨부파일)을 해당하는 `testcases/<page-id>/` 디렉토리로 복사합니다.
- 또는 합성 테스트 케이스를 만드는 경우 `testcases/<page-id>/page.xhtml`을 수동으로 복사하거나 편집합니다.

예상 출력 업데이트 방법
- Python 가상 환경을 활성화하고 테스트를 실행하여 모든 케이스의 새로운 출력을 생성합니다:
  ```bash
  source ../../venv/bin/activate
  make test-xhtml
  ```
  이 명령은 각 케이스의 `testcases/<page-id>/output.mdx`를 재생성합니다.
- 새 출력이 정확하고 이를 예상 기준으로 사용하려면 다음을 실행합니다:
  ```bash
  ./update-expected-mdx.sh
  ```
  이 명령은 각 `expected.mdx`를 해당 `output.mdx`로 교체합니다.
- 단일 테스트 케이스의 경우 하나의 예상 파일만 업데이트할 수 있습니다:
  ```bash
  source ../../venv/bin/activate
  make test-one-xhtml TEST_ID=<page-id>
  cp testcases/<page-id>/output.mdx testcases/<page-id>/expected.mdx
  ```

## 테스트 프로세스

테스트 프로세스:

1. Python 가상 환경을 활성화합니다.
2. 입력 XHTML 파일에 대해 변환 스크립트를 실행합니다.
3. 생성된 출력을 예상 출력과 비교합니다.
4. 차이점을 보고합니다.

이를 통해 변환 스크립트를 변경할 때 회귀 테스트를 수행할 수 있습니다.
