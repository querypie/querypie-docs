# Confluence XHTML to Markdown Converter Tests

This directory contains test cases for the `confluence_xhtml_to_markdown.py` script, which converts Confluence XHTML exports to Markdown format.

## Directory Structure

```
confluence-mdx/tests/
├── README.md                 # This file
├── Makefile                  # Test runner
├── copy-files-to-testcases.sh
├── update-expected-mdx.sh
└── testcases/                # Test cases directory
    └── 568918170/            # Test case ID (Confluence page ID)
        ├── page.xhtml        # Input XHTML file
        ├── expected.mdx      # Expected output MDX file
        └── output.mdx        # Actual output MDX file (generated during tests)
```

## Adding New Test Cases

To add a new test case:

1. Create a new directory under `testcases/` with the Confluence page ID or a descriptive name
2. `testcases/<page-id>`에 테스트용 입력 파일을 채우거나, 복사합니다.
   - `./copy-files-to-testcases.sh` 를 실행하여 `../../docs/latest-ko-confluence/<page-id>/` 아래의 파일을 `testcases/<page-id>/` 로 복사합니다.
3. Generate the expected output by running:
   ```
   source ../venv/bin/activate
   python ../../scripts/confluence_xhtml_to_markdown.py testcases/<page-id>/page.xhtml testcases/<page-id>/expected.mdx
   ```
   Run the above from this directory: confluence-mdx/tests.
4. 생성된 `output.mdx`를 `expected.mdx`로 간주합니다.
   - `./update-expected-mdx.sh`를 실행합니다.


## Running Tests

Tests are run using the Makefile in this directory.

### Run all tests

```bash
cd confluence-mdx/tests
make test
```

### Run a specific test

```bash
cd confluence-mdx/tests
make test-one TEST_ID=568918170
```

### Clean output files

```bash
cd confluence-mdx/tests
make clean
```

## Update input files and expected output

How to update input files
- 

How to update expected outputs

## Test Process

The test process:

1. Activates the Python virtual environment
2. Runs the conversion script on the input XHTML file
3. Compares the generated output with the expected output
4. Reports any differences

This allows for regression testing when making changes to the conversion script.