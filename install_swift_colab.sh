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

# First, find what LLDB packages are available
echo "🔍 Checking available LLDB packages..."
AVAILABLE_LLDB=$(apt-cache search python3-lldb | grep -E "^python3-lldb-[0-9]+" | head -5)
echo "$AVAILABLE_LLDB"

# Try to determine the best LLDB version to install
# Check what python3-lldb recommends
DEFAULT_LLDB=$(apt-cache show python3-lldb 2>/dev/null | grep "^Depends:" | grep -oP "python3-lldb-\K[0-9]+" | head -1)

if [ -n "$DEFAULT_LLDB" ]; then
    LLDB_PACKAGE="python3-lldb-${DEFAULT_LLDB}"
    echo "→ Installing LLDB package: $LLDB_PACKAGE (system default)"
else
    # Fallback: try versions from newest to oldest
    for ver in 18 17 16 15 14 13; do
        if apt-cache show python3-lldb-$ver &>/dev/null; then
            LLDB_PACKAGE="python3-lldb-$ver"
            echo "→ Installing LLDB package: $LLDB_PACKAGE"
            break
        fi
    done
    if [ -z "$LLDB_PACKAGE" ]; then
        echo "⚠️  Warning: No versioned python3-lldb found, trying python3-lldb..."
        LLDB_PACKAGE="python3-lldb"
    fi
fi

apt-get install -y -qq \
    libpython3-dev \
    libncurses5-dev \
    libncurses5 \
    libtinfo5 \
    libz3-dev \
    pkg-config \
    $LLDB_PACKAGE \
    > /dev/null 2>&1

echo "✅ System dependencies installed"

# Verify LLDB was installed
echo ""
echo "🔍 Verifying LLDB installation..."
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')")
echo "Python version: $PYTHON_VERSION"

# Check for LLDB Python module in common locations
LLDB_LOCATIONS=(
    "/usr/lib/python3/dist-packages/lldb"
    "/usr/lib/python${PYTHON_VERSION}/dist-packages/lldb"
    "/usr/lib/llvm-13/lib/python${PYTHON_VERSION}/dist-packages/lldb"
    "/usr/lib/llvm-14/lib/python${PYTHON_VERSION}/dist-packages/lldb"
    "/usr/lib/llvm-15/lib/python${PYTHON_VERSION}/dist-packages/lldb"
    "/usr/lib/llvm-16/lib/python${PYTHON_VERSION}/dist-packages/lldb"
    "/usr/lib/llvm-17/lib/python${PYTHON_VERSION}/dist-packages/lldb"
    "/usr/lib/llvm-18/lib/python${PYTHON_VERSION}/dist-packages/lldb"
)

LLDB_FOUND=""
for loc in "${LLDB_LOCATIONS[@]}"; do
    if [ -d "$loc" ]; then
        echo "✅ LLDB Python module found at: $loc"
        LLDB_FOUND="$loc"
        break
    fi
done

if [ -z "$LLDB_FOUND" ]; then
    echo "❌ Warning: LLDB Python module not found in any expected location!"
    echo "   Checked:"
    for loc in "${LLDB_LOCATIONS[@]}"; do
        echo "   - $loc"
    done
    echo "   Registration may fail, but will attempt anyway..."
fi
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
git clone -q https://github.com/pedronahum/swift-jupyter.git "$INSTALL_DIR"
cd "$INSTALL_DIR"

echo "✅ Repository cloned to: $INSTALL_DIR"
echo ""

# Apply Swiftly LLDB support patch
echo "🔧 Applying Swiftly LLDB compatibility patches..."
python3 << 'PYTHON_PATCH'
import os
import sys

register_py = '/content/swift-jupyter/register.py'

# Check if file exists
if not os.path.exists(register_py):
    print(f'  ⚠️  {register_py} not found, skipping patches')
    sys.exit(0)

with open(register_py, 'r') as f:
    lines = f.readlines()

# Find linux_pythonpath function and check if already patched
already_patched = any('System-installed lldb (for Swiftly' in line for line in lines)

if already_patched:
    print('  ℹ️  register.py already has Swiftly support, skipping')
    sys.exit(0)

# Find the function and replace it
in_function = False
function_start = -1
function_end = -1

for i, line in enumerate(lines):
    if 'def linux_pythonpath(root):' in line:
        in_function = True
        function_start = i
    elif in_function and line.strip() and not line.startswith(' ') and not line.startswith('\t'):
        function_end = i
        break

if function_start == -1:
    print('  ⚠️  Could not find linux_pythonpath function')
    sys.exit(1)

# Create the new function
new_function = '''def linux_pythonpath(root):
    """Find LLDB Python bindings path for Linux - with Swiftly support."""
    import os
    # Try toolchain locations first
    version_specific = '%s/lib/python%d.%d/site-packages' % (root, sys.version_info[0], sys.version_info[1])
    if os.path.isdir(version_specific) and os.path.isdir(os.path.join(version_specific, 'lldb')):
        return version_specific

    generic_dist = '%s/lib/python%s/dist-packages' % (root, sys.version_info[0])
    if os.path.isdir(generic_dist) and os.path.isdir(os.path.join(generic_dist, 'lldb')):
        return generic_dist

    # System LLDB (for Swiftly toolchains)
    print(f'  🔍 Toolchain LLDB not found, checking system locations...')
    system_paths = [
        '/usr/lib/python3/dist-packages',
        '/usr/lib/python%d/dist-packages' % sys.version_info[0],
        '/usr/lib/python%d.%d/dist-packages' % (sys.version_info[0], sys.version_info[1]),
    ]
    # Add LLVM-versioned paths
    for ver in range(11, 19):
        system_paths.append('/usr/lib/llvm-%d/lib/python%d.%d/dist-packages' % (ver, sys.version_info[0], sys.version_info[1]))

    for path in system_paths:
        if os.path.isdir(path) and os.path.isdir(os.path.join(path, 'lldb')):
            print(f'  ✅ Using system LLDB at {path}')
            return path

    print(f'  ❌ No LLDB found, falling back to {generic_dist}')
    return generic_dist

'''

# Replace the function
new_lines = lines[:function_start] + [new_function] + lines[function_end:]

# Write back
with open(register_py, 'w') as f:
    f.writelines(new_lines)

print('  ✅ Patched linux_pythonpath to support system LLDB')
PYTHON_PATCH

echo "✅ Patches applied"
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
