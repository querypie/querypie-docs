# Makefile for testing confluence_xhtml_to_markdown.py

# Variables
# Activate virtualenv located at project root: ../../venv
VENV = source ../venv/bin/activate
# Converter script now lives under confluence-mdx/bin/
SCRIPT = ../bin/confluence_xhtml_to_markdown.py
# Skeleton converter script
SKELETON_SCRIPT = ../bin/mdx_to_skeleton.py
# Testcases live under this directory
TEST_DIR = testcases
DIFF = diff -u

# Default target
.PHONY: all
all: test

# Run all tests
.PHONY: test
test: test-xhtml
	@echo "All tests completed."

# Run XHTML tests only
.PHONY: test-xhtml
test-xhtml:
	@echo "Running XHTML tests..."
	@failed=0; \
	for test_case in $$(find $(TEST_DIR) -mindepth 1 -maxdepth 1 -type d | sort); do \
		test_id=$$(basename $$test_case); \
		if [ -f "$(TEST_DIR)/$$test_id/page.xhtml" ]; then \
			echo "Testing case: $$test_id (XHTML)"; \
			$(VENV) && \
			python $(SCRIPT) --log-level warning \
				$(TEST_DIR)/$$test_id/page.xhtml \
				$(TEST_DIR)/$$test_id/output.mdx \
				--public-dir=$(TEST_DIR) \
				--attachment-dir=/$$test_id/output; \
			if ! $(DIFF) $(TEST_DIR)/$$test_id/expected.mdx $(TEST_DIR)/$$test_id/output.mdx > /dev/null 2>&1; then \
				echo "  FAILED"; \
				$(DIFF) $(TEST_DIR)/$$test_id/expected.mdx $(TEST_DIR)/$$test_id/output.mdx || true; \
				failed=$$((failed + 1)); \
			else \
				echo "  OK"; \
			fi; \
		fi; \
	done; \
	echo ""; \
	if [ $$failed -gt 0 ]; then \
		echo "$$failed test(s) failed."; \
		exit 1; \
	else \
		echo "All tests passed."; \
	fi

# Run a specific test
.PHONY: test-one
test-one:
	@if [ -z "$(TEST_ID)" ]; then \
		echo "Usage: make test-one TEST_ID=<test_id>"; \
		exit 1; \
	fi
	@echo "Testing case: $(TEST_ID) (XHTML)"
	@if [ -f "$(TEST_DIR)/$(TEST_ID)/page.xhtml" ]; then \
		$(VENV) && \
		python $(SCRIPT) --log-level warning \
			$(TEST_DIR)/$(TEST_ID)/page.xhtml \
			$(TEST_DIR)/$(TEST_ID)/output.mdx \
			--public-dir=$(TEST_DIR) \
			--attachment-dir=/$(TEST_ID)/output; \
		if ! $(DIFF) $(TEST_DIR)/$(TEST_ID)/expected.mdx $(TEST_DIR)/$(TEST_ID)/output.mdx > /dev/null 2>&1; then \
			echo "  FAILED"; \
			$(DIFF) $(TEST_DIR)/$(TEST_ID)/expected.mdx $(TEST_DIR)/$(TEST_ID)/output.mdx || true; \
			exit 1; \
		else \
			echo "  OK"; \
		fi; \
	else \
		echo "  No page.xhtml found for test case $(TEST_ID)"; \
		exit 1; \
	fi

# Run tests with debug log level
.PHONY: debug
debug: debug-xhtml
	@echo "All debug tests completed."

# Run XHTML tests with debug log level
.PHONY: debug-xhtml
debug-xhtml:
	@echo "Running XHTML tests with debug log level..."
	@failed=0; \
	for test_case in $$(find $(TEST_DIR) -mindepth 1 -maxdepth 1 -type d | sort); do \
		test_id=$$(basename $$test_case); \
		if [ -f "$(TEST_DIR)/$$test_id/page.xhtml" ]; then \
			echo "Testing case: $$test_id (XHTML)"; \
			$(VENV) && \
			python $(SCRIPT) --log-level debug \
				$(TEST_DIR)/$$test_id/page.xhtml \
				$(TEST_DIR)/$$test_id/output.mdx \
				--public-dir=$(TEST_DIR) \
				--attachment-dir=/$$test_id/output; \
			if ! $(DIFF) $(TEST_DIR)/$$test_id/expected.mdx $(TEST_DIR)/$$test_id/output.mdx > /dev/null 2>&1; then \
				echo "  FAILED"; \
				$(DIFF) $(TEST_DIR)/$$test_id/expected.mdx $(TEST_DIR)/$$test_id/output.mdx || true; \
				failed=$$((failed + 1)); \
			else \
				echo "  OK"; \
			fi; \
		fi; \
	done; \
	echo ""; \
	if [ $$failed -gt 0 ]; then \
		echo "$$failed test(s) failed."; \
		exit 1; \
	else \
		echo "All tests passed."; \
	fi

# Run a specific test with debug log level
.PHONY: debug-one
debug-one:
	@if [ -z "$(TEST_ID)" ]; then \
		echo "Usage: make debug-one TEST_ID=<test_id>"; \
		exit 1; \
	fi
	@echo "Testing case: $(TEST_ID) (XHTML) with debug log level"
	@if [ -f "$(TEST_DIR)/$(TEST_ID)/page.xhtml" ]; then \
		$(VENV) && \
		python $(SCRIPT) --log-level debug \
			$(TEST_DIR)/$(TEST_ID)/page.xhtml \
			$(TEST_DIR)/$(TEST_ID)/output.mdx \
			--public-dir=$(TEST_DIR) \
			--attachment-dir=/$(TEST_ID)/output; \
		if ! $(DIFF) $(TEST_DIR)/$(TEST_ID)/expected.mdx $(TEST_DIR)/$(TEST_ID)/output.mdx > /dev/null 2>&1; then \
			echo "  FAILED"; \
			$(DIFF) $(TEST_DIR)/$(TEST_ID)/expected.mdx $(TEST_DIR)/$(TEST_ID)/output.mdx || true; \
			exit 1; \
		else \
			echo "  OK"; \
		fi; \
	else \
		echo "  No page.xhtml found for test case $(TEST_ID)"; \
		exit 1; \
	fi

# Run skeleton tests
.PHONY: test-skeleton
test-skeleton:
	@echo "Running skeleton tests..."
	@failed=0; \
	for test_case in $$(find $(TEST_DIR) -mindepth 1 -maxdepth 1 -type d | sort); do \
		test_id=$$(basename $$test_case); \
		if [ -f "$(TEST_DIR)/$$test_id/output.mdx" ]; then \
			echo "Testing case: $$test_id (Skeleton)"; \
			$(VENV) && \
			python $(SKELETON_SCRIPT) $(TEST_DIR)/$$test_id/output.mdx; \
			if [ -f "$(TEST_DIR)/$$test_id/expected.skel.mdx" ]; then \
				if ! $(DIFF) $(TEST_DIR)/$$test_id/expected.skel.mdx $(TEST_DIR)/$$test_id/output.skel.mdx > /dev/null 2>&1; then \
					echo "  FAILED"; \
					$(DIFF) $(TEST_DIR)/$$test_id/expected.skel.mdx $(TEST_DIR)/$$test_id/output.skel.mdx || true; \
					failed=$$((failed + 1)); \
				else \
					echo "  OK"; \
				fi; \
			else \
				echo "  SKIPPED (no expected.skel.mdx)"; \
			fi; \
		else \
			echo "  Skipping $$test_id: output.mdx not found"; \
		fi; \
	done; \
	echo ""; \
	if [ $$failed -gt 0 ]; then \
		echo "$$failed test(s) failed."; \
		exit 1; \
	else \
		echo "All skeleton tests passed."; \
	fi

# Run a specific skeleton test
.PHONY: test-skeleton-one
test-skeleton-one:
	@if [ -z "$(TEST_ID)" ]; then \
		echo "Usage: make test-skeleton-one TEST_ID=<test_id>"; \
		exit 1; \
	fi
	@echo "Testing case: $(TEST_ID) (Skeleton)"
	@if [ -f "$(TEST_DIR)/$(TEST_ID)/output.mdx" ]; then \
		$(VENV) && \
		python $(SKELETON_SCRIPT) $(TEST_DIR)/$(TEST_ID)/output.mdx; \
		if [ -f "$(TEST_DIR)/$(TEST_ID)/expected.skel.mdx" ]; then \
			if ! $(DIFF) $(TEST_DIR)/$(TEST_ID)/expected.skel.mdx $(TEST_DIR)/$(TEST_ID)/output.skel.mdx > /dev/null 2>&1; then \
				echo "  FAILED"; \
				$(DIFF) $(TEST_DIR)/$(TEST_ID)/expected.skel.mdx $(TEST_DIR)/$(TEST_ID)/output.skel.mdx || true; \
				exit 1; \
			else \
				echo "  OK"; \
			fi; \
		else \
			echo "  SKIPPED (no expected.skel.mdx)"; \
		fi; \
	else \
		echo "  No output.mdx found for test case $(TEST_ID)"; \
		exit 1; \
	fi

# Clean output files
.PHONY: clean
clean:
	@echo "Cleaning output files..."
	@find $(TEST_DIR) -name "output.mdx" -type f -delete
	@find $(TEST_DIR) -name "output.skel.mdx" -type f -delete

# Help
.PHONY: help
help:
	@echo "Available targets:"
	@echo "  all                - Run all tests (default)"
	@echo "  test               - Run all tests (XHTML only)"
	@echo "  test-one           - Run a specific test for XHTML, e.g., make test-one TEST_ID=568918170"
	@echo "  test-skeleton      - Run all skeleton tests (converts output.mdx to output.skel.mdx and compares with expected.skel.mdx)"
	@echo "  test-skeleton-one  - Run a specific skeleton test, e.g., make test-skeleton-one TEST_ID=568918170"
	@echo "  debug              - Run all tests with debug log level (XHTML only)"
	@echo "  debug-one          - Run a specific test with debug log level for XHTML, e.g., make debug-one TEST_ID=568918170"
	@echo "  clean              - Remove all output files (output.mdx and output.skel.mdx)"
	@echo "  help               - Show this help message"
