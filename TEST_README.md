# Running Tests for Swift-Jupyter

This document explains how to run the tests in this repository.

## Prerequisites

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

   The main test dependencies are:
   - `jupyter-kernel-test` - Framework for testing Jupyter kernels
   - `flaky` - Handling flaky tests
   - `jupyter`, `pandas`, `matplotlib`, `numpy` - Core dependencies

2. **Register the Swift kernel:**

   The Swift Jupyter kernel must be registered with Jupyter before running tests. You can verify it's registered with:
   ```bash
   jupyter kernelspec list
   ```

   You should see `swift` in the list of available kernels.

   If not registered, follow the installation instructions in [README.md](README.md).

## Running the Tests

### Fast Tests (Recommended for Development)
Run the fast test suite which includes kernel tests and simple notebook tests:
```bash
python test/fast_test.py
```

### All Tests
Run the complete test suite including tutorial notebook tests:
```bash
python test/all_test.py
```

### Specific Test
Run a specific test class or method:
```bash
python test/fast_test.py SwiftKernelTests.test_swift_clear_output
python test/all_test.py SimpleNotebookTests.test_simple_successful
```

### Verbose Output
Add `-v` flag for verbose output:
```bash
python test/fast_test.py -v
```

## Test Structure

The test suite is organized as follows:

- **`test/fast_test.py`** - Entry point for fast tests
- **`test/all_test.py`** - Entry point for all tests
- **`test/test.py`** - Legacy entry point for backward compatibility
- **`test/notebook_tester.py`** - Utility for running and testing notebooks
- **`test/tests/`** - Test modules:
  - `kernel_tests.py` - Tests for kernel functionality (execution, errors, interrupts, etc.)
  - `simple_notebook_tests.py` - Tests for simple notebook execution
  - `tutorial_notebook_tests.py` - Tests for tutorial notebooks
  - `notebooks/` - Test notebook files

## Test Categories

### Kernel Tests (`SwiftKernelTests`)
Tests specific kernel features:
- Hello world execution
- Graphics with matplotlib
- Swift extensions
- Gradients and differentiation
- Runtime errors
- Execution interrupts
- Async stdout
- Code completion
- Clear output

### Own Kernel Tests (`OwnKernelTests`)
Tests that require their own isolated kernel instance:
- Process kill handling
- Package installation after code execution

### Notebook Tests
Tests that execute complete notebooks:
- Simple successful execution
- Intentional compile errors
- Intentional runtime errors
- Package installation

## Troubleshooting

### Import Errors
If you see `ModuleNotFoundError` for `jupyter_kernel_test` or `notebook_tester`:
- Ensure you've installed dependencies: `pip install -r requirements.txt`
- The test runners automatically add the test directory to Python path

### Kernel Not Found
If tests fail with "No such kernel named 'swift'":
- Register the kernel following the instructions in README.md
- Verify with: `jupyter kernelspec list`

### Tests Timeout or Hang
Some tests may take time as they:
- Start new kernel instances
- Execute Swift code
- Install packages
- Use longer timeouts (30s+) for certain operations

## Running Tests in Docker

The tests can also be run in Docker (after building the image per README.md):
```bash
docker run --cap-add SYS_PTRACE swift-jupyter python3 /swift-jupyter/test/all_test.py
```

Note: The `--cap-add SYS_PTRACE` flag is required for the Swift REPL to work properly.
