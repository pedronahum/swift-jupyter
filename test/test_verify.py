#!/usr/bin/env python3
"""
Simple verification script to check if the test infrastructure is working.
"""

import sys
import unittest

# Try importing the test modules
try:
    from test.tests.kernel_tests import SwiftKernelTests, OwnKernelTests
    print("✓ kernel_tests imported successfully")
except ImportError as e:
    print(f"✗ Failed to import kernel_tests: {e}")
    sys.exit(1)

try:
    from test.tests.simple_notebook_tests import SimpleNotebookTests
    print("✓ simple_notebook_tests imported successfully")
except ImportError as e:
    print(f"✗ Failed to import simple_notebook_tests: {e}")
    sys.exit(1)

# Check test discovery
loader = unittest.TestLoader()
suite = unittest.TestSuite()

try:
    suite.addTests(loader.loadTestsFromTestCase(SwiftKernelTests))
    print(f"✓ Discovered {suite.countTestCases()} tests from SwiftKernelTests")
except Exception as e:
    print(f"✗ Failed to load SwiftKernelTests: {e}")
    sys.exit(1)

try:
    suite.addTests(loader.loadTestsFromTestCase(OwnKernelTests))
    print(f"✓ Discovered {suite.countTestCases()} tests from OwnKernelTests")
except Exception as e:
    print(f"✗ Failed to load OwnKernelTests: {e}")
    sys.exit(1)

try:
    suite.addTests(loader.loadTestsFromTestCase(SimpleNotebookTests))
    print(f"✓ Discovered {suite.countTestCases()} tests from SimpleNotebookTests")
except Exception as e:
    print(f"✗ Failed to load SimpleNotebookTests: {e}")
    sys.exit(1)

print(f"\n✓ All test modules loaded successfully!")
print(f"✓ Total tests discovered: {suite.countTestCases()}")
print(f"\nTests can now be run with:")
print(f"  python test/fast_test.py  # Fast tests")
print(f"  python test/all_test.py   # All tests")
print(f"  python test/fast_test.py SimpleNotebookTests.test_simple_successful  # Specific test")
