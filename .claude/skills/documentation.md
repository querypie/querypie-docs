# Documentation Writing Guidelines

## Overview

This skill provides guidelines for writing and editing MDX documentation files in the QueryPie documentation repository.

## Project Context

- **Framework**: Next.js 15 with Nextra 4
- **Content Format**: MDX (Markdown with JSX)
- **Languages**: English (en), Japanese (ja), Korean (ko)
- **Content Location**: `src/content/{lang}/`

## MDX File Structure

### Frontmatter

Every MDX file must start with frontmatter:

```yaml
---
title: 'Page Title'
---
```

### Common Imports

For components from Nextra:

```jsx
import { Callout } from 'nextra/components'
```

## Writing Guidelines

### Language-Specific Considerations

1. **English (en)**: Primary language, should be clear and professional
2. **Korean (ko)**: Should maintain consistency with English version
3. **Japanese (ja)**: Should maintain consistency with English version

### Content Structure

- Use clear headings (H1 for main title, H2 for major sections, H3 for subsections)
- Include overview sections when appropriate
- Use Callout components for important information:
  ```jsx
  <Callout type="info">
    Important information here
  </Callout>
  ```

### Images

- Store images in `public/` directory
- Reference images with relative paths: `/user-manual/workflow/screenshot.png`
- Use figure components for images with captions:
  ```jsx
  <figure data-layout="center" data-align="center">
    ![Image Description](/path/to/image.png)
    <figcaption>
      Caption text
    </figcaption>
  </figure>
  ```

### Tables

- Use standard markdown tables
- Tables can include data attributes for styling:
  ```markdown
  <table data-table-width="760" data-layout="default">
  ```

### Links

- Use relative paths for internal links
- Format: `[Link Text](relative/path/to/page)`
- For cross-language links, maintain the same structure

## File Naming Conventions

- Use kebab-case for file names
- Match the structure across all languages
- Example: `user-manual/workflow.mdx` exists in `en/`, `ja/`, and `ko/`

## Best Practices

1. **Consistency**: Maintain the same structure across all language versions
2. **Clarity**: Write clear, concise documentation
3. **Completeness**: Ensure all three language versions are updated
4. **Testing**: Verify MDX files render correctly with `npm run dev`
5. **Accessibility**: Use descriptive alt text for images
6. **Code Comments**: Write code comments in English (as per project preference)

## Common Tasks

### Adding a New Page

1. Create MDX file in `src/content/{lang}/` for each language
2. Add frontmatter with title
3. Write content following the structure guidelines
4. Add navigation entries if needed
5. Test locally with `npm run dev`

### Editing Existing Content

1. Locate the file in the appropriate language directory
2. Make changes while maintaining consistency with other language versions
3. Update all three language versions if the change affects structure
4. Test the changes locally

### Adding Images

1. Place image in appropriate `public/` subdirectory
2. Reference with absolute path from root: `/path/to/image.png`
3. Use figure component for better presentation

## Code Examples

When including code examples:

- Use appropriate language tags
- Keep examples simple and relevant
- Include comments for clarity (in English)

```bash
npm run dev
```

```typescript
// Example TypeScript code
const example: string = "value";
```

## Review Checklist

Before committing documentation changes:

- [ ] Frontmatter is correct
- [ ] All three language versions are updated (if applicable)
- [ ] Images are properly referenced
- [ ] Links are working
- [ ] Content renders correctly in local dev server
- [ ] Code examples are accurate
- [ ] No broken markdown syntax

