# Claude Skills for QueryPie Documentation

This directory contains Claude skills that help with various tasks in the QueryPie documentation repository.

## Available Skills

### Documentation Skills
- **documentation.md** - Guidelines for writing and editing MDX documentation files
- **translation.md** - Guidelines for translating content between languages (en, ja, ko)
- **confluence-mdx.md** - Guidelines for working with Confluence to MDX conversion workflows
- **mdx-skeleton-comparison.md** - Guidelines for detecting inconsistencies between original and translated MDX files using skeleton comparison

### Development Skills
- **code-review.md** - Guidelines for reviewing code changes in this repository

## Usage

These skills are automatically available to Claude when working in this repository. They provide context-specific guidance for:

- Writing and maintaining MDX documentation
- Translating content across multiple languages
- Working with Confluence conversion scripts
- Detecting inconsistencies between original and translated MDX files
- Reviewing code changes

## Project Structure

This repository uses:
- **Next.js 15** with **Nextra 4** for documentation
- **TypeScript 5** for type safety
- **React 19** for UI components
- **MDX** format for content files
- Multi-language support: English (en), Japanese (ja), Korean (ko)

## Content Locations

- Source content: `src/content/{lang}/`
- Confluence conversion scripts: `confluence-mdx/bin/`
- Public assets: `public/`

