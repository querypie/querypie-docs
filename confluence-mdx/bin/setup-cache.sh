#!/usr/bin/env bash

# Setup cache/ directory from either local var/ or a Docker image.
#
# Usage:
#   setup-cache.sh local   — copy numeric directories from local var/ to cache/
#   setup-cache.sh docker  — extract numeric directories from confluence-mdx:latest image

set -o nounset -o errexit -o errtrace -o pipefail

SCRIPT_DIR=$(dirname "$(realpath "${BASH_SOURCE[0]}")")
CONFLUENCE_MDX_DIR=$(cd "$SCRIPT_DIR/.." && pwd)

readonly BOLD_CYAN="\e[1;36m"
readonly BOLD_RED="\e[1;91m"
readonly RESET="\e[0m"

function log::error() {
  printf "%bERROR: %s%b\n" "$BOLD_RED" "$*" "$RESET" 1>&2
}

function log::do() {
  local line_no
  line_no=$(caller | awk '{print $1}')
  # shellcheck disable=SC2064
  trap "log::error 'Failed to run at line $line_no: $*'" ERR
  printf "%b+ %s%b\n" "$BOLD_CYAN" "$*" "$RESET" 1>&2
  "$@"
}

# Create or clean cache directory (preserving dot-files)
function cache::clean() {
  local cache_dir="$CONFLUENCE_MDX_DIR/cache"

  if [[ ! -d "$cache_dir" ]]; then
    log::do mkdir -p "$cache_dir"
  else
    echo >&2 "# Cleaning cache directory..."
    log::do find "$cache_dir" -mindepth 1 -maxdepth 1 ! -name '.*' -exec rm -rf {} +
  fi
}

# Copy numeric directories from $1 (source dir) into cache/
function cache::copy_numeric_dirs() {
  local src_dir="$1"
  local cache_dir="$CONFLUENCE_MDX_DIR/cache"
  local count=0

  while IFS= read -r -d '' dir; do
    local dirname
    dirname="$(basename "$dir")"
    if [[ "$dirname" =~ ^[0-9]+$ ]]; then
      log::do cp -a "$dir" "$cache_dir/"
      (( ++count ))
    fi
  done < <(find "$src_dir" -mindepth 1 -maxdepth 1 -type d -print0 2>/dev/null)

  echo >&2 "# Copied $count directories to cache/"
}

# Move numeric directories from $1 (temp dir) into cache/
function cache::move_numeric_dirs() {
  local src_dir="$1"
  local cache_dir="$CONFLUENCE_MDX_DIR/cache"
  local count=0

  while IFS= read -r -d '' dir; do
    local dirname
    dirname="$(basename "$dir")"
    if [[ "$dirname" =~ ^[0-9]+$ ]]; then
      log::do mv "$dir" "$cache_dir/"
      (( ++count ))
    fi
  done < <(find "$src_dir" -mindepth 1 -maxdepth 1 -type d -print0 2>/dev/null)

  echo >&2 "# Moved $count directories to cache/"
}

# ── local mode ──────────────────────────────────────
function cmd::local() {
  local var_dir="$CONFLUENCE_MDX_DIR/var"

  if [[ ! -d "$var_dir" ]]; then
    log::error "var/ directory not found"
    return 1
  fi

  echo >&2 "# Source: local var/"
  cache::clean
  cache::copy_numeric_dirs "$var_dir"
}

# ── docker mode ─────────────────────────────────────
function cmd::docker() {
  local image_name="docker.io/querypie/confluence-mdx:latest"
  local container_id
  local temp_dir

  echo >&2 "# Source: Docker image"
  cache::clean

  log::do docker pull --platform linux/amd64 "$image_name"

  container_id="$(docker create --platform linux/amd64 "$image_name")"
  if [[ -z "$container_id" ]]; then
    log::error "Failed to create container"
    return 1
  fi

  temp_dir="$(mktemp -d)"
  # shellcheck disable=SC2064
  trap "rm -rf '$temp_dir'; docker rm '$container_id' >/dev/null 2>&1 || true" EXIT

  log::do docker cp "$container_id:/workdir/var" "$temp_dir/"

  docker rm "$container_id" >/dev/null 2>&1 || true

  if [[ ! -d "$temp_dir/var" ]]; then
    log::error "Extracted var directory not found"
    return 1
  fi

  cache::move_numeric_dirs "$temp_dir/var"
}

# ── main ────────────────────────────────────────────
function print_usage_and_exit() {
  local code=${1:-0} out=2
  [[ code -eq 0 ]] && out=1
  cat >&"${out}" <<END_OF_USAGE
Usage: $(basename "$0") {local|docker}

  local   Copy from local var/ directory
  docker  Extract from confluence-mdx:latest image

END_OF_USAGE
  exit "$code"
}

function main() {
  case "${1:-}" in
    local)  cmd::local ;;
    docker) cmd::docker ;;
    -h|--help) print_usage_and_exit 0 ;;
    *) print_usage_and_exit 1 ;;
  esac
}

main "$@"
