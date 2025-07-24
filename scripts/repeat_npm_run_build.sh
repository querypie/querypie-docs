#!/usr/bin/env bash

set -o nounset -o errtrace -o pipefail

# Function to extract MDX file paths from build error messages
function extract_problematic_mdx_files() {
  local output="$1" line mdx_files=() file_path

  # Look for lines containing .mdx file paths followed by error messages
  while IFS= read -r line; do
    if [[ $line == *"Error occurred prerendering page"* ]]; then
      file_path=${line}
      # Remove "Error occurred prerendering page:" and everything before it
      file_path=${file_path#*Error occurred prerendering page \"}
      # Remove ". Read more:" and everything after it
      file_path=${file_path%%\". Read more:*}
      if [[ -f src/content"$file_path".mdx ]]; then
        echo src/content"$file_path".mdx
      fi
    elif [[ $line == *"Error compiling "* ]]; then
      # [nextra] Error compiling /Users/jk/workspace/querypie-docs/src/content/ko/querypie-manual/querypie-docs/release-notes/9100-9104/external-api-changes-9100-version.mdx.
      file_path=${line}
      file_path=${file_path#* Error compiling }
      file_path=${file_path#*querypie-docs/src/content}
      file_path=${file_path%%.mdx.*}
      if [[ -f src/content"$file_path".mdx ]]; then
        echo src/content"$file_path".mdx
      fi
    fi
  done <"$output"
}

function do_npm_run_build() {
  local output problematic_files
  output=$(mktemp /tmp/npm-run-build.XXXXXX)

  if npm run build >"$output" 2>&1; then
    echo >&2 "# Build succeeded."
    rm -f "$output"
    return 0
  fi

  echo >&2 "# Build failed. Analyzing error messages..."

  # Extract problematic MDX files
  problematic_files=$(extract_problematic_mdx_files "$output")

  # Check if any problematic files were found
  if [[ -z "$problematic_files" ]]; then
    echo >&2 "# No problematic .mdx files identified. Build is failing for other reasons."
    echo >&2 "# Build output:"
    cat "$output"
    exit 1
  fi

  # Delete problematic files
  echo >&2 "# Deleting the following problematic files:"
  while IFS= read -r file; do
    echo "  - $file"
    rm -f "$file"
  done <<<"$problematic_files"

  echo >&2 "# Deleted problematic files."
  return 1
}

function main() {
  local action=${1:-build} output

  case "$action" in
  build)
    echo >&2 "# Starting the build process..."
    ;;
  extract)
    echo >&2 "# Extracting problematic .mdx files from build output..."
    for output in /tmp/npm-run-build.*; do
      if [[ -f "$output" ]]; then
        echo >&2 "# Processing file: $output"
        extract_problematic_mdx_files "$output"
      fi
    done
    # This action is not implemented in this script, but could be added later
    exit 0
    ;;
  *)
    echo >&2 "Unknown action: $action"
    echo >&2 "Usage: $0 [build]"
    exit 1
    ;;
  esac

  # Main loop to repeatedly run build until success or no more files to delete
  local max_attempts=10 attempt=1

  while [[ $attempt -le $max_attempts ]]; do
    echo "Attempt $attempt of $max_attempts: Running npm run build..."

    if do_npm_run_build; then
      echo "Build completed successfully!"
      exit 0
    fi

    ((attempt++))
  done

  echo "Maximum number of attempts reached. Build is still failing."
  exit 1
}

main "$@"
