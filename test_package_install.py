#!/usr/bin/env python3
"""Test package installation with progress indicators and error handling."""

import jupyter_client
import time

print("Starting kernel...")
km, kc = jupyter_client.manager.start_new_kernel(kernel_name='swift')

try:
    # Test: Install a small package to see progress indicators
    print("\n" + "="*70)
    print("Test: Installing a Swift package (PromiseKit)")
    print("="*70)

    # Note: This will show progress indicators if it works
    code = "%install '.package(url: \"https://github.com/mxcl/PromiseKit\", from: \"6.0.0\")' PromiseKit"

    print(f"Executing: {code}")
    kc.execute(code)

    # Wait for execute_reply
    reply = kc.get_shell_msg(timeout=300)  # 5 minute timeout for package install

    print("\n📥 Messages received:")
    # Collect all output messages
    timeout_time = time.time() + 10
    while time.time() < timeout_time:
        try:
            msg = kc.get_iopub_msg(timeout=1)
            msg_type = msg['msg_type']

            if msg_type == 'stream':
                text = msg['content']['text']
                print(text, end='')
            elif msg_type == 'error':
                print("\n❌ Error:")
                for line in msg['content']['traceback']:
                    print(line)
            elif msg_type == 'status':
                status = msg['content']['execution_state']
                if status == 'idle':
                    break
        except:
            break

    print("\n" + "="*70)
    print("Reply status:", reply['content']['status'])

    # Clear remaining messages
    try:
        while True:
            kc.get_iopub_msg(timeout=0.1)
    except:
        pass

    # Test 2: Try to use the installed package
    print("\n" + "="*70)
    print("Test: Verify package is usable")
    print("="*70)

    code = """
import PromiseKit
print("PromiseKit imported successfully!")
"""

    kc.execute(code)
    reply = kc.get_shell_msg(timeout=15)

    timeout_time = time.time() + 5
    while time.time() < timeout_time:
        try:
            msg = kc.get_iopub_msg(timeout=1)
            if msg['msg_type'] == 'stream':
                print("Output:", msg['content']['text'])
            elif msg['msg_type'] == 'error':
                print("❌ Error:")
                for line in msg['content']['traceback']:
                    print(line)
        except:
            break

finally:
    print("\n" + "="*70)
    print("Shutting down kernel...")
    kc.stop_channels()
    km.shutdown_kernel()
    print("Done!")
