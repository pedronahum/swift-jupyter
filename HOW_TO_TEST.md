# How to Test Swift Jupyter Kernel

## Method 1: Simple Python Test Script (Easiest)

Run the included test script:

```bash
cd /Users/pedro/programming/swift/swift-jupyter
/usr/bin/python3 test_kernel_simple.py
```

You should see:
```
🚀 Starting Swift kernel...
✅ Kernel manager started
⏳ Waiting for kernel to be ready...
✅ Kernel is ready!
📨 Requesting kernel_info...
✅ Received reply: kernel_info_reply
📨 Executing code: print("Hello from Swift!")
   Output: 'Hello from Swift!\r\n'
✅ Execution status: ok
✅ Test PASSED
```

## Method 2: Jupyter Console (Interactive)

Start an interactive Swift REPL in your terminal:

```bash
/Users/pedro/Library/Python/3.9/bin/jupyter console --kernel=swift
```

Then type Swift code:
```swift
In [1]: print("Hello, Swift!")
Hello, Swift!

In [2]: let x = 42
In [3]: print("The answer is \(x)")
The answer is 42

In [4]: func greet(name: String) {
   ...:     print("Hello, \(name)!")
   ...: }
In [5]: greet(name: "World")
Hello, World!
```

Press `Ctrl+D` to exit.

## Method 3: Jupyter Notebook (Web Interface)

Start Jupyter Notebook:

```bash
/Users/pedro/Library/Python/3.9/bin/jupyter notebook
```

This will open your web browser. Then:
1. Click "New" in the top right
2. Select "Swift" from the dropdown
3. Type Swift code in a cell and press `Shift+Enter`:
   ```swift
   print("Hello from Swift Notebook!")
   ```

## Method 4: Run the Official Test Suite

Run the repository's test suite:

```bash
cd /Users/pedro/programming/swift/swift-jupyter
/usr/bin/python3 test/fast_test.py SwiftKernelTests
```

Expected output:
```
Ran 22 tests in ~11s
FAILED (failures=6, skipped=10)
```

16 tests should pass (6 failures are expected - they require TensorFlow/Python interop).

## Method 5: Run a Single Test

Test just one specific feature:

```bash
# Test basic execution
/usr/bin/python3 test/fast_test.py SwiftKernelTests.test_execute_result

# Test print statements
/usr/bin/python3 test/fast_test.py SwiftKernelTests.test_stdout

# Test error handling
/usr/bin/python3 test/fast_test.py SwiftKernelTests.test_code_generate_error
```

## Troubleshooting

If you get errors:

1. **Make sure you're using system Python 3.9.6:**
   ```bash
   /usr/bin/python3 --version
   # Should show: Python 3.9.6
   ```

2. **Check kernel registration:**
   ```bash
   /Users/pedro/Library/Python/3.9/bin/jupyter kernelspec list
   # Should show 'swift' kernel
   ```

3. **Verify LLDB imports:**
   ```bash
   PYTHONPATH="/Users/pedro/Library/Developer/Toolchains/swift-DEVELOPMENT-SNAPSHOT-2025-10-02-a.xctoolchain/System/Library/PrivateFrameworks/LLDB.framework/Resources/Python" /usr/bin/python3 -c "import lldb; print('LLDB OK')"
   # Should print: LLDB OK
   ```

## What Tests Should Pass

These core features work:
- ✅ Basic Swift code execution
- ✅ Print statements
- ✅ Variable declarations
- ✅ Function definitions
- ✅ Error messages
- ✅ Multi-line code
- ✅ Extensions
- ✅ Structs and classes

These features have known limitations:
- ⚠️  matplotlib graphics (needs Python interop setup)
- ⚠️  Interrupts (timing-sensitive)
- ⚠️  TensorFlow tensors (needs Swift for TensorFlow)
- ⚠️  Code completion (version-dependent)
