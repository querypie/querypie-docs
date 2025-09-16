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
2. Populate `testcases/<page-id>` with input files.
   - Option A: Run `./copy-files-to-testcases.sh` to copy files from `../../docs/latest-ko-confluence/<page-id>/` into `testcases/<page-id>/`.
   - Option B: Manually place `page.xhtml` (and any related assets) under `testcases/<page-id>/`.
3. Generate the expected output by running:
   ```
   source ../../venv/bin/activate
   python ../../scripts/confluence_xhtml_to_markdown.py testcases/<page-id>/page.xhtml testcases/<page-id>/expected.mdx
   ```
   Run the above from this directory: confluence-mdx/tests.
4. Consider the newly generated `output.mdx` as the baseline expected output when appropriate.
   - Run `./update-expected-mdx.sh` to copy `output.mdx` to `expected.mdx` for the test case.


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
- Ensure your Confluence data has been refreshed under `docs/latest-ko-confluence/<page-id>/`.
- From this directory, run:
  ```bash
  ./copy-files-to-testcases.sh
  ```
  This copies the latest files (e.g., `page.xhtml`, `page.yaml`, attachments) for each `<page-id>` into the matching `testcases/<page-id>/` directory.
- Alternatively, manually copy or edit `testcases/<page-id>/page.xhtml` if you are crafting a synthetic test case.

How to update expected outputs
- Activate the Python virtual environment and generate fresh outputs for all cases by running the tests:
  ```bash
  source ../../venv/bin/activate
  make test-xhtml
  ```
  This regenerates `testcases/<page-id>/output.mdx` for each case.
- If the new outputs are correct, and you want to accept them as the expected baselines, run:
  ```bash
  ./update-expected-mdx.sh
  ```
  This replaces each `expected.mdx` with the corresponding `output.mdx`.
- For a single test case, you can update just one expected file:
  ```bash
  source ../../venv/bin/activate
  make test-one-xhtml TEST_ID=<page-id>
  cp testcases/<page-id>/output.mdx testcases/<page-id>/expected.mdx
  ```

## Test Process

The test process:

1. Activates the Python virtual environment
2. Runs the conversion script on the input XHTML file
3. Compares the generated output with the expected output
4. Reports any differences

This allows for regression testing when making changes to the conversion script.