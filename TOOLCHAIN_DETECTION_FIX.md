# Toolchain Detection Fix for Swiftly

## Problem

The installation script was incorrectly detecting the Swift toolchain directory as `/root/.local/share` instead of the actual toolchain location at `/root/.local/share/swiftly/toolchains/<version>`.

### Error Output
```
Swift toolchain directory: /root/.local/share
⚠️  Warning: Could not find LLDB Python bindings in standard locations
   Checked:
   - /root/.local/share/usr/lib/python3/dist-packages
   ...
Exception: lldb python libs not found at /root/.local/share/usr/lib/python3/dist-packages
```

### Root Cause

The `which swift` command returns a symlink or wrapper script that doesn't directly point to the actual Swift binary in the toolchain. When we tried to traverse up the directory tree using `dirname`, we ended up at the wrong location.

**Expected structure**:
```
~/.local/share/swiftly/toolchains/main-snapshot/
├── usr/
│   ├── bin/
│   │   └── swift
│   ├── lib/
│   │   └── swift/
│   │       └── linux/
│   └── ...
```

**What `which swift` might return**:
- `/root/.local/bin/swift` (symlink)
- `~/.local/share/swiftly/bin/swift` (wrapper script)
- Other intermediate paths

## Solution

Enhanced toolchain detection with multiple fallback strategies:

### 1. Primary Method: Resolve Symlinks

```bash
# Resolve symlinks to get the actual toolchain location
SWIFT_BIN_REAL=$(readlink -f "$SWIFT_BIN" 2>/dev/null || realpath "$SWIFT_BIN" 2>/dev/null || echo "$SWIFT_BIN")

# Traverse up from the real binary location
SWIFT_USR_BIN=$(dirname "$SWIFT_BIN_REAL")  # .../usr/bin
SWIFT_USR=$(dirname "$SWIFT_USR_BIN")  # .../usr
SWIFT_TOOLCHAIN_DIR=$(dirname "$SWIFT_USR")  # .../<version>
```

### 2. Fallback Method: Direct Swiftly Directory Search

If the resolved path doesn't contain "toolchains" (indicating detection failed):

```bash
if [[ ! "$SWIFT_TOOLCHAIN_DIR" == *"toolchains"* ]]; then
    # Look directly in Swiftly's known location
    SWIFTLY_TOOLCHAINS_DIR="$HOME/.local/share/swiftly/toolchains"

    # Find the most recently modified toolchain
    SWIFT_TOOLCHAIN_DIR=$(ls -dt "$SWIFTLY_TOOLCHAINS_DIR"/* 2>/dev/null | head -1)
fi
```

### 3. Verification Step

```bash
# Verify the toolchain directory exists and contains usr
if [ ! -d "$SWIFT_TOOLCHAIN_DIR/usr" ]; then
    # Print diagnostic information and exit
    echo "❌ Error: Toolchain directory doesn't contain 'usr' subdirectory"
    # ... detailed diagnostics
    exit 1
fi
```

## Changes Made

**File**: [install_swift_colab.sh:151-215](install_swift_colab.sh)

### Before
```bash
SWIFT_BIN=$(which swift)
SWIFT_TOOLCHAIN_DIR=$(dirname $(dirname "$SWIFT_BIN"))
```

### After
```bash
# Get the real path of swift binary (resolving symlinks)
SWIFT_BIN=$(which swift)
SWIFT_BIN_REAL=$(readlink -f "$SWIFT_BIN" 2>/dev/null || realpath "$SWIFT_BIN" 2>/dev/null || echo "$SWIFT_BIN")

# Traverse up from real location
SWIFT_USR_BIN=$(dirname "$SWIFT_BIN_REAL")
SWIFT_USR=$(dirname "$SWIFT_USR_BIN")
SWIFT_TOOLCHAIN_DIR=$(dirname "$SWIFT_USR")

# Verify path contains "toolchains"
if [[ ! "$SWIFT_TOOLCHAIN_DIR" == *"toolchains"* ]]; then
    # Fallback: Look directly in Swiftly directory
    SWIFTLY_TOOLCHAINS_DIR="$HOME/.local/share/swiftly/toolchains"
    SWIFT_TOOLCHAIN_DIR=$(ls -dt "$SWIFTLY_TOOLCHAINS_DIR"/* 2>/dev/null | head -1)
fi

# Verify usr subdirectory exists
if [ ! -d "$SWIFT_TOOLCHAIN_DIR/usr" ]; then
    # Print diagnostics and exit
    echo "❌ Error: ..."
    exit 1
fi
```

## Expected Output (Successful)

```bash
Detecting Swift toolchain location...
Current toolchain: main-snapshot
Swift binary (resolved): /root/.local/share/swiftly/toolchains/main-snapshot/usr/bin/swift
Swift toolchain directory (from binary path): /root/.local/share/swiftly/toolchains/main-snapshot
Final Swift toolchain directory: /root/.local/share/swiftly/toolchains/main-snapshot
✅ Toolchain directory verified: /root/.local/share/swiftly/toolchains/main-snapshot/usr
```

## Expected Output (Fallback Triggered)

```bash
Detecting Swift toolchain location...
Current toolchain: main-snapshot
Swift binary (resolved): /root/.local/bin/swift
Swift toolchain directory (from binary path): /root/.local/share
⚠️  Toolchain path doesn't contain 'toolchains', trying alternative method...
Found toolchain via Swiftly directory: /root/.local/share/swiftly/toolchains/main-snapshot
Final Swift toolchain directory: /root/.local/share/swiftly/toolchains/main-snapshot
✅ Toolchain directory verified: /root/.local/share/swiftly/toolchains/main-snapshot/usr
```

## Diagnostic Output (If Still Fails)

If both methods fail, the script will print comprehensive diagnostic information:

```bash
❌ Error: Toolchain directory doesn't contain 'usr' subdirectory
   Expected structure: /path/to/toolchain/usr/bin/swift

Diagnostic information:
  SWIFT_BIN: /usr/local/bin/swift
  SWIFT_BIN_REAL: /root/.local/share/swiftly/bin/swift
  SWIFT_USR_BIN: /root/.local/share/swiftly/bin
  SWIFT_USR: /root/.local/share/swiftly
  SWIFT_TOOLCHAIN_DIR: /root/.local/share

Directory contents of /root/.local/share:
drwxr-xr-x 3 root root 4096 Oct 18 12:34 swiftly

Available toolchains in ~/.local/share/swiftly/toolchains:
drwxr-xr-x 5 root root 4096 Oct 18 12:35 main-snapshot
```

This helps identify exactly where the detection is going wrong.

## Why This Happens

Swiftly creates multiple layers of indirection:

1. **System PATH**: `/usr/local/bin/swift` (installed by script via `install -Dm755`)
2. **Swiftly bin**: `~/.local/share/swiftly/bin/swift` (Swiftly's wrapper)
3. **Toolchain selector**: `~/.local/share/swiftly/toolchains/main-snapshot/usr/bin/swift` (actual binary)

The `which swift` command might return any of these depending on PATH order and how Swiftly sets up the environment.

## Benefits

1. **Robust**: Works regardless of symlink structure
2. **Self-Healing**: Automatically falls back to direct directory search
3. **Diagnostic**: Provides detailed information if detection fails
4. **Documented**: Clear output shows exactly what's being detected

## Related Files

- **[install_swift_colab.sh](install_swift_colab.sh)** - Installation script (updated)
- **[REGISTER_PY_SWIFTLY_SUPPORT.md](REGISTER_PY_SWIFTLY_SUPPORT.md)** - LLDB detection fixes
- **[COLAB_INSTALL_FIXED.md](COLAB_INSTALL_FIXED.md)** - Installation error fixes

---

**Last Updated**: October 18, 2024
**Status**: ✅ Fixed - Robust multi-method detection with fallbacks
**Testing**: Ready for Google Colab testing
