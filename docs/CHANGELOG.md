# Changelog

## November 2025 - Enhanced User Experience

### New Features

#### 1. Expression Value Display
- Automatic display of expression values like Python notebooks
- No need to explicitly call `print()` for simple expressions
- Example: typing `42` in a cell displays `42` as output

#### 2. Magic Commands
- `%help` - Display available commands and tips
- `%who` - List variables defined in the session
- `%reset` - Reset the Swift REPL (clear all state)
- `%timeit <code>` - Time the execution of Swift code

#### 3. Better Error Messages
Pattern-matched error messages with actionable suggestions for common Swift errors:
- Immutable variable assignment (`let` vs `var`)
- Type mismatches and conversions
- Optional unwrapping
- Missing return statements
- Undefined variables/functions
- Missing modules with install hints
- Protocol conformance
- Access control issues

#### 4. Package Installation Progress
Real-time feedback during package installation with 5 steps and troubleshooting tips.

Configurable timeout via `SWIFT_JUPYTER_BUILD_TIMEOUT` environment variable (default: 600 seconds).

### Bug Fixes
- Fixed `process.is_alive` AttributeError (now uses LLDB's `IsValid()` API)
- Fixed exception handlers to gracefully return error messages
- Replaced bare exception handlers with specific exception types

---

## October 2024 - PythonKit & Colab Support

### PythonKit Support for matplotlib
- Added `SWIFT_BUILD_PATH` environment variable for macOS
- Updated Package Description from 4.2 to 5.5 (required for modern SwiftPM syntax)
- Fixed dlopen to use `Darwin` module on macOS instead of `Glibc`

### Google Colab Support
- One-click installation script (`install_swift_colab.sh`)
- Automatic Swift toolchain download via Swiftly
- All dependencies configured automatically

---

## Compatibility

| Component | Version |
|-----------|---------|
| Swift | 6.0+ (main-snapshot recommended) |
| Python | 3.9-3.12 |
| Jupyter | 4.x / Notebook 7.x |
| macOS | 12+ (Apple Silicon & Intel) |
| Linux | Ubuntu 22.04+ |

## Notes for Contributors

- Use `/usr/bin/python3` on macOS for LLDB compatibility (not conda Python)
- `%install` directives must be in the first cell of notebooks
- PythonKit requires PackageDescription 5.5+
