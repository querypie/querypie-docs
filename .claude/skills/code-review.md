# Code Review Guidelines

## Overview

This skill provides guidelines for reviewing code changes in the QueryPie documentation repository.

## Project Context

- **Framework**: Next.js 15 with Nextra 4
- **Language**: TypeScript 5, React 19
- **Content**: MDX files for documentation
- **Build System**: npm-based with Vercel deployment

## Review Focus Areas

### 1. Code Quality

#### TypeScript

- **Type Safety**: Ensure proper type annotations
- **No `any` Types**: Avoid `any` unless absolutely necessary
- **Type Definitions**: Check that types are properly defined
- **Error Handling**: Verify error handling is appropriate

#### React Components

- **Component Structure**: Check component organization
- **Props Types**: Verify prop types are defined
- **Hooks Usage**: Ensure hooks follow React rules
- **Performance**: Look for unnecessary re-renders

#### Code Style

- **Consistency**: Follow existing code style
- **Naming**: Use clear, descriptive names
- **Comments**: Code comments should be in English (project preference)
- **Formatting**: Check indentation and spacing

### 2. Documentation Content

#### MDX Files

- **Frontmatter**: Verify frontmatter is correct
- **Structure**: Check heading hierarchy
- **Links**: Verify internal and external links work
- **Images**: Ensure image paths are correct
- **Multi-language**: Check all three language versions (en, ja, ko) if applicable

#### Content Quality

- **Accuracy**: Verify technical accuracy
- **Completeness**: Check that content is complete
- **Consistency**: Ensure consistency across language versions
- **Formatting**: Verify markdown formatting is correct

### 3. Build and Deployment

#### Build Process

- **No Build Errors**: Ensure `npm run build` succeeds
- **Type Errors**: Check for TypeScript compilation errors
- **Linting**: Verify no linting errors
- **Warnings**: Review and address warnings

#### Deployment

- **Vercel Configuration**: Check `vercel.json` if modified
- **Environment Variables**: Verify environment variables are documented
- **Deployment Scripts**: Review `scripts/deploy/` changes

### 4. Testing

#### Test Coverage

- **New Features**: Ensure new features have tests
- **Test Quality**: Verify tests are meaningful
- **Test Execution**: Check that tests pass

#### Manual Testing

- **Local Dev**: Verify `npm run dev` works
- **Content Rendering**: Check that MDX renders correctly
- **Navigation**: Verify navigation works
- **Responsive**: Check responsive design if UI changes

## Review Checklist

### Pre-Review

- [ ] PR description is clear
- [ ] Changes are logically grouped
- [ ] Related issues are referenced

### Code Review

- [ ] Code follows project conventions
- [ ] No obvious bugs or issues
- [ ] Error handling is appropriate
- [ ] Performance considerations addressed
- [ ] Security concerns addressed (if applicable)

### Documentation Review

- [ ] MDX files have correct frontmatter
- [ ] All three language versions updated (if applicable)
- [ ] Links are working
- [ ] Images are properly referenced
- [ ] Content is accurate and complete
- [ ] Formatting is consistent

### Build and Test

- [ ] Build succeeds without errors
- [ ] No TypeScript errors
- [ ] No linting errors
- [ ] Tests pass (if applicable)
- [ ] Local dev server works

### Final Check

- [ ] All review comments addressed
- [ ] No merge conflicts
- [ ] Ready for merge

## Common Issues to Watch For

### TypeScript Issues

- Missing type annotations
- Use of `any` type
- Incorrect type definitions
- Missing null checks

### React Issues

- Missing key props in lists
- Incorrect hook usage
- Memory leaks (missing cleanup)
- Unnecessary re-renders

### MDX Issues

- Missing frontmatter
- Broken markdown syntax
- Incorrect image paths
- Broken internal links
- Inconsistent structure across languages

### Build Issues

- Import errors
- Missing dependencies
- Configuration errors
- Type errors

## Review Comments

### Providing Feedback

1. **Be Specific**: Point to exact lines or sections
2. **Be Constructive**: Suggest improvements, not just problems
3. **Be Respectful**: Maintain professional tone
4. **Explain Why**: Help understand the reasoning

### Comment Types

- **Must Fix**: Critical issues that must be addressed
- **Should Fix**: Important issues that should be addressed
- **Nice to Have**: Suggestions for improvement
- **Questions**: Clarifications needed

## Language-Specific Considerations

### Multi-language Content

When reviewing documentation changes:

1. **Check All Languages**: Verify en, ja, ko versions
2. **Structure Alignment**: Ensure same structure across languages
3. **Link Consistency**: Check links work in all languages
4. **Translation Quality**: Verify translations are accurate

### Code Comments

- Code comments should be in English (project preference)
- Comments should explain "why" not "what"
- Keep comments up to date with code changes

## Automated Checks

### Before Review

- Check CI/CD status
- Review automated test results
- Check linting results
- Verify build status

### Tools

- **TypeScript Compiler**: Type checking
- **ESLint**: Code linting
- **Build Process**: Compilation check
- **Vercel Preview**: Deployment preview

## Best Practices

1. **Review Promptly**: Don't let PRs sit for too long
2. **Be Thorough**: Check all aspects, not just code
3. **Test Locally**: If possible, test changes locally
4. **Communicate Clearly**: Use clear, specific feedback
5. **Approve When Ready**: Don't block on minor issues
6. **Follow Up**: Check that feedback is addressed

## Special Cases

### Large PRs

- Break into smaller PRs if possible
- Focus on high-level structure first
- Review incrementally if needed

### Refactoring

- Ensure functionality is preserved
- Check test coverage
- Verify no regressions

### New Features

- Check documentation is updated
- Verify all language versions updated
- Ensure tests are included

### Bug Fixes

- Verify the fix addresses the issue
- Check for similar issues elsewhere
- Ensure tests prevent regression

## Approval Criteria

A PR should be approved when:

1. Code quality is good
2. Documentation is accurate and complete
3. Build succeeds
4. Tests pass (if applicable)
5. No critical issues remain
6. Minor issues can be addressed in follow-up

## Resources

- **Project README**: `/README.md`
- **Development Guide**: `/docs/DEVELOPMENT.md`
- **Confluence Workflow**: `/confluence-mdx/README.md`
- **Build Commands**: See `package.json` scripts

