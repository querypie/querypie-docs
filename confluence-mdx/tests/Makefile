# Makefile for testing converter/cli.py

# Variables
TEST_SCRIPT = ./run-tests.sh
VERBOSE_FLAG = $(if $(VERBOSE),--verbose,)
PROJECT_ROOT = $(shell cd ../.. && pwd)

# Default target
.PHONY: all
all: test-xhtml test-skeleton test-render
	@echo ""
	@echo "All tests completed."

# Run XHTML tests only
.PHONY: test-xhtml
test-xhtml:
	@$(TEST_SCRIPT) --type xhtml --log-level warning $(VERBOSE_FLAG)

# Run a specific XHTML test
.PHONY: test-xhtml-one
test-xhtml-one:
	@if [ -z "$(TEST_ID)" ]; then \
		echo "Usage: make test-xhtml-one TEST_ID=<test_id>"; \
		exit 1; \
	fi
	@$(TEST_SCRIPT) --type xhtml --log-level warning --test-id $(TEST_ID) $(VERBOSE_FLAG)

# Run XHTML tests with debug log level
.PHONY: debug-xhtml
debug-xhtml:
	@$(TEST_SCRIPT) --type xhtml --log-level debug $(VERBOSE_FLAG)

# Run a specific XHTML test with debug log level
.PHONY: debug-xhtml-one
debug-xhtml-one:
	@if [ -z "$(TEST_ID)" ]; then \
		echo "Usage: make debug-xhtml-one TEST_ID=<test_id>"; \
		exit 1; \
	fi
	@$(TEST_SCRIPT) --type xhtml --log-level debug --test-id $(TEST_ID) $(VERBOSE_FLAG)

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

# Help
.PHONY: help
help:
	@echo "Available targets:"
	@echo "  all                - Run all tests: XHTML + Skeleton + Render (default)"
	@echo "  test-xhtml         - Run XHTML tests"
	@echo "  test-xhtml-one     - Run a specific XHTML test"
	@echo "  test-skeleton      - Run Skeleton tests"
	@echo "  test-skeleton-one  - Run a specific Skeleton test"
	@echo "  test-reverse-sync      - Run Reverse-Sync tests"
	@echo "  test-reverse-sync-one  - Run a specific Reverse-Sync test"
	@echo "  test-render        - Run Render tests (MDX to HTML)"
	@echo "  test-render-one    - Run a specific Render test"
	@echo "  debug-xhtml        - Run XHTML tests with debug log level"
	@echo "  debug-xhtml-one    - Run a specific XHTML test with debug log level"
	@echo "  clean              - Remove all output files"
	@echo "  help               - Show this help message"
	@echo ""
	@echo "Options:"
	@echo "  TEST_ID=<id>       - Specify test case ID for *-one targets"
	@echo "  VERBOSE=1          - Show executed commands and converter output"
	@echo ""
	@echo "Examples:"
	@echo "  make                                           # Run all tests"
	@echo "  make test-xhtml VERBOSE=1                      # Run XHTML tests with verbose"
	@echo "  make test-xhtml-one TEST_ID=568918170          # Run specific XHTML test"
	@echo "  make test-reverse-sync-one TEST_ID=1911652402   # Run specific Reverse-Sync test"
	@echo "  make test-render-one TEST_ID=544382364         # Run specific Render test"
