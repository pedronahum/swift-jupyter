#!/bin/bash
#
# Swift Jupyter Kernel Installation Script for Google Colab
#
# This script installs Swift and the Swift Jupyter kernel in Google Colab.
# Usage: curl -sL https://raw.githubusercontent.com/YOUR_REPO/swift-jupyter/main/install_swift_colab.sh | bash
#
# What this script does:
# 1. Installs system dependencies (including LLDB Python bindings)
# 2. Installs Swiftly (Swift toolchain manager)
# 3. Downloads and installs latest Swift development snapshot
# 4. Clones the swift-jupyter repository
# 5. Installs Python dependencies
# 6. Registers the Swift Jupyter kernel
# 7. Creates a test notebook
#
# Requirements:
# - Ubuntu 22.04 (Google Colab default)
# - Internet connection
# - ~2GB disk space
#
# Time: ~3-5 minutes

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print with color
print_step() {
    echo -e "${BLUE}==>${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Configuration
SWIFT_SNAPSHOT="main-snapshot-2025-11-03"  # Specific known-working snapshot
SWIFT_JUPYTER_REPO="https://github.com/pedronahum/swift-jupyter.git"
SWIFT_JUPYTER_BRANCH="main"
INSTALL_DIR="/content/swift-jupyter"

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║           Swift Jupyter Kernel Installation for Google Colab        ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""

# Check if we're in Colab
if [ ! -d "/content" ]; then
    print_warning "This script is designed for Google Colab."
    print_warning "Running in a different environment may require adjustments."
fi

# Step 1: Install system dependencies
print_step "Installing system dependencies..."

# Update package list silently
apt-get update -qq > /dev/null 2>&1

# Add deadsnakes PPA for Python 3.10 (needed for Swift toolchain LLDB)
apt-get install -y -qq software-properties-common > /dev/null 2>&1
add-apt-repository -y ppa:deadsnakes/ppa > /dev/null 2>&1
apt-get update -qq > /dev/null 2>&1

# Install required packages including Python 3.10
apt-get install -y -qq \
    binutils \
    git \
    gnupg2 \
    libc6-dev \
    libcurl4-openssl-dev \
    libedit2 \
    libgcc-11-dev \
    libncurses6 \
    libpython3-dev \
    libsqlite3-0 \
    libstdc++-11-dev \
    libxml2-dev \
    libz3-dev \
    pkg-config \
    python3-lldb-15 \
    tzdata \
    unzip \
    zlib1g-dev \
    python3.10 \
    python3.10-dev \
    python3.10-venv \
    > /dev/null 2>&1

# Install pip for Python 3.10
python3.10 -m ensurepip --upgrade 2>/dev/null || curl -sS https://bootstrap.pypa.io/get-pip.py | python3.10 2>/dev/null

# Install Jupyter dependencies for Python 3.10
echo "  Installing Jupyter dependencies for Python 3.10..."
python3.10 -m pip install -q jupyter ipykernel jupyter_client > /dev/null 2>&1

# Verify Python 3.10
if command -v python3.10 &> /dev/null; then
    print_success "Python 3.10 installed at $(which python3.10)"
else
    print_warning "Python 3.10 not found, will try system Python"
fi

# Try to install python3-lldb for different LLVM versions (as fallback)
for version in 18 17 16 15 14; do
    apt-get install -y -qq python3-lldb-$version > /dev/null 2>&1 && break || true
done

print_success "System dependencies installed"

# Step 2: Install Swiftly
print_step "Installing Swiftly (Swift toolchain manager)..."

SWIFTLY_HOME="$HOME/.local/share/swiftly"
SWIFTLY_BIN="$SWIFTLY_HOME/bin"

if [ ! -f "$SWIFTLY_BIN/swiftly" ]; then
    # Try new installation method first (from https://www.swift.org/install/linux/)
    ARCH=$(uname -m)
    cd /tmp
    if curl -fsSL -O https://download.swift.org/swiftly/linux/swiftly-${ARCH}.tar.gz 2>/dev/null && \
       tar zxf swiftly-${ARCH}.tar.gz 2>/dev/null && \
       ./swiftly init --quiet-shell-followup -y > /dev/null 2>&1; then
        print_success "Swiftly installed (new method)"
    else
        # Fallback to legacy installer
        print_warning "New method failed, trying legacy installer..."
        curl -fsSL https://swiftlang.github.io/swiftly/swiftly-install.sh | bash -s -- -y > /dev/null 2>&1
        print_success "Swiftly installed (legacy method)"
    fi
    cd - > /dev/null
else
    print_success "Swiftly already installed"
fi

# Source the swiftly environment
export SWIFTLY_HOME_DIR="$SWIFTLY_HOME"
export SWIFTLY_BIN_DIR="$SWIFTLY_BIN"
export PATH="$SWIFTLY_BIN:$PATH"

# Source env.sh if it exists
if [ -f "$SWIFTLY_HOME/env.sh" ]; then
    . "$SWIFTLY_HOME/env.sh"
fi

# Step 3: Install Swift snapshot
print_step "Installing Swift (this may take 2-3 minutes)..."

# Check available toolchains
echo "  Checking available toolchains..."
swiftly list-available --platform ubuntu2204 2>/dev/null | head -10 || true

# Try multiple snapshots with fallback (snapshots only, not stable releases)
SWIFT_INSTALLED=false
for snapshot in "$SWIFT_SNAPSHOT" "${SWIFT_SNAPSHOT}a" "main-snapshot" "6.1-snapshot"; do
    echo "  Trying $snapshot..."
    if swiftly install "$snapshot" -y 2>&1; then
        swiftly use "$snapshot" 2>/dev/null
        SWIFT_INSTALLED=true
        print_success "Swift $snapshot installed"
        break
    else
        print_warning "Failed to install $snapshot, trying next..."
    fi
done

if [ "$SWIFT_INSTALLED" = false ]; then
    print_error "Failed to install any Swift version"
    exit 1
fi

# Verify Swift installation
SWIFT_VERSION=$(swift --version 2>&1 | head -1)
print_success "Swift installed: $SWIFT_VERSION"

# Get toolchain path - swiftly uses shims, so we need to read its config
SWIFT_TOOLCHAIN=""

# Method 1: Check swiftly's config.json for the in-use toolchain
SWIFTLY_CONFIG="$SWIFTLY_HOME/config.json"
if [ -f "$SWIFTLY_CONFIG" ]; then
    # Parse JSON to get inUse value (using python since jq may not be available)
    IN_USE=$(python3 -c "import json; print(json.load(open('$SWIFTLY_CONFIG')).get('inUse', ''))" 2>/dev/null)
    if [ -n "$IN_USE" ]; then
        CANDIDATE="$SWIFTLY_HOME/toolchains/$IN_USE"
        if [ -f "$CANDIDATE/usr/bin/swift" ]; then
            SWIFT_TOOLCHAIN="$CANDIDATE"
            echo "  Found toolchain via swiftly config: $IN_USE"
        fi
    fi
fi

# Method 2: Fall back to resolving symlinks if that fails
if [ -z "$SWIFT_TOOLCHAIN" ]; then
    SWIFT_PATH=$(which swift)
    SWIFT_REAL_PATH=$(readlink -f "$SWIFT_PATH" 2>/dev/null)
    # Check if realpath points to swiftly itself
    if [[ "$SWIFT_REAL_PATH" != *"swiftly/bin/swiftly"* ]]; then
        CANDIDATE=$(dirname $(dirname "$SWIFT_REAL_PATH"))
        if [ -d "$CANDIDATE/usr/bin" ] || [ -d "$CANDIDATE/bin" ]; then
            SWIFT_TOOLCHAIN="$CANDIDATE"
        fi
    fi
fi

# Method 3: Search toolchains directory for the one we just installed
if [ -z "$SWIFT_TOOLCHAIN" ]; then
    TOOLCHAINS_DIR="$SWIFTLY_HOME/toolchains"
    if [ -d "$TOOLCHAINS_DIR" ]; then
        for snapshot in "$SWIFT_SNAPSHOT" "${SWIFT_SNAPSHOT}a" "main-snapshot"; do
            for name in $(ls "$TOOLCHAINS_DIR" 2>/dev/null); do
                if [[ "$name" == *"$snapshot"* ]] || [[ "$name" == main-* ]]; then
                    CANDIDATE="$TOOLCHAINS_DIR/$name"
                    if [ -f "$CANDIDATE/usr/bin/swift" ]; then
                        SWIFT_TOOLCHAIN="$CANDIDATE"
                        echo "  Found toolchain by searching: $name"
                        break 2
                    fi
                fi
            done
        done
    fi
fi

if [ -z "$SWIFT_TOOLCHAIN" ]; then
    print_error "Could not determine Swift toolchain path. Check swiftly installation."
    exit 1
fi

echo "  Toolchain path: $SWIFT_TOOLCHAIN"

# Step 4: Clone swift-jupyter repository
print_step "Setting up Swift Jupyter kernel..."

if [ -d "$INSTALL_DIR" ]; then
    print_warning "Removing existing swift-jupyter installation..."
    rm -rf "$INSTALL_DIR"
fi

git clone --depth 1 -b $SWIFT_JUPYTER_BRANCH $SWIFT_JUPYTER_REPO "$INSTALL_DIR" > /dev/null 2>&1
print_success "Repository cloned"

# Step 5: Install Python dependencies
print_step "Installing Python dependencies..."

cd "$INSTALL_DIR"
pip install -q jupyter ipykernel jupyter_client > /dev/null 2>&1
print_success "Python dependencies installed"

# Step 6: Find LLDB Python bindings and determine which Python to use
print_step "Configuring LLDB Python bindings..."

# Get system Python version
PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')

# Build LD_LIBRARY_PATH for the toolchain (needed for LLDB to load Swift libs)
TOOLCHAIN_LD_PATH=""
for path in "$SWIFT_TOOLCHAIN/usr/lib" \
            "$SWIFT_TOOLCHAIN/usr/lib/swift/linux" \
            "$SWIFT_TOOLCHAIN/usr/lib/swift/host/compiler" \
            "$SWIFT_TOOLCHAIN/lib" \
            "$SWIFT_TOOLCHAIN/lib/swift/linux"; do
    if [ -d "$path" ]; then
        if [ -n "$TOOLCHAIN_LD_PATH" ]; then
            TOOLCHAIN_LD_PATH="$TOOLCHAIN_LD_PATH:$path"
        else
            TOOLCHAIN_LD_PATH="$path"
        fi
    fi
done

# Detect what Python version the toolchain's LLDB was built for
detect_lldb_python_version() {
    local toolchain_path="$1"
    for base in "usr/local/lib" "lib" "usr/lib"; do
        for lldb_file in "$toolchain_path/$base"/python*/dist-packages/lldb/_lldb.cpython-*.so; do
            if [ -e "$lldb_file" ]; then
                # Extract version from filename like _lldb.cpython-310-x86_64-linux-gnu.so
                local filename=$(basename "$lldb_file")
                local ver=$(echo "$filename" | sed -n 's/.*cpython-\([0-9]\)\([0-9]*\)-.*/\1.\2/p')
                if [ -n "$ver" ]; then
                    echo "$ver"
                    return 0
                fi
            fi
        done
    done
    return 1
}

TOOLCHAIN_LLDB_PYTHON=$(detect_lldb_python_version "$SWIFT_TOOLCHAIN")
if [ -n "$TOOLCHAIN_LLDB_PYTHON" ]; then
    echo "  Toolchain LLDB was built for Python $TOOLCHAIN_LLDB_PYTHON"
else
    echo "  Could not detect toolchain LLDB Python version"
fi

# Determine which Python to use for the kernel
# Priority: toolchain's Python version > Python 3.10 > system Python
PYTHON_TO_USE=""
if [ -n "$TOOLCHAIN_LLDB_PYTHON" ]; then
    py_cmd="python$TOOLCHAIN_LLDB_PYTHON"
    if command -v "$py_cmd" &> /dev/null; then
        PYTHON_TO_USE=$(which "$py_cmd")
        echo "  Found $py_cmd at $PYTHON_TO_USE"
    else
        echo "  $py_cmd not found, will try alternatives"
    fi
fi

# If toolchain Python not available, try Python 3.10 (which we installed)
if [ -z "$PYTHON_TO_USE" ]; then
    for py_ver_try in "3.10" "3.11" "3.12"; do
        py_cmd="python$py_ver_try"
        if command -v "$py_cmd" &> /dev/null; then
            PYTHON_TO_USE=$(which "$py_cmd")
            echo "  Using $py_cmd at $PYTHON_TO_USE"
            break
        fi
    done
fi

if [ -z "$PYTHON_TO_USE" ]; then
    PYTHON_TO_USE=$(which python3)
    echo "  Falling back to $PYTHON_TO_USE"
fi

# Get the Python version we'll actually use
KERNEL_PY_VERSION=$($PYTHON_TO_USE -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')
echo "  Kernel will use: $PYTHON_TO_USE (Python $KERNEL_PY_VERSION)"

# Find the LLDB Python path - try Swift toolchain first, then system
LLDB_PYTHON_PATH=""

echo "  Searching for valid LLDB Python bindings..."
echo "  Toolchain: $SWIFT_TOOLCHAIN"

# Helper function to validate LLDB module has SBDebugger
# Uses the selected Python interpreter
validate_lldb_path() {
    local path="$1"
    local ld_path="$2"
    LD_LIBRARY_PATH="$ld_path:$LD_LIBRARY_PATH" "$PYTHON_TO_USE" -c "
import sys
sys.path.insert(0, '$path')
import lldb
if hasattr(lldb, 'SBDebugger'):
    debugger = lldb.SBDebugger.Create()
    if debugger:
        lldb.SBDebugger.Destroy(debugger)
        print('valid')
    else:
        print('incomplete-create-failed')
else:
    print('incomplete-no-sbdebugger')
" 2>/dev/null
}

# Helper function to fix Python version mismatch for _lldb native module
# The _lldb.cpython-3XX-x86_64-linux-gnu.so is just a symlink to liblldb.so,
# which is Python-version agnostic. If the toolchain was built with a different
# Python version, we can create a symlink with the correct version suffix.
fix_lldb_python_version() {
    local lldb_dir="$1"
    local target_py_ver="$2"

    # Get architecture
    local arch=$(uname -m)
    local target_suffix="cpython-${target_py_ver//.}-${arch}-linux-gnu.so"
    local target_module="$lldb_dir/_lldb.$target_suffix"

    # Check if target module already exists
    if [ -e "$target_module" ]; then
        return 0
    fi

    # Find existing _lldb.cpython-*.so files
    local existing_module=$(ls "$lldb_dir"/_lldb.cpython-*.so 2>/dev/null | head -1)

    if [ -z "$existing_module" ]; then
        # Check for direct _lldb.so
        if [ -e "$lldb_dir/_lldb.so" ]; then
            ln -sf "_lldb.so" "$target_module" 2>/dev/null && \
                echo "    Created symlink: _lldb.$target_suffix -> _lldb.so" && \
                return 0
        fi
        return 1
    fi

    local existing_basename=$(basename "$existing_module")

    # Check what the existing module points to
    if [ -L "$existing_module" ]; then
        local link_target=$(readlink "$existing_module")
        echo "    Found: $existing_basename -> $link_target"
        # Create symlink with target Python version pointing to same target
        ln -sf "$link_target" "$target_module" 2>/dev/null && \
            echo "    Created symlink: _lldb.$target_suffix -> $link_target" && \
            return 0
    else
        echo "    Found: $existing_basename (not a symlink)"
        # Symlink to the existing file
        ln -sf "$existing_basename" "$target_module" 2>/dev/null && \
            echo "    Created symlink: _lldb.$target_suffix -> $existing_basename" && \
            return 0
    fi

    return 1
}

# Try Swift toolchain's LLDB first (most compatible)
# Swiftly toolchains have lldb under usr/local/lib/pythonX.Y/dist-packages
# Prioritize the kernel Python version

echo "  Searching for valid LLDB Python bindings..."
echo "  Toolchain: $SWIFT_TOOLCHAIN"
echo "  Kernel Python version: $KERNEL_PY_VERSION"
echo "  LD_LIBRARY_PATH: $TOOLCHAIN_LD_PATH"

for py_search_ver in "$KERNEL_PY_VERSION" "$TOOLCHAIN_LLDB_PYTHON" "3.10" "3.11" "3.12" "3.9" "3"; do
    [ -z "$py_search_ver" ] && continue
    for base_path in "$SWIFT_TOOLCHAIN/usr/local/lib" "$SWIFT_TOOLCHAIN/lib" "$SWIFT_TOOLCHAIN/usr/lib"; do
        for sub_path in "python$py_search_ver/dist-packages" "python$py_search_ver/site-packages"; do
            candidate="$base_path/$sub_path"
            if [ -d "$candidate/lldb" ]; then
                echo "  Checking toolchain LLDB: $candidate/lldb"
                result=$(validate_lldb_path "$candidate" "$TOOLCHAIN_LD_PATH")
                if [ "$result" = "valid" ]; then
                    LLDB_PYTHON_PATH="$candidate"
                    echo "  ✓ Valid toolchain LLDB found at: $candidate/lldb"
                    break 3
                else
                    echo "  ✗ LLDB at $candidate/lldb failed validation: $result"
                    # Check if this is a Python version mismatch - try to fix
                    echo "  Checking if Python version mismatch can be fixed..."
                    if fix_lldb_python_version "$candidate/lldb" "$KERNEL_PY_VERSION"; then
                        # Retry validation after fix
                        echo "  Retrying validation after Python version fix..."
                        result=$(validate_lldb_path "$candidate" "$TOOLCHAIN_LD_PATH")
                        if [ "$result" = "valid" ]; then
                            LLDB_PYTHON_PATH="$candidate"
                            echo "  ✓ Valid toolchain LLDB found after version fix: $candidate/lldb"
                            break 3
                        else
                            echo "  ✗ Still failed after version fix: $result"
                        fi
                    fi
                fi
            fi
        done
    done
done

# Fall back to system LLDB (without special LD_LIBRARY_PATH)
if [ -z "$LLDB_PYTHON_PATH" ]; then
    for candidate in "/usr/lib/python3/dist-packages"; do
        if [ -d "$candidate/lldb" ]; then
            echo "  Checking system LLDB: $candidate/lldb"
            result=$(validate_lldb_path "$candidate" "")
            if [ "$result" = "valid" ]; then
                LLDB_PYTHON_PATH="$candidate"
                echo "  ✓ Valid system LLDB found at: $candidate/lldb"
                break
            else
                echo "  ✗ LLDB at $candidate/lldb failed validation: $result"
            fi
        fi
    done
fi

# If still not found, search the toolchain for lldb directories
if [ -z "$LLDB_PYTHON_PATH" ]; then
    echo ""
    print_warning "Could not find complete LLDB Python bindings"
    echo "  Searching for lldb directories in toolchain..."

    for lldb_dir in $(find "$SWIFT_TOOLCHAIN" -type d -name "lldb" 2>/dev/null); do
        if [ -f "$lldb_dir/__init__.py" ]; then
            parent=$(dirname "$lldb_dir")
            echo "    Found Python package: $lldb_dir (parent: $parent)"
            result=$(validate_lldb_path "$parent" "$TOOLCHAIN_LD_PATH")
            if [ "$result" = "valid" ]; then
                LLDB_PYTHON_PATH="$parent"
                print_success "Found working LLDB at: $parent"
                break
            else
                echo "    → Failed validation: $result"
            fi
        fi
    done
fi

if [ -z "$LLDB_PYTHON_PATH" ]; then
    print_warning "Could not find working LLDB, defaulting to /usr/lib/python3/dist-packages"
    print_warning "The kernel may not work correctly!"
    LLDB_PYTHON_PATH="/usr/lib/python3/dist-packages"
else
    print_success "LLDB Python path: $LLDB_PYTHON_PATH"
fi

# Test LLDB import AND debugger creation (this is what the kernel does)
echo "  Testing LLDB import and debugger creation with $PYTHON_TO_USE..."
LLDB_TEST_RESULT=$(LD_LIBRARY_PATH="$TOOLCHAIN_LD_PATH:$LD_LIBRARY_PATH" timeout 30 "$PYTHON_TO_USE" << LLDB_TEST_EOF
import sys
import os
sys.path.insert(0, "$LLDB_PYTHON_PATH")

import lldb
print(f"LLDB module: {getattr(lldb, '__file__', 'unknown')}")

# Check if SBDebugger exists - this is critical
if not hasattr(lldb, 'SBDebugger'):
    print("ERROR: LLDB module is incomplete - missing SBDebugger attribute")
    print("This indicates the LLDB Python bindings are not properly installed")
    sys.exit(1)

print("SBDebugger attribute found")

# Test creating a debugger (this is what hangs if LLDB is misconfigured)
debugger = lldb.SBDebugger.Create()
if debugger:
    print("SBDebugger.Create() succeeded")
    debugger.SetAsync(False)

    # Test creating a target with repl_swift
    # Check both possible locations for repl_swift
    repl_swift = "$SWIFT_TOOLCHAIN/usr/bin/repl_swift"
    if not os.path.exists(repl_swift):
        repl_swift = "$SWIFT_TOOLCHAIN/bin/repl_swift"
    if os.path.exists(repl_swift):
        import platform
        arch = platform.machine()
        target = debugger.CreateTargetWithFileAndArch(repl_swift, arch)
        if target:
            print(f"Target created successfully for {repl_swift}")
        else:
            print(f"WARNING: Could not create target for {repl_swift}")
    else:
        print(f"WARNING: repl_swift not found")

    lldb.SBDebugger.Destroy(debugger)
    print("Debugger destroyed successfully")
else:
    print("ERROR: SBDebugger.Create() returned None")
    sys.exit(1)
LLDB_TEST_EOF
2>&1)

if [ $? -eq 0 ]; then
    print_success "LLDB debugger test passed"
    echo "$LLDB_TEST_RESULT" | while read line; do echo "    $line"; done
else
    print_error "LLDB debugger test FAILED:"
    echo "$LLDB_TEST_RESULT" | head -15
    echo ""
    print_warning "The LLDB Python bindings are incomplete or missing."
    echo "    This is a known issue with system python3-lldb packages."
    echo "    The kernel will NOT work until this is fixed."
    echo ""
    echo "    Possible solutions:"
    echo "    1. Use Swift toolchain's bundled LLDB (if available)"
    echo "    2. Install a different python3-lldb version"
    echo "    3. Build LLDB from source with Python support"
fi

# Step 7: Register the Swift kernel
print_step "Registering Swift Jupyter kernel..."

cd "$INSTALL_DIR"

# Create kernel spec manually for better control
KERNEL_DIR="/usr/local/share/jupyter/kernels/swift"
mkdir -p "$KERNEL_DIR"

# Determine correct bin paths (swiftly uses usr/bin, standard uses bin)
# Find repl_swift - needed for the kernel
if [ -f "$SWIFT_TOOLCHAIN/usr/bin/repl_swift" ]; then
    REPL_SWIFT_PATH="$SWIFT_TOOLCHAIN/usr/bin/repl_swift"
    TOOLCHAIN_BIN="$SWIFT_TOOLCHAIN/usr/bin"
elif [ -f "$SWIFT_TOOLCHAIN/bin/repl_swift" ]; then
    REPL_SWIFT_PATH="$SWIFT_TOOLCHAIN/bin/repl_swift"
    TOOLCHAIN_BIN="$SWIFT_TOOLCHAIN/bin"
else
    print_error "Could not find repl_swift in toolchain"
    REPL_SWIFT_PATH="$SWIFT_TOOLCHAIN/usr/bin/repl_swift"
    TOOLCHAIN_BIN="$SWIFT_TOOLCHAIN/usr/bin"
fi

# Find swift-build and swift-package paths
if [ -f "$TOOLCHAIN_BIN/swift-build" ]; then
    SWIFT_BUILD_PATH="$TOOLCHAIN_BIN/swift-build"
else
    SWIFT_BUILD_PATH="$SWIFT_TOOLCHAIN/usr/bin/swift-build"
fi

if [ -f "$TOOLCHAIN_BIN/swift-package" ]; then
    SWIFT_PACKAGE_PATH="$TOOLCHAIN_BIN/swift-package"
else
    SWIFT_PACKAGE_PATH="$SWIFT_TOOLCHAIN/usr/bin/swift-package"
fi

# Use the comprehensive TOOLCHAIN_LD_PATH we built earlier
# Add system library path as well
LD_LIB_PATH="$TOOLCHAIN_LD_PATH:/usr/lib/x86_64-linux-gnu"

# Create kernel.json with the selected Python interpreter
cat > "$KERNEL_DIR/kernel.json" << EOF
{
  "argv": [
    "$PYTHON_TO_USE",
    "-m", "swift_kernel",
    "-f", "{connection_file}"
  ],
  "display_name": "Swift",
  "language": "swift",
  "env": {
    "PYTHONPATH": "$LLDB_PYTHON_PATH:$INSTALL_DIR",
    "REPL_SWIFT_PATH": "$REPL_SWIFT_PATH",
    "SWIFT_BUILD_PATH": "$SWIFT_BUILD_PATH",
    "SWIFT_PACKAGE_PATH": "$SWIFT_PACKAGE_PATH",
    "PATH": "$TOOLCHAIN_BIN:$PATH",
    "LD_LIBRARY_PATH": "$LD_LIB_PATH",
    "SWIFT_TOOLCHAIN": "$SWIFT_TOOLCHAIN",
    "SWIFT_TOOLCHAIN_ROOT": "$SWIFT_TOOLCHAIN"
  },
  "interrupt_mode": "message"
}
EOF

echo "  Kernel config written to: $KERNEL_DIR/kernel.json"
echo "  Kernel Python: $PYTHON_TO_USE"
echo "  PYTHONPATH: $LLDB_PYTHON_PATH:$INSTALL_DIR"
echo "  Swift toolchain: $SWIFT_TOOLCHAIN"

# Also try using register.py for completeness (might set additional paths)
python3 register.py --sys-prefix --swift-toolchain "$SWIFT_TOOLCHAIN" > /dev/null 2>&1 || true

print_success "Swift kernel registered"

# Step 8: Verify installation
print_step "Verifying installation..."

# Check kernel is registered
if jupyter kernelspec list 2>/dev/null | grep -q swift; then
    print_success "Swift kernel found in Jupyter"
else
    print_error "Swift kernel not found - registration may have failed"
fi

# Test repl_swift binary (already found earlier)
echo "  Checking repl_swift binary..."
if [ -f "$REPL_SWIFT_PATH" ]; then
    print_success "repl_swift found at $REPL_SWIFT_PATH"
    if [ -x "$REPL_SWIFT_PATH" ]; then
        print_success "repl_swift is executable"
    else
        print_warning "repl_swift is not executable"
    fi
else
    print_error "repl_swift NOT found at $REPL_SWIFT_PATH"
    echo "  The kernel will NOT work without repl_swift"
fi

# Test kernel import
echo "  Testing kernel import with $PYTHON_TO_USE..."
if PYTHONPATH="$LLDB_PYTHON_PATH:$INSTALL_DIR" LD_LIBRARY_PATH="$LD_LIB_PATH" "$PYTHON_TO_USE" -c "import swift_kernel; print('Kernel module loaded')" 2>/dev/null; then
    print_success "Kernel import test passed"
else
    print_warning "Kernel import test failed"
fi

# Step 9: Create test notebook
print_step "Creating test notebook..."

cat > /content/swift_test.ipynb << 'EOF'
{
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# Swift Jupyter Kernel Test Notebook\n",
    "\n",
    "This notebook tests the Swift Jupyter kernel installation."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "// Test 1: Basic Swift\n",
    "print(\"Hello from Swift!\")\n",
    "let version = \"Swift in Google Colab\"\n",
    "print(version)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "// Test 2: Variables and types\n",
    "let x = 42\n",
    "let pi = 3.14159\n",
    "let message = \"The answer is \\(x)\"\n",
    "print(message)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "// Test 3: Arrays and functional programming\n",
    "let numbers = [1, 2, 3, 4, 5]\n",
    "let doubled = numbers.map { $0 * 2 }\n",
    "let sum = numbers.reduce(0, +)\n",
    "print(\"Doubled: \\(doubled)\")\n",
    "print(\"Sum: \\(sum)\")"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "// Test 4: Structs\n",
    "struct Point {\n",
    "    var x: Double\n",
    "    var y: Double\n",
    "    \n",
    "    func distance(to other: Point) -> Double {\n",
    "        let dx = x - other.x\n",
    "        let dy = y - other.y\n",
    "        return (dx*dx + dy*dy).squareRoot()\n",
    "    }\n",
    "}\n",
    "\n",
    "let p1 = Point(x: 0, y: 0)\n",
    "let p2 = Point(x: 3, y: 4)\n",
    "print(\"Distance: \\(p1.distance(to: p2))\")"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "// Test 5: Magic commands\n",
    "%swift-version"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## Next Steps\n",
    "\n",
    "To use Python libraries (matplotlib, numpy, pandas) from Swift:\n",
    "\n",
    "1. First cell should install PythonKit:\n",
    "```swift\n",
    "%install '.package(url: \"https://github.com/pvieito/PythonKit\", branch: \"master\")' PythonKit\n",
    "```\n",
    "\n",
    "2. Then import and use:\n",
    "```swift\n",
    "import PythonKit\n",
    "let np = Python.import(\"numpy\")\n",
    "let plt = Python.import(\"matplotlib.pyplot\")\n",
    "```"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Swift",
   "language": "swift",
   "name": "swift"
  },
  "language_info": {
   "name": "swift",
   "version": "6.0"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 4
}
EOF

print_success "Test notebook created at /content/swift_test.ipynb"

# Final summary
echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║                    Installation Complete!                            ║"
echo "╠══════════════════════════════════════════════════════════════════════╣"
echo "║                                                                      ║"
echo "║  Next Steps:                                                         ║"
echo "║                                                                      ║"
echo "║  1. RESTART THE RUNTIME                                              ║"
echo "║     Runtime → Restart runtime                                        ║"
echo "║                                                                      ║"
echo "║  2. Change runtime type to Swift:                                    ║"
echo "║     Runtime → Change runtime type → Swift                            ║"
echo "║                                                                      ║"
echo "║  3. Or open /content/swift_test.ipynb                                ║"
echo "║                                                                      ║"
echo "╠══════════════════════════════════════════════════════════════════════╣"
echo "║  Swift: $SWIFT_VERSION"
echo "║  Kernel: /usr/local/share/jupyter/kernels/swift                      ║"
echo "║  Test notebook: /content/swift_test.ipynb                            ║"
echo "╠══════════════════════════════════════════════════════════════════════╣"
echo "║  Troubleshooting:                                                    ║"
echo "║  If kernel hangs, check: !cat /tmp/swift-kernel.log                  ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""

# Export PATH for the current session
echo "export PATH=\"$HOME/.local/share/swiftly/bin:\$PATH\"" >> ~/.bashrc
echo "export PATH=\"$SWIFT_TOOLCHAIN/bin:\$PATH\"" >> ~/.bashrc

print_success "Installation complete! Please restart the runtime."
