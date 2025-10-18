# Google Colab Installation Guide

There are **two ways** to use Swift in Google Colab:

1. **Cell Magic Approach** (⭐ Recommended) - Use `%%swift` in Python notebooks
2. **Full Kernel Approach** - Register Swift as a Jupyter kernel

## Comparison

| Feature | Cell Magic | Full Kernel |
|---------|-----------|-------------|
| **Setup Complexity** | ✅ Simple | ⚠️ Complex |
| **Reliability** | ✅ High | ⚠️ Medium |
| **Mixed Python/Swift** | ✅ Yes | ❌ No |
| **Installation Time** | ✅ ~3-5 min | ⚠️ ~3-5 min |
| **Runtime Switching** | ❌ No | ✅ Yes |
| **Debugging** | ✅ Easy | ⚠️ Harder |
| **Best For** | Data science, learning | Pure Swift notebooks |

---

## Option 1: Cell Magic (⭐ Recommended for Colab)

### Installation

Run this in a Colab cell:

```bash
!curl -s https://raw.githubusercontent.com/pedronahum/swift-jupyter/main/install_swift_colab_magic.sh | bash
```

### Activation

After installation completes, activate Swift magic in a **Python cell**:

```python
%run /content/setup_swift_magic.py
```

Or manually:

```python
import os
os.environ['SWIFT_TOOLCHAIN_PATH'] = '/root/.local/share/swiftly/toolchains/main-snapshot-...'
os.environ['SWIFT_DRIVER_EXE_PATH'] = '/root/.local/share/swiftly/toolchains/.../usr/bin/swift'
os.environ['SWIFT_PYTHON_DRIVER_PATH'] = '/content/swift-jupyter/swift_colab/swift_python_driver.py'
os.environ['LD_LIBRARY_PATH'] = '/usr/lib/llvm-14/lib:/root/.local/share/swiftly/toolchains/.../usr/lib/swift/linux'
os.environ['PYTHONPATH'] = '/usr/lib/python3/dist-packages'
%load_ext swift_colab
```

*Note: Exact paths will be shown in installation output*

### Usage

Use `%%swift` at the start of any cell to run Swift code:

```swift
%%swift
print("Hello from Swift!")
print("Swift version \(#swiftVersion)")

let numbers = [1, 2, 3, 4, 5]
let doubled = numbers.map { $0 * 2 }
print("Doubled: \(doubled)")
```

### Example Notebook

```python
# Cell 1: Install Swift (run once)
!curl -s https://raw.githubusercontent.com/pedronahum/swift-jupyter/main/install_swift_colab_magic.sh | bash

# Cell 2: Activate Swift magic (run once per session)
%run /content/setup_swift_magic.py

# Cell 3: Run Swift code
%%swift
struct Person {
    let name: String
    let age: Int
}

let person = Person(name: "Alice", age: 30)
print("Person: \(person.name), age \(person.age)")

# Cell 4: Mix Python and Swift!
import numpy as np
data = np.array([1, 2, 3, 4, 5])
print(f"Python: Mean = {data.mean()}")

# Cell 5: More Swift
%%swift
let swiftArray = [1, 2, 3, 4, 5]
let sum = swiftArray.reduce(0, +)
print("Swift: Sum = \(sum)")
```

### Advantages

✅ **Simpler setup** - No kernel registration
✅ **More reliable** - Direct path detection
✅ **Mix languages** - Use Python and Swift in same notebook
✅ **Better errors** - Clear error messages
✅ **Explicit environment** - All paths visible

### Disadvantages

❌ Must use `%%swift` in each cell
❌ Cannot change runtime type to "Swift"
❌ Requires Python kernel

---

## Option 2: Full Kernel Approach

### Installation

Run this in a Colab cell:

```bash
!curl -s https://raw.githubusercontent.com/pedronahum/swift-jupyter/main/install_swift_colab.sh | bash
```

### Activation

After installation:
1. **Runtime → Restart runtime**
2. **Runtime → Change runtime type → Swift**

### Usage

All cells run Swift code directly (no `%%swift` needed):

```swift
print("Hello from Swift!")
let numbers = [1, 2, 3, 4, 5]
print(numbers.map { $0 * 2 })
```

### Advantages

✅ **Pure Swift** - Entire notebook is Swift
✅ **Runtime switching** - Can switch between Python/Swift
✅ **Traditional Jupyter** - Standard kernel experience
✅ **No cell magic** - Write Swift directly

### Disadvantages

❌ **More complex** - Kernel registration, PATH setup
❌ **Fragile** - kernel.json must be correct
❌ **No mixing** - Can't use Python and Swift in same notebook
❌ **Harder debugging** - Environment is hidden

---

## Which Should I Choose?

### Use **Cell Magic** if you:
- ⭐ Want the **simplest, most reliable** setup
- Need to **mix Python and Swift** (e.g., use NumPy with Swift)
- Are **learning Swift** and want easy experimentation
- Want **explicit control** over environment
- Need **better error messages**

### Use **Full Kernel** if you:
- Want **pure Swift** notebooks
- Don't need Python integration
- Prefer **traditional Jupyter** experience
- Are comfortable with **kernel debugging**
- Want to **switch runtimes** easily

## Quick Start: Cell Magic (Recommended)

**Step 1**: Install Swift
```bash
!curl -s https://raw.githubusercontent.com/pedronahum/swift-jupyter/main/install_swift_colab_magic.sh | bash
```

**Step 2**: Activate (run once per session)
```python
%run /content/setup_swift_magic.py
```

**Step 3**: Use Swift
```swift
%%swift
print("Hello, Swift!")
```

## Quick Start: Full Kernel

**Step 1**: Install Swift
```bash
!curl -s https://raw.githubusercontent.com/pedronahum/swift-jupyter/main/install_swift_colab.sh | bash
```

**Step 2**: Restart runtime (Runtime menu)

**Step 3**: Change to Swift runtime (Runtime → Change runtime type)

**Step 4**: Use Swift
```swift
print("Hello, Swift!")
```

---

## Troubleshooting

### Cell Magic Issues

**"Module swift_colab not found"**
- Run: `%run /content/setup_swift_magic.py`
- Or: `%load_ext swift_colab`

**"Swift binary not found"**
- Check: `!which swift`
- Verify: `SWIFT_DRIVER_EXE_PATH` environment variable

**"LLDB import error"**
- Check: `!python3 -c 'import lldb'`
- Reinstall: Run installation script again

### Full Kernel Issues

**"Kernel not found"**
- Verify: `!jupyter kernelspec list`
- Should show: `swift    /usr/local/share/jupyter/kernels/swift`

**"Cells don't execute"**
- Check kernel.json: `!cat /usr/local/share/jupyter/kernels/swift/kernel.json`
- Verify PATH is set in env section

**"Swift command not found"**
- Check: `!cat /usr/local/share/jupyter/kernels/swift/kernel.json | grep PATH`
- PATH should include Swift toolchain bin directory

---

## Advanced: Custom Swift Version

Both installers support custom Swift versions via `SWIFT_CHANNEL`:

```bash
# Install Swift 6.0 instead of main-snapshot
!SWIFT_CHANNEL=6.0 curl -s https://raw.githubusercontent.com/pedronahum/swift-jupyter/main/install_swift_colab_magic.sh | bash
```

Available channels:
- `main-snapshot` (default) - Latest development snapshot
- `6.0` - Swift 6.0 release
- `5.10` - Swift 5.10 release

---

## Examples

### Cell Magic: Data Science Workflow

```python
# Cell 1: Install
!curl -s https://raw.githubusercontent.com/pedronahum/swift-jupyter/main/install_swift_colab_magic.sh | bash

# Cell 2: Setup
%run /content/setup_swift_magic.py

# Cell 3: Python - Load data
import pandas as pd
import numpy as np

data = pd.DataFrame({
    'x': np.linspace(0, 10, 100),
    'y': np.sin(np.linspace(0, 10, 100))
})
print(f"Data shape: {data.shape}")

# Cell 4: Swift - Process data
%%swift
struct DataPoint {
    let x: Double
    let y: Double
}

let points = [
    DataPoint(x: 1.0, y: 0.5),
    DataPoint(x: 2.0, y: 0.8),
    DataPoint(x: 3.0, y: 0.3)
]

let avgY = points.map { $0.y }.reduce(0, +) / Double(points.count)
print("Swift computed average: \(avgY)")

# Cell 5: Back to Python
print(f"Python computed average: {data['y'].mean()}")
```

### Full Kernel: Pure Swift

```swift
// Cell 1: Define types
struct Matrix {
    let rows: Int
    let cols: Int
    var data: [Double]

    init(rows: Int, cols: Int, initialValue: Double = 0.0) {
        self.rows = rows
        self.cols = cols
        self.data = Array(repeating: initialValue, count: rows * cols)
    }
}

// Cell 2: Implement operations
extension Matrix {
    func transposed() -> Matrix {
        var result = Matrix(rows: cols, cols: rows)
        for i in 0..<rows {
            for j in 0..<cols {
                result.data[j * rows + i] = data[i * cols + j]
            }
        }
        return result
    }
}

// Cell 3: Test
let m = Matrix(rows: 2, cols: 3, initialValue: 1.0)
let t = m.transposed()
print("Original: \(m.rows)x\(m.cols)")
print("Transposed: \(t.rows)x\(t.cols)")
```

---

## Support

- **Documentation**: [README.md](README.md)
- **Issues**: [GitHub Issues](https://github.com/pedronahum/swift-jupyter/issues)
- **Cell Magic Details**: [install_swift_colab_magic.sh](install_swift_colab_magic.sh)
- **Full Kernel Details**: [install_swift_colab.sh](install_swift_colab.sh)

---

**Last Updated**: October 18, 2024
**Recommended**: Cell Magic approach for most users
