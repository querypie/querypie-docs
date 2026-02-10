# Makefile for testing converter/cli.py

# Variables
TEST_SCRIPT = ./run-tests.sh
VERBOSE_FLAG = $(if $(VERBOSE),--verbose,)
PROJECT_ROOT = $(shell cd ../.. && pwd)

# Default target
.PHONY: all
all: test-convert test-skeleton test-render
	@echo ""
	@echo "All tests completed."

# Run convert tests (XHTML → MDX)
.PHONY: test-convert
test-convert:
	@$(TEST_SCRIPT) --type convert --log-level warning $(VERBOSE_FLAG)

# Run a specific convert test
.PHONY: test-convert-one
test-convert-one:
	@if [ -z "$(TEST_ID)" ]; then \
		echo "Usage: make test-convert-one TEST_ID=<test_id>"; \
		exit 1; \
	fi
	@$(TEST_SCRIPT) --type convert --log-level warning --test-id $(TEST_ID) $(VERBOSE_FLAG)

# Run convert tests with debug log level
.PHONY: debug-convert
debug-convert:
	@$(TEST_SCRIPT) --type convert --log-level debug $(VERBOSE_FLAG)

# Run a specific convert test with debug log level
.PHONY: debug-convert-one
debug-convert-one:
	@if [ -z "$(TEST_ID)" ]; then \
		echo "Usage: make debug-convert-one TEST_ID=<test_id>"; \
		exit 1; \
	fi
	@$(TEST_SCRIPT) --type convert --log-level debug --test-id $(TEST_ID) $(VERBOSE_FLAG)

# Run skeleton tests
.PHONY: test-skeleton
test-skeleton:
	@$(TEST_SCRIPT) --type skeleton $(VERBOSE_FLAG)

# Run a specific skeleton test
.PHONY: test-skeleton-one
test-skeleton-one:
	@if [ -z "$(TEST_ID)" ]; then \
		echo "Usage: make test-skeleton-one TEST_ID=<test_id>"; \
		exit 1; \
	fi
	@$(TEST_SCRIPT) --type skeleton --test-id $(TEST_ID) $(VERBOSE_FLAG)

# Run reverse-sync tests
.PHONY: test-reverse-sync
test-reverse-sync:
	@$(TEST_SCRIPT) --type reverse-sync $(VERBOSE_FLAG)

# Run a specific reverse-sync test
.PHONY: test-reverse-sync-one
test-reverse-sync-one:
	@if [ -z "$(TEST_ID)" ]; then \
		echo "Usage: make test-reverse-sync-one TEST_ID=<test_id>"; \
		exit 1; \
	fi
	@$(TEST_SCRIPT) --type reverse-sync --test-id $(TEST_ID) $(VERBOSE_FLAG)

# Run image-copy tests
.PHONY: test-image-copy
test-image-copy:
	@$(TEST_SCRIPT) --type image-copy $(VERBOSE_FLAG)

# Run a specific image-copy test
.PHONY: test-image-copy-one
test-image-copy-one:
	@if [ -z "$(TEST_ID)" ]; then \
		echo "Usage: make test-image-copy-one TEST_ID=<test_id>"; \
		exit 1; \
	fi
	@$(TEST_SCRIPT) --type image-copy --test-id $(TEST_ID) $(VERBOSE_FLAG)

# Run xhtml-diff tests
.PHONY: test-xhtml-diff
test-xhtml-diff:
	@$(TEST_SCRIPT) --type xhtml-diff $(VERBOSE_FLAG)

# Run a specific xhtml-diff test
.PHONY: test-xhtml-diff-one
test-xhtml-diff-one:
	@if [ -z "$(TEST_ID)" ]; then \
		echo "Usage: make test-xhtml-diff-one TEST_ID=<test_id>"; \
		exit 1; \
	fi
	@$(TEST_SCRIPT) --type xhtml-diff --test-id $(TEST_ID) $(VERBOSE_FLAG)

# Run render tests (MDX to HTML)
.PHONY: test-render
test-render:
	@cd $(PROJECT_ROOT) && npx vitest run --config confluence-mdx/tests/render/vitest.config.ts

# Run a specific render test
.PHONY: test-render-one
test-render-one:
	@if [ -z "$(TEST_ID)" ]; then \
		echo "Usage: make test-render-one TEST_ID=<test_id>"; \
		exit 1; \
	fi
	@cd $(PROJECT_ROOT) && npx vitest run --config confluence-mdx/tests/render/vitest.config.ts -t "$(TEST_ID)"

# Clean output files
.PHONY: clean
clean:
	@echo "Cleaning output files..."
	@find testcases -name "output.mdx" -type f -delete
	@find testcases -name "output.skel.mdx" -type f -delete
	@find testcases -name "output.html" -type f -delete
	@find testcases -name "_meta.ts" -path "*/output/*" -type f -delete
	@find testcases -name "output.reverse-sync.*" -type f -delete
	@find testcases -name "output.mdx.diff" -type f -delete
	@find testcases -name "output.beautify-diff" -type f -delete

# Help
.PHONY: help
help:
	@echo "Available targets:"
	@echo ""
	@echo "  all (default)"
	@echo "    test-convert + test-skeleton + test-render 를 순서대로 실행"
	@echo ""
	@echo "  test-convert / test-convert-one"
	@echo "    XHTML → MDX 정방향 변환. expected.mdx 와 비교"
	@echo ""
	@echo "  test-skeleton / test-skeleton-one"
	@echo "    MDX → skeleton MDX 변환. expected.skel.mdx 와 비교"
	@echo ""
	@echo "  test-reverse-sync / test-reverse-sync-one"
	@echo "    MDX 편집분을 XHTML 에 역패치."
	@echo "    patched.xhtml, diff.yaml 등 5개 산출물 비교"
	@echo ""
	@echo "  test-image-copy / test-image-copy-one"
	@echo "    이미지 파일 복사 및 파일명 sanitize 검증"
	@echo ""
	@echo "  test-xhtml-diff / test-xhtml-diff-one"
	@echo "    page.xhtml ↔ patched.xhtml beautify-diff."
	@echo "    serializer 부산물 무시, 실제 변경만 검증"
	@echo ""
	@echo "  test-render / test-render-one"
	@echo "    MDX → HTML 렌더링(vitest). expected.html 과 비교"
	@echo ""
	@echo "  debug-convert / debug-convert-one"
	@echo "    test-convert 와 동일하나 debug 로그 출력"
	@echo ""
	@echo "  clean    output.* 생성 파일 삭제"
	@echo "  help     이 도움말"
	@echo ""
	@echo "Options:"
	@echo "  TEST_ID=<id>   *-one 타겟에서 실행할 testcase ID"
	@echo "  VERBOSE=1      실행 명령과 변환기 출력 표시"
	@echo ""
	@echo "Examples:"
	@echo "  make"
	@echo "  make test-convert VERBOSE=1"
	@echo "  make test-convert-one TEST_ID=568918170"
	@echo "  make test-reverse-sync-one TEST_ID=1911652402"
	@echo "  make test-render-one TEST_ID=544382364"
