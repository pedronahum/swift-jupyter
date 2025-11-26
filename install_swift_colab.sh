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

# Install required packages
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
    > /dev/null 2>&1

# Try to install python3-lldb for different LLVM versions
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

# Get toolchain path
SWIFT_TOOLCHAIN=$(dirname $(dirname $(which swift)))

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

# Step 6: Find LLDB Python bindings
print_step "Configuring LLDB Python bindings..."

# Get Python version
PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')

# Find the LLDB Python path - try Swift toolchain first, then system
LLDB_PYTHON_PATH=""

# Try Swift toolchain's LLDB first (most compatible)
for candidate in "$SWIFT_TOOLCHAIN/lib/python$PY_VERSION/site-packages" \
                 "$SWIFT_TOOLCHAIN/lib/python3/dist-packages"; do
    if [ -d "$candidate/lldb" ]; then
        LLDB_PYTHON_PATH="$candidate"
        echo "  Found Swift toolchain LLDB at: $candidate/lldb"
        break
    fi
done

# Fall back to system LLDB
if [ -z "$LLDB_PYTHON_PATH" ]; then
    for version in 18 17 16 15 14; do
        candidate="/usr/lib/python3/dist-packages"
        if [ -d "$candidate/lldb" ]; then
            LLDB_PYTHON_PATH="$candidate"
            echo "  Found system LLDB at: $candidate/lldb"
            break
        fi
        candidate="/usr/lib/llvm-$version/lib/python$PY_VERSION/dist-packages"
        if [ -d "$candidate/lldb" ]; then
            LLDB_PYTHON_PATH="$candidate"
            echo "  Found LLVM-$version LLDB at: $candidate/lldb"
            break
        fi
    done
fi

if [ -z "$LLDB_PYTHON_PATH" ]; then
    print_warning "Could not find LLDB Python bindings automatically"
    LLDB_PYTHON_PATH="/usr/lib/python3/dist-packages"
fi

print_success "LLDB Python path: $LLDB_PYTHON_PATH"

# Test LLDB import
echo "  Testing LLDB import..."
if PYTHONPATH="$LLDB_PYTHON_PATH" python3 -c "import lldb; print('LLDB loaded:', lldb.__file__)" 2>/dev/null; then
    print_success "LLDB import successful"
else
    print_warning "LLDB import test failed"
fi

# Step 7: Register the Swift kernel
print_step "Registering Swift Jupyter kernel..."

cd "$INSTALL_DIR"

# Create kernel spec manually for better control
KERNEL_DIR="/usr/local/share/jupyter/kernels/swift"
mkdir -p "$KERNEL_DIR"

# Find swift-build and swift-package paths
SWIFT_BUILD_PATH="$SWIFT_TOOLCHAIN/bin/swift-build"
SWIFT_PACKAGE_PATH="$SWIFT_TOOLCHAIN/bin/swift-package"

# Build comprehensive LD_LIBRARY_PATH
LD_LIB_PATH="$SWIFT_TOOLCHAIN/lib/swift/linux:$SWIFT_TOOLCHAIN/lib:/usr/lib/x86_64-linux-gnu"

# Create kernel.json
cat > "$KERNEL_DIR/kernel.json" << EOF
{
  "argv": [
    "$(which python3)",
    "-m", "swift_kernel",
    "-f", "{connection_file}"
  ],
  "display_name": "Swift",
  "language": "swift",
  "env": {
    "PYTHONPATH": "$LLDB_PYTHON_PATH:$INSTALL_DIR",
    "REPL_SWIFT_PATH": "$SWIFT_TOOLCHAIN/bin/repl_swift",
    "SWIFT_BUILD_PATH": "$SWIFT_BUILD_PATH",
    "SWIFT_PACKAGE_PATH": "$SWIFT_PACKAGE_PATH",
    "PATH": "$SWIFT_TOOLCHAIN/bin:$PATH",
    "LD_LIBRARY_PATH": "$LD_LIB_PATH",
    "SWIFT_TOOLCHAIN": "$SWIFT_TOOLCHAIN"
  },
  "interrupt_mode": "message"
}
EOF

echo "  Kernel config written to: $KERNEL_DIR/kernel.json"
echo "  PYTHONPATH: $LLDB_PYTHON_PATH:$INSTALL_DIR"
echo "  Swift toolchain: $SWIFT_TOOLCHAIN"

# Also try using register.py for completeness (might set additional paths)
python3 register.py --sys-prefix --swift-toolchain "$SWIFT_TOOLCHAIN" > /dev/null 2>&1 || true

print_success "Swift kernel registered"

# Test kernel import
echo "  Testing kernel import..."
if PYTHONPATH="$LLDB_PYTHON_PATH:$INSTALL_DIR" LD_LIBRARY_PATH="$LD_LIB_PATH" python3 -c "import swift_kernel; print('Kernel module loaded')" 2>/dev/null; then
    print_success "Kernel import test passed"
else
    print_warning "Kernel import test failed"
fi

# Step 8: Verify installation
print_step "Verifying installation..."

# Check kernel is registered
if jupyter kernelspec list 2>/dev/null | grep -q swift; then
    print_success "Swift kernel found in Jupyter"
else
    print_error "Swift kernel not found - registration may have failed"
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
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""

# Export PATH for the current session
echo "export PATH=\"$HOME/.local/share/swiftly/bin:\$PATH\"" >> ~/.bashrc
echo "export PATH=\"$SWIFT_TOOLCHAIN/bin:\$PATH\"" >> ~/.bashrc

print_success "Installation complete! Please restart the runtime."
