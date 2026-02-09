#!/usr/bin/env bash

set -o nounset -o errtrace -o pipefail

# Global variables
YES_MODE=false
TODO_FILE=""
CONFLUENCE_MDX_DIR=""

# Function to parse command line arguments
function parse_arguments() {
  while [[ $# -gt 0 ]]; do
    case $1 in
    --yes)
      YES_MODE=true
      shift
      ;;
    *)
      if [[ -z "$TODO_FILE" ]]; then
        TODO_FILE="$1"
      else
        echo >&2 "Error: Multiple todo files specified"
        exit 1
      fi
      shift
      ;;
    esac
  done

  if [[ -z "$TODO_FILE" ]]; then
    echo >&2 "Usage: $0 [--yes] <todo-file>"
    exit 1
  fi
}

# Function to setup environment: navigate to confluence-mdx directory and activate venv
function setup_environment() {
  local script_dir venv_path

  # Get script directory and navigate to confluence-mdx directory
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  CONFLUENCE_MDX_DIR="$(cd "$script_dir/.." && pwd)"

  # Change to confluence-mdx directory
  cd "$CONFLUENCE_MDX_DIR"

  # Activate venv if it exists
  venv_path="$CONFLUENCE_MDX_DIR/venv"
  if [[ -d "$venv_path" ]]; then
    if [[ -f "$venv_path/bin/activate" ]]; then
      source "$venv_path/bin/activate"
      echo >&2 "# Virtual environment activated: $venv_path"
    else
      echo >&2 "# Warning: venv directory exists but activate script not found"
    fi
  else
    echo >&2 "# Warning: venv directory not found at $venv_path"
  fi
}

# Function to ask user for confirmation to continue
function ask_continue() {
  local answer
  read -p "Continue to next file? (yes/no/quit): " answer </dev/tty
  case "$answer" in
  [Yy]es | [Yy])
    echo ""
    return 0
    ;;
  *)
    return 1
    ;;
  esac
}

# Function to process a single file
function process_file() {
  local file="$1"

  # Skip empty lines
  [[ -z "$file" ]] && return 0
  echo "# Target: $file"

  # Step 1: Run without --use-ignore
  echo "# --- Step 1: skeleton/cli.py (without --use-ignore) ---"
  PYTHONPATH=bin bin/skeleton/cli.py "$file" 2>&1

  # Step 2: Run with --use-ignore
  echo "# --- Step 2: skeleton/cli.py (with --use-ignore) ---"
  PYTHONPATH=bin bin/skeleton/cli.py --use-ignore "$file" 2>&1

  # Ask for user confirmation (skip if --yes option is provided)
  if [[ "$YES_MODE" == false ]]; then
    if ! ask_continue; then
      return 1
    fi
  fi

  return 0
}

# Function to process all files from the todo file
function process_all_files() {
  local file

  while IFS= read -r file || [[ -n "$file" ]]; do
    if ! process_file "$file"; then
      return 1
    fi
  done <"$TODO_FILE"

  return 0
}

# Main function
function main() {
  parse_arguments "$@"
  setup_environment

  process_all_files
}

main "$@"
