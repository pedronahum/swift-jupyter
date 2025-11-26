# Swift-Jupyter Improvements - November 2025

This document details all the improvements made to the Swift-Jupyter kernel in November 2025, focusing on enhanced user experience, better error handling, and new interactive features.

## Table of Contents

1. [Bug Fixes](#1-bug-fixes)
2. [Expression Value Display](#2-expression-value-display)
3. [Better Error Messages](#3-better-error-messages)
4. [Magic Commands](#4-magic-commands)
5. [Package Installation Progress](#5-package-installation-progress)
6. [LSP Integration Improvements](#6-lsp-integration-improvements)
7. [Rich Display Support](#7-rich-display-support)

---

## 1. Bug Fixes

### 1.1 Fixed `process.is_alive` AttributeError

**Location**: [swift_kernel.py:1808](../swift_kernel.py#L1808)

**Problem**: The code used `self.process.is_alive` which doesn't exist on LLDB's SBProcess object, causing an AttributeError.

**Before**:
```python
if not self.process.is_alive:
    # handle dead process
```

**After**:
```python
if not self.process or not self.process.IsValid():
    # handle dead process
```

### 1.2 Fixed Exception Re-raise Crashes

**Location**: [swift_kernel.py:1650-1685](../swift_kernel.py#L1650-L1685)

**Problem**: Bare `raise e` statements in exception handlers would crash the kernel instead of gracefully handling errors.

**Before**:
```python
except Exception as e:
    self._send_exception_report('_process_installs', e)
    raise e  # ❌ Crashes kernel
```

**After**:
```python
except Exception as e:
    self.log.error(f'Unexpected error in _process_installs: {e}', exc_info=True)
    error_msg = [
        'Unexpected error during package installation.',
        'The kernel may be in an unstable state. Consider restarting if issues persist.',
        '',
        f'Error: {str(e)}'
    ]
    self._send_iopub_error_message(error_msg)
    return self._make_execute_reply_error_message(error_msg)
```

### 1.3 Fixed Bare Exception Handlers

**Location**: [swift_kernel.py:608-623](../swift_kernel.py#L608-L623)

**Problem**: Bare `except:` clauses catch everything including KeyboardInterrupt and SystemExit.

**Before**:
```python
try:
    lsp_path = shutil.which('sourcekit-lsp')
except:  # ❌ Catches everything
    pass
```

**After**:
```python
try:
    lsp_path = shutil.which('sourcekit-lsp')
except (OSError, ImportError, AttributeError) as e:
    self.log.debug(f'Error searching PATH for sourcekit-lsp: {e}')
    lsp_path = None
```

---

## 2. Expression Value Display

**Location**: [swift_kernel.py:84-115](../swift_kernel.py#L84-L115), [swift_kernel.py:1739-1766](../swift_kernel.py#L1739-L1766)

Makes Swift notebooks feel more natural by automatically displaying expression values, similar to Python notebooks.

### How It Works

When you execute a cell that evaluates to a value, it's automatically displayed:

```swift
// Input:
let x = 42
x

// Output:
42
```

```swift
// Input:
[1, 2, 3].map { $0 * 2 }

// Output:
[2, 4, 6]
```

### Implementation

Added `get_formatted_value()` method to the `SuccessWithValue` class:

```python
def get_formatted_value(self):
    """Get a nicely formatted value for display in notebooks."""
    # First, try to get the full description which has the most complete info
    full_desc = self.value_description()

    # Try to extract just the value after the '='
    if '=' in full_desc:
        value_part = full_desc.split('=', 1)[1].strip()
        return value_part

    # For types without '=' (shouldn't happen often), try summary/value
    summary_str = self.result.GetSummary()
    if summary_str:
        return summary_str.strip('"')

    value_str = self.result.GetValue()
    if value_str:
        return value_str

    return full_desc
```

### Examples

| Input | Output |
|-------|--------|
| `42` | `42` |
| `"hello"` | `"hello"` |
| `[1, 2, 3]` | `3 values { [0] = 1, [1] = 2, [2] = 3 }` |
| `let msg = "test"; msg` | `"test"` |

---

## 3. Better Error Messages

**Location**: [swift_kernel.py:199-293](../swift_kernel.py#L199-L293)

Added pattern-matched error messages that provide actionable suggestions and documentation links for common Swift errors.

### Supported Error Patterns

#### 3.1 Immutable Variable Assignment

**Pattern**: `cannot assign to value: ... is a 'let' constant`

```
error: cannot assign to value: 'x' is a 'let' constant

💡 Tip: Change 'let x' to 'var x' to make it mutable
📖 Learn more: https://docs.swift.org/swift-book/LanguageGuide/TheBasics.html#ID310
```

#### 3.2 Type Mismatch

**Pattern**: `cannot convert value of type ... to`

```
error: cannot convert value of type 'String' to expected argument type 'Int'

💡 Tip: Swift is strongly typed. You may need to:
   • Use explicit conversion: Int(stringValue) or String(intValue)
   • Check that your types match the expected parameter types
📖 Learn more: https://docs.swift.org/swift-book/LanguageGuide/TheBasics.html#ID322
```

#### 3.3 Optional Unwrapping

**Pattern**: `value of optional type ... must be unwrapped`

```
error: value of optional type 'String?' must be unwrapped

💡 Tip: Use one of these to safely unwrap optionals:
   • if let value = optional { ... }
   • guard let value = optional else { ... }
   • optional ?? defaultValue
   • optional! (only if you're certain it's not nil)
📖 Learn more: https://docs.swift.org/swift-book/LanguageGuide/TheBasics.html#ID330
```

#### 3.4 Missing Return

**Pattern**: `missing return in ... expected to return`

```
error: missing return in function expected to return 'Int'

💡 Tip: All code paths in a function must return a value of the declared type
📖 Learn more: https://docs.swift.org/swift-book/LanguageGuide/Functions.html
```

#### 3.5 Undefined Variable/Function

**Pattern**: `cannot find ... in scope`

```
error: cannot find 'myVariable' in scope

💡 Tip: Check for:
   • Typos in the variable or function name
   • Missing import statement
   • Variable declared in a different scope
📖 Learn more: https://docs.swift.org/swift-book/LanguageGuide/TheBasics.html
```

#### 3.6 Missing Module

**Pattern**: `no such module`

```
error: no such module 'SomeModule'

💡 Tip: You need to install the module first. Try:
   %install '.package(url: "https://github.com/author/SomeModule", from: "1.0.0")' SomeModule
📖 Learn more: https://github.com/pedronahum/swift-jupyter#install-directive
```

#### 3.7 Protocol Conformance

**Pattern**: `does not conform to protocol`

```
error: type 'MyType' does not conform to protocol 'Equatable'

💡 Tip: To conform to a protocol, you must implement all required methods/properties
   For common protocols like Equatable, Hashable, Codable, you can often just add the conformance
   and the compiler will synthesize the implementation automatically.
📖 Learn more: https://docs.swift.org/swift-book/LanguageGuide/Protocols.html
```

#### 3.8 Access Control

**Pattern**: `is inaccessible due to ... protection level`

```
error: 'privateMethod' is inaccessible due to 'private' protection level

💡 Tip: Swift access levels from most to least restrictive:
   • private: Same declaration only
   • fileprivate: Same file only
   • internal: Same module (default)
   • public/open: Available to other modules
📖 Learn more: https://docs.swift.org/swift-book/LanguageGuide/AccessControl.html
```

#### 3.9 Closure Syntax

**Pattern**: `contextual closure type`

```
error: contextual closure type ... expects 2 arguments

💡 Tip: Check that your closure parameter count and types match what's expected
   Example: array.map { $0 * 2 } or array.map { item in item * 2 }
📖 Learn more: https://docs.swift.org/swift-book/LanguageGuide/Closures.html
```

#### 3.10 Initializer Issues

**Pattern**: `'init' is inaccessible` or `has no initializers`

```
error: class 'MyClass' has no initializers

💡 Tip: Classes need initializers for all stored properties without default values
   • Add default values: var name: String = ""
   • Or create an init method: init(name: String) { self.name = name }
📖 Learn more: https://docs.swift.org/swift-book/LanguageGuide/Initialization.html
```

### Implementation

```python
def get_helpful_message(self):
    """Get an enhanced error message with helpful suggestions."""
    original_error = self.get_cleaned_message()
    suggestions = []

    # Pattern matching for common errors
    if "cannot assign to value:" in original_error.lower() and "is a 'let' constant" in original_error.lower():
        # ... add suggestions
    elif "cannot convert value of type" in original_error.lower():
        # ... add suggestions
    # ... more patterns

    if suggestions:
        return original_error + "\n\n" + "\n".join(suggestions)
    else:
        return original_error
```

---

## 4. Magic Commands

**Location**: [swift_kernel.py:1010-1222](../swift_kernel.py#L1010-L1222)

Added interactive magic commands for a more dynamic notebook experience.

### 4.1 %help

Display available commands and features:

```
%help
```

Output:
```
╔══════════════════════════════════════════════════════════════════════╗
║                     Swift Jupyter Kernel Help                        ║
╠══════════════════════════════════════════════════════════════════════╣
║ MAGIC COMMANDS                                                       ║
║ ─────────────────────────────────────────────────────────────────── ║
║ %help           Show this help message                               ║
║ %who            List variables defined in the session                ║
║ %reset          Reset the Swift REPL (clear all state)               ║
║ %timeit <code>  Time the execution of Swift code                     ║
║                                                                      ║
║ PACKAGE INSTALLATION                                                 ║
║ ─────────────────────────────────────────────────────────────────── ║
║ %install '<package>' ModuleName                                      ║
║   Example: %install '.package(url: "...", from: "1.0.0")' MyModule  ║
║                                                                      ║
║ %install-swiftpm-flags <flags>                                       ║
║   Set additional flags for SwiftPM (e.g., -v for verbose)            ║
║                                                                      ║
║ %install-extra-include-command <cmd>                                 ║
║   Add extra include paths from command output                        ║
║                                                                      ║
║ %install-location <path>                                             ║
║   Set custom location for package installation                       ║
║                                                                      ║
║ DISPLAY                                                              ║
║ ─────────────────────────────────────────────────────────────────── ║
║ Use EnableJupyterDisplay() in your code to enable rich display       ║
║ Then use display(value) to show formatted output                     ║
║                                                                      ║
║ TIPS                                                                 ║
║ ─────────────────────────────────────────────────────────────────── ║
║ • Last expression value is automatically displayed                   ║
║ • Use print() for explicit output                                    ║
║ • Errors show helpful suggestions for common mistakes                ║
╚══════════════════════════════════════════════════════════════════════╝
```

### 4.2 %who

List all user-defined variables in the current session:

```
%who
```

Output:
```
╔══════════════════════════════════════════════════════════════════════╗
║                      Variables in Scope                              ║
╠══════════════════════════════════════════════════════════════════════╣
║ Note: Due to Swift REPL limitations, we can only track variables     ║
║ by analyzing executed code. Some variables may be missing.           ║
╠══════════════════════════════════════════════════════════════════════╣
║ Tracked declarations:                                                ║
║   • x (let)                                                          ║
║   • name (var)                                                       ║
║   • myArray (let)                                                    ║
╚══════════════════════════════════════════════════════════════════════╝
```

### 4.3 %reset

Reset the Swift REPL, clearing all state:

```
%reset
```

Output:
```
╔══════════════════════════════════════════════════════════════════════╗
║                      🔄 Resetting Swift REPL                         ║
╠══════════════════════════════════════════════════════════════════════╣
║ • Stopping current LLDB process...                                   ║
║ • Reinitializing Swift environment...                                ║
║ • ✓ Swift REPL has been reset                                        ║
║                                                                      ║
║ Note: All variables, functions, and imported modules have been       ║
║ cleared. Any installed packages will need to be re-imported.         ║
╚══════════════════════════════════════════════════════════════════════╝
```

### 4.4 %timeit

Time the execution of Swift code:

```
%timeit [1, 2, 3, 4, 5].map { $0 * $0 }
```

Output:
```
╔══════════════════════════════════════════════════════════════════════╗
║                          ⏱️  Timing Results                          ║
╠══════════════════════════════════════════════════════════════════════╣
║ Code: [1, 2, 3, 4, 5].map { $0 * $0 }                                ║
║                                                                      ║
║ Runs: 7                                                              ║
║ Total time: 0.0234s                                                  ║
║ Average: 3.34ms per run                                              ║
║ Best: 2.89ms                                                         ║
║ Worst: 4.12ms                                                        ║
╚══════════════════════════════════════════════════════════════════════╝
```

### 4.5 %lsmagic

List all available magic commands:

```
%lsmagic
```

Output:
```
Available Magic Commands
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Line Magics (single line):
  %help                     Show help message
  %lsmagic                  List all magic commands (this list)
  %who                      List defined variables
  %reset [-q]               Reset kernel (clear all state)
  %timeit CODE              Time code execution
  %env [VAR[=VALUE]]        Show/set environment variables
  %swift-version            Show Swift toolchain information
  %load FILE                Load and execute a Swift file
  %save FILE                Save cell history to a file
  %history [-n N]           Show execution history

Package Management:
  %install SPEC MODULE      Install Swift package
  %install-swiftpm-flags    Set SwiftPM build flags
  %install-location PATH    Set package install location

Kernel Control:
  %enable_completion        Enable code completion
  %disable_completion       Disable code completion
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 4.6 %env

Show or set environment variables:

```
%env                    # Show all environment variables
%env PATH               # Show specific variable
%env MY_VAR=hello       # Set environment variable
```

### 4.7 %swift-version

Show Swift toolchain information:

```
%swift-version
```

Output:
```
Swift Toolchain Information
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📍 Swift binary: /usr/bin/swift

📋 Version:
   Swift version 6.0
   Target: x86_64-unknown-linux-gnu

🎯 Target:
   Triple: x86_64-unknown-linux-gnu
   Module Triple: x86_64-unknown-linux-gnu
   Runtime Path: /usr/lib/swift/linux

🔧 LLDB:
   Version: lldb version 21.0.0

🔌 Kernel Environment:
   SWIFT_BUILD_PATH: /usr/bin/swift-build
   SWIFT_PACKAGE_PATH: /usr/bin/swift-package

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 4.8 %load

Load and execute a Swift file:

```
%load mycode.swift
%load ~/projects/utils.swift
```

Output:
```
📂 Loaded mycode.swift (1234 chars)
```

The file contents are then executed in the kernel.

### 4.9 %save

Save execution history to a Swift file:

```
%save session.swift
```

Output:
```
💾 Saved 5 cells to session.swift
```

### 4.10 %history

Show execution history:

```
%history           # Show last 10 entries
%history -n 20     # Show last 20 entries
```

Output:
```
Execution History
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[1] let x = 42
[2] let message = "Hello, Swift!"
[3] print(x + 10)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Showing 3 of 3 entries
Use %history -n N to show more entries
```

### Implementation

Magic commands are processed in the `_preprocess()` method before code execution:

```python
def _preprocess(self, code):
    stripped = code.strip()

    if stripped.startswith('%who'):
        self._handle_who_magic(stripped)
        return ''
    elif stripped.startswith('%reset'):
        self._handle_reset_magic(stripped)
        return ''
    elif stripped.startswith('%timeit '):
        return self._handle_timeit_magic(stripped)
    elif stripped.startswith('%help'):
        self._handle_help_magic()
        return ''

    # Otherwise, preprocess line by line as normal
    lines = code.split('\n')
    preprocessed_lines = [
        self._preprocess_line(i, line) for i, line in enumerate(lines)]
    return '\n'.join(preprocessed_lines)
```

---

## 5. Package Installation Progress

**Location**: [swift_kernel.py:1406-1773](../swift_kernel.py#L1406-L1773)

Enhanced the package installation experience with real-time progress indicators, better error messages, and timeout handling.

### 5.1 Progress Indicators

Installation now shows 5 clear steps:

```
📦 Installing Swift Packages
==================================================
Packages:
	.package(url: "https://github.com/author/Package", from: "1.0.0")
		PackageName
[1/5] 📋 Creating Package.swift
[2/5] 🌐 Resolving and fetching dependencies (this may take a while...)
[3/5] 🔨 Building packages...
Building for debugging...
Build complete! (5.23s)
[4/5] 📦 Copying Swift modules to kernel...
[5/5] 🔗 Loading packages into Swift REPL...

✓ Build completed in 12.3s

✅ Successfully installed: PackageName
```

### 5.2 Enhanced Error Messages

Every failure point now includes troubleshooting tips:

**Missing SWIFT_BUILD_PATH**:
```
Install Error: Cannot install packages because SWIFT_BUILD_PATH is not specified.

💡 This usually means the kernel was not registered correctly.
   • Try running: python3 register.py --sys-prefix --swift-toolchain <path>
   • See: https://github.com/pedronahum/swift-jupyter#installation
```

**Build Failure**:
```
Install Error: swift-build returned nonzero exit code 1.

💡 Troubleshooting:
   • Check that the package URL is correct
   • Verify the package version/branch exists
   • Check your internet connection
   • Try running with verbose output: %install-swiftpm-flags -v
   • Some packages may not be compatible with your Swift version
```

**Missing build.db**:
```
Install Error: build.db is missing from build directory.

💡 Troubleshooting:
   • This indicates the build may have failed silently
   • Try cleaning the build: rm -rf ~/.swift-jupyter/package_base
   • Check that swift-build is working: swift build --help
   • Verify you have write permissions in ~/.swift-jupyter/
```

**Module Copy Failure**:
```
Install Error: Failed to copy Swift module files.

💡 Troubleshooting:
   • Check permissions on ~/.swift-jupyter/modules
   • Ensure you have enough disk space
   • Try cleaning: rm -rf ~/.swift-jupyter/modules

Error details: [Permission denied]
```

**dlopen Failure**:
```
Install Error: Failed to load shared library.

💡 Common causes:
   • Missing system dependencies (try: ldd /path/to/lib.so)
   • Incompatible Swift version between kernel and packages
   • Corrupted build artifacts (try: rm -rf ~/.swift-jupyter/package_base)
   • Architecture mismatch (check Swift toolchain architecture)

Error: [detailed error]
```

### 5.3 Timeout Handling

Builds now have a configurable timeout (default 10 minutes):

```python
# Users can override with environment variable
build_timeout = int(os.environ.get('SWIFT_JUPYTER_BUILD_TIMEOUT', '600'))
```

If a build times out:
```
Install Error: Package build timed out after 600 seconds.

💡 Troubleshooting:
   • Large packages may take longer to build
   • Increase timeout: export SWIFT_JUPYTER_BUILD_TIMEOUT=1200
   • Check your internet connection for slow downloads
   • Consider building the package outside Jupyter first to cache dependencies
```

### 5.4 Build Timing

Shows elapsed time for successful builds:
```
✓ Build completed in 12.3s
```

### 5.5 Success Message

Shows exactly what was installed:
```
✅ Successfully installed: PromiseKit, Alamofire
```

---

## 6. LSP Integration Improvements

**Location**: [swift_kernel.py:601-634](../swift_kernel.py#L601-L634), [lsp_client.py](../lsp_client.py)

### 6.1 Auto-Detection of sourcekit-lsp

The kernel now automatically finds sourcekit-lsp in multiple locations:

```python
# 1. Check PATH
lsp_path = shutil.which('sourcekit-lsp')

# 2. Check relative to swift compiler
if not lsp_path:
    swift_path = shutil.which('swift')
    if swift_path:
        swift_bin_dir = os.path.dirname(os.path.realpath(swift_path))
        candidate = os.path.join(swift_bin_dir, 'sourcekit-lsp')
        if os.path.exists(candidate):
            lsp_path = candidate

# 3. Check common swiftly installation locations
if not lsp_path:
    swiftly_paths = [
        os.path.expanduser('~/.local/share/swiftly/bin/sourcekit-lsp'),
        '/usr/local/share/swiftly/bin/sourcekit-lsp',
        '/opt/swiftly/bin/sourcekit-lsp'
    ]
    for candidate in swiftly_paths:
        if os.path.exists(candidate):
            lsp_path = candidate
            break
```

### 6.2 Diagnostics Callback

Added support for receiving and processing LSP diagnostics:

```python
# In lsp_client.py
def _handle_message(self, message):
    if 'id' in message:
        # Handle response
        ...
    else:
        method = message.get('method', '')
        if method == 'textDocument/publishDiagnostics':
            if self.diagnostics_callback:
                try:
                    self.diagnostics_callback(message.get('params', {}))
                except Exception as e:
                    self.log.error(f"Error in diagnostics callback: {e}")

def set_diagnostics_callback(self, callback):
    """Set a callback for handling diagnostics notifications."""
    self.diagnostics_callback = callback
```

---

## 7. Rich Display Support

**Location**: [swift_kernel.py:117-304](../swift_kernel.py#L117-L304)

Added HTML rendering for arrays, dictionaries, and objects in Jupyter notebooks for better data visualization.

### 7.1 Array Display

Arrays are displayed as formatted HTML tables:

```swift
[1, 2, 3, 4, 5]
```

Renders as:

| Index | Value |
|-------|-------|
| 0 | 1 |
| 1 | 2 |
| 2 | 3 |
| 3 | 4 |
| 4 | 5 |

### 7.2 Dictionary Display

Dictionaries are displayed with key-value pairs in a table:

```swift
["name": "Alice", "age": "30", "city": "NYC"]
```

Renders as:

| Key | Value |
|-----|-------|
| name | Alice |
| age | 30 |
| city | NYC |

### 7.3 Object/Struct Display

Structs and classes with multiple properties are displayed in a table:

```swift
struct Person {
    let name: String
    let age: Int
}
let person = Person(name: "Alice", age: 30)
person
```

Renders as:

| Property | Type | Value |
|----------|------|-------|
| name | String | Alice |
| age | Int | 30 |

### 7.4 Implementation

The `get_rich_display()` method on `SuccessWithValue` returns both plain text and HTML:

```python
def get_rich_display(self):
    """Get rich display data including HTML for arrays, dictionaries, and tables."""
    plain_text = self.get_formatted_value()
    type_name = self.result.GetTypeName() or ""

    # Check if this is an array type
    if self._is_array_type(type_name):
        html = self._render_array_html()
        if html:
            return (plain_text, html)

    # Check if this is a dictionary type
    if self._is_dictionary_type(type_name):
        html = self._render_dictionary_html()
        if html:
            return (plain_text, html)

    # Check if this might be a struct/class with multiple fields
    num_children = self.result.GetNumChildren()
    if num_children > 0 and num_children <= 50:
        html = self._render_object_html()
        if html:
            return (plain_text, html)

    return (plain_text, None)
```

### 7.5 Jupyter Response

The kernel sends both `text/plain` and `text/html` MIME types:

```python
data = {'text/plain': plain_text}
if html:
    data['text/html'] = html

self.send_response(self.iopub_socket, 'execute_result', {
    'execution_count': self.execution_count,
    'data': data,
    'metadata': {}
})
```

JupyterLab and Jupyter Notebook automatically choose the best representation to display.

### 7.6 Limitations

- Arrays/dictionaries with more than 100 elements fall back to plain text
- Deeply nested objects may not render fully
- Image display (Data objects) is partially implemented

---

## Summary of Changes by File

### swift_kernel.py

| Lines | Change |
|-------|--------|
| 84-115 | Added `get_formatted_value()` method |
| 117-304 | Added `get_rich_display()` method with HTML rendering |
| 157-203 | Added type detection helpers (`_is_array_type`, `_is_dictionary_type`, etc.) |
| 205-304 | Added HTML rendering methods (`_render_array_html`, `_render_dictionary_html`, `_render_object_html`) |
| 199-293 | Added `get_helpful_message()` method with 10 error patterns |
| 455 | Added `execution_history` list for %save and %history |
| 601-634 | Added LSP auto-detection |
| 608-623 | Fixed bare exception handlers |
| 1010-1042 | Updated `_preprocess()` to handle new magic commands |
| 1241-1544 | Added new magic command handlers (%lsmagic, %env, %swift-version, %load, %save, %history) |
| 1406-1411 | Added `_send_install_progress()` helper |
| 1412-1773 | Enhanced package installation with progress, errors, timeout |
| 2346-2352 | Added execution history tracking in `do_execute` |
| 2646-2678 | Updated `do_execute` to use rich display support |
| 1808 | Fixed `process.is_alive` to `process.IsValid()` |
| 1650-1685 | Fixed exception re-raise crashes |

### lsp_client.py

| Lines | Change |
|-------|--------|
| 22 | Added `diagnostics_callback` attribute |
| 129-136 | Added diagnostics notification handling |
| 193-209 | Updated `initialize()` with hover/diagnostics capabilities |
| 214-220 | Added `set_diagnostics_callback()` method |

### README.md

Added "Enhanced User Experience (November 2025)" section documenting all improvements.

---

## Testing

Test files created:

1. **test_expression_values.py**: Tests automatic value display
2. **test_error_messages.py**: Tests helpful error message patterns
3. **test_magic_commands.py**: Tests %help, %who, %reset, %timeit
4. **test_new_magic_commands.py**: Tests %lsmagic, %env, %swift-version, %load, %save, %history
5. **test_package_install.py**: Tests installation progress indicators
6. **test_install_error_handling.py**: Tests installation error messages

Run all tests:
```bash
python3 -m pytest test/ -v
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SWIFT_JUPYTER_BUILD_TIMEOUT` | 600 | Build timeout in seconds |

---

## Compatibility

These improvements are compatible with:
- Swift 6.0+
- Python 3.8+
- Jupyter Client 8.x
- JupyterLab 4.x
- Notebook 7.x

All changes are backward compatible and don't break existing notebooks.
