# Google Colab Installation Script - Swiftly Integration Fixed

## Issue

The original installation script was using an incorrect URL for the Swiftly installer:
```bash
curl -L https://swift-server.github.io/swiftly/swiftly-install.sh | bash
```

This URL returned an HTML page instead of a shell script, causing the installation to fail.

## Solution

Updated to use the **official Swiftly installation method** from swift.org:

```bash
curl -O https://download.swift.org/swiftly/linux/swiftly-$(uname -m).tar.gz && \
tar zxf swiftly-$(uname -m).tar.gz && \
./swiftly init --quiet-shell-followup
```

## Changes Made

### 0. **CRITICAL FIX**: Reordered Installation Steps

**The Most Important Fix**: System dependencies MUST be installed BEFORE Swift installation.

**Before**:
- Step 1: Installing Swiftly & Swift
- Step 2: Installing System Dependencies

**After**:
- Step 1: Installing System Dependencies ← **Moved to first**
- Step 2: Installing Swiftly & Swift

**Why this matters**: When `swiftly install` runs, it checks for required dependencies. If they're not present, it shows a warning and requires the user to install them. By installing dependencies FIRST, the installation completes cleanly without warnings.

**Error that this fixes**:
```
Error: There are some dependencies that should be installed before using this toolchain.
You can run the following script as the system administrator (e.g. root) to prepare your system:
apt-get -y install libz3-dev pkg-config python3-lldb-13
```

### 1. Swiftly Installation ([install_swift_colab.sh:85-108](install_swift_colab.sh))

**Before**:
```bash
curl -L https://swift-server.github.io/swiftly/swiftly-install.sh | bash
```

**After** (based on swift-colab approach):
```bash
# Install Swiftly (official method from swift.org)
ARCH=$(uname -m)
curl -fsSL "https://download.swift.org/swiftly/linux/swiftly-${ARCH}.tar.gz" -o swiftly.tar.gz
tar -xzf swiftly.tar.gz

# Install swiftly to /usr/local/bin for system-wide access
install -Dm755 ./swiftly /usr/local/bin/swiftly

# Clean up
rm -f swiftly.tar.gz swiftly
```

**Key changes**:
- Uses `install -Dm755` to place swiftly in `/usr/local/bin` (system-wide)
- Removes the need to source environment files manually
- More reliable than user-local installation in Colab

### 2. Swiftly Initialization and Swift Installation ([install_swift_colab.sh:121-122](install_swift_colab.sh))

**Before**:
```bash
swiftly install main-snapshot --no-modify-profile
```

**After**:
```bash
# -y: auto-confirm all prompts (both init and install - non-interactive)
# --quiet-shell-followup: don't print shell modification instructions
# --use: set as the active toolchain
swiftly init -y --quiet-shell-followup
swiftly install -y --use main-snapshot
```

**Key changes**:
- Added `-y` flag to BOTH `init` and `install` commands
- Fixes TWO blocking prompts:
  1. `swiftly init` asks "Proceed? (Y/n):"
  2. `swiftly install` asks "Proceed? (y/N):" when overwriting files
- Split into two commands: `init` then `install`
- Added `--use` to automatically activate the installed toolchain

### 3. Environment Sourcing ([install_swift_colab.sh:129-139](install_swift_colab.sh))

After installing Swift, we must source the swiftly environment:

```bash
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
```

### 4. Toolchain Directory Detection ([install_swift_colab.sh:152-161](install_swift_colab.sh))

**Before**:
```bash
SWIFT_TOOLCHAIN_DIR=$(swiftly which swift | xargs dirname | xargs dirname)
```

**After**:
```bash
# Swiftly uses $HOME/.local/share/swiftly/toolchains/...
SWIFT_BIN=$(which swift)
if [ -z "$SWIFT_BIN" ]; then
    echo "❌ Error: Could not find swift binary"
    exit 1
fi

SWIFT_TOOLCHAIN_DIR=$(dirname $(dirname "$SWIFT_BIN"))
```

### 5. System Dependencies - **NOW STEP 1** ([install_swift_colab.sh:58-77](install_swift_colab.sh))

**CRITICAL**: These are now installed in Step 1, BEFORE Swift installation.

Added Swift-recommended dependencies:

```bash
apt-get install -y -qq \
    libpython3-dev \
    libncurses5-dev \
    libncurses5 \
    libtinfo5 \
    libz3-dev \
    pkg-config \
    python3-lldb-13
```

### 6. Environment Initialization ([install_swift_colab.sh:226-249](install_swift_colab.sh))

Simplified the Python initialization script to directly source swiftly's environment file:

```python
# Source swiftly environment and get PATH
swiftly_env = os.path.expanduser('~/.local/share/swiftly/env.sh')
if os.path.exists(swiftly_env):
    result = subprocess.run(['bash', '-c', f'source {swiftly_env} && echo $PATH'],
                           capture_output=True, text=True)
    if result.returncode == 0:
        os.environ['PATH'] = result.stdout.strip() + ':' + os.environ.get('PATH', '')
```

### 7. Error Handling ([install_swift_colab.sh:141-146](install_swift_colab.sh))

Added better error handling:

```bash
# Verify Swift installation
if ! command -v swift &> /dev/null; then
    echo "❌ Error: Swift binary not found after installation"
    echo "PATH: $PATH"
    exit 1
fi
```

## How Swiftly Works

**Swiftly** is the official Swift toolchain manager maintained by the Swift project.

### Installation Location

Swiftly installs to:
- **Binary**: `~/.local/share/swiftly/bin/swiftly`
- **Toolchains**: `~/.local/share/swiftly/toolchains/<version>/`
- **Environment**: `~/.local/share/swiftly/env.sh`

### Commands Used

```bash
# Install swiftly
curl -O https://download.swift.org/swiftly/linux/swiftly-$(uname -m).tar.gz && \
tar zxf swiftly-$(uname -m).tar.gz && \
./swiftly init --quiet-shell-followup

# Source environment
source ~/.local/share/swiftly/env.sh

# Install Swift
swiftly install main-snapshot

# Check version
swift --version
```

## Testing

The updated script should now:

1. ✅ Download swiftly binary correctly
2. ✅ Extract and initialize swiftly
3. ✅ Install Swift main-snapshot
4. ✅ Set up PATH correctly
5. ✅ Register the kernel with the correct toolchain path

## Usage in Google Colab

The command remains the same:

```bash
!curl -s https://raw.githubusercontent.com/YOUR_USERNAME/swift-jupyter/main/install_swift_colab.sh | bash
```

Then restart the runtime and the Swift kernel should be available.

## Verification

After running the script, verify with:

```bash
# Check swiftly
!swiftly --version

# Check Swift
!swift --version

# Check kernel
!jupyter kernelspec list
```

Expected output:
```
Available kernels:
  python3    /usr/local/share/jupyter/kernels/python3
  swift      /usr/local/share/jupyter/kernels/swift
```

## References

- **Official Swiftly Documentation**: https://www.swift.org/install/linux/
- **Swiftly GitHub**: https://github.com/swiftlang/swiftly
- **Swift.org Install Page**: https://www.swift.org/install/

## Next Steps

1. Test the updated script in a fresh Google Colab environment
2. Verify kernel registration works correctly
3. Test PythonKit installation in the Swift kernel
4. Update main documentation to reflect the changes

---

**Last Updated**: October 18, 2024
**Status**: Ready for testing ✅
