#!/usr/bin/env bash

set -o errexit -o nounset -o errtrace -o pipefail

function main() {
  local top_dir
  top_dir=$(cd "$(dirname "$0")/.." && pwd -P)
  cd "$top_dir"

  local command
  case ${1:-} in
  ls | delete)
    command=$1
    ;;
  *)
    cat <<END_OF_USAGE
Usage: $0 <command>

  $0 ls       - list up obsoleted files
  $0 delete   - remove obsoleted files

END_OF_USAGE
    exit 1
    ;;
  esac

  set -o xtrace
  find src/content/ko/ \
    -type f -name '*.mdx' \
    -mtime +2d \
    \! -path 'src/content/ko/index.mdx' \
    -"$command"
  find \
    public/querypie-overview \
    public/user-manual \
    public/administrator-manual \
    public/release-notes \
    -type f -name '*' \
    -mtime +2d \
    -"$command"
  find \
    docs/latest-ko-confluence \
    -type f -name '*' \
    -mtime +2d \
    \! -path 'docs/latest-ko-confluence/.gitignore' \
    -"$command"
  find \
    scripts/tests/confluence_xhtml_to_markdown/testcases/[0-9]* \
    -type f -name '*' \
    -mtime +2d \
    \! -path 'scripts/tests/confluence_xhtml_to_markdown/testcases/*/expected.mdx' \
    -"$command"
}

main "$@"
