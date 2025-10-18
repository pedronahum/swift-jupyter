#!/bin/bash
#
# Google Colab Swift Cell Magic Installer
#
# This script installs Swift and the swift_colab Python module
# for use with the %%swift cell magic in Google Colab.
#
# Usage in Colab:
#   !curl -s https://raw.githubusercontent.com/pedronahum/swift-jupyter/main/install_swift_colab_magic.sh | bash
#
# This approach uses cell magic (%%swift) instead of kernel registration,
# which is simpler and more reliable for Google Colab.
#

# ---
# Safety and Setup
# ---
set -Eeuo pipefail
trap 'echo "❌ Failed at line $LINENO. Last command was: $BASH_COMMAND"' ERR

export DEBIAN_FRONTEND=noninteractive
INSTALL_DIR="/content/swift-jupyter"

echo "=============================================="
echo "Swift Cell Magic Installer for Google Colab"
echo "=============================================="
echo ""
echo "This installer sets up the %%swift cell magic"
echo "for running Swift code in Python notebooks."
echo ""

# ---
# Environment Validation
# ---
if [ -d "/content" ] || [ -n "${COLAB_GPU:-}" ]; then
    echo "✅ Google Colab environment detected"
else
    echo "⚠️  Warning: This script is optimized for Google Colab"
    echo "   It may work in other environments, but is not tested."
    read -p "   Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "System: $(uname -s) $(uname -r) $(uname -m)"
echo "Python: $(python3 --version)"
echo ""

# ---
# Step 1: Install System Dependencies (LLDB)
# ---
echo "=============================================="
echo "Step 1: Installing System Dependencies"
echo "=============================================="
echo ""

echo "Updating package lists..."
apt-get update -qq

echo "🔍 Finding best LLDB package..."
# Find the best available python3-lldb package
DEFAULT_LLDB=$(apt-cache show python3-lldb 2>/dev/null | grep "^Depends:" | grep -oP "python3-lldb-\K[0-9]+" | head -1)

if [ -n "$DEFAULT_LLDB" ]; then
    LLDB_PACKAGE="python3-lldb-${DEFAULT_LLDB}"
    echo "→ Using system default: $LLDB_PACKAGE"
else
    # Fallback: try versions from newest to oldest
    LLDB_PACKAGE=""
    for ver in 18 17 16 15 14 13; do
        if apt-cache show python3-lldb-$ver &>/dev/null; then
            LLDB_PACKAGE="python3-lldb-$ver"
            echo "→ Using available version: $LLDB_PACKAGE"
            break
        fi
    done
fi

if [ -z "$LLDB_PACKAGE" ]; then
    echo "❌ Error: Could not find any python3-lldb packages"
    exit 1
fi

echo "Installing dependencies..."
apt-get install -y -qq \
    libpython3-dev \
    libncurses5-dev \
    libncurses5 \
    libtinfo5 \
    pkg-config \
    $LLDB_PACKAGE

echo "✅ System dependencies installed"
echo ""

# Verify LLDB installation
echo "🔍 Verifying LLDB installation..."
PY_LLDB_DIR=$(python3 -c 'import lldb, os; print(os.path.dirname(lldb.__file__))' 2>/dev/null || echo "")

if [ -z "$PY_LLDB_DIR" ]; then
    echo "❌ Error: Could not import 'lldb' module after installation"
    echo "   This is unexpected. The $LLDB_PACKAGE installation may have failed."
    exit 1
fi

# Find the system LLDB library path
SYSTEM_LLDB_LIB_PATH=$(dirname $(dirname "$PY_LLDB_DIR"))

echo "✅ LLDB Python module: $PY_LLDB_DIR"
echo "✅ LLDB library path: $SYSTEM_LLDB_LIB_PATH"
echo ""

# ---
# Step 2: Install Swiftly and Swift Toolchain
# ---
echo "=============================================="
echo "Step 2: Installing Swift Toolchain"
echo "=============================================="
echo ""

# Install Swiftly if not present
if ! command -v swiftly &> /dev/null; then
    echo "Installing Swiftly (Swift toolchain manager)..."
    ARCH=$(uname -m)
    curl -fsSL "https://download.swift.org/swiftly/linux/swiftly-${ARCH}.tar.gz" -o swiftly.tar.gz
    tar -xzf swiftly.tar.gz
    install -Dm755 ./swiftly /usr/local/bin/swiftly
    rm -f swiftly.tar.gz swiftly
    echo "✅ Swiftly installed"
else
    echo "✅ Swiftly already installed"
fi

# Set Swift version (allow override via environment variable)
SWIFT_VERSION="${SWIFT_CHANNEL:-main-snapshot}"
echo "Installing Swift '$SWIFT_VERSION'..."

# Initialize Swiftly and install Swift
swiftly init -y --quiet-shell-followup
swiftly install -y --use "$SWIFT_VERSION"

echo "✅ Swift '$SWIFT_VERSION' installed"
echo ""

# ---
# Step 3: Detect Swift Toolchain Paths
# ---
echo "🔍 Detecting Swift toolchain paths..."

# Source Swiftly environment
. "$HOME/.local/share/swiftly/env.sh"
hash -r

if ! command -v swift &> /dev/null; then
    echo "❌ Error: 'swift' command not found after installation"
    exit 1
fi

# Get Swift binary path
SWIFT_DRIVER_EXE_PATH=$(which swift)

# Resolve symlinks to find the actual toolchain
SWIFT_DRIVER_EXE_PATH_REAL=$(readlink -f "$SWIFT_DRIVER_EXE_PATH")

# Extract toolchain directory: .../toolchains/<version>/usr/bin/swift -> .../toolchains/<version>
SWIFT_USR_BIN=$(dirname "$SWIFT_DRIVER_EXE_PATH_REAL")
SWIFT_USR=$(dirname "$SWIFT_USR_BIN")
SWIFT_TOOLCHAIN_DIR=$(dirname "$SWIFT_USR")

# Verify toolchain structure
if [ ! -d "$SWIFT_TOOLCHAIN_DIR/usr/lib/swift/linux" ]; then
    echo "❌ Error: Invalid toolchain structure at $SWIFT_TOOLCHAIN_DIR"
    exit 1
fi

SWIFT_LIB_PATH="$SWIFT_TOOLCHAIN_DIR/usr/lib/swift/linux"

echo "✅ Swift driver: $SWIFT_DRIVER_EXE_PATH_REAL"
echo "✅ Swift toolchain: $SWIFT_TOOLCHAIN_DIR"
echo "✅ Swift libraries: $SWIFT_LIB_PATH"
echo ""

swift --version
echo ""

# ---
# Step 4: Install swift_colab Python Module
# ---
echo "=============================================="
echo "Step 3: Installing swift_colab Module"
echo "=============================================="
echo ""

# Remove existing installation
if [ -d "$INSTALL_DIR" ]; then
    echo "Removing existing installation..."
    rm -rf "$INSTALL_DIR"
fi

echo "Cloning swift-jupyter repository..."
git clone -q https://github.com/pedronahum/swift-jupyter.git "$INSTALL_DIR"

echo "Installing swift_colab Python module..."
python3 -m pip install -q -e "$INSTALL_DIR"

SWIFT_PYTHON_DRIVER_PATH="$INSTALL_DIR/swift_colab/swift_python_driver.py"

echo "✅ swift_colab module installed"
echo ""

# ---
# Step 5: Create Setup Script
# ---
echo "=============================================="
echo "Step 4: Creating Activation Script"
echo "=============================================="
echo ""

SETUP_SCRIPT="/content/setup_swift_magic.py"

cat > "$SETUP_SCRIPT" << EOF
"""
Swift Cell Magic Setup for Google Colab

Run this cell to activate the %%swift cell magic.
After running this, you can use %%swift in any cell to run Swift code.
"""

import os

# Set environment variables for Swift toolchain
os.environ['SWIFT_TOOLCHAIN_PATH'] = "$SWIFT_TOOLCHAIN_DIR"
os.environ['SWIFT_DRIVER_EXE_PATH'] = "$SWIFT_DRIVER_EXE_PATH_REAL"
os.environ['SWIFT_PYTHON_DRIVER_PATH'] = "$SWIFT_PYTHON_DRIVER_PATH"
os.environ['LD_LIBRARY_PATH'] = "$SYSTEM_LLDB_LIB_PATH:$SWIFT_LIB_PATH"
os.environ['PYTHONPATH'] = "$PY_LLDB_DIR"

# Load the swift_colab extension
get_ipython().run_line_magic('load_ext', 'swift_colab')

print("✅ Swift cell magic activated!")
print("")
print("You can now use %%swift in any cell to run Swift code.")
print("")
print("Example:")
print("  %%swift")
print('  print("Hello from Swift!")')
EOF

echo "✅ Setup script created at: $SETUP_SCRIPT"
echo ""

# ---
# Final Instructions
# ---
echo "=============================================="
echo "✅ Installation Complete!"
echo "=============================================="
echo ""
echo "To activate Swift in your notebook, run this in a Python cell:"
echo ""
echo "┌────────────────────────────────────────────┐"
echo "│ %run /content/setup_swift_magic.py         │"
echo "└────────────────────────────────────────────┘"
echo ""
echo "Or manually run:"
echo ""
echo "┌────────────────────────────────────────────────────────────┐"
echo "│ import os                                                  │"
echo "│ os.environ['SWIFT_TOOLCHAIN_PATH'] = '$SWIFT_TOOLCHAIN_DIR' │"
echo "│ os.environ['SWIFT_DRIVER_EXE_PATH'] = '$SWIFT_DRIVER_EXE_PATH_REAL' │"
echo "│ os.environ['SWIFT_PYTHON_DRIVER_PATH'] = '$SWIFT_PYTHON_DRIVER_PATH' │"
echo "│ os.environ['LD_LIBRARY_PATH'] = '$SYSTEM_LLDB_LIB_PATH:$SWIFT_LIB_PATH' │"
echo "│ os.environ['PYTHONPATH'] = '$PY_LLDB_DIR'  │"
echo "│ %load_ext swift_colab                                      │"
echo "└────────────────────────────────────────────────────────────┘"
echo ""
echo "After activation, use %%swift in cells to run Swift code:"
echo ""
echo "┌────────────────────────────────────────────┐"
echo "│ %%swift                                    │"
echo '│ print("Hello from Swift!")                │'
echo "│ print(\"Swift version \\(#swiftVersion)\")   │"
echo "└────────────────────────────────────────────┘"
echo ""
echo "Happy coding! 🚀"
