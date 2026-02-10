#!/usr/bin/env bash
#
# Run XHTML to MDX conversion tests
#
# Usage:
#   ./run-tests.sh [options]
#
# Options:
#   --type TYPE       Test type: xhtml (default), skeleton, reverse-sync, image-copy
#   --log-level LEVEL Log level: warning (default), debug, info
#   --test-id ID      Run specific test case only
#   --verbose, -v     Show converter output (stdout/stderr)
#   --help            Show this help message

set -o nounset -o errexit -o pipefail

# Change to script directory for relative paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

# Configuration (relative paths from script directory)
TEST_DIR="testcases"
BIN_DIR="../bin"
VENV_DIR="../venv"

CONVERTER_SCRIPT="${BIN_DIR}/converter/cli.py"
SKELETON_SCRIPT="${BIN_DIR}/skeleton/cli.py"

# Ensure bin/ is on PYTHONPATH so skeleton package imports resolve
export PYTHONPATH="${BIN_DIR}:${PYTHONPATH:-}"

# Default options
TEST_TYPE="xhtml"
LOG_LEVEL="warning"
TEST_ID=""
VERBOSE=false

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

# Print command if verbose mode
log_cmd() {
    if [[ "${VERBOSE}" == "true" ]]; then
        echo -e "${YELLOW}+ $*${NC}"
    fi
}

# Run command with optional verbose logging
run_cmd() {
    log_cmd "$@"
    "$@"
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
        --verbose|-v)
            VERBOSE=true
            shift
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

# Resolve page_id → slug path from pages.yaml
resolve_slug_path() {
    local page_id="$1"
    python3 -c "
import sys, yaml
pages = yaml.safe_load(open('${VENV_DIR}/../var/pages.yaml'))
for p in pages:
    if str(p.get('page_id', '')) == sys.argv[1]:
        print('/' + '/'.join(p['path']))
        sys.exit(0)
print(f'ERROR: page_id {sys.argv[1]} not found in pages.yaml', file=sys.stderr)
sys.exit(1)
" "${page_id}"
}

# Run XHTML test for a single test case
run_xhtml_test() {
    local test_id="$1"
    local test_path="${TEST_DIR}/${test_id}"

    if [[ ! -f "${test_path}/page.xhtml" ]]; then
        return 1
    fi

    local slug_path
    slug_path=$(resolve_slug_path "${test_id}" 2>/dev/null) || slug_path=""

    run_cmd python "${CONVERTER_SCRIPT}" --log-level "${LOG_LEVEL}" \
        "${test_path}/page.xhtml" \
        "${test_path}/output.mdx" \
        --public-dir="${TEST_DIR}" \
        --attachment-dir="${slug_path}" \
        --skip-image-copy

    if [[ ! -f "${test_path}/expected.mdx" ]]; then
        echo "  Error: expected.mdx not found"
        return 1
    fi

    run_cmd diff -u "${test_path}/expected.mdx" "${test_path}/output.mdx"
}

# Run skeleton test for a single test case
run_skeleton_test() {
    local test_id="$1"
    local test_path="${TEST_DIR}/${test_id}"

    if [[ ! -f "${test_path}/output.mdx" ]]; then
        return 1
    fi

    run_cmd python "${SKELETON_SCRIPT}" "${test_path}/output.mdx"

    if [[ ! -f "${test_path}/expected.skel.mdx" ]]; then
        echo "  Error: expected.skel.mdx not found"
        return 1  # Failure
    fi

    run_cmd diff -u "${test_path}/expected.skel.mdx" "${test_path}/output.skel.mdx"
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

# Run reverse-sync test for a single test case
run_reverse_sync_test() {
    local test_id="$1"
    local test_path="${TEST_DIR}/${test_id}"

    # verify 실행 (cwd를 confluence-mdx root로 이동 — run_verify()가 var/<page_id>/에 중간 파일을 쓰므로)
    pushd .. > /dev/null
    run_cmd env PYTHONPATH=bin python3 bin/reverse_sync_test_verify.py \
        "${test_id}" \
        "tests/${test_path}/original.mdx" \
        "tests/${test_path}/improved.mdx" \
        "tests/${test_path}/page.xhtml"
    popd > /dev/null

    # var/에 생성된 중간 파일을 output.*으로 복사
    local var_dir="../var/${test_id}"
    cp "${var_dir}/reverse-sync.result.yaml"           "${test_path}/output.reverse-sync.result.yaml"
    cp "${var_dir}/reverse-sync.patched.xhtml"          "${test_path}/output.reverse-sync.patched.xhtml"
    cp "${var_dir}/reverse-sync.diff.yaml"              "${test_path}/output.reverse-sync.diff.yaml"
    cp "${var_dir}/reverse-sync.mapping.original.yaml"  "${test_path}/output.reverse-sync.mapping.original.yaml"
    cp "${var_dir}/reverse-sync.mapping.patched.yaml"   "${test_path}/output.reverse-sync.mapping.patched.yaml"

    # MDX diff 검증: original.mdx ↔ improved.mdx 차이가 expected와 일치하는지 확인
    diff -u --label a/original.mdx --label b/improved.mdx \
        "${test_path}/original.mdx" "${test_path}/improved.mdx" \
        > "${test_path}/output.mdx.diff" || true
    diff -u "${test_path}/expected.mdx.diff" "${test_path}/output.mdx.diff"

    # expected와 비교 (timestamp/경로 필드 제외)
    diff -u <(grep -v 'created_at' "${test_path}/expected.reverse-sync.result.yaml") \
            <(grep -v 'created_at' "${test_path}/output.reverse-sync.result.yaml")
    diff -u "${test_path}/expected.reverse-sync.patched.xhtml" \
            "${test_path}/output.reverse-sync.patched.xhtml"
    diff -u <(grep -v 'created_at\|original_mdx\|improved_mdx' "${test_path}/expected.reverse-sync.diff.yaml") \
            <(grep -v 'created_at\|original_mdx\|improved_mdx' "${test_path}/output.reverse-sync.diff.yaml")
    diff -u <(grep -v 'created_at\|source_xhtml' "${test_path}/expected.reverse-sync.mapping.original.yaml") \
            <(grep -v 'created_at\|source_xhtml' "${test_path}/output.reverse-sync.mapping.original.yaml")
    diff -u <(grep -v 'created_at\|source_xhtml' "${test_path}/expected.reverse-sync.mapping.patched.yaml") \
            <(grep -v 'created_at\|source_xhtml' "${test_path}/output.reverse-sync.mapping.patched.yaml")
}

has_reverse_sync_input() {
    local test_id="$1"
    [[ -f "${TEST_DIR}/${test_id}/original.mdx" ]] && \
    [[ -f "${TEST_DIR}/${test_id}/improved.mdx" ]]
}

# Run image-copy test: verify converter copies and sanitizes image files correctly
run_image_copy_test() {
    local test_id="$1"
    local test_path="${TEST_DIR}/${test_id}"

    if [[ ! -f "${test_path}/page.xhtml" ]]; then
        return 1
    fi

    local slug_path
    slug_path=$(resolve_slug_path "${test_id}")

    # Image copy destination (temporary)
    local img_output_dir="${test_path}/output-images"
    rm -rf "${img_output_dir}"

    # Run WITHOUT --skip-image-copy → images get copied
    run_cmd python "${CONVERTER_SCRIPT}" --log-level "${LOG_LEVEL}" \
        "${test_path}/page.xhtml" \
        "${test_path}/output-images.mdx" \
        --public-dir="${TEST_DIR}" \
        --attachment-dir="/${test_id}/output-images"

    if [[ ! -d "${img_output_dir}" ]]; then
        echo "  Error: output-images directory was not created"
        return 1
    fi

    # Compare actual file list with expected
    diff -u "${test_path}/expected-images.txt" \
            <(cd "${img_output_dir}" && ls -1 | sort)

    # Cleanup
    rm -rf "${img_output_dir}" "${test_path}/output-images.mdx"
}

has_image_copy_input() {
    local test_id="$1"
    [[ -f "${TEST_DIR}/${test_id}/page.xhtml" ]] && \
    [[ -f "${TEST_DIR}/${test_id}/expected-images.txt" ]]
}

# Run all tests of specified type
run_all_tests() {
    local test_func="$1"
    local test_label="$2"
    local input_check="$3"
    local failed=0
    local passed=0

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

        if [[ "${VERBOSE}" == "true" ]]; then
            # Show all output in verbose mode
            if ${test_func} "${test_id}"; then
                log_ok
                passed=$((passed + 1))
            else
                log_failed
                failed=$((failed + 1))
            fi
        else
            # Suppress output, show only on failure
            if ${test_func} "${test_id}" > /dev/null 2>&1; then
                log_ok
                passed=$((passed + 1))
            else
                log_failed
                # Show diff output on failure
                ${test_func} "${test_id}" 2>&1 || true
                failed=$((failed + 1))
            fi
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

    if [[ "${VERBOSE}" == "true" ]]; then
        # Show all output in verbose mode
        if ${test_func} "${test_id}"; then
            log_ok
        else
            log_failed
            exit 1
        fi
    else
        # Suppress output, show only on failure
        if ${test_func} "${test_id}" > /dev/null 2>&1; then
            log_ok
        else
            log_failed
            ${test_func} "${test_id}" || true
            exit 1
        fi
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
        reverse-sync)
            if [[ -n "${TEST_ID}" ]]; then
                run_single_test run_reverse_sync_test "Reverse-Sync" "${TEST_ID}"
            else
                run_all_tests run_reverse_sync_test "Reverse-Sync" has_reverse_sync_input
            fi
            ;;
        image-copy)
            if [[ -n "${TEST_ID}" ]]; then
                run_single_test run_image_copy_test "Image-Copy" "${TEST_ID}"
            else
                run_all_tests run_image_copy_test "Image-Copy" has_image_copy_input
            fi
            ;;
        *)
            echo "Unknown test type: ${TEST_TYPE}"
            exit 1
            ;;
    esac
}

main
