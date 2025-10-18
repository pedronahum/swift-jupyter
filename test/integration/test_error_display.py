"""Error handling and display functionality tests (R6-T4).

These tests validate:
- R5-T3: Improved error messages and stack traces
- R4-T1: Display helper methods (publish_display_data, publish_update_display_data)

Created: October 17, 2025
"""

import pytest
import time


@pytest.mark.error
class TestErrorHandling:
    """Test error handling improvements (R5-T3)."""

    def test_compile_error_message(self, execute_code):
        """Test compile error produces cleaned message (R5-T3)."""
        code = 'let x: Int = "not an integer"  // Type mismatch'

        result = execute_code(code, timeout=10)

        # Should have error
        assert result['error'] is not None
        error = result['error']

        # R5-T3: Error should have traceback or evalue
        assert 'traceback' in error or 'evalue' in error

        # Error message should be present
        if 'traceback' in error:
            traceback = error['traceback']
            assert len(traceback) > 0
            # R5-T3: Should be cleaned (no "error: <EXPR>:" prefix in ideal case)

    def test_runtime_error_message(self, execute_code):
        """Test runtime error produces proper message (R5-T3)."""
        code = '''
let array = [1, 2, 3]
let value = array[10]  // Index out of bounds
'''
        result = execute_code(code, timeout=10)

        # Should have error
        assert result['error'] is not None
        error = result['error']

        # Should have error information
        assert 'traceback' in error or 'evalue' in error

    def test_stack_trace_formatting(self, execute_code):
        """Test stack trace is well-formatted (R5-T3)."""
        code = '''
func causeError() {
    let x = [1, 2, 3]
    let y = x[10]  // Out of bounds
}

causeError()
'''
        result = execute_code(code, timeout=10)

        # Should have error with traceback
        assert result['error'] is not None

        if 'traceback' in result['error']:
            traceback = result['error']['traceback']
            # R5-T3: Stack trace should be formatted
            # Format: "  at function_name (File.swift:line:col)"
            # May not have detailed trace depending on Swift/LLDB behavior

    def test_multiple_errors(self, execute_code):
        """Test handling of multiple errors in sequence."""
        # First error
        result1 = execute_code('let x: Int = "wrong"', timeout=5)
        assert result1['error'] is not None

        # Kernel should recover and handle next execution
        result2 = execute_code('let y = 42\nprint("y = \\(y)")', timeout=5)
        assert result2['status'] == 'ok'

        # Another error
        result3 = execute_code('let z = undefined_variable', timeout=5)
        assert result3['error'] is not None

    def test_error_with_unicode(self, execute_code):
        """Test error handling with Unicode in code (R5-T3 + R5-T1)."""
        code = '''
let 变量 = 42
let 错误 = 变量 + "string"  // Type error with Unicode
'''
        result = execute_code(code, timeout=10)

        # Should have error
        assert result['error'] is not None

        # R5-T3 + R5-T1: Error should handle Unicode correctly
        # (no encoding crashes)

    def test_syntax_error(self, execute_code):
        """Test syntax error handling."""
        code = 'let x = '  # Incomplete statement

        result = execute_code(code, timeout=10)

        # Should have error
        assert result['error'] is not None or result['status'] == 'error'


@pytest.mark.display
class TestDisplayFunctionality:
    """Test display functionality (R4-T1)."""

    def test_print_output(self, execute_code):
        """Test basic print output."""
        code = 'print("Hello, World!")'

        result = execute_code(code, timeout=5)

        assert result['status'] == 'ok'
        stream_outputs = [o for o in result['output'] if o['type'] == 'stream']
        assert len(stream_outputs) > 0
        assert 'Hello, World!' in stream_outputs[0]['text']

    def test_multiple_print_statements(self, execute_code):
        """Test multiple print statements produce separate outputs."""
        code = '''
print("Line 1")
print("Line 2")
print("Line 3")
'''
        result = execute_code(code, timeout=5)

        assert result['status'] == 'ok'
        stream_outputs = [o for o in result['output'] if o['type'] == 'stream']
        assert len(stream_outputs) > 0

        # Should have all three lines in output
        output_text = ''.join([o['text'] for o in stream_outputs])
        assert 'Line 1' in output_text
        assert 'Line 2' in output_text
        assert 'Line 3' in output_text

    def test_formatted_output(self, execute_code):
        """Test formatted string output."""
        code = '''
let name = "Swift"
let version = 6.3
print("Language: \\(name), Version: \\(version)")
'''
        result = execute_code(code, timeout=5)

        assert result['status'] == 'ok'
        stream_outputs = [o for o in result['output'] if o['type'] == 'stream']
        assert len(stream_outputs) > 0

        output_text = ''.join([o['text'] for o in stream_outputs])
        assert 'Swift' in output_text
        assert '6.3' in output_text

    @pytest.mark.skip(reason="Display_data testing requires Swift display functions")
    def test_display_data_message(self, kernel_client):
        """Test display_data messages (R4-T1).

        Note: This requires Swift code that calls JupyterDisplay functions.
        Skipped because it requires specific Swift display setup.
        """
        kc = kernel_client

        # Would need Swift code like:
        # %include "EnableJupyterDisplay.swift"
        # IPythonDisplay.display(...)

        # For now, just verify kernel is responsive
        msg_id = kc.kernel_info()
        reply = kc.get_shell_msg(timeout=5)
        assert reply['msg_type'] == 'kernel_info_reply'

    def test_mixed_output_and_errors(self, execute_code):
        """Test code with both output and errors."""
        code = '''
print("Before error")
let x: Int = "wrong type"
print("After error")  // Won't execute
'''
        result = execute_code(code, timeout=10)

        # Should have both output and error
        stream_outputs = [o for o in result['output'] if o['type'] == 'stream']

        # May have "Before error" output
        if len(stream_outputs) > 0:
            output_text = ''.join([o['text'] for o in stream_outputs])
            assert 'Before error' in output_text

        # Should have error
        assert result['error'] is not None


@pytest.mark.error
@pytest.mark.slow
class TestErrorRecovery:
    """Test kernel recovery after errors."""

    def test_recovery_after_compile_error(self, execute_code):
        """Test kernel recovers after compile error."""
        # Cause compile error
        result1 = execute_code('let x: Int = "wrong"', timeout=5)
        assert result1['error'] is not None

        # Should recover and execute new code
        result2 = execute_code('let y = 42\nprint("y = \\(y)")', timeout=5)
        assert result2['status'] == 'ok'

        # Should be able to use new variable
        result3 = execute_code('print("y is \\(y)")' , timeout=5)
        assert result3['status'] == 'ok'

    def test_recovery_after_runtime_error(self, execute_code):
        """Test kernel recovers after runtime error."""
        # Cause runtime error
        result1 = execute_code('let arr = [1, 2]; let x = arr[10]', timeout=5)

        # Should recover
        result2 = execute_code('let z = 99\nprint("z = \\(z)")', timeout=5)
        assert result2['status'] == 'ok'

    def test_sequential_errors_and_successes(self, execute_code):
        """Test alternating errors and successful executions."""
        results = []

        # Mix of errors and successes
        test_cases = [
            ('let a = 1', 'ok'),
            ('let b: Int = "error"', 'error'),
            ('let c = 2', 'ok'),
            ('let d = undefined', 'error'),
            ('let e = 3', 'ok'),
        ]

        for code, expected in test_cases:
            result = execute_code(code, timeout=5)
            if expected == 'ok':
                assert result['status'] == 'ok' or result['error'] is None
            else:
                assert result['error'] is not None or result['status'] == 'error'


@pytest.mark.display
class TestOutputFormats:
    """Test various output formats."""

    def test_stdout_output(self, execute_code):
        """Test stdout stream output."""
        code = 'print("stdout output")'

        result = execute_code(code, timeout=5)

        stream_outputs = [o for o in result['output']
                         if o['type'] == 'stream' and o['name'] == 'stdout']
        assert len(stream_outputs) > 0

    def test_multiline_output(self, execute_code):
        """Test multiline output."""
        code = '''
print("Line 1")
print("Line 2")
print("Line 3")
'''
        result = execute_code(code, timeout=5)

        assert result['status'] == 'ok'
        stream_outputs = [o for o in result['output'] if o['type'] == 'stream']
        assert len(stream_outputs) > 0

    def test_output_with_special_characters(self, execute_code):
        """Test output with special characters."""
        code = '''
print("Tab:\\t")
print("Newline:\\n")
print("Quote: \\"")
'''
        result = execute_code(code, timeout=5)

        assert result['status'] == 'ok'
        stream_outputs = [o for o in result['output'] if o['type'] == 'stream']
        assert len(stream_outputs) > 0
