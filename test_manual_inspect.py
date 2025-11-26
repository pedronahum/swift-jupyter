#!/usr/bin/env python3
"""Manual test for inspect functionality."""

import jupyter_client
import time

print("Starting kernel...")
km, kc = jupyter_client.manager.start_new_kernel(kernel_name='swift')

try:
    # Execute some code to define a struct
    code = """
struct MyStruct {
    /// This is a test method
    func myMethod() -> Int {
        return 42
    }
}
let s = MyStruct()
"""
    print("Executing code to define MyStruct...")
    kc.execute(code)
    reply = kc.get_shell_msg(timeout=15)
    print(f"Execute reply status: {reply['content']['status']}")

    # Flush iopub messages
    time.sleep(0.5)
    try:
        while True:
            msg = kc.get_iopub_msg(timeout=0.1)
    except:
        pass

    # Now try to inspect 's'
    print("\nSending inspect request for 's'...")
    kc.inspect("s", 1, detail_level=0)

    # Get the reply
    while True:
        msg = kc.get_shell_msg(timeout=15)
        if msg['msg_type'] == 'inspect_reply':
            content = msg['content']
            print(f"\nInspect reply:")
            print(f"  Status: {content['status']}")
            print(f"  Found: {content['found']}")
            if content['found']:
                print(f"  Data keys: {content['data'].keys()}")
                if 'text/plain' in content['data']:
                    print(f"  Content:\n{content['data']['text/plain']}")
            break

    # Try inspecting method name
    print("\n\nSending inspect request for 'myMethod'...")
    inspect_code = "s.myMethod"
    cursor_pos = len(inspect_code)

    # Send inspect manually via kernel client
    msg_id = kc.inspect(inspect_code, cursor_pos, detail_level=0)

    while True:
        msg = kc.get_shell_msg(timeout=15)
        if msg['msg_type'] == 'inspect_reply':
            content = msg['content']
            print(f"\nInspect reply for myMethod:")
            print(f"  Status: {content['status']}")
            print(f"  Found: {content['found']}")
            if content['found']:
                print(f"  Data keys: {content['data'].keys()}")
                if 'text/plain' in content['data']:
                    print(f"  Content:\n{content['data']['text/plain']}")
            break

finally:
    print("\nShutting down kernel...")
    kc.stop_channels()
    km.shutdown_kernel()
    print("Done.")
