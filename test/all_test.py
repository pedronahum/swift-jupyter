"""Runs all tests."""

import os
import sys
import unittest

# Add test directory to path so notebook_tester can be imported
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
if TEST_DIR not in sys.path:
    sys.path.insert(0, TEST_DIR)

from tests.kernel_tests import SwiftKernelTests, OwnKernelTests
from tests.simple_notebook_tests import *
from tests.tutorial_notebook_tests import *


if __name__ == '__main__':
    unittest.main()
