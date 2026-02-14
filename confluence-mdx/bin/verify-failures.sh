#!/usr/bin/env bash
#
# verify-failures.sh
#
# 이전 verify 실행 로그에서 fail/error 항목만 추출하여 재검증한다.
# reverse_sync_cli.py 코드를 수정한 뒤, 실패 항목만 빠르게 확인할 때 사용.
#
# Usage:
#   bin/verify-failures.sh <log-file>
#
# 로그 파일 첫 줄에서 브랜치명을 자동 추출하여 ref:path 형식으로 verify 실행.
# 예) "Processing 211/211 file(s) from branch fix/proofread-mdx..."
#     → fix/proofread-mdx:src/content/ko/...

set -o nounset -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLI="${SCRIPT_DIR}/reverse_sync_cli.py"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

usage() {
    sed -n '3,13p' "$0" | sed 's/^# //' | sed 's/^#//'
    exit 0
}

# 로그 첫 줄에서 브랜치명 추출
# "Processing N/N file(s) from branch <branch>..." → <branch>
extract_branch() {
    local log="$1"
    head -1 "${log}" | sed -n 's/.*from branch \([^ ]*\)\.\.\..*/\1/p'
}

# 로그에서 fail/error 파일 경로 추출
extract_failures() {
    local log="$1"
    grep -E '\.\.\.\s+(fail|error)$' "$log" \
        | sed 's/.*] //' \
        | sed 's/ \.\.\. \(fail\|error\)$//'
}

main() {
    local log_file="${1:-}"

    if [[ -z "${log_file}" || "${log_file}" == "--help" || "${log_file}" == "-h" ]]; then
        usage
    fi

    if [[ ! -f "${log_file}" ]]; then
        echo "ERROR: 로그 파일을 찾을 수 없습니다: ${log_file}" >&2
        exit 1
    fi

    local branch
    branch="$(extract_branch "${log_file}")"
    if [[ -z "${branch}" ]]; then
        echo "ERROR: 로그 첫 줄에서 브랜치명을 추출할 수 없습니다." >&2
        echo "       expected: 'Processing N/N file(s) from branch <branch>...'" >&2
        exit 1
    fi

    local failures=()
    while IFS= read -r path; do
        failures+=("${path}")
    done < <(extract_failures "${log_file}")

    if [[ ${#failures[@]} -eq 0 ]]; then
        echo "fail/error 항목이 없습니다."
        exit 0
    fi

    echo "=== branch: ${branch}, 재검증 대상: ${#failures[@]}건 ==="
    echo ""

    local passed=0
    local failed=0
    local errors=0
    local still_failing=()

    for (( i=0; i<${#failures[@]}; i++ )); do
        local mdx="${failures[$i]}"
        local ref="${branch}:${mdx}"
        printf "[%d/%d] %s ... " "$((i + 1))" "${#failures[@]}" "${mdx}"

        local output
        output="$(python3 "${CLI}" verify "${ref}" 2>&1)" || true
        local result
        result="$(echo "${output}" | grep -oE '(pass|fail|error)$' | tail -1)" || true
        result="${result:-error}"

        case "${result}" in
            pass)
                echo -e "${GREEN}${result}${NC}"
                passed=$((passed + 1))
                ;;
            fail)
                echo -e "${RED}${result}${NC}"
                failed=$((failed + 1))
                still_failing+=("${mdx}")
                ;;
            *)
                echo -e "${RED}${result}${NC}"
                errors=$((errors + 1))
                still_failing+=("${mdx}")
                ;;
        esac
    done

    echo ""
    echo "Results: ${passed} passed, ${failed} failed, ${errors} errors (total ${#failures[@]})"

    if [[ ${#still_failing[@]} -gt 0 ]]; then
        echo ""
        echo "Still failing:"
        printf "  %s\n" "${still_failing[@]}"
        exit 1
    fi
}

main "$@"
