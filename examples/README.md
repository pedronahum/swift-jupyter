# Swift Jupyter Examples

This directory contains example notebooks demonstrating various features of the Swift Jupyter kernel.

## PythonKit + matplotlib Test

**File**: [test_pythonkit_matplotlib.ipynb](test_pythonkit_matplotlib.ipynb)

A comprehensive test notebook that verifies PythonKit integration with matplotlib.

### What it tests:

1. ✅ PythonKit installation via `%install`
2. ✅ `Python.import()` functionality
3. ✅ NumPy integration
4. ✅ matplotlib import and inline plotting
5. ✅ Various plot types (line, scatter, subplots)

### Running the test:

#### Option 1: Manual Interactive Test (Recommended for first run)

```bash
./test_pythonkit_manual.sh
```

This will:
- Check that Jupyter and the Swift kernel are installed
- Open the test notebook in your browser
- Allow you to manually execute each cell and see the plots

**Expected results:**
- All cells execute without errors
- You see 4 plots displayed inline in the notebook
- Final cell shows "All tests PASSED"

#### Option 2: Automated Test

```bash
python3 test_pythonkit_automated.py
```

This will:
- Automatically execute the entire notebook
- Verify that all checks pass
- Report success/failure

**Note**: First run will take several minutes as PythonKit needs to be compiled.

### Requirements:

- Jupyter installed: `/usr/bin/python3 -m pip install --user jupyter`
- Swift kernel registered: `python3 register.py`
- matplotlib installed: `/usr/bin/python3 -m pip install --user matplotlib numpy`

### Troubleshooting:

If the test fails:

1. **Kernel dies on startup**: Make sure you're using system Python 3.9.6, not conda Python. See [README.md](../README.md) for details.

2. **PythonKit compilation fails**: The first `%install` cell may take 5-10 minutes to compile. Be patient.

3. **matplotlib not found**: Install matplotlib in system Python:
   ```bash
   /usr/bin/python3 -m pip install --user matplotlib numpy
   ```

4. **Import errors**: Make sure PYTHONPATH is set correctly in kernel.json. See [PYTHONKIT_SETUP.md](../PYTHONKIT_SETUP.md).

### What this proves:

✅ **matplotlib IS fully supported** with the Swift Jupyter kernel using PythonKit

This demonstrates that:
- PythonKit provides the same `Python.import()` API as Swift for TensorFlow
- EnableIPythonDisplay.swift works seamlessly with PythonKit
- Full Python ecosystem (matplotlib, numpy, pandas, etc.) is accessible from Swift
- Standard Swift 6.3+ toolchains work perfectly (no S4TF required)

### See also:

- [PYTHONKIT_SETUP.md](../PYTHONKIT_SETUP.md) - Complete PythonKit setup guide
- [MATPLOTLIB_STATUS.md](../MATPLOTLIB_STATUS.md) - matplotlib support status
- [README.md](../README.md) - Main project documentation
