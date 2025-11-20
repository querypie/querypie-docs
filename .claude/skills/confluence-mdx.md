# Confluence to MDX Conversion Guidelines

## Overview

This skill provides guidelines for working with the Confluence to MDX conversion workflow in the QueryPie documentation repository.

## Project Context

- **Conversion Scripts**: Located in `confluence-mdx/bin/`
- **Python Environment**: Uses Python 3 with virtual environment
- **Input Format**: Confluence XHTML exports
- **Output Format**: MDX files in `src/content/{lang}/`
- **Workflow**: Multi-step process from Confluence to final MDX

## Directory Structure

```
confluence-mdx/
├── bin/                    # Conversion scripts
│   ├── pages_of_confluence.py
│   ├── translate_titles.py
│   ├── generate_commands_for_xhtml2markdown.py
│   ├── confluence_xhtml_to_markdown.py
│   └── xhtml2markdown.ko.sh
├── var/                    # Working directory for Confluence data
│   ├── list.txt           # Page list (Korean titles)
│   ├── list.en.txt        # Page list (English titles)
│   └── {page_id}/         # Per-page data
│       ├── page.yaml      # Page metadata
│       └── page.xhtml     # Page content
├── etc/                    # Configuration and translation files
│   └── korean-titles-translations.txt
├── target/                 # Output directory
│   ├── en/
│   ├── ja/
│   ├── ko/
│   └── public/            # Public assets
└── tests/                  # Test cases
    └── testcases/
```

## Conversion Workflow

### Step 1: Collect Confluence Data

**Script**: `pages_of_confluence.py`

**Purpose**: Download pages and metadata from Confluence API

**Usage**:
```bash
cd confluence-mdx
source venv/bin/activate

# Full download with attachments (first time or when attachments change)
python bin/pages_of_confluence.py --attachments

# Regular update (pages only)
python bin/pages_of_confluence.py

# Update specific page and children
python bin/pages_of_confluence.py --page-id 123456789 --attachments

# Generate/update list.txt from local data
python bin/pages_of_confluence.py --local >var/list.txt
```

**Output**:
- `var/list.txt`: Tab-separated list of pages (ID, path, title)
- `var/{page_id}/page.yaml`: Page metadata
- `var/{page_id}/page.xhtml`: Page content in XHTML format
- `var/{page_id}/attachments/`: Downloaded attachments (if `--attachments` used)

### Step 2: Translate Titles

**Script**: `translate_titles.py`

**Purpose**: Translate Korean page titles to English

**Usage**:
```bash
python bin/translate_titles.py
```

**Input**: `var/list.txt` (Korean titles)
**Output**: `var/list.en.txt` (English titles)
**Translation Source**: `etc/korean-titles-translations.txt`

**Note**: If titles are not translated, update `etc/korean-titles-translations.txt`

### Step 3: Generate Conversion Commands

**Script**: `generate_commands_for_xhtml2markdown.py`

**Purpose**: Generate shell script with conversion commands

**Usage**:
```bash
python bin/generate_commands_for_xhtml2markdown.py var/list.en.txt >bin/xhtml2markdown.ko.sh
chmod +x bin/xhtml2markdown.ko.sh
```

**Output**: `bin/xhtml2markdown.ko.sh` - Executable script with conversion commands

### Step 4: Convert XHTML to MDX

**Script**: `xhtml2markdown.ko.sh` (generated in step 3)

**Purpose**: Execute conversion of all XHTML files to MDX

**Usage**:
```bash
./bin/xhtml2markdown.ko.sh
```

**Process**: 
- Calls `confluence_xhtml_to_markdown.py` for each page
- Converts XHTML to Markdown/MDX format
- Handles special cases: code blocks, tables, macros, etc.

**Output**:
- `target/ko/`: MDX files for Korean content
- `target/public/`: Public assets (images, attachments)

## Core Conversion Script

### confluence_xhtml_to_markdown.py

**Purpose**: Convert individual XHTML file to Markdown/MDX

**Usage**:
```bash
python bin/confluence_xhtml_to_markdown.py input.xhtml output.mdx
```

**Features**:
- Handles CDATA sections in code blocks
- Converts tables with colspan/rowspan
- Processes Confluence-specific macros
- Preserves structure and formatting

## Testing

### Test Framework

**Location**: `confluence-mdx/tests/`

**Test Cases**: `tests/testcases/`
- Each test case has:
  - `page.xhtml`: Input XHTML
  - `expected.mdx`: Expected output
  - `output.mdx`: Generated output (created during test)

### Running Tests

```bash
cd confluence-mdx/tests

# Run all tests
make test

# Run specific test
make test-one TEST_ID=<test_id>

# Run with debug logging
make debug

# Clean output files
make clean
```

## Common Tasks

### Adding New Pages from Confluence

1. Download new pages:
   ```bash
   python bin/pages_of_confluence.py --page-id <new_page_id> --attachments
   ```

2. Update list:
   ```bash
   python bin/pages_of_confluence.py --local >var/list.txt
   ```

3. Translate titles:
   ```bash
   python bin/translate_titles.py
   ```

4. Regenerate conversion script:
   ```bash
   python bin/generate_commands_for_xhtml2markdown.py var/list.en.txt >bin/xhtml2markdown.ko.sh
   ```

5. Convert:
   ```bash
   ./bin/xhtml2markdown.ko.sh
   ```

### Updating Existing Pages

1. Download updated pages:
   ```bash
   python bin/pages_of_confluence.py --page-id <page_id>
   ```

2. Convert only changed pages:
   ```bash
   # Manual conversion for specific page
   python bin/confluence_xhtml_to_markdown.py \
     var/{page_id}/page.xhtml \
     target/ko/path/to/page.mdx
   ```

### Handling Translation Issues

If titles are not properly translated:

1. Check `etc/korean-titles-translations.txt`
2. Add missing translations in format:
   ```
   Korean Title<TAB>English Title
   ```
3. Re-run `translate_titles.py`

## Python Environment Setup

### Initial Setup

```bash
cd confluence-mdx
python3 -m venv venv
source venv/bin/activate
pip install requests beautifulsoup4 pyyaml
```

### Activating Environment

```bash
cd confluence-mdx
source venv/bin/activate
```

### Deactivating Environment

```bash
deactivate
```

## Best Practices

1. **Backup Before Conversion**: Always backup existing MDX files before running conversion
2. **Test Locally**: Test converted files with `npm run dev` before committing
3. **Review Changes**: Manually review converted content, especially:
   - Code blocks
   - Tables
   - Images and links
   - Special formatting
4. **Incremental Updates**: Use `--page-id` for updating specific pages instead of full conversion
5. **Attachment Handling**: Use `--attachments` flag when attachments are updated
6. **Version Control**: Commit `var/list.txt` and `var/list.en.txt` for tracking
7. **Translation Maintenance**: Keep `korean-titles-translations.txt` updated

## Troubleshooting

### Common Issues

1. **Missing Translations**: Update `etc/korean-titles-translations.txt`
2. **Broken Links**: Check image paths and internal links after conversion
3. **Formatting Issues**: Review special cases in `confluence_xhtml_to_markdown.py`
4. **API Errors**: Check Confluence API credentials and rate limits
5. **Test Failures**: Compare `output.mdx` with `expected.mdx` to identify issues

### Debug Mode

Enable debug logging:
```bash
python bin/confluence_xhtml_to_markdown.py input.xhtml output.mdx --log-level debug
```

## Integration with Documentation Workflow

After conversion:

1. Review converted MDX files in `target/ko/`
2. Copy to `src/content/ko/` (if needed)
3. Test with local dev server: `npm run dev`
4. Make manual adjustments if needed
5. Update other language versions (en, ja) if structure changes

## Notes

- Conversion is primarily for Korean (ko) content
- English and Japanese versions may need separate workflows
- Manual editing is often required after conversion
- Test cases help ensure conversion quality

