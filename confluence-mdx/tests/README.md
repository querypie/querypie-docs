# Confluence XHTML to Markdown Converter Tests

This directory contains test cases for the `confluence_xhtml_to_markdown.py` script, which converts Confluence XHTML exports to Markdown format.

## Directory Structure

```
tests/confluence_xhtml_to_markdown/
├── README.md                 # This file
└── testcases/                # Test cases directory
    └── 568918170/            # Test case ID (Confluence page ID)
        ├── page.xhtml        # Input XHTML file
        ├── expected.mdx      # Expected output MDX file
        └── output.mdx        # Actual output MDX file (generated during tests)
```

## Adding New Test Cases

To add a new test case:

1. Create a new directory under `testcases/` with the Confluence page ID or a descriptive name
2. Add the input XHTML file as `page.xhtml`
3. Generate the expected output by running:
   ```
   source venv/bin/activate
   python scripts/confluence_xhtml_to_markdown.py scripts/tests/confluence_xhtml_to_markdown/testcases/YOUR_TEST_ID/page.xhtml scripts/tests/confluence_xhtml_to_markdown/testcases/YOUR_TEST_ID/expected.mdx
   ```

## Running Tests

Tests can be run using the Makefile in the `scripts` directory:

### Run all tests

```bash
cd scripts
make test
```

### Run a specific test

```bash
cd scripts
make test-one TEST_ID=568918170
```

### Clean output files

```bash
cd scripts
make clean
```

## Test Process

The test process:

1. Activates the Python virtual environment
2. Runs the conversion script on the input XHTML file
3. Compares the generated output with the expected output
4. Reports any differences

This allows for regression testing when making changes to the conversion script.