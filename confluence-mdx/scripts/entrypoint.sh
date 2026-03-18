#!/bin/bash

set -o errexit -o nounset

# ── Diagnostic metadata ────────────────────────────
# Display image build date and fetch_state.yaml summary
print_image_info() {
  echo "# ── Image Metadata ──────────────────────────"
  if [[ -f /workdir/.build-date ]]; then
    echo "#   Build Date : $(cat /workdir/.build-date)"
  else
    echo "#   Build Date : unknown"
  fi

  local state_file
  state_file=$(find /workdir/var -name fetch_state.yaml -print -quit 2>/dev/null)
  if [[ -n "$state_file" ]]; then
    echo "#   Fetch State: $state_file"
    while IFS= read -r line; do
      echo "#     $line"
    done < "$state_file"
  else
    echo "#   Fetch State: not found"
  fi

  local page_count
  page_count=$(find /workdir/var -mindepth 1 -maxdepth 1 -type d -name '[0-9]*' 2>/dev/null | wc -l | tr -d ' ')
  echo "#   Pages in var/: $page_count"
  echo "# ─────────────────────────────────────────────"
}

# ── Commands ────────────────────────────────────────
case "${1:-help}" in
  fetch_cli.py|convert_all.py|converter/cli.py)
    print_image_info
    command=$1
    shift
    echo "+ bin/$command $@"
    exec bin/$command "$@"
    ;;
  full) # Execute full workflow for a single Space
    print_image_info
    shift
    # Extract --sync-code value from args (default: qm)
    sync_code="qm"
    prev_arg=""
    for arg in "$@"; do
      if [[ "$prev_arg" == "--sync-code" ]]; then
        sync_code="$arg"
      elif [[ "$arg" == "--sync-code="* ]]; then
        sync_code="${arg#--sync-code=}"
      fi
      prev_arg="$arg"
    done
    echo "# Starting full workflow (sync-code: $sync_code)..."
    echo "+ bin/fetch_cli.py $@"
    bin/fetch_cli.py "$@"
    echo "+ bin/convert_all.py --sync-code $sync_code"
    bin/convert_all.py --sync-code "$sync_code"
    ;;
  full-all) # Execute full workflow for all Spaces
    print_image_info
    shift
    for CODE in qm qcp; do
      echo "# Starting full workflow for Space: $CODE..."
      echo "+ bin/fetch_cli.py --sync-code $CODE $@"
      bin/fetch_cli.py --sync-code "$CODE" "$@"
      echo "+ bin/convert_all.py --sync-code $CODE"
      bin/convert_all.py --sync-code "$CODE"
    done
    ;;
  status) # Show detailed var/ data status report
    exec bin/image_status.py "${@:2}"
    ;;
  bash|sh)
    echo "+ $@"
    exec "$@"
    ;;
  help|--help|-h)
    print_image_info
    cat << EOF

Confluence-MDX Container

Usage:
  docker run <image> <command> [args...]

Commands:
  fetch_cli.py [args...]            - Collect Confluence data
  convert_all.py [args...]          - Convert all pages to MDX
  full [fetch args...]              - Execute full workflow for a single Space (default: --sync-code qm)
  full-all [fetch args...]          - Execute full workflow for all Spaces (qm, qcp) sequentially
  converter/cli.py <in> <out>       - Convert a single XHTML to MDX
  status                            - Show var/ data freshness report
  bash                              - Run interactive shell
  help                              - Show this help message

Examples:
  docker run docker.io/querypie/confluence-mdx:latest full
  docker run docker.io/querypie/confluence-mdx:latest full --sync-code qm --recent
  docker run docker.io/querypie/confluence-mdx:latest full-all
  docker run docker.io/querypie/confluence-mdx:latest convert_all.py --sync-code qm
  docker run docker.io/querypie/confluence-mdx:latest fetch_cli.py --attachments
  docker run docker.io/querypie/confluence-mdx:latest status
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
