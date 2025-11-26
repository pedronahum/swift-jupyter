#!/usr/bin/env python3
"""Test magic commands."""

import jupyter_client
import time

print("Starting kernel...")
km, kc = jupyter_client.manager.start_new_kernel(kernel_name='swift')

try:
    # Test 1: %help command
    print("\n" + "="*70)
    print("Test 1: %help command")
    print("="*70)
    kc.execute("%help")
    reply = kc.get_shell_msg(timeout=15)

    # Get stdout
    timeout_time = time.time() + 3
    while time.time() < timeout_time:
        try:
            msg = kc.get_iopub_msg(timeout=1)
            if msg['msg_type'] == 'stream' and msg['content']['name'] == 'stdout':
                print(msg['content']['text'])
                break
        except:
            break

    # Clear messages
    try:
        while True:
            kc.get_iopub_msg(timeout=0.1)
    except:
        pass

    # Test 2: %timeit command
    print("\n" + "="*70)
    print("Test 2: %timeit command")
    print("="*70)
    kc.execute("%timeit let x = Array(1...100).reduce(0, +)")
    reply = kc.get_shell_msg(timeout=15)

    timeout_time = time.time() + 3
    while time.time() < timeout_time:
        try:
            msg = kc.get_iopub_msg(timeout=1)
            if msg['msg_type'] == 'stream':
                print(msg['content']['text'])
        except:
            break

    # Clear messages
    try:
        while True:
            kc.get_iopub_msg(timeout=0.1)
    except:
        pass

    # Test 3: Regular code execution (to initialize Swift)
    print("\n" + "="*70)
    print("Test 3: Running some Swift code")
    print("="*70)
    kc.execute("let myVar = 42\nprint(myVar)")
    reply = kc.get_shell_msg(timeout=15)

    timeout_time = time.time() + 3
    while time.time() < timeout_time:
        try:
            msg = kc.get_iopub_msg(timeout=1)
            if msg['msg_type'] == 'stream':
                print("Output:", msg['content']['text'])
        except:
            break

    # Clear messages
    try:
        while True:
            kc.get_iopub_msg(timeout=0.1)
    except:
        pass

    # Test 4: %who command
    print("\n" + "="*70)
    print("Test 4: %who command")
    print("="*70)
    kc.execute("%who")
    reply = kc.get_shell_msg(timeout=15)

    timeout_time = time.time() + 3
    while time.time() < timeout_time:
        try:
            msg = kc.get_iopub_msg(timeout=1)
            if msg['msg_type'] == 'stream':
                print(msg['content']['text'])
                break
        except:
            break

    # Clear messages
    try:
        while True:
            kc.get_iopub_msg(timeout=0.1)
    except:
        pass

    # Test 5: %reset command
    print("\n" + "="*70)
    print("Test 5: %reset command")
    print("="*70)
    kc.execute("%reset")
    reply = kc.get_shell_msg(timeout=15)

    timeout_time = time.time() + 3
    while time.time() < timeout_time:
        try:
            msg = kc.get_iopub_msg(timeout=1)
            if msg['msg_type'] == 'stream':
                print(msg['content']['text'])
        except:
            break

finally:
    print("\n" + "="*70)
    print("Shutting down kernel...")
    kc.stop_channels()
    km.shutdown_kernel()
    print("Done!")
