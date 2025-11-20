# Translation Guidelines

## Overview

This skill provides guidelines for translating content in the QueryPie documentation repository, which supports three languages: English (en), Japanese (ja), and Korean (ko).

**Important**: The source language is **Korean (ko)**, not English. All translations should be done from Korean to English and Japanese.

## Project Context

- **Languages**: English (en), Japanese (ja), Korean (ko)
- **Content Location**: `src/content/{lang}/`
- **Source Language**: Korean (ko) - the original content
- **Target Languages**: English (en), Japanese (ja)
- **Translation Direction**: ko → en, ko → ja

## Translation Principles

### Consistency

1. **Terminology**: Use consistent technical terms across all languages
2. **Structure**: Maintain the same document structure across languages
3. **Formatting**: Preserve all markdown formatting, code blocks, and components
4. **Links**: Update internal links to match the language structure

### Accuracy

1. **Technical Terms**: Preserve technical terms appropriately (may use English terms in some contexts)
2. **Context**: Maintain the meaning and context of the original
3. **Tone**: Match the professional tone of the documentation
4. **Completeness**: Ensure all content is translated, including alt text and captions

## File Structure

### Directory Organization

```
src/content/
├── ko/          # Korean (source/original)
├── en/          # English (translated from Korean)
└── ja/          # Japanese (translated from Korean)
```

Each language directory should have the same file structure. The path and filename after the language directory must be identical across all languages.

### File Naming

- Use the same file names across all languages
- Use kebab-case: `user-manual/workflow.mdx`
- Example: All three languages have `user-manual/workflow.mdx`

## Translation Workflow

### Source Content

- **Original Content**: `src/content/ko/` - Korean MDX files are the source
- **MDX Format**: Markdown with JSX extensions
- **Inter-document Links**: MDX documents contain links that reference each other

### When Translating New Content

1. **Start with Korean**: Korean version in `src/content/ko/` is the source
2. **Translate to English**: Create English version in `src/content/en/` maintaining structure
3. **Translate to Japanese**: Create Japanese version in `src/content/ja/` maintaining structure
4. **Verify Consistency**: Check that all three versions have the same structure and file paths

### When Updating Existing Content

1. **Identify Changes**: Check Korean source for updates
2. **Update Translations**: Update English and Japanese versions to match Korean changes
3. **Maintain Alignment**: Ensure sections, headings, and links align across languages
4. **Test**: Verify all language versions render correctly with `npm run build`

### Translation Process Guidelines

1. **Batch Processing**: Translate or review 50 documents at a time, then request review
2. **Build Verification**: After translation, run `npm run build` to verify MDX files build correctly
   - Fix any build errors by checking error messages
   - Repeat until `npm run build` succeeds
   - Run `npm run build` directly without asking for confirmation
3. **No Re-translation**: Do not re-translate already translated documents unless specifically instructed
4. **No Re-review**: Do not perform proofreading on documents that already have review results unless specifically instructed
5. **Feedback**: Report any typos, grammar errors, or inappropriate expressions found in Korean source, as well as any difficulties encountered during translation

## Special Considerations

### Frontmatter

Translate the title in frontmatter. The Korean source has the original title:

```yaml
---
title: 'Workflow'  # Korean (source)
---
```

```yaml
---
title: 'Workflow'  # English (translated)
---
```

```yaml
---
title: 'ワークフロー'  # Japanese (translated)
---
```

### Code Blocks

- **Do NOT translate code**: Keep code examples in their original language
- **Comments in code**: Code comments should remain in English (project preference)
- **Language tags**: Keep language tags as-is: ````bash`, ````typescript`, etc.

### Component Usage

Preserve all component syntax:

```jsx
import { Callout } from 'nextra/components'

<Callout type="info">
  Translated content here
</Callout>
```

### Links

- **Keep relative paths**: Maintain relative paths in links across all languages
- **Translate link text**: Only the link text should be translated, not the path

```markdown
# Korean (source)
[Workflow](user-manual/workflow)

# English (translated)
[Workflow](user-manual/workflow)

# Japanese (translated)
[ワークフロー](user-manual/workflow)
```

### Images

- **Image Location**: Images are stored in `public/` directory
- **Image Path**: Determined by the MDX file path
  - For `src/content/ko/path/filename.mdx`, images are in `public/path/filename/`
- **Image Names**: Typically `screenshot-yyyymmdd-hhmmss.png` or `image-yyyymmdd-hhmmss.png`
- **Shared Across Languages**: Images are language-agnostic and shared across all language versions
- **No Image Replacement**: Do not replace images when translating; use the same images from Korean source

**Translate only alt text and captions**:

```jsx
# Korean (source)
<figure>
  ![Workflow 메뉴](/user-manual/workflow/screenshot-20240902-172212.png)
  <figcaption>
    Workflow 메뉴
  </figcaption>
</figure>

# English (translated)
<figure>
  ![Workflow Menu](/user-manual/workflow/screenshot-20240902-172212.png)
  <figcaption>
    Workflow Menu
  </figcaption>
</figure>

# Japanese (translated)
<figure>
  ![Workflowメニュー](/user-manual/workflow/screenshot-20240902-172212.png)
  <figcaption>
    Workflowメニュー
  </figcaption>
</figure>
```

## Language-Specific Guidelines

### Korean (ko) - Source Language

- This is the original source content
- Use appropriate honorifics when addressing users
- Technical terms may be kept in English if commonly used
- Maintain professional tone
- Use proper spacing and punctuation

### English (en) - Translated Language

- **Standard English**: Use standard English
- **Formal but Friendly**: Use formal expressions appropriate for a software company providing high-quality technical support
  - Prefer friendly conversational tone over stiff and dry style
  - Avoid casual, everyday colloquial expressions or light tone used among friends
- **Clear and Concise**: Professional but accessible
- **Use Active Voice**: When possible
- **Technical Terms**: Should be clearly defined

### Japanese (ja) - Translated Language

- **Standard Japanese**: Use standard Japanese
- **Formal but Friendly**: Use formal expressions appropriate for a software company providing high-quality technical support
  - Prefer friendly conversational tone over stiff and dry style
  - Avoid casual, everyday colloquial expressions or light tone used among friends
- **Use Appropriate Keigo**: Honorific language when addressing users
- **Technical Terms**: May be kept in English or use katakana
- **Maintain Professional Tone**: Follow Japanese typography rules

## Critical Translation Rules

### Markdown Formatting

- **Preserve Formatting**: Maintain all markdown expressions, line breaks, and formatting from Korean source
- **Keep Structure**: Tables, lists, emphasis (e.g., `**text**`) should match Korean source exactly
- **Keep Emphasis Markers**: Maintain `**Example Phrase**` format; do not replace with `<strong>`
- **Fix Inconsistencies**: If English/Japanese translation has different markdown formatting than Korean source, fix it to match

### HTML Encoding

- **Do NOT Decode**: Do not arbitrarily decode properly escaped strings from Korean source
- **Keep HTML Entities**: Maintain HTML-encoded strings as-is
  - Example: Keep `&lt;token&gt;` as-is, do not convert to `<token>`
  - Example: Keep `{querypie url}` with backquote, do not remove it

### Document Structure

- **Same Path Structure**: File paths and names must be identical across languages
  - `src/content/ko/path/filename.mdx` → `src/content/en/path/filename.mdx`
  - `src/content/ko/path/filename.mdx` → `src/content/ja/path/filename.mdx`
- **Relative Links**: Maintain relative paths in links

## Common Translation Patterns

### UI Elements

- Buttons, menus, and UI elements: Translate to match the actual UI language
- If UI is in English, may keep English terms in other languages

### Technical Terms

- Database terms: May keep English (e.g., "SQL", "Query")
- Product names: Keep as-is (e.g., "QueryPie")
- Feature names: Translate appropriately

### Navigation Terms

- Menu items: Translate to match user interface
- Section headers: Translate fully
- Breadcrumbs: Translate appropriately

## Quality Checklist

Before completing a translation:

- [ ] Korean source is correctly identified and used
- [ ] All content is translated from Korean (no Korean text left untranslated in en/ja versions)
- [ ] Frontmatter title is translated
- [ ] Code blocks are preserved (not translated)
- [ ] Image alt text and captions are translated
- [ ] Image paths are correct (based on MDX file path)
- [ ] Links use relative paths and are maintained
- [ ] Technical terms are handled consistently
- [ ] Markdown formatting matches Korean source exactly
- [ ] HTML-encoded strings are preserved (e.g., `&lt;`, `&gt;`)
- [ ] Structure matches Korean source (same file paths and names)
- [ ] File renders correctly in local dev server
- [ ] `npm run build` succeeds without errors

## Tools and Resources

### Translation Files

- Korean title translations: `confluence-mdx/etc/korean-titles-translations.txt`
- Used by `translate_titles.py` script

### Testing Translations

```bash
# Run local dev server
npm run dev

# Navigate to each language version
# http://localhost:3000/en/...
# http://localhost:3000/ja/...
# http://localhost:3000/ko/...
```

## Best Practices

1. **Review Korean Source**: Always review the Korean source (`src/content/ko/`) to understand context
2. **Maintain Structure**: Keep the same heading hierarchy and organization as Korean source
3. **Preserve Formatting**: Don't change markdown syntax or component usage - match Korean source exactly
4. **Build Verification**: Always run `npm run build` after translation to verify MDX files build correctly
5. **Test Locally**: Test translated content in the dev server (`npm run dev`)
6. **Consistency**: Use the same translation for repeated terms
7. **Formal but Friendly Tone**: Use formal expressions appropriate for enterprise software documentation, but prefer friendly conversational tone
8. **Code Comments**: Keep code comments in English (project preference)
9. **Batch Processing**: Work on 50 documents at a time, then request review
10. **Report Issues**: Report typos, grammar errors, or inappropriate expressions found in Korean source

## Target Audience

This documentation is provided by QueryPie, a software development company, to:
- End users
- Customer company employees
- Security officers
- Customer engineers
- Business partner engineers

Maintain a tone appropriate for enterprise software documentation with high-quality technical support.

