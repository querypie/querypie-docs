# MDX Skeleton Comparison Guidelines

## Overview

This skill provides guidelines for detecting inconsistencies between original Korean MDX files and their translations (English and Japanese) using the `mdx_to_skeleton.py` tool. The tool converts MDX files to skeleton format (replacing text content with `_TEXT_` placeholders) to compare document structure across languages.

## Purpose

The goal is to identify structural inconsistencies between:
- **Original MDX files** (Korean): Located in `confluence-mdx/target/ko/`
- **Translated MDX files** (English): Located in `confluence-mdx/target/en/`
- **Translated MDX files** (Japanese): Located in `confluence-mdx/target/ja/`

## Tool: mdx_to_skeleton.py

### Location

The tool is located at: `confluence-mdx/bin/mdx_to_skeleton.py`

### How It Works

The `mdx_to_skeleton.py` script converts MDX files to skeleton format by:
1. Preserving document structure (headers, lists, code blocks, links, etc.)
2. Replacing all text content with `_TEXT_` placeholder
3. Maintaining whitespace and formatting structure
4. Generating `.skel.mdx` files alongside original `.mdx` files

This allows comparison of document structure across languages without being affected by actual text content differences.

### Usage

To check for inconsistencies between original and translated MDX files:

```bash
cd confluence-mdx/
source venv/bin/activate  # Activate Python virtual environment
bin/mdx_to_skeleton.py --recursive --max-diff=20
```

**Command Options:**
- `--recursive`: Process directories recursively (defaults to `target/ko`, `target/ja`, `target/en` if no directories specified)
- `--max-diff=20`: Maximum number of differences to output before stopping (default: 20)

**What It Does:**
1. Converts all `.mdx` files in `target/ko/`, `target/ja/`, and `target/en/` to `.skel.mdx` format
2. Compares each translated skeleton file (English/Japanese) with its Korean equivalent
3. Reports differences in document structure (whitespace, line breaks, formatting)
4. Shows original `.mdx` file content for each difference found

## Workflow: Detecting and Fixing Inconsistencies

### Step 1: Run the Comparison Tool

Execute the command as shown above. The tool will:
- Process all MDX files recursively
- Generate skeleton files (`.skel.mdx`)
- Compare translated versions with Korean originals
- Output differences found (up to `--max-diff` limit)

### Step 2: Analyze the Results

The tool outputs differences in two formats:
1. **Skeleton diff**: Shows differences in `.skel.mdx` files (structure comparison)
2. **Original content diff**: Shows differences in original `.mdx` files (actual content)

Look for patterns indicating:
- Whitespace differences (spaces, tabs, indentation)
- Line break differences
- Formatting structure differences

### Step 3: Determine the Cause

There are three possible scenarios when inconsistencies are found:

#### Case 1: Original File Changes (Source Document Updates)

**Symptom**: The skeleton comparison shows differences because the original Korean `.mdx` file has been updated after the translation was completed.

**Cause**: The original Korean file was changed for various reasons:
- Image insertions or additions
- Typo corrections
- Product feature improvements requiring documentation updates
- Document error corrections
- Content additions or modifications

**Solution**: Compare the original and translated `.mdx` files to identify differences, then update the translation file to reflect the changes in the original.

**Important Notes:**
- Check the git log of the original Korean MDX file to see when changes were made
- **For large-scale batch translations completed by September 25, 2025**: Check the git log to identify changes made after that date
- The git log will show all modifications to the original file since the batch translation
- Update the translation to match the current state of the original
- Ensure all new content is properly translated
- Maintain consistency with the updated original structure

**How to Identify:**
- Use `git log` to check when the original file was last modified:
  ```bash
  git log --follow --oneline src/content/ko/path/to/file.mdx
  ```
- For files in `confluence-mdx/target/ko/`:
  ```bash
  git log --follow --oneline confluence-mdx/target/ko/path/to/file.mdx
  ```
- Filter changes after September 25, 2025 (post-batch-translation):
  ```bash
  git log --follow --oneline --since="2025-09-25" src/content/ko/path/to/file.mdx
  ```
- Compare the original file with the translation file
- Look for added sections, modified content, or structural changes
- Check if images were added or modified

**Example Fix:**
If the Korean original was updated to add a new section:
```markdown
## 설정

이 기능을 사용하면 데이터베이스에 연결할 수 있습니다.

## 새로운 기능

이제 자동 백업을 지원합니다.
```

The English translation should be updated to include the new section:
```markdown
## Setting

You can connect to the database.

## New Feature

Automatic backup is now supported.
```

**Workflow for Case 1:**
1. Check git history of the original Korean file to identify when changes were made (especially changes after September 25, 2025 for post-batch-translation updates)
2. Review the git log to understand what was changed and why (image additions, typo fixes, feature updates, etc.)
3. Compare the current original file with the translation file
4. Identify all differences (added, modified, or removed content)
5. Translate and add new content following `translation.md` guidelines
6. Update modified sections to match the original
7. Remove any content that was removed from the original

#### Case 2: Translation Errors (Incorrect or Incomplete Translation)

**Symptom**: The skeleton comparison shows differences indicating issues in the translation file, such as:
- Whitespace, line breaks, or formatting differences
- Missing content (parts of the original were not translated)
- Untranslated content (original Korean text left in translation)
- Incorrectly translated content (not following guidelines)
- Added content (text that doesn't exist in the original)

**Cause**: The translation process failed to follow guidelines or had errors, resulting in:
- **Whitespace/formatting differences**: The translated `.mdx` file has different whitespace or line breaks compared to the Korean original
- **Translation not following guidelines**: Content translated incorrectly or not according to `translation.md` guidelines
- **Missing content**: Parts of the original Korean text were not translated (content omission)
- **Untranslated content**: Original Korean text was left in the translation file instead of being translated
- **Added content**: Text that doesn't exist in the original Korean file was added to the translation

**Solution**: Compare the original and translated `.mdx` files to identify differences, then fix and supplement the translation file to match the original.

**Important Notes:**
- Do NOT modify `mdx_to_skeleton.py` to fix translation issues
- The translation file should match the original's formatting exactly (spaces, tabs, line breaks, indentation)
- Review the original Korean file and the translated file side by side
- Ensure all content from the original is properly translated
- Remove any untranslated Korean text
- Remove any content that doesn't exist in the original
- Follow `translation.md` guidelines for proper translation
- Maintain the same document structure as the original
- Refer to `translation.md` guidelines for translation formatting requirements

**How to Identify:**
- Check the original content diff output from the tool
- Look for whitespace differences (missing spaces after markdown elements)
- Look for missing sections, paragraphs, or sentences
- Look for Korean text in English/Japanese translations
- Look for content in translations that doesn't appear in the original

**Example Fixes:**

**Whitespace/Formatting Fix:**
If Korean original has:
```markdown
**Setting** 문서
```

And Japanese translation has:
```markdown
**Setting**文書
```

The Japanese translation should be fixed to:
```markdown
**Setting** 文書
```
(Note the space after `**Setting**`)

**Missing Content Fix:**
If Korean original has:
```markdown
## 설정

이 기능을 사용하면 데이터베이스에 연결할 수 있습니다.

### 주의사항

이 기능은 관리자 권한이 필요합니다.
```

And English translation has:
```markdown
## Setting

You can connect to the database.
```

The English translation should be updated to include the missing section:
```markdown
## Setting

You can connect to the database.

### Note

This feature requires administrator privileges.
```

#### Case 3: MDX Skeleton Comparison Tool Error

**Symptom**: The skeleton comparison shows differences because the original Korean `.mdx` file has been updated after the translation was completed.

**Cause**: The original Korean file was changed for various reasons:
- Image insertions or additions
- Typo corrections
- Product feature improvements requiring documentation updates
- Document error corrections
- Content additions or modifications

**Solution**: Compare the original and translated `.mdx` files to identify differences, then update the translation file to reflect the changes in the original.

**Important Notes:**
- Check the git log of the original Korean MDX file to see when changes were made
- **For large-scale batch translations completed by September 25, 2025**: Check the git log to identify changes made after that date
- The git log will show all modifications to the original file since the batch translation
- Update the translation to match the current state of the original
- Ensure all new content is properly translated
- Maintain consistency with the updated original structure

**How to Identify:**
- Use `git log` to check when the original file was last modified:
  ```bash
  git log --follow --oneline src/content/ko/path/to/file.mdx
  ```
- For files in `confluence-mdx/target/ko/`:
  ```bash
  git log --follow --oneline confluence-mdx/target/ko/path/to/file.mdx
  ```
- Filter changes after September 25, 2025 (post-batch-translation):
  ```bash
  git log --follow --oneline --since="2025-09-25" src/content/ko/path/to/file.mdx
  ```
- Compare the original file with the translation file
- Look for added sections, modified content, or structural changes
- Check if images were added or modified

**Example Fix:**
If the Korean original was updated to add a new section:
```markdown
## 설정

이 기능을 사용하면 데이터베이스에 연결할 수 있습니다.

## 새로운 기능

이제 자동 백업을 지원합니다.
```

The English translation should be updated to include the new section:
```markdown
## Setting

You can connect to the database.

## New Feature

Automatic backup is now supported.
```

**Workflow for Case 1:**
1. Check git history of the original Korean file to identify when changes were made (especially changes after September 25, 2025 for post-batch-translation updates)
2. Review the git log to understand what was changed and why (image additions, typo fixes, feature updates, etc.)
3. Compare the current original file with the translation file
4. Identify all differences (added, modified, or removed content)
5. Translate and add new content following `translation.md` guidelines
6. Update modified sections to match the original
7. Remove any content that was removed from the original

## Best Practices

### When to Check for Inconsistencies

- After bulk translation updates
- Before committing translation changes
- When reviewing translation quality
- After manual edits to translated files
- **After updates to original Korean files**: Check git log for changes made after September 25, 2025 (the date when large-scale batch translation was completed) to identify post-translation updates (Case 1)
- When reviewing translation completeness
- When original files are updated due to product feature improvements, typo corrections, or documentation fixes

### Translation Guidelines

When fixing translation files (Case 1, Case 2), follow these guidelines from `translation.md`:

1. **Preserve Formatting**: Maintain exact markdown formatting, line breaks, and whitespace from the Korean original
2. **Whitespace Consistency**: Ensure spaces around markdown elements match the original
   - After inline code: `` `code` text `` (space after backtick)
   - After links: `[text](url) text` (space after closing parenthesis)
   - After HTML tags: `<br/> text` (space after tag)
   - After formatting: `**text** text` (space after closing markers)
3. **Line Breaks**: Match line breaks exactly with the original
4. **Indentation**: Preserve indentation for lists, code blocks, and nested structures

### Excluding Files from Comparison

Some files may be intentionally different across languages. To exclude files from comparison:

1. Use `--exclude` option:
   ```bash
   bin/mdx_to_skeleton.py --recursive --max-diff=5 --exclude /index.skel.mdx /other-file.skel.mdx
   ```

2. Or configure in `ignore_skeleton_diff.yaml` (see script documentation)

## Related Files

- **Tool Script**: `confluence-mdx/bin/mdx_to_skeleton.py`
- **Supporting Modules**: 
  - `confluence-mdx/bin/skeleton_diff.py` - Comparison logic
  - `confluence-mdx/bin/skeleton_common.py` - Common utilities
- **Translation Guidelines**: `docs/translation.md`
- **Test Files**: `confluence-mdx/tests/test_mdx_to_skeleton.py`

## Example Output

When differences are found, the tool outputs:

```
+ diff -u -U 2 -b target/ko/path/file.skel.mdx target/en/path/file.skel.mdx
--- target/ko/path/file.skel.mdx
+++ target/en/path/file.skel.mdx
@@ -10,7 +10,7 @@
  ## _TEXT_
  
  _TEXT_
-**_TEXT_** _TEXT_
+**_TEXT_**_TEXT_
  
  _TEXT_
```

This shows that the English translation is missing a space after `**_TEXT_**`, which should be fixed in the English `.mdx` file.

