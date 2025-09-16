#!/usr/bin/env bash

# Copy generated files from docs/latest-ko-confluence into matching testcases.
# Run this script from confluence-mdx/tests directory.

set -o nounset -o errtrace -o pipefail

script_dir="$(dirname "${BASH_SOURCE[0]}")"
pushd "$script_dir" || exit 1

for testcase in testcases/[0-9]*; do
  doc_dir=$(basename "$testcase")
  for source in ../../docs/latest-ko-confluence/"$doc_dir"/*; do
    target=$(basename "$source")
    ( set -x; cp "$source" "$testcase/$target" )
  done
done
