#!/usr/bin/env bash
set -o nounset -o errtrace -o pipefail

commit=3807b220

set -o xtrace

for lang in ko ja en; do
  for subdir in administrator-manual user-manual querypie-overview release-notes; do
    git diff --name-only $commit HEAD -- "../../src/content/${lang}/${subdir}/**" ':(exclude)**/index.mdx' >${lang}.${subdir}.diff.nameonly
    git diff --stat $commit HEAD -- "../../src/content/${lang}/${subdir}/**" ':(exclude)**/index.mdx' >${lang}.${subdir}.diff.stat
    git diff --numstat $commit HEAD -- "../../src/content/${lang}/${subdir}/**" ':(exclude)**/index.mdx' >${lang}.${subdir}.diff.numstat
    git diff $commit HEAD -- "../../src/content/${lang}/${subdir}/**" ':(exclude)**/index.mdx' >${lang}.${subdir}.diff.patch
  done
done
