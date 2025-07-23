# QueryPie Documentation Files

This directory contains files related to the QueryPie documentation project. Below is a description of the files and directories in this location.

## Prompt Files

### prompt-1-ko.md
This file contains detailed instructions for creating Korean documentation for QueryPie 11.0.0. It explains:
- The structure of the documentation
- How to process breadcrumbs.txt to create breadcrumbs.revised.txt
- How to convert HTML content to Markdown format
- How to handle images and file naming conventions
- The process for generating Korean content in the src/content/ko/ directory

### prompt-2-en.md
This file contains instructions for creating English documentation for QueryPie 11.0.0. It explains:
- The structure of the English documentation
- How to process breadcrumbs.txt to create breadcrumbs.revised.txt for English content
- The directory structure for English documentation in src/content/en/

## Documentation Directories

### 11.0.0-en
This directory contains the English version of the QueryPie 11.0.0 documentation. It includes:
- HTML files for each documentation page
- Supporting files for documentation generation

### 11.0.0-ko
This directory contains the Korean version of the QueryPie 11.0.0 documentation. It includes:
- HTML files for each documentation page
- Supporting files for documentation generation

## Text Files in Documentation Directories

Both 11.0.0-en and 11.0.0-ko directories contain the following important text files:

### sitemap.xml
- XML file containing the sitemap of the documentation website
- Used to understand the structure of the documentation and the relationships between pages

### urls.txt
- Contains a list of URLs for all documentation pages
- Each line represents one URL
- Used to identify all pages that need to be processed

### titles.txt
- Contains URLs and titles for all documentation pages
- Format: `URL\tTitle`
- Used to extract page titles for documentation generation

### breadcrumbs.txt
- Contains URLs and breadcrumb navigation information for all documentation pages
- Format: `URL\tBreadcrumbs`
- Breadcrumbs are in the format `[Document Title](URI)` separated by `/`
- Used to understand the hierarchical structure of the documentation

### breadcrumbs.revised.txt
- Generated file with revised breadcrumb information
- Used in the documentation generation process
- Contains corrected URI paths following the specified format rules

## Image Files

### deploy-action.png
- Screenshot showing the deployment action process for the documentation

### preview-deploy-url.png
- Screenshot showing the preview deployment URL for the documentation

## Note
The `venv` directory is excluded from this documentation as it contains Python virtual environment files not directly related to the documentation content.