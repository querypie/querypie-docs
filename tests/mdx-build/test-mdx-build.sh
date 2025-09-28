#!/usr/bin/env bash
set -o nounset -o errexit -o errtrace -o pipefail
# MDX Build Test Script - supports single or multiple MDX files

SCRIPT_DIR=$(dirname "$(realpath "${BASH_SOURCE[0]}")")
TEST_ENV_DIR="$SCRIPT_DIR"
PROJECT_ROOT="$(realpath "$SCRIPT_DIR/../..")"

# Color definitions
readonly BOLD_CYAN="\e[1;36m"
readonly BOLD_RED="\e[1;91m"
readonly RESET="\e[0m"

# Logging functions
function log::do() {
  local line_no
  line_no=$(caller | awk '{print $1}')
  # shellcheck disable=SC2064
  trap "log::error 'Failed to run at line $line_no: $*'" ERR
  log::trace "$@"
  "$@"
}

function log::trace() {
  printf "%b+ %s%b\n" "$BOLD_CYAN" "$*" "$RESET" 1>&2
}


function log::error() {
  printf "%bERROR: %s%b\n" "$BOLD_RED" "$*" "$RESET" 1>&2
}


function validate_mdx_files() {
  local mdx_files=("$@")

  for mdx_file in "${mdx_files[@]}"; do
    local full_path="$PROJECT_ROOT/$mdx_file"

    if [[ ! -f "$full_path" ]]; then
      log::error "MDX file not found: $full_path"
      exit 1
    fi

    if [[ ! "$mdx_file" =~ \.mdx$ ]]; then
      log::error "File must have .mdx extension: $mdx_file"
      exit 1
    fi
  done
}

function setup_test_environment() {
  local mdx_files=("$@")
  
  # Files to copy
  local all_items=(
    "next.config.ts"
    "package.json"
    "tsconfig.json"
    "src/app/globals.css"
    "src/app/[lang]/layout.tsx"
    "src/app/[lang]/[[...mdxPath]]/page.tsx"
    "src/mdx-components.js"
  )
  
  # Copy all files if they don't exist or are older than source
  for item in "${all_items[@]}"; do
    if [[ -f "$PROJECT_ROOT/$item" ]]; then
      local target_file="$TEST_ENV_DIR/$item"
      local source_file="$PROJECT_ROOT/$item"
      
      # Copy if target doesn't exist or source is newer
      if [[ ! -f "$target_file" ]] || [[ "$source_file" -nt "$target_file" ]]; then
        log::do cp -p "$source_file" "$target_file"
      fi
    fi
  done
  
  # Copy only referenced public files
  copy_public_files "${mdx_files[@]}"
  
  # Install dependencies if node_modules doesn't exist or package.json is newer
  if [[ ! -d "$TEST_ENV_DIR/node_modules" ]] || [[ "$TEST_ENV_DIR/package.json" -nt "$TEST_ENV_DIR/node_modules" ]]; then
    log::do cd "$TEST_ENV_DIR"
    log::do npm install --silent --no-audit --no-fund
    cd "$SCRIPT_DIR"
  fi
}

function copy_public_files() {
  local mdx_files=("$@")
  local referenced_files=()

  # Extract referenced files from MDX content
  for mdx_file in "${mdx_files[@]}"; do
    local full_path="$PROJECT_ROOT/$mdx_file"
    if [[ -f "$full_path" ]]; then
      # Find image references in MDX content using grep
      while IFS= read -r image_path; do
        # Remove leading slash if present
        image_path="${image_path#/}"
        # Add to referenced_files if it's a public file
        if [[ "$image_path" =~ ^public/ ]]; then
          referenced_files+=("$image_path")
        fi
      done < <(grep -o '!\[.*\]([^)]*)' "$full_path" | sed 's/!\[.*\](\([^)]*\))/\1/')
    fi
  done

  # Copy only referenced files
  for file in "${referenced_files[@]}"; do
    local source_file="$PROJECT_ROOT/$file"
    local target_file="$TEST_ENV_DIR/$file"
    if [[ -f "$source_file" ]]; then
      log::do cp -p "$source_file" "$target_file"
    fi
  done
}

function copy_mdx_files() {
  local mdx_files=("$@")
  
  # Copy all MDX files at once
  for mdx_file in "${mdx_files[@]}"; do
    local full_path="$PROJECT_ROOT/$mdx_file"
    local target_dir="$TEST_ENV_DIR/src/content/$(dirname "$mdx_file" | sed 's|src/content/||')"
    log::do cp -p "$full_path" "$target_dir/"
  done
}

function run_mdx_build_test() {
  local mdx_files=("$@")

  echo >&2 "## Running MDX build test for ${#mdx_files[@]} files"

  # Setup test environment (reuse existing directory)
  setup_test_environment "${mdx_files[@]}"

  # Copy all MDX files at once
  copy_mdx_files "${mdx_files[@]}"

  # Try to build the project (skip postbuild scripts)
  echo >&2 "## Attempting to build MDX files..."
  cd "$TEST_ENV_DIR"
  
  # Set environment variables for build
  echo >&2 "## Setting build environment variables..."
  log::trace export NPM_CONFIG_IGNORE_SCRIPTS=true
  export NPM_CONFIG_IGNORE_SCRIPTS=true
  log::trace export NODE_OPTIONS="--trace-warnings --trace-uncaught"
  export NODE_OPTIONS="--trace-warnings --trace-uncaught"
  log::trace export NEXT_DEBUG=1
  export NEXT_DEBUG=1
  log::trace export NEXT_TELEMETRY_DEBUG=1
  export NEXT_TELEMETRY_DEBUG=1

  # Log the build command
  echo >&2 "## Running build command with DEBUG logging..."
  if log::do npm run build 2>&1 | tee build.log; then
    echo >&2 "Build successful for ${#mdx_files[@]} MDX files"
    cd "$SCRIPT_DIR"
    return 0
  else
    log::error "Build failed for ${#mdx_files[@]} MDX files"
    echo >&2 "# Build log:"
    cat build.log >&2
    cd "$SCRIPT_DIR"
    return 1
  fi
}


function main() {
  local mdx_files=("$@")

  if [[ ${#mdx_files[@]} -eq 0 ]]; then
    cat <<END_OF_USAGE
Usage: $0 <mdx-file-path> [mdx-file-path ...]
  mdx-file-path: Path to MDX file relative to project root

EXAMPLES:
  $0 src/content/ko/release-notes/1020-10212.mdx
  $0 src/content/en/administrator-manual/general/installation.mdx
  $0 src/content/ja/user-manual/database-access-control/overview.mdx
  $0 src/content/ko/release-notes/1020-10212.mdx src/content/en/release-notes/1020-10212.mdx

Available MDX files:
$(find "$PROJECT_ROOT/src/content" -name "*.mdx" | head -20 | sed "s|$PROJECT_ROOT/||")

END_OF_USAGE
    exit 1
  fi
  
  echo >&2 "### MDX Build Test ###"
  echo >&2 "# MDX files: ${mdx_files[*]}"

  validate_mdx_files "${mdx_files[@]}"
  
  echo >&2 "## Running MDX build test for ${#mdx_files[@]} files"
  echo >&2 "=========================================="
  
  if run_mdx_build_test "${mdx_files[@]}"; then
    echo >&2 "PASSED: All ${#mdx_files[@]} files"
    return 0
  else
    log::error "FAILED: ${#mdx_files[@]} files"
    return 1
  fi
}

main "$@"
