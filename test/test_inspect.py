import unittest
import jupyter_client
import os
import time
import shutil
import sys

class TestInspect(unittest.TestCase):
    def setUp(self):
        self.kernel_name = 'swift'
        self.km, self.kc = jupyter_client.manager.start_new_kernel(
            kernel_name=self.kernel_name
        )

    def tearDown(self):
        self.kc.stop_channels()
        self.km.shutdown_kernel()

    def test_inspect_simple(self):
        # 1. Define a struct with documentation
        code = """
        /// This is a test struct
        struct MyStruct {
            /// This is a test method
            func myMethod() {}
        }
        let s = MyStruct()
        """
        self.kc.execute(code)
        reply = self.kc.get_shell_msg(timeout=10)
        self.assertEqual(reply['content']['status'], 'ok')
        
        # Flush any extra messages
        try:
            while True:
                msg = self.kc.get_shell_msg(timeout=0.1)
                print(f"DEBUG: Flushed shell msg: {msg['msg_type']}")
        except:
            pass

        # 2. Inspect the struct instance
        # Code: "s"
        # Cursor pos: 1
        print("DEBUG: Sending inspect request...", file=sys.stderr)
        self.kc.inspect("s", 1)
        
        # Check IOPub for debug prints
        try:
            while True:
                msg = self.kc.get_iopub_msg(timeout=1)
                if msg['msg_type'] == 'stream':
                    print(f"DEBUG: IOPub stream: {msg['content']['text']}")
        except:
            pass

        # Wait for inspect_reply
        while True:
            reply = self.kc.get_shell_msg(timeout=10)
            print(f"DEBUG: Received shell msg: {reply['msg_type']}")
            if reply['msg_type'] == 'inspect_reply':
                break
        
        content = reply['content']
        print(f"DEBUG: Inspect reply content: {content}")
        self.assertEqual(content['status'], 'ok')
        self.assertTrue(content['found'])
        self.assertIn('text/plain', content['data'])
        # We expect the doc comment to be present
        self.assertIn('This is a test struct', str(content['data']))

if __name__ == '__main__':
    unittest.main()
