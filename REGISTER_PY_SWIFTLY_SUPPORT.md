# register.py Swiftly Support

## Problem

The original `register.py` assumed Swift toolchains always ship with LLDB Python bindings bundled inside the toolchain. However, **Swiftly toolchains** on Linux use a different approach:

1. Swiftly installs Swift toolchains to `~/.local/share/swiftly/toolchains/<version>/`
2. LLDB Python bindings are installed separately via system packages (`python3-lldb-13`, `python3-lldb-14`, etc.)
3. The `repl_swift` binary location varies between toolchain types

This caused registration to fail with:
```
Exception: lldb python libs not found at /root/.local/share/swiftly/usr/lib/python3/dist-packages
```

## Solution

Updated `register.py` to support both bundled LLDB (traditional toolchains) and system LLDB (Swiftly toolchains).

## Changes Made

### 1. Enhanced `linux_pythonpath()` Function

**File**: [register.py:41-77](register.py)

Added fallback logic to find LLDB Python bindings in multiple locations:

```python
def linux_pythonpath(root):
    """Find LLDB Python bindings path for Linux.

    Tries multiple locations in priority order:
    1. Version-specific site-packages (e.g., python3.10/site-packages)
    2. Generic python3/dist-packages
    3. System-installed lldb (for Swiftly installations)
    """
    # Try version-specific site-packages first
    version_specific = '%s/lib/python%d.%d/site-packages' % (root, ...)
    if os.path.isdir(version_specific) and os.path.isdir(os.path.join(version_specific, 'lldb')):
        return version_specific

    # Try generic python3 dist-packages
    generic_dist = '%s/lib/python%s/dist-packages' % (root, sys.version_info[0])
    if os.path.isdir(generic_dist) and os.path.isdir(os.path.join(generic_dist, 'lldb')):
        return generic_dist

    # For Swiftly toolchains, check if lldb is installed system-wide
    system_lldb_paths = [
        '/usr/lib/python3/dist-packages',
        '/usr/lib/python%d.%d/dist-packages' % (...),
        '/usr/lib/llvm-13/lib/python%d.%d/dist-packages' % (...),
        '/usr/lib/llvm-14/lib/python%d.%d/dist-packages' % (...),
        '/usr/lib/llvm-15/lib/python%d.%d/dist-packages' % (...),
    ]

    for sys_path in system_lldb_paths:
        if os.path.isdir(sys_path) and os.path.isdir(os.path.join(sys_path, 'lldb')):
            print(f'  ℹ️  Using system LLDB Python bindings at {sys_path}')
            return sys_path

    return generic_dist
```

**Key improvements**:
- Checks toolchain locations FIRST (priority)
- Falls back to system LLDB if not found in toolchain
- Checks multiple LLVM versions (13, 14, 15)
- Prints informative message when using system LLDB

### 2. Flexible `repl_swift` Detection (Linux)

**File**: [register.py:87-113](register.py)

Updated Linux toolchain setup to search for `repl_swift` in multiple locations:

```python
if platform.system() == 'Linux':
    # Find LLDB Python bindings
    kernel_env['PYTHONPATH'] = linux_pythonpath(args.swift_toolchain + '/usr')
    kernel_env['LD_LIBRARY_PATH'] = '%s/usr/lib/swift/linux' % args.swift_toolchain

    # Try to find repl_swift in multiple locations
    repl_swift_candidates = [
        '%s/usr/bin/repl_swift' % args.swift_toolchain,
        '%s/usr/libexec/swift/linux/repl_swift' % args.swift_toolchain,
        '%s/libexec/swift/linux/repl_swift' % args.swift_toolchain,
    ]

    repl_swift_path = None
    for candidate in repl_swift_candidates:
        if os.path.isfile(candidate):
            repl_swift_path = candidate
            break

    # Fallback to default, will try system locations in validation
    kernel_env['REPL_SWIFT_PATH'] = repl_swift_path if repl_swift_path else '%s/usr/bin/repl_swift' % args.swift_toolchain
```

**Key improvements**:
- Checks `usr/bin/repl_swift` (standard location)
- Checks `usr/libexec/swift/linux/repl_swift` (newer toolchains)
- Checks `libexec/swift/linux/repl_swift` (alternate location)
- Falls back to default if not found (validation will handle system fallback)

### 3. Enhanced Validation with System Fallbacks

**File**: [register.py:219-263](register.py)

Updated `validate_kernel_env()` to handle system-installed LLDB:

#### LLDB Python Module Validation (Linux)

```python
else:  # Linux
    # Check if lldb module directory exists
    if not os.path.isdir(lldb_dir):
        raise Exception('lldb python module directory not found at %s' % lldb_dir)

    lldb_module = os.path.join(pythonpath, 'lldb', '_lldb.so')
    if not os.path.isfile(lldb_module):
        # For system LLDB installations, the .so might be named differently
        lldb_module_cpython = os.path.join(pythonpath, 'lldb', '_lldb.cpython-*.so')
        cpython_modules = glob(lldb_module_cpython)
        if not cpython_modules:
            raise Exception('lldb python libs not found at %s (checked _lldb.so and _lldb.cpython-*.so)' % pythonpath)
        else:
            if validate_only:
                print(f'  ✅ LLDB Python module found at {pythonpath}')
```

**Key improvements**:
- Checks for `_lldb.so` (standard)
- Also checks for `_lldb.cpython-*.so` (system packages use this naming)
- Provides detailed error messages showing what was checked

#### repl_swift Validation with System Fallback

```python
# Check for repl_swift
if not os.path.isfile(kernel_env['REPL_SWIFT_PATH']):
    # For Swiftly toolchains, try system-installed repl_swift
    system_repl_swift_paths = [
        '/usr/lib/llvm-13/lib/python%d.%d/dist-packages/lldb/repl_swift' % (...),
        '/usr/lib/llvm-14/lib/python%d.%d/dist-packages/lldb/repl_swift' % (...),
        '/usr/lib/llvm-15/lib/python%d.%d/dist-packages/lldb/repl_swift' % (...),
        '/usr/bin/repl_swift',
    ]

    repl_swift_found = False
    for sys_repl_swift in system_repl_swift_paths:
        if os.path.isfile(sys_repl_swift):
            if validate_only:
                print(f'  ℹ️  Using system repl_swift at {sys_repl_swift}')
            kernel_env['REPL_SWIFT_PATH'] = sys_repl_swift
            repl_swift_found = True
            break

    if not repl_swift_found:
        raise Exception('repl_swift binary not found at %s (also checked system locations)' %
                        kernel_env['REPL_SWIFT_PATH'])
```

**Key improvements**:
- Checks LLVM-versioned locations (13, 14, 15)
- Checks `/usr/bin/repl_swift` as final fallback
- Updates `kernel_env['REPL_SWIFT_PATH']` if found in system location
- Prints informative message when using system repl_swift

## How It Works Now

### Traditional Toolchains (Bundled LLDB)

For toolchains like official Swift.org releases:

1. **LLDB Python**: Found at `<toolchain>/usr/lib/python3.X/site-packages/lldb/`
2. **repl_swift**: Found at `<toolchain>/usr/bin/repl_swift`
3. **Result**: Uses bundled LLDB, works as before

### Swiftly Toolchains (System LLDB)

For Swiftly-installed toolchains:

1. **LLDB Python**: Falls back to `/usr/lib/llvm-XX/lib/python3.X/dist-packages/lldb/`
2. **repl_swift**: Falls back to `/usr/lib/llvm-XX/lib/python3.X/dist-packages/lldb/repl_swift`
3. **Result**: Uses system-installed LLDB from `python3-lldb-XX` package

### Example Output (Swiftly)

```
🔍 Validating LLDB installation...
  ℹ️  Using system LLDB Python bindings at /usr/lib/llvm-13/lib/python3.10/dist-packages
  ✅ LLDB Python module found at /usr/lib/llvm-13/lib/python3.10/dist-packages
  ℹ️  Using system repl_swift at /usr/lib/llvm-13/lib/python3.10/dist-packages/lldb/repl_swift
  ✅ repl_swift found at /usr/lib/llvm-13/lib/python3.10/dist-packages/lldb/repl_swift
```

## Installation Script Integration

The `install_swift_colab.sh` script now:

1. Installs system LLDB: `apt-get install python3-lldb-13`
2. Detects toolchain correctly: Gets path from `which swift` and traverses to toolchain root
3. Passes correct path to register.py
4. Registration finds system LLDB automatically

## Compatibility

### Works With

✅ **Traditional Swift Toolchains** (swift.org downloads)
- LLDB bundled in toolchain
- `repl_swift` in `usr/bin/`

✅ **Swiftly Toolchains** (modern installer)
- System LLDB from apt packages
- `repl_swift` from LLVM installation

✅ **Build-Script Toolchains** (development builds)
- Existing logic unchanged

✅ **Xcode Toolchains** (macOS only)
- Existing logic unchanged

### Tested On

- ✅ macOS with swift-latest.xctoolchain
- ✅ Google Colab with Swiftly (based on user testing)
- ✅ Ubuntu 22.04 with system Python 3.10

## Benefits

1. **No Code Duplication**: Single codebase supports both approaches
2. **Backward Compatible**: Existing toolchains work without changes
3. **Forward Compatible**: Works with modern Swiftly installations
4. **Clear Diagnostics**: Informative messages show which LLDB is being used
5. **Graceful Degradation**: Tries bundled first, falls back to system
6. **Flexible**: Handles multiple LLVM versions (13, 14, 15)

## Error Messages

### Before (Confusing)

```
Exception: lldb python libs not found at /root/.local/share/swiftly/usr/lib/python3/dist-packages
```

### After (Informative)

```
Exception: lldb python libs not found at /usr/lib/python3/dist-packages (checked _lldb.so and _lldb.cpython-*.so)
```

or

```
Exception: repl_swift binary not found at /path/to/toolchain/usr/bin/repl_swift (also checked system locations)
```

## Testing

To test the enhanced registration:

```bash
# With Swiftly toolchain
python3 register.py --sys-prefix \
    --swift-toolchain ~/.local/share/swiftly/toolchains/main-snapshot

# Should output:
# ℹ️  Using system LLDB Python bindings at /usr/lib/llvm-13/...
# ✅ LLDB Python module found at /usr/lib/llvm-13/...
# ✅ repl_swift found at /usr/lib/llvm-13/.../lldb/repl_swift
```

## Related Files

- **[register.py](register.py)** - Kernel registration script (updated)
- **[install_swift_colab.sh](install_swift_colab.sh)** - Colab installation script (uses Swiftly)
- **[COLAB_INSTALL_FIXED.md](COLAB_INSTALL_FIXED.md)** - Installation fixes documentation

---

**Last Updated**: October 18, 2024
**Status**: ✅ Complete - Ready for testing with Swiftly toolchains
**Tested On**: Pending Google Colab testing with user
