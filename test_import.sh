#!/bin/bash
export PYTHONPATH="/Users/pedro/Library/Developer/Toolchains/swift-DEVELOPMENT-SNAPSHOT-2025-10-02-a.xctoolchain/System/Library/PrivateFrameworks/LLDB.framework/Resources/Python"
export DYLD_FRAMEWORK_PATH="/Users/pedro/Library/Developer/Toolchains/swift-DEVELOPMENT-SNAPSHOT-2025-10-02-a.xctoolchain/System/Library/PrivateFrameworks"
export LD_LIBRARY_PATH="/Users/pedro/Library/Developer/Toolchains/swift-DEVELOPMENT-SNAPSHOT-2025-10-02-a.xctoolchain/usr/lib/swift/macosx:/Users/pedro/miniforge3/envs/swift-jupyter-39/lib"

/Users/pedro/miniforge3/envs/swift-jupyter-39/bin/python3 -c "import sys; sys.path.insert(0, '$PYTHONPATH'); import lldb; print('Success! LLDB version:', lldb.SBDebugger.GetVersionString())"
