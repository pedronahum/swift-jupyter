#!/usr/bin/env python3
"""Test the new magic commands: %lsmagic, %env, %swift-version, %load, %save, %history"""

import jupyter_client
import time

print("Starting kernel...")
km, kc = jupyter_client.manager.start_new_kernel(kernel_name='swift')

def execute_and_print(code, timeout=15):
    """Execute code and print the output."""
    print(f"\n{'='*70}")
    print(f"Executing: {code}")
    print('='*70)

    kc.execute(code)

    try:
        reply = kc.get_shell_msg(timeout=timeout)
        print(f"Status: {reply['content']['status']}")
    except Exception as e:
        print(f"Error getting reply: {e}")
        return

    # Collect output messages
    timeout_time = time.time() + 5
    while time.time() < timeout_time:
        try:
            msg = kc.get_iopub_msg(timeout=0.5)
            msg_type = msg['msg_type']

            if msg_type == 'stream':
                text = msg['content']['text']
                print(text, end='')
            elif msg_type == 'error':
                print("Error:")
                for line in msg['content']['traceback']:
                    print(line)
            elif msg_type == 'status':
                if msg['content']['execution_state'] == 'idle':
                    break
        except:
            break
    print()

try:
    # Test 1: %lsmagic
    execute_and_print('%lsmagic')

    # Test 2: %env (show specific variable)
    execute_and_print('%env PATH')

    # Test 3: %env (set variable)
    execute_and_print('%env MY_TEST_VAR=hello_world')

    # Test 4: %env (verify it was set)
    execute_and_print('%env MY_TEST_VAR')

    # Test 5: %swift-version
    execute_and_print('%swift-version')

    # Test 6: Execute some Swift code to build history
    execute_and_print('let x = 42')
    execute_and_print('let message = "Hello, Swift!"')
    execute_and_print('print(x + 10)')

    # Test 7: %history
    execute_and_print('%history')

    # Test 8: %history -n 2 (show only last 2 entries)
    execute_and_print('%history -n 2')

    # Test 9: Test %load with a non-existent file (should show error)
    execute_and_print('%load /nonexistent/file.swift')

    # Test 10: Updated %help
    execute_and_print('%help')

finally:
    print("\n" + "="*70)
    print("Shutting down kernel...")
    kc.stop_channels()
    km.shutdown_kernel()
    print("Done!")
