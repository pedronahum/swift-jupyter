#!/usr/bin/env python3
"""Test enhanced error messages with helpful suggestions."""

import jupyter_client
import time

print("Starting kernel...")
km, kc = jupyter_client.manager.start_new_kernel(kernel_name='swift')

try:
    test_cases = [
        # Test 1: Immutable variable assignment
        ("""let x = 5
x = 10""", "Immutable variable error"),

        # Test 2: Undeclared identifier
        ("print(undefinedVariable)", "Undeclared identifier error"),

        # Test 3: Type mismatch
        ('let num: Int = "hello"', "Type mismatch error"),

        # Test 4: Optional unwrapping
        ("""let optional: Int? = nil
let value: Int = optional""", "Optional unwrapping error"),
    ]

    for code, description in test_cases:
        print(f"\n{'='*70}")
        print(f"Test: {description}")
        print(f"Code: {code!r}")
        print(f"{'='*70}")

        kc.execute(code)

        # Wait for execute_reply
        reply = kc.get_shell_msg(timeout=15)

        # Look for error messages in iopub
        timeout_time = time.time() + 5
        found_error = False

        while time.time() < timeout_time:
            try:
                msg = kc.get_iopub_msg(timeout=1)
                if msg['msg_type'] == 'error':
                    found_error = True
                    traceback = msg['content']['traceback']
                    print("\n❌ Error received:")
                    for line in traceback:
                        print(line)
                    break
            except:
                break

        if not found_error:
            print("✓ No error (unexpected)")

        # Clear remaining messages
        try:
            while True:
                kc.get_iopub_msg(timeout=0.1)
        except:
            pass

finally:
    print("\n" + "="*70)
    print("Shutting down kernel...")
    kc.stop_channels()
    km.shutdown_kernel()
    print("Done!")
