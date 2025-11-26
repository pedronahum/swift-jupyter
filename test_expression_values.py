#!/usr/bin/env python3
"""Test expression value display."""

import jupyter_client
import time

print("Starting kernel...")
km, kc = jupyter_client.manager.start_new_kernel(kernel_name='swift')

try:
    test_cases = [
        ("42", "simple integer"),
        ("let x = 100\nx", "variable reference"),
        ('"hello world"', "string literal"),
        ('[1, 2, 3]', "array literal"),
        ('let msg = "test"\nmsg', "string variable"),
    ]

    for code, description in test_cases:
        print(f"\n{'='*60}")
        print(f"Test: {description}")
        print(f"Code: {code!r}")
        print(f"{'='*60}")

        kc.execute(code)

        # Wait for execute_reply
        reply = kc.get_shell_msg(timeout=15)

        # Check for execute_result in iopub
        found_result = False
        timeout = time.time() + 5
        while time.time() < timeout:
            try:
                msg = kc.get_iopub_msg(timeout=1)
                if msg['msg_type'] == 'execute_result':
                    content = msg['content']
                    print(f"✓ Got result!")
                    print(f"  Execution count: {content['execution_count']}")
                    if 'text/plain' in content['data']:
                        value = content['data']['text/plain']
                        print(f"  Value displayed: {value!r}")
                        found_result = True
                        break
            except:
                break

        if not found_result:
            print("✗ No execute_result received")

        # Clear remaining messages
        try:
            while True:
                kc.get_iopub_msg(timeout=0.1)
        except:
            pass

finally:
    print("\n" + "="*60)
    print("Shutting down kernel...")
    kc.stop_channels()
    km.shutdown_kernel()
    print("Done!")
