#!/usr/bin/env python3
"""Test matplotlib support in Swift kernel."""

import jupyter_client
import time

print("🧪 Testing matplotlib support in Swift kernel...\n")

km, kc = jupyter_client.manager.start_new_kernel(kernel_name='swift', startup_timeout=60)

try:
    kc.wait_for_ready(timeout=60)
    print("✅ Kernel started\n")

    # Test 1: Check if Python interop is available
    print("📝 Test 1: Checking Python interop...")
    msg_id = kc.execute('import Python')

    outputs = []
    errors = []
    while True:
        try:
            msg = kc.get_iopub_msg(timeout=10)
            if msg['msg_type'] == 'stream':
                outputs.append(msg['content']['text'])
            elif msg['msg_type'] == 'error':
                errors.append('\n'.join(msg['content']['traceback']))
            elif msg['msg_type'] == 'status' and msg['content']['execution_state'] == 'idle':
                break
        except:
            break

    reply = kc.get_shell_msg(timeout=5)

    if reply['content']['status'] == 'ok':
        print("✅ Python interop is available\n")
    else:
        print("❌ Python interop NOT available")
        if errors:
            print("Error:", errors[0])
        print("\nThis Swift toolchain may not have Python interop support.")
        print("Skipping matplotlib tests.\n")
        km.shutdown_kernel(now=True)
        exit(0)

    # Test 2: Try to import numpy
    print("📝 Test 2: Importing numpy via Python interop...")
    msg_id = kc.execute('let np = Python.import("numpy")')

    errors = []
    while True:
        try:
            msg = kc.get_iopub_msg(timeout=10)
            if msg['msg_type'] == 'error':
                errors.append('\n'.join(msg['content']['traceback']))
            elif msg['msg_type'] == 'status' and msg['content']['execution_state'] == 'idle':
                break
        except:
            break

    reply = kc.get_shell_msg(timeout=5)

    if reply['content']['status'] == 'ok':
        print("✅ numpy imported successfully\n")
    else:
        print("❌ Failed to import numpy")
        if errors:
            print("Error:", errors[0][:500])
        print()

    # Test 3: Try to import matplotlib
    print("📝 Test 3: Importing matplotlib.pyplot...")
    msg_id = kc.execute('let plt = Python.import("matplotlib.pyplot")')

    errors = []
    while True:
        try:
            msg = kc.get_iopub_msg(timeout=10)
            if msg['msg_type'] == 'error':
                errors.append('\n'.join(msg['content']['traceback']))
            elif msg['msg_type'] == 'status' and msg['content']['execution_state'] == 'idle':
                break
        except:
            break

    reply = kc.get_shell_msg(timeout=5)

    if reply['content']['status'] == 'ok':
        print("✅ matplotlib.pyplot imported successfully\n")
    else:
        print("❌ Failed to import matplotlib.pyplot")
        if errors:
            print("Error:", errors[0][:500])
        print()

    # Test 4: Try to load EnableIPythonDisplay.swift
    print("📝 Test 4: Loading EnableIPythonDisplay.swift...")
    msg_id = kc.execute('%include "EnableIPythonDisplay.swift"')

    errors = []
    outputs = []
    while True:
        try:
            msg = kc.get_iopub_msg(timeout=10)
            if msg['msg_type'] == 'stream':
                outputs.append(msg['content']['text'])
            elif msg['msg_type'] == 'error':
                errors.append('\n'.join(msg['content']['traceback']))
            elif msg['msg_type'] == 'status' and msg['content']['execution_state'] == 'idle':
                break
        except:
            break

    reply = kc.get_shell_msg(timeout=5)

    if reply['content']['status'] == 'ok':
        print("✅ EnableIPythonDisplay.swift loaded successfully\n")
    else:
        print("❌ Failed to load EnableIPythonDisplay.swift")
        if errors:
            print("Error:", errors[0][:500])
        if outputs:
            print("Output:", outputs[0][:500])
        print()

    # Test 5: Try to enable matplotlib inline
    print("📝 Test 5: Enabling matplotlib inline...")
    msg_id = kc.execute('IPythonDisplay.shell.enable_matplotlib("inline")')

    errors = []
    while True:
        try:
            msg = kc.get_iopub_msg(timeout=10)
            if msg['msg_type'] == 'error':
                errors.append('\n'.join(msg['content']['traceback']))
            elif msg['msg_type'] == 'status' and msg['content']['execution_state'] == 'idle':
                break
        except:
            break

    reply = kc.get_shell_msg(timeout=5)

    if reply['content']['status'] == 'ok':
        print("✅ matplotlib inline mode enabled\n")
    else:
        print("❌ Failed to enable matplotlib inline")
        if errors:
            print("Error:", errors[0][:500])
        print()

    # Test 6: Try to create a simple plot
    print("📝 Test 6: Creating a simple plot...")
    msg_id = kc.execute('''
let x = np.arange(0, 10, 0.1)
let y = np.sin(x)
plt.plot(x, y)
plt.show()
''')

    errors = []
    display_data = []
    while True:
        try:
            msg = kc.get_iopub_msg(timeout=10)
            if msg['msg_type'] == 'error':
                errors.append('\n'.join(msg['content']['traceback']))
            elif msg['msg_type'] == 'display_data':
                display_data.append(msg['content'])
            elif msg['msg_type'] == 'status' and msg['content']['execution_state'] == 'idle':
                break
        except:
            break

    reply = kc.get_shell_msg(timeout=5)

    if reply['content']['status'] == 'ok' and display_data:
        print("✅ Plot created successfully!")
        print(f"   Display data mimetypes: {list(display_data[0]['data'].keys())}")
        if 'image/png' in display_data[0]['data']:
            print("   ✅ PNG image data present!\n")
        else:
            print("   ⚠️  No PNG image in display data\n")
    else:
        print("❌ Failed to create plot")
        if errors:
            print("Error:", errors[0][:500])
        print()

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print("If all tests passed, matplotlib support is working!")
    print("If tests failed, check the errors above for diagnosis.")

finally:
    km.shutdown_kernel(now=True)
