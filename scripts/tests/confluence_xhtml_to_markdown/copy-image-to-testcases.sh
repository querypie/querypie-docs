#!/usr/bin/env bash

set -o nounset -o errtrace -o pipefail

script_dir="$(dirname "${BASH_SOURCE[0]}")"
pushd "$script_dir" || exit 1

for testcase in testcases/[0-9]*; do
  doc_dir=$(basename "$testcase")
  for img in ../../../docs/latest-ko-confluence/"$doc_dir"/*.png; do
    filename=$(basename "$img")
    ( set -x; cp "$img" "$testcase/$filename" )
  done
done
