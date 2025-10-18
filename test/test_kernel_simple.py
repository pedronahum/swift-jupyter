#!/usr/bin/env python3
"""Simple test to verify Swift kernel works."""

import jupyter_client
import time

print("🚀 Starting Swift kernel...")
try:
    km, kc = jupyter_client.manager.start_new_kernel(
        kernel_name='swift',
        startup_timeout=60
    )
    print("✅ Kernel manager started")

    print("⏳ Waiting for kernel to be ready...")
    kc.wait_for_ready(timeout=60)
    print("✅ Kernel is ready!")

    # Test kernel_info
    print("\n📨 Requesting kernel_info...")
    msg_id = kc.kernel_info()
    reply = kc.get_shell_msg(timeout=10)
    print(f"✅ Received reply: {reply['msg_type']}")

    content = reply['content']
    print(f"   Protocol version: {content.get('protocol_version')}")
    print(f"   Language: {content.get('language_info', {}).get('name')}")
    print(f"   Language version: {content.get('language_info', {}).get('version')}")

    # Test code execution
    print("\n📨 Executing code: print(\"Hello from Swift!\")")
    msg_id = kc.execute('print("Hello from Swift!")')

    # Collect outputs
    outputs = []
    while True:
        try:
            msg = kc.get_iopub_msg(timeout=5)
            msg_type = msg['msg_type']
            print(f"   Received: {msg_type}")

            if msg_type == 'stream':
                text = msg['content']['text']
                print(f"   Output: {repr(text)}")
                outputs.append(text)
            elif msg_type == 'execute_reply':
                break
            elif msg_type == 'status' and msg['content']['execution_state'] == 'idle':
                pass  # Expected
        except Exception as e:
            print(f"   Timeout or error: {e}")
            break

    # Get execute reply
    reply = kc.get_shell_msg(timeout=5)
    status = reply['content']['status']
    print(f"✅ Execution status: {status}")

    if outputs:
        print(f"✅ Test PASSED - Got output: {outputs}")
    else:
        print(f"⚠️  Test incomplete - No output received")

    print("\n🛑 Shutting down kernel...")
    km.shutdown_kernel(now=True)
    print("✅ Kernel shutdown complete")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
