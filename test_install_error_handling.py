#!/usr/bin/env python3
"""Test package installation error handling."""

import jupyter_client
import time

print("Starting kernel...")
km, kc = jupyter_client.manager.start_new_kernel(kernel_name='swift')

try:
    # Test: Try to install a non-existent package to see error handling
    print("\n" + "="*70)
    print("Test: Installing non-existent package (should show helpful error)")
    print("="*70)

    code = "%install '.package(url: \"https://github.com/nonexistent/package\", from: \"1.0.0\")' FakePackage"

    print(f"Executing: {code}")
    kc.execute(code)

    # Wait for execute_reply
    reply = kc.get_shell_msg(timeout=120)

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
                print("\n❌ Error (this is expected - should show helpful message):")
                for line in msg['content']['traceback']:
                    print(line)
                break
            elif msg_type == 'status':
                status = msg['content']['execution_state']
                if status == 'idle':
                    break
        except:
            break

    print("\n" + "="*70)
    print("Reply status:", reply['content']['status'])

finally:
    print("\n" + "="*70)
    print("Shutting down kernel...")
    kc.stop_channels()
    km.shutdown_kernel()
    print("Done!")
