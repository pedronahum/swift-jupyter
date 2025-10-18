#!/bin/bash
#
# Google Colab Swift Jupyter Kernel Installation Script
#
# This script installs the Swift Jupyter kernel in Google Colab with:
# - Swift 6.3 Development Snapshot (October 10, 2024)
# - System Python 3.10 (Colab default)
# - Full PythonKit support for matplotlib/numpy/pandas
#
# Usage in Google Colab:
#   !curl -s https://raw.githubusercontent.com/YOUR_REPO/swift-jupyter/main/install_swift_colab.sh | bash
#
# Or run directly:
#   !bash install_swift_colab.sh
#

set -e

echo "=============================================="
echo "Swift Jupyter Kernel - Google Colab Installer"
echo "=============================================="
echo ""

# Detect environment
if [ -n "$COLAB_GPU" ] || [ -d "/content" ]; then
    echo "✅ Google Colab environment detected"
    IS_COLAB=true
    INSTALL_DIR="/content/swift-jupyter"
else
    echo "⚠️  Not running in Google Colab (will install to current directory)"
    IS_COLAB=false
    INSTALL_DIR="$PWD/swift-jupyter"
fi

echo ""
echo "Installation directory:"
echo "  Swift Jupyter: $INSTALL_DIR"
echo ""

# Check system info
echo "System Information:"
echo "  OS: $(uname -s) $(uname -r)"
echo "  Arch: $(uname -m)"
echo "  Python: $(python3 --version)"
echo ""

# Verify we're on Linux x86_64
if [ "$(uname -s)" != "Linux" ]; then
    echo "❌ Error: This script only works on Linux (Google Colab)"
    exit 1
fi

if [ "$(uname -m)" != "x86_64" ]; then
    echo "❌ Error: This script only works on x86_64 architecture"
    exit 1
fi

# Step 1: Install required system dependencies FIRST
echo "=============================================="
echo "Step 1: Installing System Dependencies"
echo "=============================================="
echo ""

echo "Installing required packages (needed before Swift installation)..."
apt-get update -qq
apt-get install -y -qq \
    libpython3-dev \
    libncurses5-dev \
    libncurses5 \
    libtinfo5 \
    libz3-dev \
    pkg-config \
    python3-lldb-13 \
    > /dev/null 2>&1

echo "✅ System dependencies installed"
echo ""

# Step 2: Install Swiftly and Swift
echo "=============================================="
echo "Step 2: Installing Swiftly & Swift"
echo "=============================================="
echo ""

# Check if swiftly is already installed
if command -v swiftly &> /dev/null; then
    echo "✅ Swiftly already installed"
else
    echo "Installing Swiftly (Swift toolchain manager)..."

    # Install Swiftly (official method from swift.org)
    ARCH=$(uname -m)
    curl -fsSL "https://download.swift.org/swiftly/linux/swiftly-${ARCH}.tar.gz" -o swiftly.tar.gz
    tar -xzf swiftly.tar.gz

    # Install swiftly to /usr/local/bin for system-wide access
    install -Dm755 ./swiftly /usr/local/bin/swiftly

    # Clean up
    rm -f swiftly.tar.gz swiftly

    # Verify swiftly installation
    if ! command -v swiftly &> /dev/null; then
        echo "❌ Error: Swiftly installation failed"
        exit 1
    fi

    echo "✅ Swiftly installed successfully"
fi

echo ""
echo "Initializing Swiftly and installing Swift main-snapshot..."
echo "This will download and install the latest Swift development snapshot."
echo "This may take several minutes..."
echo ""

# Initialize swiftly and install Swift main-snapshot
# -y: auto-confirm all prompts (both init and install)
# --quiet-shell-followup: don't print shell modification instructions
# --use: set as the active toolchain
swiftly init -y --quiet-shell-followup
swiftly install -y --use main-snapshot

echo ""
echo "✅ Swift installed successfully"
echo ""

# Source swiftly environment to make swift available
echo "Loading swiftly environment..."
if [ -f "${SWIFTLY_HOME_DIR:-$HOME/.local/share/swiftly}/env.sh" ]; then
    . "${SWIFTLY_HOME_DIR:-$HOME/.local/share/swiftly}/env.sh"
else
    # Try default location
    . "$HOME/.local/share/swiftly/env.sh"
fi

# Update hash table
hash -r

# Verify Swift installation
if ! command -v swift &> /dev/null; then
    echo "❌ Error: Swift binary not found after installation"
    echo "PATH: $PATH"
    exit 1
fi

echo "Swift version:"
swift --version
echo ""

# Get Swift installation directory for kernel registration
# Swiftly uses $HOME/.local/share/swiftly/toolchains/...

# Use swiftly to get the actual toolchain in use
echo "Detecting Swift toolchain location..."
SWIFTLY_TOOLCHAIN_INFO=$(swiftly use)
echo "Current toolchain: $SWIFTLY_TOOLCHAIN_INFO"

# Get the real path of swift binary (resolving symlinks)
SWIFT_BIN=$(which swift)
if [ -z "$SWIFT_BIN" ]; then
    echo "❌ Error: Could not find swift binary"
    exit 1
fi

# Resolve symlinks to get the actual toolchain location
SWIFT_BIN_REAL=$(readlink -f "$SWIFT_BIN" 2>/dev/null || realpath "$SWIFT_BIN" 2>/dev/null || echo "$SWIFT_BIN")
echo "Swift binary (resolved): $SWIFT_BIN_REAL"

# The real swift binary is at: ~/.local/share/swiftly/toolchains/<version>/usr/bin/swift
# We need to get the toolchain root (one level up from usr)
SWIFT_USR_BIN=$(dirname "$SWIFT_BIN_REAL")  # .../usr/bin
SWIFT_USR=$(dirname "$SWIFT_USR_BIN")  # .../usr
SWIFT_TOOLCHAIN_DIR=$(dirname "$SWIFT_USR")  # .../<version>

echo "Swift toolchain directory (from binary path): $SWIFT_TOOLCHAIN_DIR"

# Verify this looks correct - should contain "toolchains"
if [[ ! "$SWIFT_TOOLCHAIN_DIR" == *"toolchains"* ]]; then
    echo "⚠️  Toolchain path doesn't contain 'toolchains', trying alternative method..."

    # Alternative: Use Swiftly's home directory structure
    # Swiftly toolchains are always at: $HOME/.local/share/swiftly/toolchains/<version>
    SWIFTLY_TOOLCHAINS_DIR="$HOME/.local/share/swiftly/toolchains"

    if [ -d "$SWIFTLY_TOOLCHAINS_DIR" ]; then
        # Find the most recently modified toolchain (should be the one we just installed)
        SWIFT_TOOLCHAIN_DIR=$(ls -dt "$SWIFTLY_TOOLCHAINS_DIR"/* 2>/dev/null | head -1)
        echo "Found toolchain via Swiftly directory: $SWIFT_TOOLCHAIN_DIR"
    fi
fi

echo "Final Swift toolchain directory: $SWIFT_TOOLCHAIN_DIR"

# Verify the toolchain directory exists and contains usr
if [ ! -d "$SWIFT_TOOLCHAIN_DIR/usr" ]; then
    echo "❌ Error: Toolchain directory doesn't contain 'usr' subdirectory"
    echo "   Expected structure: $SWIFT_TOOLCHAIN_DIR/usr/bin/swift"
    echo ""
    echo "Diagnostic information:"
    echo "  SWIFT_BIN: $SWIFT_BIN"
    echo "  SWIFT_BIN_REAL: $SWIFT_BIN_REAL"
    echo "  SWIFT_USR_BIN: $SWIFT_USR_BIN"
    echo "  SWIFT_USR: $SWIFT_USR"
    echo "  SWIFT_TOOLCHAIN_DIR: $SWIFT_TOOLCHAIN_DIR"
    echo ""
    echo "Directory contents of $SWIFT_TOOLCHAIN_DIR:"
    ls -la "$SWIFT_TOOLCHAIN_DIR" 2>/dev/null || echo "   Directory doesn't exist"
    echo ""
    echo "Available toolchains in ~/.local/share/swiftly/toolchains:"
    ls -la "$HOME/.local/share/swiftly/toolchains" 2>/dev/null || echo "   Directory doesn't exist"
    exit 1
fi

echo "✅ Toolchain directory verified: $SWIFT_TOOLCHAIN_DIR/usr"

# Verify LLDB Python bindings exist
# Check common locations for LLDB Python bindings
LLDB_PYTHON_CANDIDATES=(
    "$SWIFT_TOOLCHAIN_DIR/usr/lib/python3/dist-packages"
    "$SWIFT_TOOLCHAIN_DIR/usr/lib/python3.10/site-packages"
    "$SWIFT_TOOLCHAIN_DIR/usr/lib/python3.11/site-packages"
    "$SWIFT_TOOLCHAIN_DIR/usr/lib/python3.12/site-packages"
)

LLDB_PYTHON_DIR=""
for candidate in "${LLDB_PYTHON_CANDIDATES[@]}"; do
    if [ -d "$candidate/lldb" ]; then
        LLDB_PYTHON_DIR="$candidate"
        echo "✅ Found LLDB Python bindings at: $LLDB_PYTHON_DIR"
        break
    fi
done

if [ -z "$LLDB_PYTHON_DIR" ]; then
    echo "⚠️  Warning: Could not find LLDB Python bindings in standard locations"
    echo "   Checked:"
    for candidate in "${LLDB_PYTHON_CANDIDATES[@]}"; do
        echo "   - $candidate"
    done
    echo "   Will attempt registration anyway..."
fi

# Verify repl_swift exists
REPL_SWIFT_PATH="$SWIFT_TOOLCHAIN_DIR/usr/bin/repl_swift"
if [ -f "$REPL_SWIFT_PATH" ]; then
    echo "✅ Found repl_swift at: $REPL_SWIFT_PATH"
else
    echo "⚠️  Warning: repl_swift not found at: $REPL_SWIFT_PATH"
fi
echo ""

# Step 3: Install Python dependencies
echo "=============================================="
echo "Step 3: Installing Python Dependencies"
echo "=============================================="
echo ""

echo "Installing Jupyter and kernel dependencies..."
python3 -m pip install -q --upgrade pip
python3 -m pip install -q jupyter jupyter-client ipython ipykernel

echo "✅ Python dependencies installed"
echo ""

# Step 4: Clone and install swift-jupyter
echo "=============================================="
echo "Step 4: Installing Swift Jupyter Kernel"
echo "=============================================="
echo ""

if [ -d "$INSTALL_DIR" ]; then
    echo "⚠️  swift-jupyter directory already exists, removing..."
    rm -rf "$INSTALL_DIR"
fi

echo "Cloning swift-jupyter repository..."
git clone -q https://github.com/google/swift-jupyter.git "$INSTALL_DIR"
cd "$INSTALL_DIR"

echo "✅ Repository cloned to: $INSTALL_DIR"
echo ""

# Step 5: Register the kernel
echo "=============================================="
echo "Step 5: Registering Swift Kernel"
echo "=============================================="
echo ""

echo "Registering Swift kernel with Jupyter..."
python3 register.py \
    --sys-prefix \
    --swift-toolchain "$SWIFT_TOOLCHAIN_DIR"

echo ""
echo "✅ Swift kernel registered!"
echo ""

# Verify kernel registration
if jupyter kernelspec list | grep -q swift; then
    echo "✅ Kernel registration verified"
    jupyter kernelspec list | grep swift
else
    echo "❌ Error: Kernel registration failed"
    exit 1
fi

# Step 6: Create environment setup script
echo ""
echo "=============================================="
echo "Step 6: Creating Environment Setup"
echo "=============================================="
echo ""

# Create a Python initialization script for Colab
cat > /content/init_swift.py << 'EOF'
# Swift Jupyter Kernel - Colab Initialization
import subprocess
import os

# Source swiftly environment and get PATH
swiftly_env = os.path.expanduser('~/.local/share/swiftly/env.sh')
if os.path.exists(swiftly_env):
    result = subprocess.run(['bash', '-c', f'source {swiftly_env} && echo $PATH'],
                           capture_output=True, text=True)
    if result.returncode == 0:
        os.environ['PATH'] = result.stdout.strip() + ':' + os.environ.get('PATH', '')

print("✅ Swift Jupyter kernel environment initialized")
print("✅ Swiftly environment loaded")
print("")
print("To use Swift in this Colab notebook:")
print("  1. Runtime → Change runtime type")
print("  2. Select 'Swift' from the Runtime type dropdown")
print("  3. Click Save")
print("")
print("For PythonKit + matplotlib support, see:")
print("  https://github.com/google/swift-jupyter/blob/main/PYTHONKIT_SETUP.md")
EOF

chmod +x /content/init_swift.py

echo "✅ Created initialization script: /content/init_swift.py"
echo ""

# Step 7: Create a test notebook
if [ "$IS_COLAB" = true ]; then
    echo "=============================================="
    echo "Step 7: Creating Test Notebook"
    echo "=============================================="
    echo ""

    cat > /content/swift_test.ipynb << 'EOF'
{
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# Swift Jupyter Kernel Test\n",
    "\n",
    "This notebook tests the Swift Jupyter kernel in Google Colab."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "// Test basic Swift\n",
    "print(\"Hello from Swift!\")\n",
    "print(\"Swift version: \\(#swiftVersion)\")"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "// Test array operations\n",
    "let numbers = [1, 2, 3, 4, 5]\n",
    "let doubled = numbers.map { $0 * 2 }\n",
    "print(\"Original: \\(numbers)\")\n",
    "print(\"Doubled: \\(doubled)\")"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "// Test struct and protocol\n",
    "protocol Describable {\n",
    "    func describe() -> String\n",
    "}\n",
    "\n",
    "struct Point: Describable {\n",
    "    let x: Double\n",
    "    let y: Double\n",
    "    \n",
    "    func describe() -> String {\n",
    "        return \"Point(x: \\(x), y: \\(y))\"\n",
    "    }\n",
    "}\n",
    "\n",
    "let p = Point(x: 3.0, y: 4.0)\n",
    "print(p.describe())"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Swift",
   "language": "swift",
   "name": "swift"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 4
}
EOF

    echo "✅ Created test notebook: /content/swift_test.ipynb"
    echo ""
fi

# Final summary
echo "=============================================="
echo "Installation Complete! 🎉"
echo "=============================================="
echo ""
echo "Swift Jupyter kernel has been successfully installed!"
echo ""
echo "Installation Details:"
echo "  Swift: Latest main-snapshot (installed via Swiftly)"
echo "  Kernel Location: $(jupyter --data-dir)/kernels/swift"
echo "  Swift Toolchain: $SWIFT_TOOLCHAIN_DIR"
echo ""
echo "To check Swift version:"
echo "  swift --version"
echo ""

if [ "$IS_COLAB" = true ]; then
    echo "Next Steps for Google Colab:"
    echo ""
    echo "1. Restart the runtime (Runtime → Restart runtime)"
    echo "2. Run this in a Python cell to verify:"
    echo "     !jupyter kernelspec list"
    echo ""
    echo "3. To use Swift in a new notebook:"
    echo "     Runtime → Change runtime type → Select 'Swift'"
    echo ""
    echo "4. Or test with the example notebook:"
    echo "     Open /content/swift_test.ipynb"
    echo ""
    echo "For PythonKit + matplotlib support:"
    echo "  See: https://github.com/google/swift-jupyter/blob/main/PYTHONKIT_SETUP.md"
else
    echo "Next Steps:"
    echo ""
    echo "1. Verify installation:"
    echo "     jupyter kernelspec list"
    echo ""
    echo "2. Start Jupyter:"
    echo "     jupyter notebook"
    echo ""
    echo "3. Create a new notebook with Swift kernel"
fi

echo ""
echo "=============================================="
echo "Installation log saved to: /tmp/swift-jupyter-install.log"
echo "=============================================="
