#!/usr/bin/env python3
import sys

print(f"Python version: {sys.version}")
print(f"Python executable: {sys.executable}")

# Add LLDB path
lldb_path = "/Users/pedro/Library/Developer/Toolchains/swift-DEVELOPMENT-SNAPSHOT-2025-10-02-a.xctoolchain/System/Library/PrivateFrameworks/LLDB.framework/Resources/Python"
print(f"\nAdding to sys.path: {lldb_path}")
sys.path.insert(0, lldb_path)

print(f"\nsys.path[0:3]: {sys.path[0:3]}")

try:
    import lldb
    print(f"\n✅ LLDB imported successfully!")
    print(f"LLDB file: {lldb.__file__}")
    print(f"LLDB version: {lldb.SBDebugger.GetVersionString()}")
except Exception as e:
    print(f"\n❌ Failed to import LLDB:")
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
