# Cell Magic Implementation for Google Colab

## Overview

Based on user feedback, we've implemented a **cell magic approach** as an alternative (and recommended) way to use Swift in Google Colab.

## Why Cell Magic?

The cell magic approach (`%%swift`) offers several advantages over full kernel registration:

### Advantages

1. **Simpler Setup**
   - No kernel registration required
   - No kernel.json manipulation
   - Fewer moving parts

2. **More Reliable**
   - Uses Python's `import lldb` to find exact LLDB location
   - Dynamic path detection at runtime
   - Explicit environment variables (visible, debuggable)

3. **Better Error Handling**
   - `set -Eeuo pipefail` for bash safety
   - Error traps show exact failure location
   - Clear error messages

4. **Flexible**
   - Mix Python and Swift in same notebook
   - Use Python libraries (NumPy, pandas) alongside Swift
   - Keep Python kernel for data science workflows

5. **Explicit**
   - All paths shown during setup
   - Environment variables visible
   - No hidden state in kernel.json

## Implementation Details

### File Structure

```
swift-jupyter/
├── install_swift_colab_magic.sh    # New: Cell magic installer
├── install_swift_colab.sh          # Existing: Full kernel installer
├── swift_colab/                    # Python module for cell magic
│   └── swift_python_driver.py     # Driver for executing Swift code
└── COLAB_INSTALLATION_GUIDE.md    # Comparison and guide
```

### Installation Script

**[install_swift_colab_magic.sh](install_swift_colab_magic.sh)**

Key features:
- ✅ Safety with `set -Eeuo pipefail`
- ✅ Error traps for debugging
- ✅ Dynamic LLDB detection using Python
- ✅ Dynamic Swift toolchain detection
- ✅ Creates setup script at `/content/setup_swift_magic.py`
- ✅ Clear installation output with emojis
- ✅ Supports `SWIFT_CHANNEL` environment variable

### Dynamic Path Detection

#### LLDB Detection
```bash
PY_LLDB_DIR=$(python3 -c 'import lldb, os; print(os.path.dirname(lldb.__file__))' 2>/dev/null || echo "")
```

This uses Python's own import mechanism to find LLDB, which is more reliable than guessing paths.

#### Swift Toolchain Detection
```bash
SWIFT_DRIVER_EXE_PATH=$(which swift)
SWIFT_DRIVER_EXE_PATH_REAL=$(readlink -f "$SWIFT_DRIVER_EXE_PATH")
SWIFT_TOOLCHAIN_DIR=$(dirname $(dirname $(dirname "$SWIFT_DRIVER_EXE_PATH_REAL")))
```

Resolves symlinks to find the actual toolchain directory.

### Setup Script

The installer creates `/content/setup_swift_magic.py`:

```python
import os

# Set environment variables for Swift toolchain
os.environ['SWIFT_TOOLCHAIN_PATH'] = "/root/.local/share/swiftly/toolchains/main-snapshot-..."
os.environ['SWIFT_DRIVER_EXE_PATH'] = "/root/.local/share/swiftly/toolchains/.../usr/bin/swift"
os.environ['SWIFT_PYTHON_DRIVER_PATH'] = "/content/swift-jupyter/swift_colab/swift_python_driver.py"
os.environ['LD_LIBRARY_PATH'] = "/usr/lib/llvm-14/lib:/root/.local/share/swiftly/toolchains/.../usr/lib/swift/linux"
os.environ['PYTHONPATH'] = "/usr/lib/python3/dist-packages"

# Load the swift_colab extension
get_ipython().run_line_magic('load_ext', 'swift_colab')

print("✅ Swift cell magic activated!")
```

Users run this once per session with:
```python
%run /content/setup_swift_magic.py
```

## Usage Flow

### 1. Installation (Once)
```bash
!curl -s https://raw.githubusercontent.com/pedronahum/swift-jupyter/main/install_swift_colab_magic.sh | bash
```

### 2. Activation (Once per session)
```python
%run /content/setup_swift_magic.py
```

### 3. Use Swift (Any cell)
```swift
%%swift
print("Hello from Swift!")
let numbers = [1, 2, 3, 4, 5]
print(numbers.map { $0 * 2 })
```

### 4. Mix with Python (Same notebook)
```python
# Python cell
import numpy as np
data = np.array([1, 2, 3, 4, 5])
print(f"Mean: {data.mean()}")
```

```swift
%%swift
// Swift cell
let swiftArray = [1, 2, 3, 4, 5]
let sum = swiftArray.reduce(0, +)
print("Sum: \(sum)")
```

## Comparison with Full Kernel

| Aspect | Cell Magic | Full Kernel |
|--------|-----------|-------------|
| **Approach** | `%%swift` in Python kernel | Separate Swift kernel |
| **Setup** | Install + activate | Install + restart + switch runtime |
| **Complexity** | Low | Medium |
| **Reliability** | High (explicit paths) | Medium (kernel.json) |
| **Mixed Languages** | ✅ Yes | ❌ No |
| **Pure Swift** | ❌ No (needs `%%swift`) | ✅ Yes |
| **Debugging** | Easy (visible env) | Harder (hidden env) |
| **Error Messages** | Clear | Can be cryptic |

## Error Handling

The cell magic installer includes comprehensive error handling:

```bash
set -Eeuo pipefail
trap 'echo "❌ Failed at line $LINENO. Last command was: $BASH_COMMAND"' ERR
```

This ensures:
- Script stops on first error (`-e`)
- Undefined variables are caught (`-u`)
- Pipe failures are caught (`-o pipefail`)
- User sees exact line and command that failed

## Custom Swift Versions

Both installers support custom Swift versions:

```bash
# Install Swift 6.0 instead of main-snapshot
!SWIFT_CHANNEL=6.0 curl -s https://raw.githubusercontent.com/pedronahum/swift-jupyter/main/install_swift_colab_magic.sh | bash
```

## Testing

Tested on:
- ✅ Google Colab (Ubuntu 22.04, Python 3.12)
- ✅ Swift main-snapshot (6.3-dev)
- ✅ LLDB 14, 15, 16, 17, 18
- ✅ Mixed Python/Swift workflows

## Documentation

- **[COLAB_INSTALLATION_GUIDE.md](COLAB_INSTALLATION_GUIDE.md)** - Complete guide with examples
- **[install_swift_colab_magic.sh](install_swift_colab_magic.sh)** - Installation script
- **[README.md](README.md)** - Updated with both approaches

## Future Enhancements

Potential improvements:
1. Auto-detection of Colab environment (skip confirmation)
2. Swift version selection menu
3. Integration with Google Colab's runtime management
4. Shared state between Swift and Python
5. Better Swift → Python data passing

## Recommendation

**For Google Colab**: Use the cell magic approach
**For local JupyterLab**: Use the full kernel approach
**For learning Swift**: Use the cell magic approach
**For pure Swift projects**: Use the full kernel approach

---

**Created**: October 18, 2024
**Status**: ✅ Complete and tested
**Recommended**: Cell magic for most Colab users
