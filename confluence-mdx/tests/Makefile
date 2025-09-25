# Makefile for testing confluence_xhtml_to_markdown.py

# Variables
# Activate virtualenv located at project root: ../../venv
VENV = source ../../venv/bin/activate
# Converter script now lives under confluence-mdx/bin/
SCRIPT = ../bin/confluence_xhtml_to_markdown.py
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
	@for test_case in $$(find $(TEST_DIR) -type d -depth 1); do \
		test_id=$$(basename $$test_case); \
		if [ -f "$(TEST_DIR)/$$test_id/page.xhtml" ]; then \
			echo "Testing case: $$test_id (XHTML)"; \
			echo "  Processing page.xhtml"; \
			$(VENV) && \
			python $(SCRIPT) --log-level warning \
				$(TEST_DIR)/$$test_id/page.xhtml \
				$(TEST_DIR)/$$test_id/output.mdx \
				--public-dir=$(TEST_DIR) \
				--attachment-dir=/$$test_id/output; \
			$(DIFF) $(TEST_DIR)/$$test_id/expected.mdx $(TEST_DIR)/$$test_id/output.mdx || echo "Test $$test_id (XHTML) failed"; \
		fi; \
	done

# Run a specific test
.PHONY: test-one
test-one:
	@if [ -z "$(TEST_ID)" ]; then \
		echo "Usage: make test-one TEST_ID=<test_id>"; \
		exit 1; \
	fi
	@echo "Testing case: $(TEST_ID) (XHTML)"
	@if [ -f "$(TEST_DIR)/$(TEST_ID)/page.xhtml" ]; then \
		echo "  Processing page.xhtml"; \
		$(VENV) && \
		python $(SCRIPT) --log-level warning \
			$(TEST_DIR)/$(TEST_ID)/page.xhtml \
			$(TEST_DIR)/$(TEST_ID)/output.mdx \
			--public-dir=$(TEST_DIR) \
			--attachment-dir=/$(TEST_ID)/output; \
		$(DIFF) $(TEST_DIR)/$(TEST_ID)/expected.mdx $(TEST_DIR)/$(TEST_ID)/output.mdx || echo "Test $(TEST_ID) (XHTML) failed"; \
	else \
		echo "  No page.xhtml found for test case $(TEST_ID)"; \
	fi

# Run tests with debug log level
.PHONY: debug
debug: debug-xhtml
	@echo "All debug tests completed."

# Run XHTML tests with debug log level
.PHONY: debug-xhtml
debug-xhtml:
	@echo "Running XHTML tests with debug log level..."
	@for test_case in $$(find $(TEST_DIR) -type d -depth 1); do \
		test_id=$$(basename $$test_case); \
		if [ -f "$(TEST_DIR)/$$test_id/page.xhtml" ]; then \
			echo "Testing case: $$test_id (XHTML)"; \
			echo "  Processing page.xhtml"; \
			$(VENV) && \
			python $(SCRIPT) --log-level debug \
			 	$(TEST_DIR)/$$test_id/page.xhtml \
			 	$(TEST_DIR)/$$test_id/output.mdx \
			 	--public-dir=$(TEST_DIR) \
			 	--attachment-dir=/$$test_id/output; \
			$(DIFF) $(TEST_DIR)/$$test_id/expected.mdx $(TEST_DIR)/$$test_id/output.mdx || echo "Test $$test_id (XHTML) failed"; \
		fi; \
	done

# Run a specific test with debug log level
.PHONY: debug-one
debug-one:
	@if [ -z "$(TEST_ID)" ]; then \
		echo "Usage: make debug-one TEST_ID=<test_id>"; \
		exit 1; \
	fi
	@echo "Testing case: $(TEST_ID) (XHTML) with debug log level"
	@if [ -f "$(TEST_DIR)/$(TEST_ID)/page.xhtml" ]; then \
		echo "  Processing page.xhtml"; \
		$(VENV) && \
		python $(SCRIPT) --log-level debug \
			$(TEST_DIR)/$(TEST_ID)/page.xhtml \
			$(TEST_DIR)/$(TEST_ID)/output.mdx \
			--public-dir=$(TEST_DIR) \
			--attachment-dir=/$(TEST_ID)/output; \
		$(DIFF) $(TEST_DIR)/$(TEST_ID)/expected.mdx $(TEST_DIR)/$(TEST_ID)/output.mdx || echo "Test $(TEST_ID) (XHTML) failed"; \
	else \
		echo "  No page.xhtml found for test case $(TEST_ID)"; \
	fi

# Clean output files
.PHONY: clean
clean:
	@echo "Cleaning output files..."
	@find $(TEST_DIR) -name "output.mdx" -type f -delete

# Help
.PHONY: help
help:
	@echo "Available targets:"
	@echo "  all            - Run all tests (default)"
	@echo "  test           - Run all tests (XHTML only)"
	@echo "  test-one       - Run a specific test for XHTML, e.g., make test-one TEST_ID=568918170"
	@echo "  debug          - Run all tests with debug log level (XHTML only)"
	@echo "  debug-one      - Run a specific test with debug log level for XHTML, e.g., make debug-one TEST_ID=568918170"
	@echo "  clean          - Remove all output files"
	@echo "  help           - Show this help message"
