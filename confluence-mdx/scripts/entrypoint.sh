#!/bin/bash

set -o errexit -o nounset

case "${1:-help}" in
  fetch_cli.py|convert_all.py|converter/cli.py)
    command=$1
    shift
    echo "+ python3 bin/$command $@"
    exec python3 bin/$command "$@"
    ;;
  full) # Execute full workflow
    shift
    echo "# Starting full workflow..."
    echo "+ python3 bin/fetch_cli.py $@"
    python3 bin/fetch_cli.py "$@"
    echo "+ python3 bin/convert_all.py"
    python3 bin/convert_all.py
    ;;
  bash|sh)
    echo "+ $@"
    exec "$@"
    ;;
  help|--help|-h)
    cat << EOF
Confluence-MDX Container

Usage:
  docker run <image> <command> [args...]

Commands:
  fetch_cli.py [args...]            - Collect Confluence data
  convert_all.py [args...]          - Convert all pages to MDX
  full [fetch args...]              - Execute full workflow (fetch + convert)
  converter/cli.py <in> <out>       - Convert a single XHTML to MDX
  bash                              - Run interactive shell
  help                              - Show this help message

Examples:
  docker run docker.io/querypie/confluence-mdx:latest full
  docker run docker.io/querypie/confluence-mdx:latest full --recent
  docker run docker.io/querypie/confluence-mdx:latest convert_all.py
  docker run docker.io/querypie/confluence-mdx:latest fetch_cli.py --attachments
  docker run -v \$(pwd)/target:/workdir/target docker.io/querypie/confluence-mdx:latest full --local

Environment Variables:
  ATLASSIAN_USERNAME  - Confluence user email
  ATLASSIAN_API_TOKEN - Confluence API token
EOF
    ;;
  *)
    echo "+ $@"
    exec "$@"
    ;;
esac

