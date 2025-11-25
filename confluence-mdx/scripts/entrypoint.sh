#!/bin/bash

set -o errexit -o nounset

case "${1:-help}" in
  pages_of_confluence.py|translate_titles.py|generate_commands_for_xhtml2markdown.py|confluence_xhtml_to_markdown.py)
    echo "+ python bin/$@"
    exec python "bin/$@"
    ;;
  generate_commands)
    shift
    echo "+ python bin/generate_commands_for_xhtml2markdown.py $@"
    python bin/generate_commands_for_xhtml2markdown.py "$@"
    ;;
  convert)
    echo "+ bash bin/xhtml2markdown.ko.sh"
    exec bash bin/xhtml2markdown.ko.sh
    ;;
  full) # Execute full workflow
    shift
    echo "# Starting full workflow..."
    echo "+ python bin/pages_of_confluence.py $@"
    python bin/pages_of_confluence.py "$@"
    echo "+ python bin/translate_titles.py"
    python bin/translate_titles.py
    echo "+ python bin/generate_commands_for_xhtml2markdown.py var/list.en.txt > bin/xhtml2markdown.ko.sh"
    python bin/generate_commands_for_xhtml2markdown.py var/list.en.txt > bin/xhtml2markdown.ko.sh
    echo "+ chmod +x bin/xhtml2markdown.ko.sh"
    chmod +x bin/xhtml2markdown.ko.sh
    echo "+ bash bin/xhtml2markdown.ko.sh"
    bash bin/xhtml2markdown.ko.sh
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
  pages_of_confluence.py [args...]  - Collect Confluence data
  translate_titles.py               - Translate titles
  generate_commands <list_file>     - Generate conversion commands
  convert                           - Convert XHTML to MDX
  full                              - Execute full workflow
  bash                              - Run interactive shell
  help                              - Show this help message

Examples:
  docker run docker.io/querypie/confluence-mdx:latest pages_of_confluence.py --attachments
  docker run docker.io/querypie/confluence-mdx:latest translate_titles.py
  docker run docker.io/querypie/confluence-mdx:latest generate_commands var/list.en.txt
  docker run docker.io/querypie/confluence-mdx:latest convert
  docker run -v \$(pwd)/target:/workdir/target docker.io/querypie/confluence-mdx:latest convert

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

