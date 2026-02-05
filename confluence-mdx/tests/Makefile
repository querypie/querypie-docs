# Makefile for testing confluence_xhtml_to_markdown.py

# Variables
TEST_SCRIPT = ./run-tests.sh
VERBOSE_FLAG = $(if $(VERBOSE),--verbose,)

# Default target
.PHONY: all
all: test-xhtml test-skeleton
	@echo ""
	@echo "All tests completed."

# Run XHTML tests (alias)
.PHONY: test
test: test-xhtml

# Run XHTML tests only
.PHONY: test-xhtml
test-xhtml:
	@$(TEST_SCRIPT) --type xhtml --log-level warning $(VERBOSE_FLAG)

# Run a specific XHTML test
.PHONY: test-one
test-one:
	@if [ -z "$(TEST_ID)" ]; then \
		echo "Usage: make test-one TEST_ID=<test_id>"; \
		exit 1; \
	fi
	@$(TEST_SCRIPT) --type xhtml --log-level warning --test-id $(TEST_ID) $(VERBOSE_FLAG)

# Run XHTML tests with debug log level
.PHONY: debug
debug: debug-xhtml
	@echo "All debug tests completed."

# Run XHTML tests with debug log level
.PHONY: debug-xhtml
debug-xhtml:
	@$(TEST_SCRIPT) --type xhtml --log-level debug $(VERBOSE_FLAG)

# Run a specific XHTML test with debug log level
.PHONY: debug-one
debug-one:
	@if [ -z "$(TEST_ID)" ]; then \
		echo "Usage: make debug-one TEST_ID=<test_id>"; \
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

# Clean output files
.PHONY: clean
clean:
	@echo "Cleaning output files..."
	@find testcases -name "output.mdx" -type f -delete
	@find testcases -name "output.skel.mdx" -type f -delete
	@find testcases -name "_meta.ts" -path "*/output/*" -type f -delete

# Help
.PHONY: help
help:
	@echo "Available targets:"
	@echo "  all                - Run all tests: XHTML + Skeleton (default)"
	@echo "  test, test-xhtml   - Run XHTML tests only"
	@echo "  test-one           - Run a specific XHTML test"
	@echo "  test-skeleton      - Run Skeleton tests only"
	@echo "  test-skeleton-one  - Run a specific Skeleton test"
	@echo "  debug, debug-xhtml - Run XHTML tests with debug log level"
	@echo "  debug-one          - Run a specific XHTML test with debug log level"
	@echo "  clean              - Remove all output files"
	@echo "  help               - Show this help message"
	@echo ""
	@echo "Options:"
	@echo "  TEST_ID=<id>       - Specify test case ID for *-one targets"
	@echo "  VERBOSE=1          - Show executed commands and converter output"
	@echo ""
	@echo "Examples:"
	@echo "  make                                      # Run all tests"
	@echo "  make test-xhtml VERBOSE=1                 # Run XHTML tests with verbose"
	@echo "  make test-one TEST_ID=568918170           # Run specific XHTML test"
	@echo "  make debug-one TEST_ID=568918170 VERBOSE=1"
