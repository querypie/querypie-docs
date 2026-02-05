#!/usr/bin/env bash
#
# Run XHTML to MDX conversion tests
#
# Usage:
#   ./run-tests.sh [options]
#
# Options:
#   --type TYPE       Test type: xhtml (default), skeleton
#   --log-level LEVEL Log level: warning (default), debug, info
#   --test-id ID      Run specific test case only
#   --help            Show this help message

set -o nounset -o errexit -o pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_DIR="${SCRIPT_DIR}/testcases"
BIN_DIR="${SCRIPT_DIR}/../bin"
VENV_DIR="${SCRIPT_DIR}/../venv"

CONVERTER_SCRIPT="${BIN_DIR}/confluence_xhtml_to_markdown.py"
SKELETON_SCRIPT="${BIN_DIR}/mdx_to_skeleton.py"

# Default options
TEST_TYPE="xhtml"
LOG_LEVEL="warning"
TEST_ID=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

usage() {
    sed -n '3,12p' "$0" | sed 's/^# //' | sed 's/^#//'
    exit 0
}

log_ok() {
    echo -e "  ${GREEN}OK${NC}"
}

log_failed() {
    echo -e "  ${RED}FAILED${NC}"
}

log_skipped() {
    echo -e "  ${YELLOW}SKIPPED${NC} ($1)"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --type)
            TEST_TYPE="$2"
            shift 2
            ;;
        --log-level)
            LOG_LEVEL="$2"
            shift 2
            ;;
        --test-id)
            TEST_ID="$2"
            shift 2
            ;;
        --help|-h)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

# Activate virtual environment
activate_venv() {
    # shellcheck disable=SC1091
    source "${VENV_DIR}/bin/activate"
}

# Run XHTML test for a single test case
run_xhtml_test() {
    local test_id="$1"
    local test_path="${TEST_DIR}/${test_id}"

    if [[ ! -f "${test_path}/page.xhtml" ]]; then
        return 1
    fi

    python "${CONVERTER_SCRIPT}" --log-level "${LOG_LEVEL}" \
        "${test_path}/page.xhtml" \
        "${test_path}/output.mdx" \
        --public-dir="${TEST_DIR}" \
        --attachment-dir="/${test_id}/output"

    if [[ ! -f "${test_path}/expected.mdx" ]]; then
        echo "  Warning: expected.mdx not found"
        return 1
    fi

    diff -u "${test_path}/expected.mdx" "${test_path}/output.mdx"
}

# Run skeleton test for a single test case
run_skeleton_test() {
    local test_id="$1"
    local test_path="${TEST_DIR}/${test_id}"

    if [[ ! -f "${test_path}/output.mdx" ]]; then
        return 1
    fi

    python "${SKELETON_SCRIPT}" "${test_path}/output.mdx"

    if [[ ! -f "${test_path}/expected.skel.mdx" ]]; then
        echo "  Error: expected.skel.mdx not found"
        return 1  # Failure
    fi

    diff -u "${test_path}/expected.skel.mdx" "${test_path}/output.skel.mdx"
}

# Check if test case has required input files
has_xhtml_input() {
    local test_id="$1"
    [[ -f "${TEST_DIR}/${test_id}/page.xhtml" ]]
}

has_skeleton_input() {
    local test_id="$1"
    [[ -f "${TEST_DIR}/${test_id}/output.mdx" ]] && [[ -f "${TEST_DIR}/${test_id}/expected.skel.mdx" ]]
}

# Run all tests of specified type
run_all_tests() {
    local test_func="$1"
    local test_label="$2"
    local input_check="$3"
    local failed=0
    local passed=0
    local skipped=0

    echo "Running ${test_label} tests..."
    echo ""

    for test_case in $(find "${TEST_DIR}" -mindepth 1 -maxdepth 1 -type d | sort); do
        local test_id
        test_id=$(basename "${test_case}")

        # Skip if required input files don't exist
        if ! ${input_check} "${test_id}"; then
            continue
        fi

        echo "Testing case: ${test_id}"

        if ${test_func} "${test_id}" > /dev/null 2>&1; then
            log_ok
            passed=$((passed + 1))
        else
            log_failed
            # Show diff output
            ${test_func} "${test_id}" 2>&1 || true
            failed=$((failed + 1))
        fi
    done

    echo ""
    echo "Results: ${passed} passed, ${failed} failed"

    if [[ $failed -gt 0 ]]; then
        exit 1
    fi
}

# Run single test
run_single_test() {
    local test_func="$1"
    local test_label="$2"
    local test_id="$3"

    echo "Testing case: ${test_id} (${test_label})"

    if ${test_func} "${test_id}"; then
        log_ok
    else
        log_failed
        ${test_func} "${test_id}" || true
        exit 1
    fi
}

# Main
main() {
    activate_venv

    case "${TEST_TYPE}" in
        xhtml)
            if [[ -n "${TEST_ID}" ]]; then
                run_single_test run_xhtml_test "XHTML" "${TEST_ID}"
            else
                run_all_tests run_xhtml_test "XHTML" has_xhtml_input
            fi
            ;;
        skeleton)
            if [[ -n "${TEST_ID}" ]]; then
                run_single_test run_skeleton_test "Skeleton" "${TEST_ID}"
            else
                run_all_tests run_skeleton_test "Skeleton" has_skeleton_input
            fi
            ;;
        *)
            echo "Unknown test type: ${TEST_TYPE}"
            exit 1
            ;;
    esac
}

main
