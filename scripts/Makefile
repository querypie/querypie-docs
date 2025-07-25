# Makefile for testing confluence_xhtml_to_markdown.py

# Variables
VENV = source ../venv/bin/activate
SCRIPT = confluence_xhtml_to_markdown.py
TEST_DIR = tests/confluence_xhtml_to_markdown/testcases
DIFF = diff -u

# Default target
.PHONY: all
all: test

# Run all tests
.PHONY: test
test:
	@echo "Running all tests..."
	@for test_case in $$(find $(TEST_DIR) -type d -depth 1); do \
		test_id=$$(basename $$test_case); \
		echo "Testing case: $$test_id"; \
		$(VENV) && python $(SCRIPT) --log-level warning $(TEST_DIR)/$$test_id/page.xhtml $(TEST_DIR)/$$test_id/output.mdx; \
		$(DIFF) $(TEST_DIR)/$$test_id/expected.mdx $(TEST_DIR)/$$test_id/output.mdx || echo "Test $$test_id failed"; \
	done

# Run a specific test
.PHONY: test-one
test-one:
	@if [ -z "$(TEST_ID)" ]; then \
		echo "Usage: make test-one TEST_ID=<test_id>"; \
		exit 1; \
	fi
	@echo "Testing case: $(TEST_ID)"
	@$(VENV) && python $(SCRIPT) --log-level warning $(TEST_DIR)/$(TEST_ID)/page.xhtml $(TEST_DIR)/$(TEST_ID)/output.mdx
	@$(DIFF) $(TEST_DIR)/$(TEST_ID)/expected.mdx $(TEST_DIR)/$(TEST_ID)/output.mdx || echo "Test $(TEST_ID) failed"

# Run tests with debug log level
.PHONY: debug
debug:
	@echo "Running all tests with debug log level..."
	@for test_case in $$(find $(TEST_DIR) -type d -depth 1); do \
		test_id=$$(basename $$test_case); \
		echo "Testing case: $$test_id"; \
		$(VENV) && python $(SCRIPT) --log-level debug $(TEST_DIR)/$$test_id/page.xhtml $(TEST_DIR)/$$test_id/output.mdx; \
		$(DIFF) $(TEST_DIR)/$$test_id/expected.mdx $(TEST_DIR)/$$test_id/output.mdx || echo "Test $$test_id failed"; \
	done

# Run a specific test with debug log level
.PHONY: debug-one
debug-one:
	@if [ -z "$(TEST_ID)" ]; then \
		echo "Usage: make debug-one TEST_ID=<test_id>"; \
		exit 1; \
	fi
	@echo "Testing case: $(TEST_ID)"
	@$(VENV) && python $(SCRIPT) --log-level debug $(TEST_DIR)/$(TEST_ID)/page.xhtml $(TEST_DIR)/$(TEST_ID)/output.mdx
	@$(DIFF) $(TEST_DIR)/$(TEST_ID)/expected.mdx $(TEST_DIR)/$(TEST_ID)/output.mdx || echo "Test $(TEST_ID) failed"

# Clean output files
.PHONY: clean
clean:
	@echo "Cleaning output files..."
	@find $(TEST_DIR) -name "output.mdx" -type f -delete

# Help
.PHONY: help
help:
	@echo "Available targets:"
	@echo "  all       - Run all tests (default)"
	@echo "  test      - Run all tests"
	@echo "  test-one  - Run a specific test, e.g., make test-one TEST_ID=568918170"
	@echo "  debug     - Run all tests with debug log level"
	@echo "  debug-one - Run a specific test with debug log level, e.g., make debug-one TEST_ID=568918170"
	@echo "  clean     - Remove all output files"
	@echo "  help      - Show this help message"
