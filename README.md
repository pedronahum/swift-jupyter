# Swift-Jupyter

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/pedronahum/swift-jupyter/blob/main/examples/Swift_Differentiable_Programming.ipynb)

A Jupyter Kernel for Swift, enabling interactive Swift programming in Jupyter notebooks.

## Quick Start (Google Colab)

The easiest way to try Swift in Jupyter is with Google Colab:

1. Click the **Open in Colab** badge above
2. Run the first cell to install Swift (~3-5 minutes)
3. Go to **Runtime → Change runtime type → Swift**
4. Run Swift code!

Or create a new Colab notebook and run:

```bash
!curl -sL https://raw.githubusercontent.com/pedronahum/swift-jupyter/main/install_swift_colab.sh | bash
```

## Features

- **Swift Execution**: Variables, functions, structs, classes, protocols
- **Automatic Differentiation**: Built-in `Differentiable` protocol and `gradient()` function
- **SwiftPM Packages**: Install packages with `%install` directive
- **Magic Commands**: `%help`, `%who`, `%reset`, `%timeit`
- **Expression Display**: Values display automatically like Python notebooks
- **PythonKit**: Access matplotlib, numpy, pandas via Swift

## Example: Differentiable Programming

```swift
struct Model: Differentiable {
    var w: Float
    var b: Float
    func applied(to input: Float) -> Float {
        return w * input + b
    }
}

let model = Model(w: 4, b: 3)
let input: Float = 2
let (gradModel, gradInput) = gradient(at: model, input) { model, input in
    model.applied(to: input)
}

print(gradModel)  // Model.TangentVector(w: 2.0, b: 1.0)
print(gradInput)  // 4.0
```

## Local Installation

### macOS

```bash
# Install Jupyter
/usr/bin/python3 -m pip install --user jupyter ipykernel

# Clone and register
git clone https://github.com/pedronahum/swift-jupyter.git
cd swift-jupyter
/usr/bin/python3 register.py --sys-prefix \
  --swift-toolchain /Library/Developer/Toolchains/swift-latest.xctoolchain/usr

# Start Jupyter
jupyter notebook
```

**Important**: Use system Python (`/usr/bin/python3`), not conda or virtualenv.

### Linux (Ubuntu 22.04+)

```bash
# Install Swift via swiftly
curl -L https://swiftlang.github.io/swiftly/swiftly-install.sh | bash
swiftly install main-snapshot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate
pip install jupyter ipykernel

# Clone and register
git clone https://github.com/pedronahum/swift-jupyter.git
cd swift-jupyter
python3 register.py --sys-prefix --use-swiftly-toolchain

# Start Jupyter
jupyter notebook
```

## Installing Swift Packages

Use the `%install` directive in the first cell:

```swift
%install '.package(url: "https://github.com/pvieito/PythonKit", branch: "master")' PythonKit
```

Then import and use:

```swift
import PythonKit

let np = Python.import("numpy")
let plt = Python.import("matplotlib.pyplot")

let x = np.linspace(0, 10, 100)
let y = np.sin(x)
plt.plot(x, y)
plt.show()
```

## Magic Commands

| Command | Description |
|---------|-------------|
| `%help` | Show available commands |
| `%lsmagic` | List all magic commands |
| `%who` | List defined variables |
| `%reset` | Clear all state |
| `%timeit <code>` | Time code execution |
| `%env [VAR[=VALUE]]` | Show/set environment variables |
| `%swift-version` | Show Swift toolchain information |
| `%load <file>` | Load and execute a Swift file |
| `%save <file>` | Save execution history to file |
| `%history [-n N]` | Show execution history |
| `%install` | Install Swift packages |
| `%enable_completion` | Enable code completion |
| `%disable_completion` | Disable code completion |

## Pre-compiled Library Directives

For pre-compiled Swift libraries that cannot use `%install` (due to SPM's unsafeFlags restrictions):

| Directive | Example | Description |
|-----------|---------|-------------|
| `%swiftir_setup` | `%swiftir_setup /opt/sdk` | One-line SDK setup (recommended) |
| `%swift_library_path` | `%swift_library_path /opt/lib` | Add to LD_LIBRARY_PATH |
| `%swift_module_path` | `%swift_module_path /opt/modules` | Add Swift module search paths |
| `%swift_env` | `%swift_env MY_VAR=/opt` | Set environment variables |
| `%swift_flags` | `%swift_flags -I/path -L/path` | Add compiler flags |
| `%swift_link` | `%swift_link MyLibrary` | Link libraries |
| `%swift_framework_path` | `%swift_framework_path /opt/fw` | Add framework paths (macOS) |
| `%swift_config` | `%swift_config` | Display current configuration |

Example usage:

```swift
// Set up a pre-compiled SDK
%swiftir_setup /opt/swiftir-deps

// Or configure paths individually
%swift_library_path /opt/mylib/lib
%swift_module_path /opt/mylib/swift-modules
%swift_link MyRuntime

// Verify configuration
%swift_config

// Now import and use
import MyRuntime
```

## Compatibility

| Component | Version |
|-----------|---------|
| Swift | 6.0+ (main-snapshot recommended) |
| Python | 3.9-3.12 |
| Jupyter | 4.x / Notebook 7.x |
| macOS | 12+ (Apple Silicon & Intel) |
| Linux | Ubuntu 22.04+ |

## Documentation

- [Google Colab Guide](docs/GOOGLE_COLAB_GUIDE.md)
- [PythonKit Setup](docs/PYTHONKIT_SETUP.md)
- [Changelog](docs/CHANGELOG.md)

## License

Apache License 2.0

## Acknowledgments

Originally created by Google as part of Swift for TensorFlow. Modernized in 2025 by Pedro Nahum.
