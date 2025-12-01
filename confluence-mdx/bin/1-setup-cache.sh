#!/usr/bin/env bash

# This script sets up the cache directory by pulling the Docker image
# docker.io/querypie/confluence-mdx:latest and copying numeric directories
# from /workdir/var in the image to the local cache/ directory.
# It creates or cleans the cache directory before copying.

set -o nounset -o errtrace -o pipefail

# Global variables
CONFLUENCE_MDX_DIR=""

# Function to setup environment: navigate to confluence-mdx directory
function setup_environment() {
  local script_dir

  # Get script directory and navigate to confluence-mdx directory
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  CONFLUENCE_MDX_DIR="$(cd "$script_dir/.." && pwd)"

  # Change to confluence-mdx directory
  cd "$CONFLUENCE_MDX_DIR"
}

# Function to setup cache directory: create or clean existing cache directory
function setup_cache() {
  local cache_dir="$CONFLUENCE_MDX_DIR/cache"

  # Create cache directory if it doesn't exist
  if [[ ! -d "$cache_dir" ]]; then
    mkdir -p "$cache_dir"
    echo >&2 "# Created cache directory: $cache_dir"
  else
    echo >&2 "# Cache directory already exists: $cache_dir"
    echo >&2 "# Cleaning cache directory contents..."

    # Remove all subdirectories and files, but ignore files starting with .
    if [[ -n "$(find "$cache_dir" -mindepth 1 -maxdepth 1 ! -name '.*' 2>/dev/null)" ]]; then
      find "$cache_dir" -mindepth 1 -maxdepth 1 ! -name '.*' -exec rm -rf {} +
      echo >&2 "# Removed all contents from cache directory"
    else
      echo >&2 "# Cache directory is already empty"
    fi
  fi
}

# Function to copy numeric directories from Docker image to cache/
function copy_numeric_dirs_from_image() {
  local image_name="docker.io/querypie/confluence-mdx:latest"
  local image_var_dir="/workdir/var"
  local cache_dir="$CONFLUENCE_MDX_DIR/cache"
  local container_id
  local temp_dir
  local dir

  echo >&2 "# Pulling Docker image: $image_name"
  if ! docker pull "$image_name"; then
    echo >&2 "# Error: Failed to pull Docker image $image_name"
    return 1
  fi

  echo >&2 "# Creating temporary container from image..."
  container_id="$(docker create "$image_name")"
  if [[ -z "$container_id" ]]; then
    echo >&2 "# Error: Failed to create container from image"
    return 1
  fi

  # Create temporary directory to extract files from container
  temp_dir="$(mktemp -d)"
  trap "rm -rf '$temp_dir'; docker rm '$container_id' >/dev/null 2>&1 || true" EXIT

  echo >&2 "# Copying /workdir/var from container..."
  if ! docker cp "$container_id:$image_var_dir" "$temp_dir/" 2>/dev/null; then
    echo >&2 "# Warning: /workdir/var directory not found in container or copy failed"
    docker rm "$container_id" >/dev/null 2>&1 || true
    return 0
  fi

  # Remove container as we no longer need it
  docker rm "$container_id" >/dev/null 2>&1 || true

  local extracted_var_dir="$temp_dir/var"
  if [[ ! -d "$extracted_var_dir" ]]; then
    echo >&2 "# Warning: Extracted var directory not found"
    return 0
  fi

  echo >&2 "# Moving numeric directories to cache/..."

  # Find all directories in extracted var/ that contain only digits and move them to cache
  while IFS= read -r -d '' dir; do
    local dirname
    dirname="$(basename "$dir")"
    # Check if directory name contains only digits
    if [[ "$dirname" =~ ^[0-9]+$ ]]; then
      echo >&2 "# Moving: $dirname"
      mv "$dir" "$cache_dir/"
    fi
  done < <(find "$extracted_var_dir" -mindepth 1 -maxdepth 1 -type d -print0 2>/dev/null)

  echo >&2 "# Finished moving numeric directories"
}

# Main function
function main() {
  setup_environment
  setup_cache
  copy_numeric_dirs_from_image
}

main "$@"

