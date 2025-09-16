#!/usr/bin/env bash

set -o nounset -o errtrace -o pipefail

script_dir="$(dirname "${BASH_SOURCE[0]}")"
pushd "$script_dir" || exit 1

for testcase in testcases/[0-9]*; do
  pushd $testcase
  (set -x; cp output.mdx expected.mdx)
  popd
done
