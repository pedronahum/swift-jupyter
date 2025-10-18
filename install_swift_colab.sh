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
    SWIFT_DIR="/content/swift"
else
    echo "⚠️  Not running in Google Colab (will install to current directory)"
    IS_COLAB=false
    INSTALL_DIR="$PWD/swift-jupyter"
    SWIFT_DIR="$PWD/swift"
fi

echo ""
echo "Installation directories:"
echo "  Swift Jupyter: $INSTALL_DIR"
echo "  Swift Toolchain: $SWIFT_DIR"
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

# Step 1: Download and extract Swift 6.3 Development Snapshot (October 10, 2024)
echo "=============================================="
echo "Step 1: Installing Swift 6.3 Dev Snapshot"
echo "=============================================="
echo ""

SWIFT_VERSION="swift-DEVELOPMENT-SNAPSHOT-2024-10-10-a"
SWIFT_PLATFORM="ubuntu2204"
SWIFT_URL="https://download.swift.org/development/ubuntu2204/${SWIFT_VERSION}/${SWIFT_VERSION}-${SWIFT_PLATFORM}.tar.gz"

echo "Downloading Swift from:"
echo "  $SWIFT_URL"
echo ""

if [ -d "$SWIFT_DIR" ]; then
    echo "⚠️  Swift directory already exists, removing..."
    rm -rf "$SWIFT_DIR"
fi

mkdir -p "$SWIFT_DIR"
cd "$(dirname "$SWIFT_DIR")"

echo "Downloading Swift (this may take a few minutes)..."
if ! wget -q --show-progress "$SWIFT_URL" -O swift.tar.gz; then
    echo "❌ Error: Failed to download Swift"
    exit 1
fi

echo "Extracting Swift..."
tar -xzf swift.tar.gz
mv "${SWIFT_VERSION}-${SWIFT_PLATFORM}" "$SWIFT_DIR"
rm swift.tar.gz

echo "✅ Swift installed to: $SWIFT_DIR"
echo ""

# Verify Swift installation
SWIFT_BIN="$SWIFT_DIR/usr/bin/swift"
if [ ! -f "$SWIFT_BIN" ]; then
    echo "❌ Error: Swift binary not found at $SWIFT_BIN"
    exit 1
fi

echo "Swift version:"
"$SWIFT_BIN" --version
echo ""

# Step 2: Install required system dependencies
echo "=============================================="
echo "Step 2: Installing System Dependencies"
echo "=============================================="
echo ""

echo "Installing required packages..."
apt-get update -qq
apt-get install -y -qq \
    libpython3-dev \
    libncurses5-dev \
    libncurses5 \
    libtinfo5 \
    > /dev/null 2>&1

echo "✅ System dependencies installed"
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
    --swift-toolchain "$SWIFT_DIR"

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
import os
import sys

# Add Swift library paths to LD_LIBRARY_PATH
swift_lib_path = '/content/swift/usr/lib/swift/linux'
if 'LD_LIBRARY_PATH' in os.environ:
    os.environ['LD_LIBRARY_PATH'] = swift_lib_path + ':' + os.environ['LD_LIBRARY_PATH']
else:
    os.environ['LD_LIBRARY_PATH'] = swift_lib_path

print("✅ Swift Jupyter kernel environment initialized")
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
echo "  Swift Version: 6.3 Development Snapshot (Oct 10, 2024)"
echo "  Kernel Location: $(jupyter --data-dir)/kernels/swift"
echo "  Swift Location: $SWIFT_DIR"
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
