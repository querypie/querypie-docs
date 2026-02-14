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
trap 'exit 130' INT

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$(cd "${SCRIPT_DIR}/.." && pwd)"

readonly BOLD_CYAN="\e[1;36m"
readonly RESET="\e[0m"

usage() {
    sed -n '3,13p' "$0" | sed 's/^# //' | sed 's/^#//'
    exit 0
}

log::cmd() {
    printf "%b+ %s%b\n" "${BOLD_CYAN}" "$*" "${RESET}" 1>&2
}

# 로그 첫 줄에서 브랜치명 추출
# "Processing N/N file(s) from branch <branch>..." → <branch>
extract_branch() {
    local log="$1"
    head -1 "${log}" | sed -n 's/.*from branch \([^ ]*\)\.\.\..*/\1/p'
}

# 로그에서 fail/error 파일 경로 추출
# 로그 형식: "[N/M] src/content/ko/.../file.mdx ... fail"
extract_failures() {
    local log="$1"
    grep -E '\.\.\.\s+(fail|error)' "$log" \
        | sed 's/.*] //' \
        | sed 's/ \.\.\..*$//'
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

    for (( i=0; i<${#failures[@]}; i++ )); do
        local mdx="${failures[$i]}"
        local ref="${branch}:${mdx}"

        echo "──── [$(( i + 1 ))/${#failures[@]}] ${mdx} ────"
        log::cmd bin/reverse_sync_cli.py verify "${ref}"
        bin/reverse_sync_cli.py verify "${ref}"
        echo ""
    done
}

main "$@"
