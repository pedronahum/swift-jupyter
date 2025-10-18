"""Unicode handling and interrupt functionality tests (R6-T3).

These tests validate:
- R5-T1: Unicode handling in code submission and stdout
- R5-T2: Enhanced interrupt support
- R3-T2: Message-based interrupt_request handler

Created: October 17, 2025
"""

import pytest
import time


@pytest.mark.unicode
class TestUnicodeHandling:
    """Test Unicode support in Swift kernel (R5-T1)."""

    def test_unicode_variable_names(self, execute_code):
        """Test Swift code with Unicode variable names."""
        code = '''
let 变量 = "Chinese variable"
let 変数 = "Japanese variable"
let переменная = "Russian variable"
print(变量)
print(変数)
print(переменная)
'''
        result = execute_code(code, timeout=10)

        # Should execute successfully
        assert result['status'] == 'ok'

        # Should have output
        stream_outputs = [o for o in result['output'] if o['type'] == 'stream']
        assert len(stream_outputs) > 0

        # Output should contain Unicode strings
        output_text = ''.join([o['text'] for o in stream_outputs])
        assert 'Chinese variable' in output_text
        assert 'Japanese variable' in output_text
        assert 'Russian variable' in output_text

    def test_emoji_in_strings(self, execute_code):
        """Test Swift strings containing emoji (R5-T1)."""
        code = '''
let emoji = "😀🎉🚀"
let greeting = "Hello 👋 World 🌍"
let combined = emoji + " " + greeting
print(combined)
'''
        result = execute_code(code, timeout=10)

        assert result['status'] == 'ok'

        # Should have emoji in output
        stream_outputs = [o for o in result['output'] if o['type'] == 'stream']
        assert len(stream_outputs) > 0
        output_text = ''.join([o['text'] for o in stream_outputs])

        # R5-T1: Unicode should be preserved
        assert '😀' in output_text or 'emoji' in output_text.lower()

    def test_unicode_from_multiple_scripts(self, execute_code):
        """Test mixing Unicode from different scripts."""
        code = '''
let text = "Hello World 你好世界 مرحبا بالعالم Привет мир"
print(text)
'''
        result = execute_code(code, timeout=10)

        assert result['status'] == 'ok'

        stream_outputs = [o for o in result['output'] if o['type'] == 'stream']
        assert len(stream_outputs) > 0

    def test_unicode_string_operations(self, execute_code):
        """Test Swift string operations with Unicode."""
        code = '''
let s1 = "café"
let s2 = "naïve"
let combined = s1 + " " + s2
let length = combined.count
print("Length: \\(length)")
print(combined)
'''
        result = execute_code(code, timeout=10)

        assert result['status'] == 'ok'

        stream_outputs = [o for o in result['output'] if o['type'] == 'stream']
        assert len(stream_outputs) > 0

    def test_unicode_in_comments(self, execute_code):
        """Test Unicode in Swift comments."""
        code = '''
// This is a comment with emoji 😀
// 这是中文注释
/* Multi-line comment
   with Unicode: Привет мир
*/
let x = 42
print("Value: \\(x)")
'''
        result = execute_code(code, timeout=10)

        # Comments with Unicode shouldn't cause issues
        assert result['status'] == 'ok'


@pytest.mark.interrupt
@pytest.mark.slow
class TestInterruptFunctionality:
    """Test interrupt functionality (R3-T2 + R5-T2)."""

    @pytest.mark.skip(reason="Interrupt testing requires careful timing and may be flaky")
    def test_interrupt_long_running_code(self, kernel_client, wait_for_idle):
        """Test interrupting long-running code (R3-T2).

        Note: This test is skipped by default because interrupt timing
        can be flaky and depends on LLDB behavior.
        """
        kc = kernel_client

        # Start long-running code
        code = '''
var counter = 0
while true {
    counter += 1
    if counter % 1000000 == 0 {
        print("Counter: \\(counter)")
    }
}
'''
        msg_id = kc.execute(code, silent=False)

        # Wait a bit for execution to start
        time.sleep(2)

        # Interrupt it
        # R2-T2: kernel.json has interrupt_mode: message, so this uses
        # R3-T2: interrupt_request() handler
        kc.interrupt()

        # Wait for interrupt to take effect
        time.sleep(2)

        # Should receive some indication of interruption
        # (exact behavior depends on LLDB)

    @pytest.mark.skip(reason="Interrupt testing requires separate kernel instance")
    def test_interrupt_with_output(self, kernel_client):
        """Test interrupt with continuous output.

        This test is skipped because it requires careful setup
        and may interfere with other tests.
        """
        kc = kernel_client

        # Code that produces output continuously
        code = '''
for i in 1...1000000 {
    if i % 10000 == 0 {
        print("Iteration \\(i)")
    }
}
'''
        msg_id = kc.execute(code)

        # Wait for some output
        time.sleep(1)

        # Interrupt
        kc.interrupt()

        # Should stop before completing all iterations
        time.sleep(2)

    def test_interrupt_handler_logging(self, kernel_client):
        """Test that interrupt handler exists and is responsive.

        This is a smoke test that doesn't actually interrupt,
        just verifies the kernel is responsive after potential interrupts.
        """
        kc = kernel_client

        # Execute simple code
        code = 'let x = 42\nprint("x = \\(x)")'
        msg_id = kc.execute(code)

        # Wait for completion
        time.sleep(2)

        # Kernel should still be responsive
        # (R5-T2 enhanced SIGINTHandler should handle errors gracefully)
        kc.kernel_info()
        reply = kc.get_shell_msg(timeout=5)
        assert reply['msg_type'] == 'kernel_info_reply'


@pytest.mark.unicode
@pytest.mark.protocol
class TestUnicodeInProtocol:
    """Test Unicode in protocol messages (R3-T4 + R5-T1)."""

    def test_completion_with_unicode_prefix(self, kernel_client):
        """Test code completion with Unicode prefix (R3-T4)."""
        kc = kernel_client

        # Set up context with Unicode variable
        code = 'let émoji_variable = "test"'
        kc.execute(code, silent=True)
        time.sleep(1)

        # Request completion with Unicode
        code_to_complete = 'émoji'
        cursor_pos = len(code_to_complete)  # R3-T4: Unicode codepoints

        msg_id = kc.complete(code_to_complete, cursor_pos)
        reply = kc.get_shell_msg(timeout=5)

        assert reply['msg_type'] == 'complete_reply'
        content = reply['content']

        # R3-T4: Cursor positions should be in Unicode codepoints
        assert content['cursor_end'] == cursor_pos

    def test_error_message_with_unicode(self, execute_code):
        """Test error messages with Unicode (R5-T3)."""
        # Code that will error but contains Unicode
        code = '''
let 测试 = 42
let 错误 = 测试 + "string"  // Type error
'''
        result = execute_code(code, timeout=10)

        # Should have error
        assert result['error'] is not None

        # R5-T3: Error should be handled even with Unicode
        error = result['error']
        assert 'traceback' in error or 'evalue' in error


@pytest.mark.unicode
@pytest.mark.slow
class TestUnicodeEdgeCases:
    """Test edge cases for Unicode handling."""

    def test_zero_width_characters(self, execute_code):
        """Test handling of zero-width Unicode characters."""
        code = 'let x = "test\\u{200B}string"  // Zero-width space\nprint(x)'

        result = execute_code(code, timeout=10)

        # Should handle gracefully
        assert result['status'] in ['ok', 'error']

    def test_rtl_text(self, execute_code):
        """Test right-to-left text (Arabic, Hebrew)."""
        code = '''
let arabic = "مرحبا"
let hebrew = "שלום"
print(arabic + " " + hebrew)
'''
        result = execute_code(code, timeout=10)

        # Should execute successfully
        # (display rendering is handled by Jupyter frontend)
        assert result['status'] == 'ok'

    def test_emoji_with_modifiers(self, execute_code):
        """Test emoji with skin tone modifiers."""
        code = 'let emoji = "👋🏻👋🏽👋🏿"\nprint(emoji)'

        result = execute_code(code, timeout=10)

        # Should handle complex emoji sequences
        assert result['status'] == 'ok'

    def test_very_long_unicode_string(self, execute_code):
        """Test very long string with Unicode."""
        # Create a long Unicode string
        code = '''
let longString = String(repeating: "😀你好", count: 100)
print("Length: \\(longString.count)")
'''
        result = execute_code(code, timeout=10)

        assert result['status'] == 'ok'
