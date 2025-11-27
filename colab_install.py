#!/usr/bin/env python3
"""
Swift Jupyter Kernel Installer for Google Colab

This script can be run directly in a Colab notebook to install Swift and the
Swift Jupyter kernel.

Usage in Colab (Python cell):
    !pip install -q requests
    exec(open('/content/colab_install.py').read())

Or:
    import urllib.request
    exec(urllib.request.urlopen('https://raw.githubusercontent.com/YOUR_REPO/swift-jupyter/main/colab_install.py').read().decode())
"""

import os
import subprocess
import sys
import json
import shutil
from pathlib import Path

# Configuration
SWIFT_SNAPSHOT = "main-snapshot-2025-11-03"  # Specific known-working snapshot
SWIFT_JUPYTER_REPO = "https://github.com/pedronahum/swift-jupyter.git"
SWIFT_JUPYTER_BRANCH = "main"
INSTALL_DIR = "/content/swift-jupyter"


def run(cmd, check=True, capture=False, shell=True):
    """Run a command and optionally capture output."""
    if capture:
        result = subprocess.run(cmd, shell=shell, capture_output=True, text=True)
        if check and result.returncode != 0:
            print(f"Command failed: {cmd}")
            print(f"stderr: {result.stderr}")
            raise subprocess.CalledProcessError(result.returncode, cmd)
        return result.stdout.strip()
    else:
        subprocess.run(cmd, shell=shell, check=check)


def print_step(msg):
    print(f"\n\033[94m==>\033[0m {msg}")


def print_success(msg):
    print(f"\033[92m✓\033[0m {msg}")


def print_warning(msg):
    print(f"\033[93m⚠\033[0m {msg}")


def print_error(msg):
    print(f"\033[91m✗\033[0m {msg}")


def install_swift_jupyter():
    """Main installation function."""

    print("\n" + "="*70)
    print("     Swift Jupyter Kernel Installation for Google Colab")
    print("="*70 + "\n")

    # Step 1: Install system dependencies
    print_step("Installing system dependencies...")

    packages = [
        "binutils", "git", "gnupg2", "libc6-dev", "libcurl4-openssl-dev",
        "libedit2", "libgcc-11-dev", "libncurses6", "libpython3-dev",
        "libsqlite3-0", "libstdc++-11-dev", "libxml2-dev", "libz3-dev",
        "pkg-config", "tzdata", "unzip", "zlib1g-dev",
        # Python 3.10 is needed because Swift toolchain LLDB is compiled against it
        "python3.10", "python3.10-dev", "python3.10-venv"
    ]

    run("apt-get update -qq", check=False)
    # Add deadsnakes PPA for Python 3.10 on Ubuntu 22.04
    run("apt-get install -y -qq software-properties-common", check=False)
    run("add-apt-repository -y ppa:deadsnakes/ppa", check=False)
    run("apt-get update -qq", check=False)
    run(f"apt-get install -y -qq {' '.join(packages)}", check=False)

    # Install pip for Python 3.10
    run("python3.10 -m ensurepip --upgrade 2>/dev/null || curl -sS https://bootstrap.pypa.io/get-pip.py | python3.10", check=False)

    # Install Jupyter dependencies for Python 3.10
    print("  Installing Jupyter dependencies for Python 3.10...")
    run("python3.10 -m pip install -q jupyter ipykernel jupyter_client", check=False)

    # Install LLDB Python bindings (for fallback)
    for version in [18, 17, 16, 15, 14]:
        result = subprocess.run(
            f"apt-get install -y -qq python3-lldb-{version}",
            shell=True, capture_output=True
        )
        if result.returncode == 0:
            print_success(f"Installed python3-lldb-{version}")
            break

    # Verify Python 3.10 is installed
    py310_path = shutil.which("python3.10")
    if py310_path:
        print_success(f"Python 3.10 installed at {py310_path}")
    else:
        print_warning("Python 3.10 not found, will try system Python")

    print_success("System dependencies installed")

    # Step 2: Install Swiftly
    print_step("Installing Swiftly...")

    swiftly_home = os.path.expanduser("~/.local/share/swiftly")
    swiftly_bin = os.path.join(swiftly_home, "bin")
    swiftly_path = os.path.join(swiftly_bin, "swiftly")

    if not os.path.exists(swiftly_path):
        # Try new method first (from https://www.swift.org/install/linux/)
        import platform
        arch = platform.machine()  # x86_64 or aarch64

        try:
            install_cmds = f"""
                cd /tmp &&
                curl -fsSL -O https://download.swift.org/swiftly/linux/swiftly-{arch}.tar.gz &&
                tar zxf swiftly-{arch}.tar.gz &&
                ./swiftly init --quiet-shell-followup -y
            """
            run(install_cmds)
            print_success("Swiftly installed (new method)")
        except Exception:
            # Fallback to old method (works in some environments)
            print_warning("New method failed, trying legacy installer...")
            run("curl -fsSL https://swiftlang.github.io/swiftly/swiftly-install.sh | bash -s -- -y")
            print_success("Swiftly installed (legacy method)")
    else:
        print_success("Swiftly already installed")

    # Source the swiftly environment
    env_file = os.path.join(swiftly_home, "env.sh")
    if os.path.exists(env_file):
        # Parse env.sh and add to environment
        os.environ["SWIFTLY_HOME_DIR"] = swiftly_home
        os.environ["SWIFTLY_BIN_DIR"] = swiftly_bin

    # Add to PATH
    os.environ["PATH"] = f"{swiftly_bin}:{os.environ['PATH']}"

    # Step 3: Install Swift
    print_step(f"Installing Swift {SWIFT_SNAPSHOT} (2-3 minutes)...")

    # Try to install the specified snapshot, with fallbacks (snapshots only, not stable releases)
    swift_installed = False
    snapshots_to_try = [
        SWIFT_SNAPSHOT,
        f"{SWIFT_SNAPSHOT}a",      # Sometimes snapshots have 'a' suffix
        "main-snapshot",           # Latest main snapshot
        "6.1-snapshot",            # Release branch snapshot
    ]

    # First, let's see what swiftly can list
    print("  Checking available toolchains...")
    list_result = subprocess.run(
        f"{swiftly_bin}/swiftly list-available --platform ubuntu2204",
        shell=True, capture_output=True, text=True
    )
    if list_result.returncode == 0 and list_result.stdout:
        print(f"  Available: {list_result.stdout[:300]}...")

    for snapshot in snapshots_to_try:
        try:
            print(f"  Trying {snapshot}...")
            # Run swiftly install - it may return non-zero for dependency warnings even when successful
            result = subprocess.run(
                f"{swiftly_bin}/swiftly install {snapshot} -y",
                shell=True, capture_output=True, text=True
            )

            # Check if toolchain was actually installed despite any warnings
            # Swiftly stores toolchains in ~/.local/share/swiftly/toolchains/
            toolchain_dir = os.path.join(swiftly_home, "toolchains")
            installed_toolchain = None
            if os.path.isdir(toolchain_dir):
                for name in os.listdir(toolchain_dir):
                    if snapshot in name:
                        candidate = os.path.join(toolchain_dir, name)
                        if os.path.isfile(os.path.join(candidate, "usr", "bin", "swift")):
                            installed_toolchain = candidate
                            break

            if installed_toolchain:
                print(f"  Toolchain found at: {installed_toolchain}")
                run(f"{swiftly_bin}/swiftly use {snapshot}", check=False)
                swift_installed = True
                print_success(f"Swift {snapshot} installed")
                break
            elif result.returncode == 0:
                run(f"{swiftly_bin}/swiftly use {snapshot}", check=False)
                swift_installed = True
                print_success(f"Swift {snapshot} installed")
                break
            else:
                print_warning(f"Failed to install {snapshot}: {result.stderr[:200] if result.stderr else 'unknown error'}")
        except Exception as e:
            print_warning(f"Failed to install {snapshot}: {e}")

    if not swift_installed:
        raise Exception("Failed to install any Swift version. Please check your internet connection and try again.")

    # Get Swift version and path
    swift_version = run("swift --version", capture=True).split('\n')[0]

    # Find the toolchain path - swiftly uses shims, so we need to read its config
    swift_toolchain = None

    # Method 1: Check swiftly's config.json for the in-use toolchain
    swiftly_config = os.path.join(swiftly_home, "config.json")
    if os.path.exists(swiftly_config):
        try:
            with open(swiftly_config) as f:
                config = json.load(f)
            in_use = config.get("inUse")
            if in_use:
                candidate = os.path.join(swiftly_home, "toolchains", in_use)
                if os.path.exists(os.path.join(candidate, "usr", "bin", "swift")):
                    swift_toolchain = candidate
                    print(f"  Found toolchain via swiftly config: {in_use}")
        except Exception as e:
            print_warning(f"Could not read swiftly config: {e}")

    # Method 2: Fall back to resolving symlinks if that fails
    if not swift_toolchain:
        swift_path = run("which swift", capture=True)
        swift_real_path = os.path.realpath(swift_path)
        # If realpath points to swiftly itself, we can't use it
        if "swiftly/bin/swiftly" not in swift_real_path:
            swift_toolchain = str(Path(swift_real_path).parent.parent)
            # Verify this is a valid toolchain path
            if not os.path.exists(os.path.join(swift_toolchain, "usr", "bin")) and \
               not os.path.exists(os.path.join(swift_toolchain, "bin")):
                alt_toolchain = str(Path(swift_real_path).parent.parent.parent)
                if os.path.exists(os.path.join(alt_toolchain, "usr", "bin")):
                    swift_toolchain = alt_toolchain
                else:
                    swift_toolchain = None

    # Method 3: Search toolchains directory for the one we just installed
    if not swift_toolchain:
        toolchains_dir = os.path.join(swiftly_home, "toolchains")
        if os.path.exists(toolchains_dir):
            # Look for the snapshot we tried to install
            for snapshot in [SWIFT_SNAPSHOT, f"{SWIFT_SNAPSHOT}a", "main-snapshot"]:
                for name in os.listdir(toolchains_dir):
                    if snapshot in name or name.startswith(snapshot.split("-")[0]):
                        candidate = os.path.join(toolchains_dir, name)
                        if os.path.exists(os.path.join(candidate, "usr", "bin", "swift")):
                            swift_toolchain = candidate
                            print(f"  Found toolchain by searching: {name}")
                            break
                if swift_toolchain:
                    break

    if not swift_toolchain:
        raise Exception("Could not determine Swift toolchain path. Check swiftly installation.")

    print_success(f"Swift installed: {swift_version}")
    print(f"  Toolchain path: {swift_toolchain}")

    # Step 4: Clone swift-jupyter
    print_step("Setting up Swift Jupyter kernel...")

    if os.path.exists(INSTALL_DIR):
        shutil.rmtree(INSTALL_DIR)

    run(f"git clone --depth 1 -b {SWIFT_JUPYTER_BRANCH} {SWIFT_JUPYTER_REPO} {INSTALL_DIR}")
    print_success("Repository cloned")

    # Step 5: Install Python dependencies (already done for Python 3.10 above)
    print_step("Installing Python dependencies...")
    run("pip install -q jupyter ipykernel jupyter_client")
    print_success("Python dependencies installed")

    # Step 6: Find LLDB Python path and determine which Python to use
    print_step("Configuring LLDB Python bindings...")

    lldb_python_path = None
    kernel_python = sys.executable  # Default to current Python
    py_ver = f"{sys.version_info[0]}.{sys.version_info[1]}"

    # Build LD_LIBRARY_PATH for the toolchain (needed for LLDB to load Swift libs)
    toolchain_lib_paths = [
        f"{swift_toolchain}/usr/lib",
        f"{swift_toolchain}/usr/lib/swift/linux",
        f"{swift_toolchain}/usr/lib/swift/host/compiler",
        f"{swift_toolchain}/lib",
        f"{swift_toolchain}/lib/swift/linux",
    ]
    toolchain_ld_path = ":".join(p for p in toolchain_lib_paths if os.path.exists(p))

    # First, detect what Python version the toolchain's LLDB was built for
    # by looking for _lldb.cpython-3XX-*.so files
    def detect_lldb_python_version(toolchain_path):
        """Detect what Python version the toolchain's LLDB was built for."""
        import glob
        import re

        # Search for LLDB Python bindings in the toolchain
        for base in ["usr/local/lib", "lib", "usr/lib"]:
            pattern = os.path.join(toolchain_path, base, "python*/dist-packages/lldb/_lldb.cpython-*.so")
            matches = glob.glob(pattern)
            if matches:
                # Extract Python version from filename like _lldb.cpython-310-x86_64-linux-gnu.so
                for match in matches:
                    filename = os.path.basename(match)
                    m = re.search(r'cpython-(\d)(\d+)-', filename)
                    if m:
                        major, minor = m.groups()
                        return f"{major}.{minor}"
        return None

    toolchain_lldb_python = detect_lldb_python_version(swift_toolchain)
    if toolchain_lldb_python:
        print(f"  Toolchain LLDB was built for Python {toolchain_lldb_python}")
    else:
        print("  Could not detect toolchain LLDB Python version")

    # Determine which Python to use for the kernel
    # Priority: toolchain's Python version > system Python
    python_to_use = None
    if toolchain_lldb_python:
        # Check if that Python version is available
        py_cmd = f"python{toolchain_lldb_python}"
        py_path = shutil.which(py_cmd)
        if py_path:
            python_to_use = py_path
            print(f"  Found {py_cmd} at {py_path}")
        else:
            print(f"  {py_cmd} not found, will try alternatives")

    # If toolchain Python not available, try system Python 3.10 (which we installed)
    if not python_to_use:
        for py_ver_try in ["3.10", "3.11", "3.12"]:
            py_path = shutil.which(f"python{py_ver_try}")
            if py_path:
                python_to_use = py_path
                print(f"  Using python{py_ver_try} at {py_path}")
                break

    if not python_to_use:
        python_to_use = sys.executable
        print(f"  Falling back to {python_to_use}")

    # Get the Python version we'll actually use
    try:
        result = subprocess.run([python_to_use, '-c', 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")'],
                                capture_output=True, text=True, timeout=10)
        kernel_py_ver = result.stdout.strip()
    except Exception:
        kernel_py_ver = py_ver

    print(f"  Kernel will use: {python_to_use} (Python {kernel_py_ver})")

    # Helper function to validate LLDB module has SBDebugger using specific Python
    def validate_lldb_path(path, ld_lib_path="", python_exe=None):
        """Check if the LLDB module at path has SBDebugger."""
        if python_exe is None:
            python_exe = python_to_use

        test_script = f'''
import sys
import os
sys.path.insert(0, "{path}")
if "{ld_lib_path}":
    os.environ["LD_LIBRARY_PATH"] = "{ld_lib_path}:" + os.environ.get("LD_LIBRARY_PATH", "")
try:
    import lldb
    if hasattr(lldb, 'SBDebugger'):
        debugger = lldb.SBDebugger.Create()
        if debugger:
            lldb.SBDebugger.Destroy(debugger)
            print("valid")
        else:
            print("incomplete-create-failed")
    else:
        print("incomplete-no-sbdebugger")
except Exception as e:
    print(f"error: {{e}}")
'''
        env = os.environ.copy()
        if ld_lib_path:
            env["LD_LIBRARY_PATH"] = ld_lib_path + ":" + env.get("LD_LIBRARY_PATH", "")
        try:
            result = subprocess.run(
                [python_exe, '-c', test_script],
                capture_output=True, text=True, timeout=15,
                env=env
            )
            output = result.stdout.strip()
            if output != "valid":
                print(f"    Validation output: {output}")
                if result.stderr:
                    stderr_preview = result.stderr[:200].replace('\n', ' ')
                    print(f"    Validation stderr: {stderr_preview}")
            return output == "valid"
        except Exception as e:
            print(f"    Validation exception: {e}")
            return False

    # Build list of LLDB candidates - prioritize the detected Python version
    swift_lldb_candidates = []
    search_versions = [kernel_py_ver]
    if toolchain_lldb_python and toolchain_lldb_python != kernel_py_ver:
        search_versions.append(toolchain_lldb_python)
    search_versions.extend(["3.10", "3.11", "3.12", "3.9", "3"])
    search_versions = list(dict.fromkeys(search_versions))  # Remove duplicates

    for py_search_ver in search_versions:
        swift_lldb_candidates.extend([
            f"{swift_toolchain}/usr/local/lib/python{py_search_ver}/dist-packages",
            f"{swift_toolchain}/lib/python{py_search_ver}/site-packages",
            f"{swift_toolchain}/lib/python{py_search_ver}/dist-packages",
            f"{swift_toolchain}/usr/lib/python{py_search_ver}/site-packages",
            f"{swift_toolchain}/usr/lib/python{py_search_ver}/dist-packages",
        ])
    swift_lldb_candidates = list(dict.fromkeys(swift_lldb_candidates))

    # System LLDB as fallback
    system_candidates = []
    for llvm_ver in [18, 17, 16, 15, 14]:
        system_candidates.extend([
            f"/usr/lib/llvm-{llvm_ver}/lib/python{kernel_py_ver}/dist-packages",
            f"/usr/lib/llvm-{llvm_ver}/lib/python3/dist-packages",
        ])
    system_candidates.append("/usr/lib/python3/dist-packages")

    print("  Searching for valid LLDB Python bindings...")
    print(f"  Toolchain: {swift_toolchain}")
    print(f"  Kernel Python: {kernel_py_ver}")
    print(f"  LD_LIBRARY_PATH: {toolchain_ld_path}")

    # Helper function to fix Python version mismatch for _lldb native module
    def fix_lldb_python_version(lldb_dir, target_py_ver):
        """Create symlink for _lldb native module if Python version doesn't match.

        The _lldb.cpython-3XX-x86_64-linux-gnu.so is just a symlink to liblldb.so,
        which is Python-version agnostic. If the toolchain was built with a different
        Python version, we can create a symlink with the correct version suffix.

        Args:
            lldb_dir: Path to lldb directory (e.g., .../dist-packages/lldb)
            target_py_ver: Target Python version (e.g., "3.12")

        Returns:
            True if fixed or already correct, False if cannot fix
        """
        import glob
        import platform

        arch = platform.machine()
        target_suffix = f"cpython-{target_py_ver.replace('.', '')}-{arch}-linux-gnu.so"
        target_module = os.path.join(lldb_dir, f"_lldb.{target_suffix}")

        # Check if target module already exists
        if os.path.exists(target_module):
            return True

        # Find existing _lldb.cpython-*.so files
        existing_modules = glob.glob(os.path.join(lldb_dir, "_lldb.cpython-*.so"))

        if not existing_modules:
            # No native modules found - check if there's a direct _lldb.so
            direct_module = os.path.join(lldb_dir, "_lldb.so")
            if os.path.exists(direct_module):
                # Create versioned symlink to direct module
                try:
                    os.symlink("_lldb.so", target_module)
                    print(f"    Created symlink: _lldb.{target_suffix} -> _lldb.so")
                    return True
                except Exception as e:
                    print(f"    Failed to create symlink: {e}")
                    return False
            return False

        # Get the first existing module (they all point to the same liblldb.so)
        existing_module = existing_modules[0]
        existing_basename = os.path.basename(existing_module)

        # Check what the existing module points to
        if os.path.islink(existing_module):
            link_target = os.readlink(existing_module)
            print(f"    Found: {existing_basename} -> {link_target}")
        else:
            link_target = existing_basename
            print(f"    Found: {existing_basename} (not a symlink)")

        # Create symlink with target Python version pointing to same target
        try:
            # If existing is a symlink, use the same target
            # If existing is a real file, symlink to that file
            if os.path.islink(existing_module):
                os.symlink(link_target, target_module)
            else:
                os.symlink(existing_basename, target_module)
            print(f"    Created symlink: _lldb.{target_suffix} -> {link_target}")
            return True
        except Exception as e:
            print(f"    Failed to create symlink: {e}")
            return False

    # First try toolchain LLDB with proper LD_LIBRARY_PATH
    for candidate in swift_lldb_candidates:
        lldb_path = os.path.join(candidate, "lldb")
        exists = os.path.isdir(lldb_path)
        print(f"  Checking candidate: {candidate} (lldb exists: {exists})")
        if exists:
            print(f"  Validating toolchain LLDB: {lldb_path}")
            if validate_lldb_path(candidate, toolchain_ld_path):
                lldb_python_path = candidate
                print(f"  ✓ Valid toolchain LLDB found at: {lldb_path}")
                break
            else:
                # Check if this is a Python version mismatch
                # Try to fix by creating symlink for the kernel's Python version
                print(f"  ✗ LLDB at {lldb_path} failed validation, checking Python version mismatch...")
                if fix_lldb_python_version(lldb_path, kernel_py_ver):
                    # Try validation again after fixing
                    print(f"  Retrying validation after Python version fix...")
                    if validate_lldb_path(candidate, toolchain_ld_path):
                        lldb_python_path = candidate
                        print(f"  ✓ Valid toolchain LLDB found after version fix: {lldb_path}")
                        break
                    else:
                        print(f"  ✗ Still failed after version fix")
                else:
                    print(f"  Could not fix Python version mismatch")

    # Then try system LLDB (without special LD_LIBRARY_PATH)
    if not lldb_python_path:
        for candidate in system_candidates:
            lldb_path = os.path.join(candidate, "lldb")
            if os.path.isdir(lldb_path):
                print(f"  Checking system LLDB: {lldb_path}")
                if validate_lldb_path(candidate, ""):
                    lldb_python_path = candidate
                    print(f"  ✓ Valid system LLDB found at: {lldb_path}")
                    break
                else:
                    print(f"  ✗ LLDB at {lldb_path} is incomplete or failed validation")

    # If still not found, list what's in the toolchain for debugging
    if not lldb_python_path:
        print("")
        print_warning("Could not find complete LLDB Python bindings")
        print(f"  Searching for lldb directories in toolchain...")

        # Search for lldb directories in the toolchain
        found_lldb_dirs = []
        for root, dirs, files in os.walk(swift_toolchain):
            if 'lldb' in dirs:
                lldb_dir = os.path.join(root, 'lldb')
                found_lldb_dirs.append(lldb_dir)
                print(f"    Found: {lldb_dir}")
                # Check if it has __init__.py (Python package)
                init_file = os.path.join(lldb_dir, '__init__.py')
                if os.path.exists(init_file):
                    parent = os.path.dirname(lldb_dir)
                    print(f"    → This is a Python package, parent: {parent}")
                    # Try validating with toolchain LD_LIBRARY_PATH
                    if validate_lldb_path(parent, toolchain_ld_path):
                        lldb_python_path = parent
                        print_success(f"Found working LLDB at: {parent}")
                        break

        if not lldb_python_path and found_lldb_dirs:
            print_warning("Found LLDB directories but none passed validation")
            print(f"  This may indicate missing native libraries")
            print(f"  LD_LIBRARY_PATH tried: {toolchain_ld_path}")

    if not lldb_python_path:
        # Last resort: use system path even though it might not work
        lldb_python_path = "/usr/lib/python3/dist-packages"
        print_warning(f"Could not find working LLDB, defaulting to {lldb_python_path}")
        print_warning("The kernel may not work correctly!")
    else:
        print_success(f"LLDB Python path: {lldb_python_path}")

    # Verify LLDB can be imported AND has required attributes (SBDebugger)
    # The system python3-lldb-XX packages often have incomplete bindings
    print("  Testing LLDB import and debugger creation...")

    # First, verify the LLDB module has SBDebugger
    lldb_validation_script = f'''
import sys
import os
sys.path.insert(0, "{lldb_python_path}")

# Set LD_LIBRARY_PATH for Swift libs (comprehensive path for toolchain LLDB)
os.environ["LD_LIBRARY_PATH"] = "{toolchain_ld_path}:" + os.environ.get("LD_LIBRARY_PATH", "")

import lldb
print(f"LLDB module: {{getattr(lldb, '__file__', 'unknown')}}")

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
    repl_swift = "{swift_toolchain}/bin/repl_swift"
    if os.path.exists(repl_swift):
        import platform
        arch = platform.machine()
        target = debugger.CreateTargetWithFileAndArch(repl_swift, arch)
        if target:
            print(f"Target created successfully for {{repl_swift}}")
        else:
            print(f"WARNING: Could not create target for {{repl_swift}}")
    else:
        print(f"WARNING: repl_swift not found at {{repl_swift}}")

    lldb.SBDebugger.Destroy(debugger)
    print("Debugger destroyed successfully")
else:
    print("ERROR: SBDebugger.Create() returned None")
    sys.exit(1)
'''
    test_result = subprocess.run(
        [python_to_use, '-c', lldb_validation_script],
        capture_output=True, text=True, timeout=30
    )
    if test_result.returncode == 0:
        print_success(f"LLDB debugger test passed")
        for line in test_result.stdout.strip().split('\n'):
            print(f"    {line}")
    else:
        print_error(f"LLDB debugger test FAILED:")
        print(f"    stdout: {test_result.stdout[:500]}")
        print(f"    stderr: {test_result.stderr[:500]}")
        print("")
        print_warning("The LLDB Python bindings are incomplete or missing.")
        print("    This is a known issue with system python3-lldb packages.")
        print("    The kernel will NOT work until this is fixed.")
        print("")
        print("    Possible solutions:")
        print("    1. Use Swift toolchain's bundled LLDB (if available)")
        print("    2. Install a different python3-lldb version")
        print("    3. Build LLDB from source with Python support")

    # Step 7: Register kernel
    print_step("Registering Swift Jupyter kernel...")

    kernel_dir = "/usr/local/share/jupyter/kernels/swift"
    os.makedirs(kernel_dir, exist_ok=True)

    # Build comprehensive LD_LIBRARY_PATH for kernel runtime
    # This must include all paths needed for toolchain LLDB to work
    ld_library_paths = [
        f"{swift_toolchain}/usr/lib",                      # liblldb.so for swiftly toolchains
        f"{swift_toolchain}/usr/lib/swift/linux",          # Swift runtime for swiftly
        f"{swift_toolchain}/usr/lib/swift/host/compiler",  # Compiler libs for main-snapshot
        f"{swift_toolchain}/lib",                          # Alternative layout
        f"{swift_toolchain}/lib/swift/linux",              # Alternative Swift runtime
        "/usr/lib/x86_64-linux-gnu",                       # System libs
    ]
    # Only include paths that exist
    ld_library_path = ":".join(p for p in ld_library_paths if os.path.exists(p))

    # Determine correct bin paths (swiftly uses usr/bin, standard uses bin)
    # Find repl_swift - needed for the kernel
    repl_swift_candidates = [
        f"{swift_toolchain}/usr/bin/repl_swift",  # Swiftly layout
        f"{swift_toolchain}/bin/repl_swift",       # Standard layout
    ]
    repl_swift_path = next((p for p in repl_swift_candidates if os.path.exists(p)), repl_swift_candidates[0])

    # Find swift-build
    swift_build_candidates = [
        f"{swift_toolchain}/usr/bin/swift-build",
        f"{swift_toolchain}/bin/swift-build",
    ]
    swift_build_path = next((p for p in swift_build_candidates if os.path.exists(p)), swift_build_candidates[0])

    # Find swift-package
    swift_package_candidates = [
        f"{swift_toolchain}/usr/bin/swift-package",
        f"{swift_toolchain}/bin/swift-package",
    ]
    swift_package_path = next((p for p in swift_package_candidates if os.path.exists(p)), swift_package_candidates[0])

    # Determine bin directory
    toolchain_bin = os.path.dirname(repl_swift_path)

    kernel_json = {
        "argv": [
            python_to_use,  # Use the Python version compatible with toolchain LLDB
            "-m", "swift_kernel",
            "-f", "{connection_file}"
        ],
        "display_name": "Swift",
        "language": "swift",
        "env": {
            "PYTHONPATH": f"{lldb_python_path}:{INSTALL_DIR}",
            "REPL_SWIFT_PATH": repl_swift_path,
            "SWIFT_BUILD_PATH": swift_build_path,
            "SWIFT_PACKAGE_PATH": swift_package_path,
            "PATH": f"{toolchain_bin}:{swiftly_bin}:{os.environ['PATH']}",
            "LD_LIBRARY_PATH": ld_library_path,
            "SWIFT_TOOLCHAIN": swift_toolchain,
            "SWIFT_TOOLCHAIN_ROOT": swift_toolchain  # Used by kernel for pre-loading libs
        },
        "interrupt_mode": "message"
    }

    print(f"  Kernel Python: {python_to_use}")

    with open(os.path.join(kernel_dir, "kernel.json"), "w") as f:
        json.dump(kernel_json, f, indent=2)

    # Print the kernel.json for debugging
    print(f"  Kernel config written to: {kernel_dir}/kernel.json")
    print(f"  PYTHONPATH: {lldb_python_path}:{INSTALL_DIR}")
    print(f"  Swift toolchain: {swift_toolchain}")

    print_success("Swift kernel registered")

    # Step 8: Verify installation
    print_step("Verifying installation...")

    result = run("jupyter kernelspec list", capture=True)
    if "swift" in result:
        print_success("Swift kernel found in Jupyter")
    else:
        print_error("Swift kernel not found")

    # Test repl_swift binary exists and is executable
    print(f"  Checking repl_swift binary...")
    if os.path.exists(repl_swift_path):
        print_success(f"repl_swift found at {repl_swift_path}")
        # Check if it's executable
        if os.access(repl_swift_path, os.X_OK):
            print_success("repl_swift is executable")
        else:
            print_warning("repl_swift is not executable")
    else:
        print_error(f"repl_swift NOT found at {repl_swift_path}")
        print("  The kernel will NOT work without repl_swift")

    # Test kernel import
    print("  Testing kernel import...")
    test_cmd = f'''PYTHONPATH="{lldb_python_path}:{INSTALL_DIR}" LD_LIBRARY_PATH="{ld_library_path}" {python_to_use} -c "
import sys
sys.path.insert(0, '{INSTALL_DIR}')
import swift_kernel
print('Kernel module loaded successfully')
"'''
    test_result = subprocess.run(test_cmd, shell=True, capture_output=True, text=True)
    if test_result.returncode == 0:
        print_success("Kernel import test passed")
    else:
        print_warning(f"Kernel import test failed: {test_result.stderr[:200]}")

    # Step 9: Create test notebook
    print_step("Creating test notebook...")

    test_notebook = {
        "cells": [
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": ["# Swift Test Notebook\n", "Test the Swift kernel installation."]
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": ['print("Hello from Swift!")']
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "let numbers = [1, 2, 3, 4, 5]\n",
                    "let sum = numbers.reduce(0, +)\n",
                    'print("Sum: \\(sum)")'
                ]
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": ["%swift-version"]
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

    with open("/content/swift_test.ipynb", "w") as f:
        json.dump(test_notebook, f, indent=2)

    print_success("Test notebook created at /content/swift_test.ipynb")

    # Final message
    print("\n" + "="*70)
    print("                    Installation Complete!")
    print("="*70)
    print("""
    Next Steps:

    1. RESTART THE RUNTIME
       Runtime → Restart runtime

    2. Change runtime type to Swift:
       Runtime → Change runtime type → Swift

    3. Or open /content/swift_test.ipynb

    Swift: """ + swift_version + """
    Kernel: /usr/local/share/jupyter/kernels/swift

    Troubleshooting:
    If the kernel hangs or fails to start, check the log file:
        !cat /tmp/swift-kernel.log
    """)
    print("="*70 + "\n")

    return True


if __name__ == "__main__":
    try:
        install_swift_jupyter()
    except Exception as e:
        print_error(f"Installation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
