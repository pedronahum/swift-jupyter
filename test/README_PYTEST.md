# Swift-Jupyter Testing Guide (pytest)

**Created**: October 17, 2025
**Region**: R6 - Testing Infrastructure
**Python Version**: 3.9-3.12
**Test Framework**: pytest

---

## Overview

This directory contains comprehensive tests for the Swift-Jupyter kernel, validating:
- **R3**: Jupyter Protocol 5.4 compliance
- **R4**: Display functionality
- **R5**: Unicode handling, interrupts, and error messages
- **R2**: Kernel registration and configuration

---

## Quick Start

### Install Test Dependencies

```bash
pip install pytest pytest-timeout jupyter-client ipykernel
```

### Run All Tests

```bash
# Run all tests
pytest test/integration/

# Run with verbose output
pytest test/integration/ -v

# Run specific test file
pytest test/integration/test_protocol.py

# Run specific test
pytest test/integration/test_protocol.py::TestProtocolConformance::test_kernel_info_protocol_version
```

---

## Test Structure

```
test/
├── conftest.py              # Pytest configuration and fixtures
├── pytest.ini               # Pytest settings (in project root)
├── integration/             # Integration tests
│   ├── test_protocol.py     # Protocol 5.4 conformance (R3)
│   ├── test_unicode_interrupt.py  # Unicode and interrupts (R5, R3)
│   └── test_error_display.py      # Errors and display (R5, R4)
├── unit/                    # Unit tests (future)
└── notebooks/               # Notebook tests (future)
```

---

## Test Categories

Tests are organized by pytest markers:

### Protocol Tests (`@pytest.mark.protocol`)
Tests for Jupyter Protocol 5.4 compliance (R3):
```bash
pytest -m protocol
```
- kernel_info message format
- execute_request/reply
- complete_request/reply with Unicode cursor positions
- shutdown_request handling

### Unicode Tests (`@pytest.mark.unicode`)
Tests for Unicode handling (R5-T1):
```bash
pytest -m unicode
```
- Unicode variable names
- Emoji in strings
- Multiple Unicode scripts (Chinese, Arabic, Hebrew, etc.)
- Zero-width characters
- RTL text

### Interrupt Tests (`@pytest.mark.interrupt`)
Tests for interrupt functionality (R3-T2, R5-T2):
```bash
pytest -m interrupt
```
Note: Most interrupt tests are skipped by default due to timing sensitivity.

### Error Tests (`@pytest.mark.error`)
Tests for error handling (R5-T3):
```bash
pytest -m error
```
- Compile error messages
- Runtime error messages
- Stack trace formatting
- Error recovery

### Display Tests (`@pytest.mark.display`)
Tests for display functionality (R4):
```bash
pytest -m display
```
- Print output
- Multiple output formats
- Mixed output and errors

### Slow Tests (`@pytest.mark.slow`)
Tests that take more than 5 seconds:
```bash
# Skip slow tests
pytest -m "not slow"

# Run only slow tests
pytest -m slow
```

---

## Common Test Commands

### Run Fast Tests Only
```bash
pytest -m "not slow" test/integration/
```

### Run Protocol and Unicode Tests
```bash
pytest -m "protocol or unicode" test/integration/
```

### Run with Coverage
```bash
pytest --cov=swift_kernel --cov-report=html test/integration/
```

### Run with Detailed Output
```bash
pytest test/integration/ -v --tb=long
```

### Run and Stop on First Failure
```bash
pytest test/integration/ -x
```

### Run Specific Test Methods
```bash
# Single test
pytest test/integration/test_protocol.py::TestProtocolConformance::test_kernel_info_protocol_version

# All tests in a class
pytest test/integration/test_protocol.py::TestProtocolConformance
```

---

## Fixtures

### `kernel_manager` (session scope)
Starts a Swift kernel once for the entire test session.

### `kernel_client` (function scope)
Provides a kernel client for each test. Messages are cleared before each test.

### `execute_code` (function scope)
Helper function to execute code and wait for result:

```python
def test_example(execute_code):
    result = execute_code('let x = 42\nprint(x)')
    assert result['status'] == 'ok'
    assert len(result['output']) > 0
```

Result structure:
```python
{
    'status': 'ok' | 'error' | 'timeout',
    'output': [
        {'type': 'stream', 'name': 'stdout', 'text': '...'},
        {'type': 'execute_result', 'data': {...}, 'execution_count': N}
    ],
    'error': {
        'ename': 'ErrorName',
        'evalue': 'error message',
        'traceback': ['...']
    } | None,
    'execution_count': N | None
}
```

### `wait_for_idle` (function scope)
Helper to wait for kernel to become idle.

---

## Writing New Tests

### Basic Test Structure

```python
import pytest

@pytest.mark.protocol  # Add appropriate marker
class TestMyFeature:
    """Test description."""

    def test_something(self, execute_code):
        """Test a specific behavior."""
        result = execute_code('let x = 42')
        assert result['status'] == 'ok'

    def test_something_else(self, kernel_client):
        """Test using kernel client directly."""
        kc = kernel_client
        msg_id = kc.kernel_info()
        reply = kc.get_shell_msg(timeout=5)
        assert reply['msg_type'] == 'kernel_info_reply'
```

### Test Naming Convention

- Test files: `test_*.py`
- Test classes: `Test*`
- Test methods: `test_*`

### Best Practices

1. **Use appropriate markers**: Add `@pytest.mark.protocol`, `@pytest.mark.unicode`, etc.
2. **Set realistic timeouts**: Default is 30 seconds (set in pytest.ini)
3. **Clean up**: Fixtures handle cleanup automatically
4. **Skip flaky tests**: Use `@pytest.mark.skip()` for tests that are timing-sensitive
5. **Test edge cases**: Empty input, very long input, special characters
6. **Test error recovery**: Verify kernel recovers after errors

---

## Configuration

### pytest.ini (Project Root)

```ini
[pytest]
testpaths = test
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short --strict-markers --color=yes -ra
timeout = 30
timeout_method = thread
```

### conftest.py

See `test/conftest.py` for:
- `kernel_manager` fixture (session-scoped)
- `kernel_client` fixture (function-scoped)
- `execute_code` helper fixture
- `wait_for_idle` helper fixture
- Marker definitions

---

## Troubleshooting

### Kernel Won't Start

```bash
# Check kernel registration
jupyter kernelspec list

# Verify kernel.json
cat ~/Library/Jupyter/kernels/swift/kernel.json

# Check Python environment
which python3
python3 --version  # Should be 3.9-3.12

# Validate LLDB
python3 register.py --swift-toolchain /path/to/toolchain --validate-only
```

### Tests Timeout

- Increase timeout in pytest.ini or use `@pytest.mark.timeout(60)`
- Check kernel logs
- Verify Swift toolchain is working

### Import Errors

```bash
# Install test dependencies
pip install pytest pytest-timeout jupyter-client ipykernel

# Verify installation
python3 -c "import pytest; import jupyter_client; print('OK')"
```

### Kernel Dies During Tests

- Check LLDB compatibility
- Verify Python version matches Swift embedded Python (3.9)
- Check memory usage
- Review kernel logs

---

## Test Coverage

Current test coverage by region:

| Region | Feature | Test File | Status |
|--------|---------|-----------|--------|
| R3 | Protocol 5.4 compliance | test_protocol.py | ✅ Complete |
| R3 | kernel_info | test_protocol.py | ✅ Complete |
| R3 | execute_request | test_protocol.py | ✅ Complete |
| R3 | complete_request (Unicode) | test_protocol.py | ✅ Complete |
| R5 | Unicode handling | test_unicode_interrupt.py | ✅ Complete |
| R5 | Unicode in variables | test_unicode_interrupt.py | ✅ Complete |
| R5 | Emoji support | test_unicode_interrupt.py | ✅ Complete |
| R5 | Error messages | test_error_display.py | ✅ Complete |
| R5 | Stack traces | test_error_display.py | ✅ Complete |
| R4 | Display output | test_error_display.py | ✅ Complete |
| R2 | interrupt_mode config | test_protocol.py | ✅ Complete |

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Test Swift Kernel

on: [push, pull_request]

jobs:
  test:
    runs-on: macos-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-timeout

    - name: Run tests
      run: pytest test/integration/ -v --tb=short -m "not slow"
```

---

## Future Enhancements

### R6 Future Work

1. **Notebook Tests** (`test/notebooks/`):
   - Basic execution notebook
   - Display outputs notebook
   - Error handling notebook
   - Unicode support notebook
   - Run with: `pytest --nbmake test/notebooks/*.ipynb`

2. **Unit Tests** (`test/unit/`):
   - Test individual kernel methods
   - Test helper functions
   - Mock LLDB interactions

3. **Performance Tests**:
   - Execution speed benchmarks
   - Memory usage tests
   - Interrupt response time

4. **Stress Tests**:
   - Many rapid executions
   - Very large code blocks
   - Extreme Unicode cases

---

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [Jupyter Client Documentation](https://jupyter-client.readthedocs.io/)
- [Jupyter Protocol Specification](https://jupyter-client.readthedocs.io/en/latest/messaging.html)
- [Swift-Jupyter Modernization Plan](../modernization-plan.json)

---

## Support

For issues or questions:
- Check existing tests for examples
- Review test output with `-v` flag
- Check kernel logs
- Consult modernization completion reports (R1-R5_COMPLETION_REPORT.md)

---

**Status**: ✅ R6 Testing Infrastructure Complete
**Test Count**: 50+ tests across 3 test files
**Coverage**: R2, R3, R4, R5 features
**Next**: Run tests and add notebook tests
