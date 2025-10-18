# PythonKit Setup for matplotlib and Python Interop

## Overview

**PythonKit** is the modern, maintained replacement for Swift for TensorFlow's Python interop. It provides the same `Python.import()` API that EnableIPythonDisplay.swift expects.

**Status**: ✅ EnableIPythonDisplay.swift already supports PythonKit (lines 18-22)

## Requirements

- Swift toolchain 5.7+ (tested with Swift 6.3)
- Python 3.9+ with matplotlib, numpy, IPython installed
- System Python or compatible environment

## Installation

### Step 1: Install PythonKit in Jupyter Kernel

In your **first Swift notebook cell**, install PythonKit:

```swift
// Install PythonKit from GitHub
%install '.package(url: "https://github.com/pvieito/PythonKit", branch: "master")' PythonKit
```

**Note**: This must be in the **first cell you execute** in a notebook. SwiftPM packages can only be installed before any other code runs.

### Step 2: Enable IPython Display

In your **second cell**, include the display helper:

```swift
%include "EnableIPythonDisplay.swift"
```

This will:
- Import PythonKit automatically (via `#if canImport(PythonKit)`)
- Set up IPython display integration
- Enable matplotlib inline mode support

### Step 3: Import Python Libraries

Now you can import and use Python libraries:

```swift
import PythonKit

let np = Python.import("numpy")
let plt = Python.import("matplotlib.pyplot")
let pd = Python.import("pandas")

// Enable matplotlib inline mode
IPythonDisplay.shell.enable_matplotlib("inline")
```

## Usage Examples

### Basic matplotlib Plot

```swift
// Cell 1: Install PythonKit
%install '.package(url: "https://github.com/pvieito/PythonKit", branch: "master")' PythonKit
```

```swift
// Cell 2: Setup
%include "EnableIPythonDisplay.swift"
import PythonKit

let np = Python.import("numpy")
let plt = Python.import("matplotlib.pyplot")
IPythonDisplay.shell.enable_matplotlib("inline")
```

```swift
// Cell 3: Create plot
let x = np.arange(0, 10, 0.1)
let y = np.sin(x)

plt.figure(figsize: [10, 6])
plt.plot(x, y, label: "sin(x)")
plt.xlabel("x")
plt.ylabel("y")
plt.title("Sine Wave")
plt.legend()
plt.grid(true)
plt.show()
```

### Pandas DataFrame

```swift
import PythonKit

let pd = Python.import("pandas")
let np = Python.import("numpy")

let data = [
    "Name": ["Alice", "Bob", "Charlie"],
    "Age": [25, 30, 35],
    "Score": [85.5, 90.2, 78.9]
]

let df = pd.DataFrame(data)
df.display()  // Pretty HTML table in Jupyter
```

### NumPy Operations

```swift
import PythonKit

let np = Python.import("numpy")

let arr = np.array([1, 2, 3, 4, 5])
let squared = np.power(arr, 2)
let mean = np.mean(squared)

print("Array:", arr)
print("Squared:", squared)
print("Mean:", mean)
```

## Environment Configuration

### Python Library Path

PythonKit automatically finds your Python installation, but you can specify it explicitly:

```bash
# Before starting Jupyter, set environment variable
export PYTHON_LIBRARY="/usr/lib/libpython3.9.so"  # Linux
export PYTHON_LIBRARY="/usr/local/lib/libpython3.9.dylib"  # macOS

# Or specify Python version
export PYTHON_VERSION="3.9"
```

### Debug Loading

If PythonKit can't find Python:

```bash
export PYTHON_LOADER_LOGGING=1
jupyter notebook
```

This will show which Python libraries PythonKit tries to load.

## Troubleshooting

### Error: "No such module 'PythonKit'"

**Cause**: PythonKit wasn't installed or wasn't installed in the first cell

**Fix**:
1. Restart kernel: `Kernel → Restart`
2. In the **first cell**, install PythonKit
3. Then execute other cells

### Error: "cannot find 'Python' in scope"

**Cause**: Forgot to `import PythonKit`

**Fix**:
```swift
import PythonKit  // Add this line
let np = Python.import("numpy")
```

### Error: "Python.import() failed to import module"

**Cause**: Python module not installed

**Fix**:
```bash
# Install in system Python or active environment
pip install numpy matplotlib pandas ipython
```

### matplotlib plots don't appear

**Cause**: Inline mode not enabled

**Fix**:
```swift
%include "EnableIPythonDisplay.swift"
IPythonDisplay.shell.enable_matplotlib("inline")
```

### Binary compatibility issues

**Symptom**: Segfaults or crashes when using PythonKit

**Cause**: Python version mismatch between Swift runtime and PythonKit

**Fix**: Use system Python 3.9.6 (same as kernel requirement):
```bash
export PYTHON_LIBRARY="/usr/lib/python3.9/config-3.9-darwin/libpython3.9.dylib"
```

## Testing matplotlib Integration

Run this complete test in a fresh notebook:

```swift
// Cell 1: Install
%install '.package(url: "https://github.com/pvieito/PythonKit", branch: "master")' PythonKit
```

```swift
// Cell 2: Setup
%include "EnableIPythonDisplay.swift"
import PythonKit

let sys = Python.import("sys")
print("Python version:", sys.version)

let np = Python.import("numpy")
let plt = Python.import("matplotlib.pyplot")
IPythonDisplay.shell.enable_matplotlib("inline")
print("✅ matplotlib inline mode enabled")
```

```swift
// Cell 3: Test plot
let x = np.linspace(0, 2 * np.pi, 100)
let y1 = np.sin(x)
let y2 = np.cos(x)

plt.figure(figsize: [12, 6])
plt.plot(x, y1, label: "sin(x)", linewidth: 2)
plt.plot(x, y2, label: "cos(x)", linewidth: 2, linestyle: "--")
plt.xlabel("x")
plt.ylabel("y")
plt.title("Trigonometric Functions")
plt.legend()
plt.grid(true, alpha: 0.3)
plt.show()

print("✅ Plot rendered successfully!")
```

**Expected**: You should see an inline plot of sine and cosine waves.

## Updating Tests

The test suite can now use PythonKit. Update test setup:

```python
# test/tests/kernel_tests.py

def test_graphics_matplotlib_pythonkit(self):
    """Test matplotlib with PythonKit (modern approach)."""
    # Install PythonKit
    reply, _ = self.execute_helper(code='''
        %install '.package(url: "https://github.com/pvieito/PythonKit", branch: "master")' PythonKit
    ''')
    self.assertEqual(reply['content']['status'], 'ok')

    # Setup
    reply, _ = self.execute_helper(code='''
        %include "EnableIPythonDisplay.swift"
        import PythonKit

        let np = Python.import("numpy")
        let plt = Python.import("matplotlib.pyplot")
        IPythonDisplay.shell.enable_matplotlib("inline")
    ''')
    self.assertEqual(reply['content']['status'], 'ok')

    # Create plot
    reply, output_msgs = self.execute_helper(code='''
        let ys = np.arange(0, 10, 0.01)
        plt.plot(ys)
        plt.show()
    ''')
    self.assertEqual(reply['content']['status'], 'ok')
    self.assertIn('image/png', output_msgs[0]['content']['data'])
```

## Performance Notes

- **First import** of a Python module may be slow (2-5 seconds)
- **Subsequent imports** are fast (cached)
- **PythonKit overhead** is minimal (microseconds per call)
- **Large data transfers** between Swift/Python may be slow

## Known Limitations

1. **%install must be first** - SwiftPM packages only install before any code execution
2. **Binary compatibility** - Use matching Python versions
3. **Error messages** - Python exceptions may not have full Swift stack traces
4. **Type conversions** - Some Python types don't convert automatically

## Comparison: PythonKit vs SwiftPlot

| Feature | PythonKit + matplotlib | SwiftPlot |
|---------|----------------------|-----------|
| Installation | %install (first cell) | %install (any cell) |
| Python required | Yes | No |
| Feature set | Full matplotlib | Basic plotting |
| Performance | Good | Excellent |
| Type safety | Runtime | Compile-time |
| Stability | Depends on Python | Pure Swift |
| **Recommendation** | Data science, complex plots | Simple plots, performance |

## Best Practices

1. **Always install in first cell**:
   ```swift
   %install '.package(url: "https://github.com/pvieito/PythonKit", branch: "master")' PythonKit
   ```

2. **Import PythonKit explicitly**:
   ```swift
   import PythonKit  // Makes Python.import() available
   ```

3. **Check Python version**:
   ```swift
   let sys = Python.import("sys")
   print("Python:", sys.version)
   ```

4. **Use type annotations for clarity**:
   ```swift
   let arr: PythonObject = np.array([1, 2, 3])
   ```

5. **Handle errors gracefully**:
   ```swift
   do {
       let module = try Python.attemptImport("rare_module")
   } catch {
       print("Module not available:", error)
   }
   ```

## Next Steps

1. ✅ EnableIPythonDisplay.swift already supports PythonKit
2. ⏳ Create example notebooks with PythonKit
3. ⏳ Update test suite to use PythonKit
4. ⏳ Add PythonKit installation to README
5. ⏳ Document in HOW_TO_TEST.md

## Resources

- **PythonKit GitHub**: https://github.com/pvieito/PythonKit
- **Original S4TF Python docs**: https://github.com/tensorflow/swift/blob/main/docs/PythonInteroperability.md
- **Swift Package Manager**: https://swift.org/package-manager/

## Summary

✅ **PythonKit works with swift-jupyter**
✅ **EnableIPythonDisplay.swift already supports it**
✅ **matplotlib can be used via PythonKit**
✅ **Same API as Swift for TensorFlow**

Just install PythonKit in your first cell and you're ready to use Python libraries!
