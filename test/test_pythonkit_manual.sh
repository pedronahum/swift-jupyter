#!/bin/bash
# Manual test script for PythonKit + matplotlib integration
# This script runs the PythonKit test notebook and reports results

set -e

echo "=========================================="
echo "PythonKit + matplotlib Integration Test"
echo "=========================================="
echo ""

# Check if jupyter is installed
if ! command -v jupyter &> /dev/null; then
    echo "❌ Error: jupyter not found"
    echo "Please install: /usr/bin/python3 -m pip install --user jupyter"
    exit 1
fi

# Check if the kernel is registered
if ! jupyter kernelspec list | grep -q swift; then
    echo "❌ Error: Swift kernel not registered"
    echo "Please run: python3 register.py"
    exit 1
fi

echo "✅ Jupyter is installed"
echo "✅ Swift kernel is registered"
echo ""

# Check if matplotlib is available in the system Python
if /usr/bin/python3 -c "import matplotlib" 2>/dev/null; then
    echo "✅ matplotlib is available in system Python"
else
    echo "⚠️  matplotlib not found in system Python"
    echo "Installing matplotlib..."
    /usr/bin/python3 -m pip install --user matplotlib numpy
fi

echo ""
echo "=========================================="
echo "Running PythonKit Test Notebook"
echo "=========================================="
echo ""
echo "IMPORTANT: This will open Jupyter in your browser."
echo "Please manually execute all cells in the notebook:"
echo ""
echo "  examples/test_pythonkit_matplotlib.ipynb"
echo ""
echo "Expected results:"
echo "  ✅ All cells should execute without errors"
echo "  ✅ You should see 4 plots displayed inline"
echo "  ✅ Final cell should show 'All tests PASSED'"
echo ""
echo "Press Ctrl+C in this terminal when done testing."
echo ""
read -p "Press Enter to launch Jupyter..."

# Launch Jupyter with the test notebook
jupyter notebook examples/test_pythonkit_matplotlib.ipynb
