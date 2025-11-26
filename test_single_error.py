#!/usr/bin/env python3
"""Test a single error message."""

import jupyter_client
import time

print("Starting kernel...")
km, kc = jupyter_client.manager.start_new_kernel(kernel_name='swift')

try:
    code = "print(undefinedVariable)"
    print(f"Testing code: {code}")
    print("="*70)

    kc.execute(code)

    # Wait for execute_reply
    reply = kc.get_shell_msg(timeout=15)

    # Look for error messages in iopub
    timeout_time = time.time() + 5

    while time.time() < timeout_time:
        try:
            msg = kc.get_iopub_msg(timeout=1)
            if msg['msg_type'] == 'error':
                traceback = msg['content']['traceback']
                print("\n❌ Error received:")
                for line in traceback:
                    print(line)
                break
        except:
            break

finally:
    print("\n" + "="*70)
    print("Shutting down kernel...")
    kc.stop_channels()
    km.shutdown_kernel()
    print("Done!")
