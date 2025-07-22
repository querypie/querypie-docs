# Image Migration Summary

## Completed Tasks

1. Created and executed `move_images.py` script that:
   - Processed breadcrumbs.revised.txt to map line numbers to .mdx files
   - Copied images from docs/11.0.0-ko/<number>/ to src/content/ko/pam/ directories
   - Renamed images using the required format:
     - Screenshots: `<prefix>-screenshot-<number>.png`
     - Diagrams/illustrations: `<prefix>-image-<number>.png`

2. Created and executed `update_image_references.py` script that:
   - Updated all image references in .mdx files to point to new locations
   - Processed 257 MDX files and updated 1317 image references

## Verification

- Images are correctly stored in the same directory as their corresponding .mdx files
- Image filenames follow the required format with the correct prefix
- Screenshots use the `prefix-screenshot-N.png` format
- Diagrams/illustrations use the `prefix-image-N.png` format
- Images are numbered sequentially

All requirements specified in the issue description have been successfully implemented.