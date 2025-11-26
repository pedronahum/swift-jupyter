
import unittest
import jupyter_kernel_test
import time

class SwiftCompletionRepro(jupyter_kernel_test.KernelTests):
    language_name = 'swift'
    kernel_name = 'swift'

    def test_multicell_completion(self):
        self.flush_channels()
        
        # Cell 1: Define a struct
        self.execute_helper(code='struct MyStruct { func myMethod() -> Int { return 42 } }')
        self.flush_channels()
        
        # Cell 2: Instantiate it
        self.execute_helper(code='let myInstance = MyStruct()')
        self.flush_channels()
        
        # Cell 3: Try to complete the method
        # We type 'myInstance.myM'
        self.kc.complete('myInstance.myM')
        reply = self.kc.get_shell_msg(timeout=10)
        
        print(f"\nCompletion Reply: {reply['content']}")
        
        matches = reply['content']['matches']
        self.assertTrue(len(matches) > 0, "No matches found")
        self.assertTrue(any('myMethod' in m for m in matches), f"Expected 'myMethod' in {matches}")

if __name__ == '__main__':
    unittest.main()
