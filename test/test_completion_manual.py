
import unittest
import jupyter_kernel_test
import time

class SwiftCompletionTest(jupyter_kernel_test.KernelTests):
    language_name = 'swift'
    kernel_name = 'swift'

    def test_completion(self):
        # Define a function
        self.execute_helper(code='func myUniqueFunction() {}')
        
        # Try to complete it
        self.kc.complete('myUnique')
        reply = self.kc.get_shell_msg(timeout=10)
        
        print(f"\nCompletion Reply: {reply['content']}")
        
        matches = reply['content']['matches']
        self.assertTrue(len(matches) > 0, "No matches found")
        self.assertTrue(any('myUniqueFunction' in m for m in matches), f"Expected function not found in {matches}")

if __name__ == '__main__':
    unittest.main()
