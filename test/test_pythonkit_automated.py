#!/usr/bin/env python3
"""
Automated test for PythonKit + matplotlib integration.

This script executes the PythonKit test notebook and verifies that:
1. PythonKit can be installed via %install
2. Python.import() works
3. NumPy can be imported and used
4. matplotlib can be imported and plots can be created

Usage:
    python3 test_pythonkit_automated.py
"""

import os
import sys
import json
import subprocess
import tempfile
import shutil
from pathlib import Path

def check_requirements():
    """Check if required tools are installed."""
    print("Checking requirements...")

    # Check jupyter
    try:
        result = subprocess.run(
            ['jupyter', '--version'],
            capture_output=True,
            text=True,
            check=True
        )
        print("✅ jupyter is installed")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ jupyter not found. Install with: /usr/bin/python3 -m pip install --user jupyter")
        return False

    # Check if Swift kernel is registered
    result = subprocess.run(
        ['jupyter', 'kernelspec', 'list'],
        capture_output=True,
        text=True
    )
    if 'swift' not in result.stdout.lower():
        print("❌ Swift kernel not registered. Run: python3 register.py")
        return False
    print("✅ Swift kernel is registered")

    # Check matplotlib
    try:
        result = subprocess.run(
            [sys.executable, '-c', 'import matplotlib'],
            capture_output=True,
            check=True
        )
        print("✅ matplotlib is available")
    except subprocess.CalledProcessError:
        print("⚠️  matplotlib not found. Installing...")
        subprocess.run(
            [sys.executable, '-m', 'pip', 'install', '--user', 'matplotlib', 'numpy'],
            check=True
        )

    return True

def run_notebook(notebook_path):
    """
    Execute a Jupyter notebook and return whether it succeeded.

    Args:
        notebook_path: Path to the notebook file

    Returns:
        (success: bool, output_notebook_path: str, error_msg: str)
    """
    print(f"\nExecuting notebook: {notebook_path}")
    print("This may take a few minutes as PythonKit needs to be compiled...")

    # Create a temporary directory for output
    temp_dir = tempfile.mkdtemp(prefix='pythonkit_test_')
    output_path = os.path.join(temp_dir, 'output.ipynb')

    try:
        # Execute the notebook using jupyter nbconvert
        result = subprocess.run(
            [
                'jupyter', 'nbconvert',
                '--to', 'notebook',
                '--execute',
                '--ExecutePreprocessor.timeout=600',  # 10 minute timeout for compilation
                '--ExecutePreprocessor.kernel_name=swift',
                '--output', output_path,
                notebook_path
            ],
            capture_output=True,
            text=True,
            timeout=660  # Slightly longer than nbconvert timeout
        )

        if result.returncode == 0:
            print("✅ Notebook executed successfully")
            return True, output_path, None
        else:
            error_msg = f"Notebook execution failed:\n{result.stderr}"
            print(f"❌ {error_msg}")
            return False, output_path, error_msg

    except subprocess.TimeoutExpired:
        error_msg = "Notebook execution timed out (>10 minutes)"
        print(f"❌ {error_msg}")
        return False, output_path, error_msg
    except Exception as e:
        error_msg = f"Error executing notebook: {e}"
        print(f"❌ {error_msg}")
        return False, output_path, error_msg

def verify_notebook_output(output_path):
    """
    Verify the notebook output contains expected success messages.

    Args:
        output_path: Path to the executed notebook

    Returns:
        (success: bool, details: list)
    """
    print("\nVerifying notebook output...")

    if not os.path.exists(output_path):
        print("❌ Output notebook not found")
        return False, ["Output notebook not found"]

    with open(output_path, 'r') as f:
        notebook = json.load(f)

    checks = {
        'pythonkit_import': False,
        'python_import_works': False,
        'numpy_works': False,
        'matplotlib_works': False,
        'all_tests_passed': False
    }

    details = []

    # Check each cell's outputs
    for cell in notebook.get('cells', []):
        if cell.get('cell_type') != 'code':
            continue

        outputs = cell.get('outputs', [])
        for output in outputs:
            # Check stdout
            if output.get('name') == 'stdout':
                text = output.get('text', '')
                if isinstance(text, list):
                    text = ''.join(text)

                if '✅ PythonKit imported successfully' in text:
                    checks['pythonkit_import'] = True
                if '✅ Python.import() works' in text:
                    checks['python_import_works'] = True
                if '✅ NumPy works' in text:
                    checks['numpy_works'] = True
                if '✅ matplotlib imported and inline mode enabled' in text:
                    checks['matplotlib_works'] = True
                if 'All PythonKit + matplotlib tests PASSED' in text:
                    checks['all_tests_passed'] = True

            # Check for errors
            if output.get('output_type') == 'error':
                error_name = output.get('ename', 'Unknown')
                error_value = output.get('evalue', '')
                details.append(f"❌ Error in cell: {error_name}: {error_value}")

    # Report results
    for check_name, passed in checks.items():
        status = "✅" if passed else "❌"
        check_display = check_name.replace('_', ' ').title()
        details.append(f"{status} {check_display}: {'PASSED' if passed else 'FAILED'}")
        print(f"{status} {check_display}")

    all_passed = all(checks.values())
    return all_passed, details

def main():
    """Main test execution."""
    print("="*60)
    print("PythonKit + matplotlib Automated Test")
    print("="*60)
    print()

    # Check requirements
    if not check_requirements():
        print("\n❌ Requirements check failed")
        return 1

    # Find the test notebook
    notebook_path = 'examples/test_pythonkit_matplotlib.ipynb'
    if not os.path.exists(notebook_path):
        print(f"\n❌ Test notebook not found: {notebook_path}")
        return 1

    # Execute the notebook
    success, output_path, error_msg = run_notebook(notebook_path)

    if not success:
        print("\n" + "="*60)
        print("TEST FAILED - Notebook execution failed")
        print("="*60)
        if error_msg:
            print(f"\nError: {error_msg}")
        return 1

    # Verify outputs
    verified, details = verify_notebook_output(output_path)

    print("\n" + "="*60)
    if verified:
        print("TEST PASSED ✅")
        print("="*60)
        print("\n🎉 PythonKit + matplotlib integration is working!")
        print("\nConclusion: matplotlib IS fully supported via PythonKit")
        print("with standard Swift 6.3+ toolchains.")
        return 0
    else:
        print("TEST FAILED ❌")
        print("="*60)
        print("\nSome checks did not pass:")
        for detail in details:
            print(f"  {detail}")
        print(f"\nOutput notebook saved to: {output_path}")
        print("Review the notebook for details.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
