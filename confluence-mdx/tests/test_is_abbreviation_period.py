#!/usr/bin/env python3
"""
Unit tests for is_abbreviation_period function in mdx_to_skeleton.py

This test suite validates that the is_abbreviation_period function correctly
identifies periods that are part of abbreviations (e.g., .NET, 7.0.5, e.g., etc.)
and should not be used for sentence splitting.

Note: Title abbreviations (Dr., Mr., Mrs., Ms., Prof.) are not handled
by this function and are excluded from these tests.

Usage:
    cd confluence-mdx/tests
    python3 test_is_abbreviation_period.py
"""

import sys
import os

# Add the bin directory to the path so we can import mdx_to_skeleton
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bin'))

from mdx_to_skeleton import is_abbreviation_period


def test_case(text: str, period_pos: int, expected: bool, description: str) -> bool:
    """Test a single case and return True if it passes, False otherwise."""
    result = is_abbreviation_period(text, period_pos)
    status = "✓" if result == expected else "✗"
    print(f"{status} {description}")
    if result != expected:
        print(f"   Text: {repr(text)}")
        print(f"   Period position: {period_pos} (char: {repr(text[period_pos] if period_pos < len(text) else 'N/A')})")
        print(f"   Expected: {expected}, Got: {result}")
        print(f"   ❌ FAILED")
        return False
    return True


def test_dotnet_cases() -> bool:
    """Test .NET abbreviation cases."""
    print("\n1. .NET cases:")
    all_passed = True
    
    all_passed &= test_case(".NET", 0, True, ".NET at start")
    all_passed &= test_case(" .NET", 1, True, ".NET after space")
    all_passed &= test_case("Use .NET Core", 4, True, ".NET in sentence")
    all_passed &= test_case(".NET Framework", 0, True, ".NET Framework")
    all_passed &= test_case("Microsoft .NET", 10, True, ".NET after word")
    
    return all_passed


def test_common_abbreviations() -> bool:
    """Test common abbreviations like e.g., etc., i.e."""
    print("\n2. Common abbreviations:")
    all_passed = True
    
    all_passed &= test_case("e.g.", 3, True, "e.g.")
    all_passed &= test_case("etc.", 3, True, "etc.")
    all_passed &= test_case("i.e.", 3, True, "i.e.")
    all_passed &= test_case("For example, e.g., use this", 16, True, "e.g. in sentence")
    
    return all_passed


def test_version_numbers() -> bool:
    """Test version number patterns like 7.0.5, 1.2.3."""
    print("\n3. Version numbers:")
    all_passed = True
    
    all_passed &= test_case("7.0.5", 1, True, "7.0.5 - first period")
    all_passed &= test_case("7.0.5", 3, True, "7.0.5 - second period")
    all_passed &= test_case("1.2.3", 1, True, "1.2.3 - first period")
    all_passed &= test_case("9.14.0", 1, True, "9.14.0 - first period")
    all_passed &= test_case("10.2.5", 2, True, "10.2.5 - first period")
    all_passed &= test_case("Version 1.2.3", 9, True, "Version number in text - first period")
    
    return all_passed


def test_false_positives() -> bool:
    """Test cases that should return False (normal sentence periods)."""
    print("\n4. False positives (should be False):")
    all_passed = True
    
    all_passed &= test_case("Hello. World", 5, False, "Normal sentence period")
    all_passed &= test_case("End.", 3, False, "End of sentence")
    all_passed &= test_case("A. B", 1, False, "Initial with space")
    all_passed &= test_case("The end.", 7, False, "Sentence ending")
    all_passed &= test_case("Test. Another.", 4, False, "Multiple sentences")
    
    return all_passed


def test_edge_cases() -> bool:
    """Test edge cases and boundary conditions."""
    print("\n5. Edge cases:")
    all_passed = True
    
    all_passed &= test_case("", 0, False, "Empty string")
    all_passed &= test_case(".", 0, False, "Just period")
    all_passed &= test_case("A.", 1, False, "Single letter")
    all_passed &= test_case("..", 0, False, "Double period - first")
    all_passed &= test_case("..", 1, False, "Double period - second")
    
    return all_passed


def main() -> int:
    """Run all test suites."""
    print("Testing is_abbreviation_period function")
    print("=" * 60)
    
    all_passed = True
    all_passed &= test_dotnet_cases()
    all_passed &= test_common_abbreviations()
    all_passed &= test_version_numbers()
    all_passed &= test_false_positives()
    all_passed &= test_edge_cases()
    
    print("=" * 60)
    if all_passed:
        print("\n✓ All tests passed!")
        return 0
    else:
        print("\n✗ Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())

