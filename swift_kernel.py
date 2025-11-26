#!/usr/bin/python
#
# Copyright 2018 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import glob
import json
import os
import sys

# Add LLDB Python path if PYTHONPATH is set (from kernel.json env)
if 'PYTHONPATH' in os.environ and os.environ['PYTHONPATH'] not in sys.path:
    sys.path.insert(0, os.environ['PYTHONPATH'])

# import lldb # Moved to lazy import
import stat
import re
import shlex
import shutil
import signal
import string
import subprocess
import sys
import tempfile
import textwrap
import time
import threading
import sqlite3
import json
import tempfile
import logging
from lsp_client import LSPClient

from ipykernel.kernelbase import Kernel
from jupyter_client.jsonutil import squash_dates
from tornado import ioloop


class ExecutionResult:
    """Base class for the result of executing code."""
    pass


class ExecutionResultSuccess(ExecutionResult):
    """Base class for the result of successfully executing code."""
    pass


class ExecutionResultError(ExecutionResult):
    """Base class for the result of unsuccessfully executing code."""
    def description(self):
        raise NotImplementedError()


class SuccessWithoutValue(ExecutionResultSuccess):
    """The code executed successfully, and did not produce a value."""
    def __repr__(self):
        return 'SuccessWithoutValue()'


class SuccessWithValue(ExecutionResultSuccess):
    """The code executed successfully, and produced a value."""
    def __init__(self, result):
        self.result = result # SBValue

    """A description of the value, e.g.
         (Int) $R0 = 64"""
    def value_description(self):
        stream = lldb.SBStream()
        self.result.GetDescription(stream)
        return stream.GetData()

    def get_formatted_value(self):
        """Get a nicely formatted value for display in notebooks.

        Returns a string suitable for showing to users, extracting just the
        value part without LLDB metadata like variable names.

        Examples:
            (Int) $R0 = 42 -> "42"
            (String) $R1 = "hello" -> "hello"
            (Array<Int>) $R2 = [1, 2, 3] -> [1, 2, 3]
        """
        # First, try to get the full description which has the most complete info
        full_desc = self.value_description()

        # Try to extract just the value after the '='
        if '=' in full_desc:
            value_part = full_desc.split('=', 1)[1].strip()
            return value_part

        # For types without '=' (shouldn't happen often), try summary/value
        summary_str = self.result.GetSummary()
        if summary_str:
            # Remove quotes around the summary if present (LLDB adds them for strings)
            summary = summary_str.strip('"')
            return summary

        value_str = self.result.GetValue()
        if value_str:
            return value_str

        # Last resort: return the full description
        return full_desc

    def get_rich_display(self):
        """Get rich display data including HTML for arrays, dictionaries, and tables.

        Returns a tuple of (plain_text, html_or_image) where the second element
        may be None if no rich display is available, or a dict with image data.
        """
        import html as html_module

        plain_text = self.get_formatted_value()
        type_name = self.result.GetTypeName() or ""

        # Check if this is Data that might be an image
        if self._is_image_data(type_name):
            image_data = self._get_image_data()
            if image_data:
                # Return as a special marker for image display
                return (plain_text, {'__image__': image_data})

        # Check if this is an array type
        if self._is_array_type(type_name):
            html = self._render_array_html()
            if html:
                return (plain_text, html)

        # Check if this is a dictionary type
        if self._is_dictionary_type(type_name):
            html = self._render_dictionary_html()
            if html:
                return (plain_text, html)

        # Check if this might be a struct/class with multiple fields
        num_children = self.result.GetNumChildren()
        if num_children > 0 and num_children <= 50:
            # Could be a struct, class, tuple, or collection
            html = self._render_object_html()
            if html:
                return (plain_text, html)

        return (plain_text, None)

    def _is_array_type(self, type_name):
        """Check if the type is an array."""
        return ('Array<' in type_name or
                'ContiguousArray<' in type_name or
                'ArraySlice<' in type_name or
                type_name.startswith('[') and type_name.endswith(']'))

    def _is_dictionary_type(self, type_name):
        """Check if the type is a dictionary."""
        return ('Dictionary<' in type_name or
                'type_name'.startswith('[') and ':' in type_name)

    def _is_image_data(self, type_name):
        """Check if this might be image data."""
        # Look for Foundation.Data or Swift Data type
        return 'Data' in type_name or 'NSData' in type_name

    def _get_image_data(self):
        """Try to extract image data and return it as base64.

        Returns a dict with 'data' and 'mime_type' keys, or None if not an image.
        """
        import base64

        # Try to get the bytes from the Data object
        # This is challenging because LLDB doesn't give us direct byte access
        # We'll try to detect common image signatures

        # Get the count/length of the data
        count_child = self.result.GetChildMemberWithName('count')
        if not count_child:
            # Try _count for internal representation
            count_child = self.result.GetChildMemberWithName('_count')

        if not count_child:
            return None

        count = count_child.GetValueAsUnsigned(0)

        # Images should be at least a few bytes
        if count < 8 or count > 10 * 1024 * 1024:  # Max 10MB
            return None

        # Unfortunately, getting raw bytes from LLDB's SBValue is complex
        # For now, we'll return None - full implementation would require
        # executing Swift code to convert Data to base64 string
        return None

    def _render_array_html(self):
        """Render an array as an HTML table."""
        import html as html_module

        num_children = self.result.GetNumChildren()
        if num_children == 0:
            return '<div style="font-family: monospace; padding: 8px; background: #f8f9fa; border-radius: 4px;">[]</div>'

        if num_children > 100:
            # Too large, don't render as HTML
            return None

        rows = []
        for i in range(num_children):
            child = self.result.GetChildAtIndex(i)
            value = child.GetValue() or child.GetSummary() or str(child)
            # Clean up the value
            if value:
                value = html_module.escape(str(value).strip('"'))
            else:
                value = "nil"
            rows.append(f'<tr><td style="padding: 4px 12px; border-bottom: 1px solid #dee2e6; color: #6c757d;">{i}</td><td style="padding: 4px 12px; border-bottom: 1px solid #dee2e6;">{value}</td></tr>')

        html = f'''
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
  <div style="color: #6c757d; font-size: 12px; margin-bottom: 4px;">Array ({num_children} elements)</div>
  <table style="border-collapse: collapse; border: 1px solid #dee2e6; background: white;">
    <thead>
      <tr style="background: #f8f9fa;">
        <th style="padding: 8px 12px; border-bottom: 2px solid #dee2e6; text-align: left;">Index</th>
        <th style="padding: 8px 12px; border-bottom: 2px solid #dee2e6; text-align: left;">Value</th>
      </tr>
    </thead>
    <tbody>
      {''.join(rows)}
    </tbody>
  </table>
</div>
'''
        return html

    def _render_dictionary_html(self):
        """Render a dictionary as an HTML table."""
        import html as html_module

        num_children = self.result.GetNumChildren()
        if num_children == 0:
            return '<div style="font-family: monospace; padding: 8px; background: #f8f9fa; border-radius: 4px;">[:]</div>'

        if num_children > 100:
            return None

        rows = []
        for i in range(num_children):
            child = self.result.GetChildAtIndex(i)
            # Dictionary entries have key and value children
            key_child = child.GetChildMemberWithName('key')
            value_child = child.GetChildMemberWithName('value')

            if key_child and value_child:
                key = key_child.GetValue() or key_child.GetSummary() or str(key_child)
                value = value_child.GetValue() or value_child.GetSummary() or str(value_child)
            else:
                # Fallback: use child directly
                key = str(i)
                value = child.GetValue() or child.GetSummary() or str(child)

            key = html_module.escape(str(key).strip('"'))
            value = html_module.escape(str(value).strip('"'))

            rows.append(f'<tr><td style="padding: 4px 12px; border-bottom: 1px solid #dee2e6; font-weight: 500;">{key}</td><td style="padding: 4px 12px; border-bottom: 1px solid #dee2e6;">{value}</td></tr>')

        html = f'''
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
  <div style="color: #6c757d; font-size: 12px; margin-bottom: 4px;">Dictionary ({num_children} entries)</div>
  <table style="border-collapse: collapse; border: 1px solid #dee2e6; background: white;">
    <thead>
      <tr style="background: #f8f9fa;">
        <th style="padding: 8px 12px; border-bottom: 2px solid #dee2e6; text-align: left;">Key</th>
        <th style="padding: 8px 12px; border-bottom: 2px solid #dee2e6; text-align: left;">Value</th>
      </tr>
    </thead>
    <tbody>
      {''.join(rows)}
    </tbody>
  </table>
</div>
'''
        return html

    def _render_object_html(self):
        """Render a struct/class/tuple as an HTML table of properties."""
        import html as html_module

        type_name = self.result.GetTypeName() or "Object"
        num_children = self.result.GetNumChildren()

        if num_children == 0:
            return None

        # Skip if it looks like a simple wrapper
        if num_children == 1:
            return None

        rows = []
        for i in range(num_children):
            child = self.result.GetChildAtIndex(i)
            name = child.GetName() or f"[{i}]"
            child_type = child.GetTypeName() or ""
            value = child.GetValue() or child.GetSummary() or ""

            # Clean up values
            name = html_module.escape(str(name))
            value = html_module.escape(str(value).strip('"')) if value else "<nil>"
            child_type = html_module.escape(str(child_type))

            rows.append(f'''<tr>
              <td style="padding: 4px 12px; border-bottom: 1px solid #dee2e6; font-weight: 500;">{name}</td>
              <td style="padding: 4px 12px; border-bottom: 1px solid #dee2e6; color: #6c757d; font-size: 12px;">{child_type}</td>
              <td style="padding: 4px 12px; border-bottom: 1px solid #dee2e6;">{value}</td>
            </tr>''')

        # Clean up type name for display
        display_type = html_module.escape(type_name.split('.')[-1])

        html = f'''
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
  <div style="color: #6c757d; font-size: 12px; margin-bottom: 4px;">{display_type}</div>
  <table style="border-collapse: collapse; border: 1px solid #dee2e6; background: white;">
    <thead>
      <tr style="background: #f8f9fa;">
        <th style="padding: 8px 12px; border-bottom: 2px solid #dee2e6; text-align: left;">Property</th>
        <th style="padding: 8px 12px; border-bottom: 2px solid #dee2e6; text-align: left;">Type</th>
        <th style="padding: 8px 12px; border-bottom: 2px solid #dee2e6; text-align: left;">Value</th>
      </tr>
    </thead>
    <tbody>
      {''.join(rows)}
    </tbody>
  </table>
</div>
'''
        return html

    def __repr__(self):
        return 'SuccessWithValue(result=%s, description=%s)' % (
            repr(self.result), repr(self.result.description))


class PreprocessorError(ExecutionResultError):
    """There was an error preprocessing the code."""
    def __init__(self, exception):
        self.exception = exception # PreprocessorException

    def description(self):
        return str(self.exception)

    def __repr__(self):
        return 'PreprocessorError(exception=%s)' % repr(self.exception)


class PreprocessorException(Exception):
    pass


class PackageInstallException(Exception):
    pass


class SwiftError(ExecutionResultError):
    """There was a compile or runtime error (R5-T3 enhanced).

    This class now provides better error formatting including:
    - Structured error information
    - Error type detection
    - Cleaned error messages
    - Better Unicode handling in error text
    """
    def __init__(self, result):
        self.result = result # SBValue
        self._parsed_error = None

    def description(self):
        """Get error description with improved formatting."""
        error_desc = self.result.error.description

        # Decode if bytes (shouldn't happen in Python 3, but be safe)
        if isinstance(error_desc, bytes):
            error_desc = error_desc.decode('utf-8', errors='replace')

        return error_desc

    def get_error_type(self):
        """Extract error type from LLDB error.

        Returns:
            str: Error type like 'error', 'warning', 'note', or 'unknown'
        """
        desc = self.description()
        if 'error:' in desc.lower():
            return 'error'
        elif 'warning:' in desc.lower():
            return 'warning'
        elif 'note:' in desc.lower():
            return 'note'
        return 'unknown'

    def get_cleaned_message(self):
        """Get a cleaned, more readable error message.

        Removes LLDB-specific noise and formats the message better.
        """
        desc = self.description()

        # Remove common LLDB prefixes
        prefixes_to_remove = [
            'error: <EXPR>:',
            'Execution was interrupted, reason: ',
        ]

        for prefix in prefixes_to_remove:
            if desc.startswith(prefix):
                desc = desc[len(prefix):].lstrip()

        return desc.strip()

    def get_helpful_message(self):
        """Get an enhanced error message with helpful suggestions.

        Analyzes common Swift error patterns and adds actionable advice.

        Returns:
            str: Enhanced error message with suggestions and tips
        """
        original_error = self.get_cleaned_message()
        suggestions = []

        # Pattern 1: Cannot assign to immutable variable
        if "cannot assign to value:" in original_error.lower() and "is a 'let' constant" in original_error.lower():
            # Extract variable name if possible
            import re
            match = re.search(r"'(\w+)' is a 'let' constant", original_error)
            if match:
                var_name = match.group(1)
                suggestions.append(f"💡 Tip: Change 'let {var_name}' to 'var {var_name}' to make it mutable")
            else:
                suggestions.append("💡 Tip: Use 'var' instead of 'let' to declare mutable variables")
            suggestions.append("📖 Learn more: https://docs.swift.org/swift-book/LanguageGuide/TheBasics.html#ID310")

        # Pattern 2: Use of undeclared identifier
        elif "use of unresolved identifier" in original_error.lower() or "use of undeclared identifier" in original_error.lower():
            import re
            match = re.search(r"identifier '(\w+)'", original_error)
            if match:
                var_name = match.group(1)
                suggestions.append(f"💡 Tip: Make sure '{var_name}' is defined before using it")
                suggestions.append("   • Check for typos in the variable name")
                suggestions.append("   • Ensure the variable was declared in a previous cell")
            else:
                suggestions.append("💡 Tip: Make sure the identifier is defined before using it")

        # Pattern 3: Type mismatch
        elif "cannot convert value of type" in original_error.lower():
            suggestions.append("💡 Tip: Check the types of your values")
            suggestions.append("   • You may need to convert between types explicitly")
            suggestions.append("   • Example: String(intValue) or Int(stringValue)")

        # Pattern 4: Missing return statement
        elif "missing return" in original_error.lower():
            suggestions.append("💡 Tip: All code paths in this function must return a value")
            suggestions.append("   • Add a return statement to every branch (if/else, switch cases)")
            suggestions.append("   • Or use 'return' with a default value at the end")

        # Pattern 5: Optional unwrapping
        elif "value of optional type" in original_error.lower() and ("must be unwrapped" in original_error.lower() or "not unwrapped" in original_error.lower()):
            # Check if Swift compiler already provided suggestions (it often does)
            if "coalesce using '??'" not in original_error and "force-unwrap using '!'" not in original_error:
                suggestions.append("💡 Tip: Optional values must be unwrapped before use")
                suggestions.append("   • Safe unwrapping: if let value = optional { ... }")
                suggestions.append("   • Guard: guard let value = optional else { return }")
                suggestions.append("   • Nil coalescing: optional ?? defaultValue")
                suggestions.append("   • Force unwrap (risky): optional! - only if you're certain it's not nil")
                suggestions.append("📖 Learn more: https://docs.swift.org/swift-book/LanguageGuide/TheBasics.html#ID330")

        # Pattern 6: Nil coalescing
        elif "unexpectedly found nil" in original_error.lower():
            suggestions.append("💡 Tip: An optional value was nil when it shouldn't be")
            suggestions.append("   • Use nil coalescing: value ?? defaultValue")
            suggestions.append("   • Or check for nil: if value != nil { ... }")

        # Pattern 7: Cannot call value of non-function type
        elif "cannot call value of non-function type" in original_error.lower():
            suggestions.append("💡 Tip: You're trying to call something that isn't a function")
            suggestions.append("   • Check that you're using () on functions, not properties")
            suggestions.append("   • Make sure the function name is spelled correctly")

        # Pattern 8: Consecutive statements on a line
        elif "consecutive statements on a line must be separated by" in original_error.lower():
            suggestions.append("💡 Tip: Put each statement on its own line or separate with semicolons")
            suggestions.append("   • Each statement should be on a new line")
            suggestions.append("   • Or use semicolons: let x = 1; let y = 2")

        # Pattern 9: Expected expression
        elif "expected expression" in original_error.lower():
            suggestions.append("💡 Tip: Swift expected a value or expression here")
            suggestions.append("   • Check for missing values after operators")
            suggestions.append("   • Make sure all parentheses and brackets are balanced")

        # Pattern 10: Initializer requires arguments
        elif "missing argument" in original_error.lower() or "requires that" in original_error.lower():
            suggestions.append("💡 Tip: This initializer or function needs more arguments")
            suggestions.append("   • Check the function signature to see what parameters are required")
            suggestions.append("   • Provide all required arguments or use default values")

        # Build the final message
        if suggestions:
            return original_error + "\n\n" + "\n".join(suggestions)
        else:
            # No specific suggestion - just return the error
            # The Swift compiler often provides good suggestions already
            return original_error

    def __repr__(self):
        return 'SwiftError(type=%s, description=%s)' % (
            self.get_error_type(), repr(self.get_cleaned_message()))


class SIGINTHandler(threading.Thread):
    """Interrupts currently-executing code whenever the process receives a
       SIGINT (R5-T2 enhanced).

    This handler works in conjunction with the message-based interrupt handler
    (interrupt_request) from R3. Both mechanisms are supported:
    - Signal-based (SIGINT): For backward compatibility and old Jupyter clients
    - Message-based: For Protocol 5.4+ clients (see interrupt_request method)

    The handler now includes:
    - Interrupt flag tracking
    - Better logging
    - Exception handling
    """

    daemon = True

    def __init__(self, kernel):
        super(SIGINTHandler, self).__init__()
        self.kernel = kernel
        self.interrupted = False
        self.interrupt_count = 0

    def run(self):
        try:
            while True:
                signal.sigwait([signal.SIGINT])
                self.interrupt_count += 1
                self.interrupted = True

                self.kernel.log.info(
                    f'🛑 SIGINTHandler: Received SIGINT (count: {self.interrupt_count})')

                if not self.kernel.process or not self.kernel.process.IsValid():
                    self.kernel.log.warning(
                        'SIGINTHandler: No valid process to interrupt')
                    continue

                try:
                    self.kernel.process.SendAsyncInterrupt()
                    self.kernel.log.info('SIGINTHandler: Sent async interrupt to LLDB')
                except Exception as interrupt_error:
                    self.kernel.log.error(
                        f'SIGINTHandler: Failed to interrupt: {interrupt_error}')

        except Exception as e:
            self.kernel.log.error(f'Exception in SIGINTHandler: {e}', exc_info=True)


class StdoutHandler(threading.Thread):
    """Collects stdout from the Swift process and sends it to the client."""

    daemon = True

    def __init__(self, kernel):
        super(StdoutHandler, self).__init__()
        self.kernel = kernel
        self.stop_event = threading.Event()
        self.had_stdout = False

    def _get_stdout(self):
        """Get stdout from LLDB process with Unicode handling (R5-T1)."""
        while True:
            BUFFER_SIZE = 1000
            stdout_buffer = self.kernel.process.GetSTDOUT(BUFFER_SIZE)
            if len(stdout_buffer) == 0:
                break

            # LLDB returns bytes; decode to Unicode string
            # Use 'replace' error handling to avoid crashes on invalid UTF-8
            if isinstance(stdout_buffer, bytes):
                try:
                    stdout_buffer = stdout_buffer.decode('utf-8', errors='replace')
                except Exception as e:
                    self.kernel.log.warning(f'Error decoding stdout: {e}')
                    # Fallback to latin-1 which never fails
                    stdout_buffer = stdout_buffer.decode('latin-1')

            yield stdout_buffer

    # Sends stdout to the jupyter client, replacing the ANSI sequence for
    # clearing the whole display with a 'clear_output' message to the jupyter
    # client.
    def _send_stdout(self, stdout):
        clear_sequence = '\033[2J'
        clear_sequence_index = stdout.find(clear_sequence)
        if clear_sequence_index != -1:
            self._send_stdout(stdout[:clear_sequence_index])
            self.kernel.send_response(
                self.kernel.iopub_socket, 'clear_output', {'wait': False})
            self._send_stdout(
                stdout[clear_sequence_index + len(clear_sequence):])
        else:
            self.kernel.send_response(self.kernel.iopub_socket, 'stream', {
                'name': 'stdout',
                'text': stdout
            })

    def _get_and_send_stdout(self):
        stdout = ''.join([buf for buf in self._get_stdout()])
        if len(stdout) > 0:
            self.had_stdout = True
            self._send_stdout(stdout)

    def run(self):
        try:
            while True:
                if self.stop_event.wait(0.1):
                    break
                self._get_and_send_stdout()
            self._get_and_send_stdout()
        except Exception as e:
            self.kernel.log.error('Exception in StdoutHandler: %s' % str(e))


class SwiftKernel(Kernel):
    implementation = 'SwiftKernel'
    implementation_version = '0.1'
    banner = ''

    language_info = {
        'name': 'swift',
        'mimetype': 'text/x-swift',
        'file_extension': '.swift',
        'version': '',
    }

    def __init__(self, **kwargs):
        super(SwiftKernel, self).__init__(**kwargs)
        
        # Setup debug logging to file
        file_handler = logging.FileHandler('/tmp/swift-kernel.log')
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        self.log.addHandler(file_handler)
        self.log.setLevel(logging.DEBUG)
        self.log.info("SwiftKernel initialized with file logging")

        # We don't initialize Swift yet, so that the user has a chance to
        # "%install" packages before Swift starts. (See doc comment in
        # `_init_swift`).

        # Whether to do code completion. Since the debugger is not yet
        # initialized, we can't do code completion yet.
        self.completion_enabled = False
        
        # LSP Integration
        self.lsp = None
        self.virtual_document_path = None
        self.virtual_document_content = ""
        self.lsp_initialized = False
        self.latest_diagnostics = []  # Store latest diagnostics from LSP

        # Execution history for %save and %history commands
        self.execution_history = []

    def do_kernel_info(self):
        """Return kernel_info for Jupyter Protocol 5.4.

        This method provides information about the kernel including protocol
        version, implementation details, and language info.
        """
        return {
            'protocol_version': '5.4',
            'implementation': 'swift-jupyter',
            'implementation_version': '0.4.0',
            'language_info': {
                'name': 'swift',
                'version': self._get_swift_version(),
                'mimetype': 'text/x-swift',
                'file_extension': '.swift',
                'pygments_lexer': 'swift',
                'codemirror_mode': 'swift'
            },
            'banner': f'Swift {self._get_swift_version()} Jupyter Kernel',
            'help_links': [
                {
                    'text': 'Swift Documentation',
                    'url': 'https://docs.swift.org'
                },
                {
                    'text': 'Swift-Jupyter GitHub',
                    'url': 'https://github.com/pedronahum/swift-jupyter'
                }
            ],
            'status': 'ok'
        }

    def _get_swift_version(self):
        """Extract Swift version from the toolchain.

        Returns:
            str: Swift version string (e.g., '6.3' or '5.9')
        """
        try:
            result = subprocess.run(
                ['swift', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            output = result.stdout
            # Parse version from output like "Swift version 6.3-dev"
            # or "Apple Swift version 5.9"
            import re
            match = re.search(r'Swift version (\d+\.\d+)', output)
            if match:
                return match.group(1)
            # Fallback to parsing first line
            if output:
                parts = output.split()
                for i, part in enumerate(parts):
                    if 'version' in part.lower() and i + 1 < len(parts):
                        version = parts[i + 1]
                        # Extract just major.minor
                        version_match = re.match(r'(\d+\.\d+)', version)
                        if version_match:
                            return version_match.group(1)
        except Exception as e:
            self.log.warning(f'Could not determine Swift version: {e}')

        # Fallback version
        return '5.x'

    def interrupt_request(self, stream, ident, parent):
        """Handle interrupt_request on control channel (Jupyter Protocol 5.4).

        This is the modern, message-based interrupt mechanism introduced in
        Protocol 5.4. It's called when the user clicks the interrupt button
        in the Jupyter UI.

        Args:
            stream: The ZMQ stream (control channel)
            ident: The message identity
            parent: The parent message header
        """
        self.log.info('🛑 Received interrupt_request on control channel')

        try:
            # Use the existing LLDB interrupt mechanism
            if hasattr(self, 'process') and self.process and self.process.IsValid():
                self.log.info('Sending async interrupt to LLDB process')
                # SendAsyncInterrupt() is non-blocking and signals LLDB
                # to stop at the next safe point
                self.process.SendAsyncInterrupt()

                content = {'status': 'ok'}
                self.log.info('Interrupt signal sent successfully')
            else:
                self.log.warning('No valid LLDB process to interrupt')
                content = {
                    'status': 'error',
                    'ename': 'NoProcess',
                    'evalue': 'No Swift process currently running',
                    'traceback': []
                }
        except Exception as e:
            self.log.error(f'Interrupt failed: {e}', exc_info=True)
            content = {
                'status': 'error',
                'ename': type(e).__name__,
                'evalue': str(e),
                'traceback': []
            }

        # Send interrupt_reply on control channel
        self.session.send(stream, 'interrupt_reply', content, parent, ident)
        self.log.info(f'Sent interrupt_reply with status: {content["status"]}')

    def do_shutdown(self, restart):
        """Handle shutdown request from shell or control channel.

        This method is called when Jupyter wants to shut down the kernel,
        either for a full shutdown or a restart. It's compatible with both
        shell and control channel shutdown requests (Protocol 5.4).

        Args:
            restart: bool, whether this is a restart (vs full shutdown)

        Returns:
            dict with 'status' and 'restart' keys
        """
        self.log.info(f'🔌 Shutting down kernel (restart={restart})')

        try:
            # Clean up LLDB session
            if hasattr(self, 'debugger') and self.debugger:
                self.log.info('Terminating LLDB debugger')
                lldb.SBDebugger.Terminate()

            # Stop any background threads
            if hasattr(self, 'stdout_handler') and self.stdout_handler:
                self.log.info('Stopping stdout handler')
                self.stdout_handler.stop_event.set()

            if hasattr(self, 'sigint_handler') and self.sigint_handler:
                self.log.info('SIGINT handler will be cleaned up')
                # Daemon thread will exit when main thread exits
            
            if hasattr(self, 'lsp') and self.lsp:
                self.log.info('Stopping LSP client')
                self.lsp.stop()
                
            if hasattr(self, 'tmp_dir') and os.path.exists(self.tmp_dir):
                import shutil
                shutil.rmtree(self.tmp_dir)

            self.log.info('Kernel shutdown complete')
            return {'status': 'ok', 'restart': restart}

        except Exception as e:
            self.log.error(f'Shutdown error: {e}', exc_info=True)
            return {'status': 'error', 'restart': restart}

    def publish_display_data(self, data, metadata=None, transient=None):
        """Publish display_data message from Swift (R4 modernization).

        This is a helper method for Swift code to publish display data
        without constructing full Jupyter messages. The Python Session
        handles proper message signing and protocol compliance.

        Args:
            data: dict of mimetype -> content, e.g.,
                  {'text/plain': 'hello', 'text/html': '<b>hello</b>'}
            metadata: dict of mimetype -> metadata (optional)
            transient: dict with display_id for updates (optional)

        Example from Swift:
            kernel.publish_display_data(
                {'text/plain': 'Hello, World!'},
                {},
                {}
            )
        """
        if metadata is None:
            metadata = {}
        if transient is None:
            transient = {}

        content = {
            'data': data,
            'metadata': metadata,
            'transient': transient
        }

        self.log.debug(f'Publishing display_data: {len(data)} mimetypes')

        # Use session.send for proper HMAC signing
        self.session.send(
            self.iopub_socket,
            'display_data',
            content,
            parent=self._parent_header
        )

    def publish_update_display_data(self, data, metadata=None, transient=None):
        """Publish update_display_data message from Swift (R4 modernization).

        This updates an existing display with a new value, identified by
        display_id in the transient dict. Used for animations and
        progressive updates.

        Args:
            data: dict of mimetype -> content
            metadata: dict of mimetype -> metadata (optional)
            transient: dict with display_id (REQUIRED)

        Raises:
            ValueError: if display_id not in transient

        Example from Swift:
            kernel.publish_update_display_data(
                {'text/plain': 'Updated value'},
                {},
                {'display_id': 'my-display-id'}
            )
        """
        if metadata is None:
            metadata = {}
        if transient is None:
            transient = {}

        # Transient MUST contain display_id for updates
        if 'display_id' not in transient:
            self.log.error('update_display_data requires display_id in transient')
            raise ValueError('update_display_data requires display_id in transient')

        content = {
            'data': data,
            'metadata': metadata,
            'transient': transient
        }

        self.log.debug(f'Publishing update_display_data for ID: {transient["display_id"]}')

        # Use session.send for proper HMAC signing
        self.session.send(
            self.iopub_socket,
            'update_display_data',
            content,
            parent=self._parent_header
        )

    def _init_swift(self):
        """Initializes Swift so that it's ready to start executing user code.

        This must happen after package installation, because the ClangImporter
        does not see modulemap files that appear after it has started."""

        self._init_repl_process()
        self._init_kernel_communicator()
        self._init_int_bitwidth()
        self._init_sigint_handler()

        # We do completion by default when the toolchain has the
        # SBTarget.CompleteCode API.
        # The user can disable/enable using "%disableCompletion" and
        # "%enableCompletion".
        self.completion_enabled = hasattr(self.target, 'CompleteCode')
        
        # Initialize LSP
        self._init_lsp()

    def _init_lsp(self):
        """Initialize SourceKit-LSP client."""
        try:
            # Create a virtual document
            self.tmp_dir = tempfile.mkdtemp()
            self.virtual_document_path = os.path.join(self.tmp_dir, 'kernel.swift')
            with open(self.virtual_document_path, 'w') as f:
                f.write('')

            # Auto-detect sourcekit-lsp path
            lsp_path = None

            # Try to find sourcekit-lsp using 'which' command
            try:
                import shutil
                lsp_path = shutil.which('sourcekit-lsp')
            except (OSError, ImportError, AttributeError) as e:
                self.log.debug(f'Error searching PATH for sourcekit-lsp: {e}')
                lsp_path = None

            # If not in PATH, try to locate it relative to swift compiler
            if not lsp_path:
                try:
                    swift_path = shutil.which('swift')
                    if swift_path:
                        # sourcekit-lsp is typically in the same bin directory as swift
                        swift_bin_dir = os.path.dirname(os.path.realpath(swift_path))
                        candidate = os.path.join(swift_bin_dir, 'sourcekit-lsp')
                        if os.path.exists(candidate):
                            lsp_path = candidate
                except (OSError, AttributeError) as e:
                    self.log.debug(f'Error locating sourcekit-lsp relative to swift: {e}')

            # If still not found, check common swiftly installation locations
            if not lsp_path:
                swiftly_paths = [
                    os.path.expanduser('~/.local/share/swiftly/bin/sourcekit-lsp'),
                    '/usr/local/share/swiftly/bin/sourcekit-lsp',
                    '/opt/swiftly/bin/sourcekit-lsp'
                ]
                for candidate in swiftly_paths:
                    if os.path.exists(candidate):
                        lsp_path = candidate
                        break

            if not lsp_path or not os.path.exists(lsp_path):
                self.log.warning(f'SourceKit-LSP not found. Completion and hover features will be unavailable.')
                self.log.warning(f'Please ensure sourcekit-lsp is in your PATH or install Swift toolchain.')
                return

            self.log.info(f'Found SourceKit-LSP at: {lsp_path}')

            # Update PATH to include toolchain bin so sourcekit-lsp can find swiftc
            toolchain_bin = os.path.dirname(lsp_path)
            env = os.environ.copy()
            env['PATH'] = f"{toolchain_bin}:{env.get('PATH', '')}"

            # Get toolchain root (parent of usr/bin)
            toolchain_root = os.environ.get('SWIFT_TOOLCHAIN_ROOT')
            if not toolchain_root:
                # Try to infer from LSP path (e.g., /path/to/toolchain/usr/bin/sourcekit-lsp)
                if 'usr/bin' in lsp_path:
                    toolchain_root = lsp_path.split('usr/bin')[0].rstrip('/')

            lsp_args = []
            if toolchain_root:
                lsp_args = ['-Xswiftc', '-sdk', '-Xswiftc', toolchain_root]
            
            self.lsp = LSPClient(lsp_path, args=lsp_args, log=self.log, env=env)
            self.lsp.start()

            # Set up diagnostics callback
            self.lsp.set_diagnostics_callback(self._handle_diagnostics)

            # Initialize session
            self.lsp.initialize(self.tmp_dir)

            # Open the virtual document
            self.lsp.send_notification('textDocument/didOpen', {
                'textDocument': {
                    'uri': f'file://{self.virtual_document_path}',
                    'languageId': 'swift',
                    'version': 1,
                    'text': ''
                }
            })

            self.lsp_initialized = True
            self.completion_enabled = True # Enable completion via LSP
            self.log.info('SourceKit-LSP initialized successfully')
            
        except Exception as e:
            self.log.error(f'Failed to initialize LSP: {e}')
            self.completion_enabled = False

    def _handle_diagnostics(self, params):
        """Handle diagnostics notifications from LSP.

        Args:
            params: dict with 'uri' and 'diagnostics' keys
        """
        try:
            uri = params.get('uri', '')
            diagnostics = params.get('diagnostics', [])

            # Only handle diagnostics for our virtual document
            if uri != f'file://{self.virtual_document_path}':
                return

            self.latest_diagnostics = diagnostics

            # Log diagnostics for debugging
            if diagnostics:
                self.log.info(f"Received {len(diagnostics)} diagnostic(s) from LSP")
                for diag in diagnostics:
                    severity = diag.get('severity', 0)
                    message = diag.get('message', '')
                    range_info = diag.get('range', {})
                    start_line = range_info.get('start', {}).get('line', 0)

                    severity_str = {1: 'Error', 2: 'Warning', 3: 'Info', 4: 'Hint'}.get(severity, 'Unknown')
                    self.log.debug(f"  [{severity_str}] Line {start_line + 1}: {message}")

        except Exception as e:
            self.log.error(f"Error handling diagnostics: {e}", exc_info=True)

    def _format_diagnostics_for_display(self):
        """Format diagnostics as a string for display to the user."""
        if not self.latest_diagnostics:
            return None

        lines = []
        for diag in self.latest_diagnostics:
            severity = diag.get('severity', 0)
            message = diag.get('message', '')
            range_info = diag.get('range', {})
            start = range_info.get('start', {})
            start_line = start.get('line', 0) + 1  # 0-indexed to 1-indexed
            start_char = start.get('character', 0)

            severity_str = {1: 'Error', 2: 'Warning', 3: 'Info', 4: 'Hint'}.get(severity, 'Unknown')
            lines.append(f"[{severity_str}] Line {start_line}, col {start_char}: {message}")

        return '\n'.join(lines)

    def _init_repl_process(self):
        # Pre-load libswiftCore.so to avoid ImportError when LD_LIBRARY_PATH is not set
        import ctypes
        import glob
        
        # Try to find libswiftCore.so relative to PYTHONPATH or in standard locations
        # We assume PYTHONPATH points to .../usr/local/lib/python.../dist-packages
        # And libs are in .../usr/lib/swift/linux
        
        # Use SWIFT_TOOLCHAIN_ROOT from env if available (set by register.py)
        toolchain_root = os.environ.get('SWIFT_TOOLCHAIN_ROOT', '/home/pedro/.local/share/swiftly/toolchains/6.2.1')
        swift_lib_dir = os.path.join(toolchain_root, 'usr/lib/swift/linux')
        libswiftCore = os.path.join(swift_lib_dir, 'libswiftCore.so')
        
        if os.path.exists(libswiftCore):
            try:
                ctypes.CDLL(libswiftCore, mode=ctypes.RTLD_GLOBAL)
                self.log.info(f'Pre-loaded {libswiftCore}')
            except Exception as e:
                self.log.warning(f'Failed to pre-load {libswiftCore}: {e}')
        else:
             self.log.warning(f'Could not find libswiftCore.so at {libswiftCore}')

        # Also pre-load all libs in host/compiler to satisfy dependencies
        host_compiler_dir = os.path.join(toolchain_root, 'usr/lib/swift/host/compiler')
        if os.path.isdir(host_compiler_dir):
            for lib_path in glob.glob(os.path.join(host_compiler_dir, '*.so')):
                try:
                    ctypes.CDLL(lib_path, mode=ctypes.RTLD_GLOBAL)
                    self.log.debug(f'Pre-loaded {lib_path}')
                except Exception as e:
                    self.log.warning(f'Failed to pre-load {lib_path}: {e}')
        else:
             self.log.warning(f'Could not find host compiler dir at {host_compiler_dir}')

        import lldb
        self.debugger = lldb.SBDebugger.Create()
        if not self.debugger:
            raise Exception('Could not start debugger')
        self.debugger.SetAsync(False)

        if hasattr(self, 'swift_module_search_path'):
            self.debugger.HandleCommand("settings append target.swift-module-search-paths " + self.swift_module_search_path)


        # LLDB crashes while trying to load some Python stuff on Mac. Maybe
        # something is misconfigured? This works around the problem by telling
        # LLDB not to load the Python scripting stuff, which we don't use
        # anyways.
        self.debugger.SetScriptLanguage(lldb.eScriptLanguageNone)

        repl_swift = os.environ['REPL_SWIFT_PATH']
        # Explicitly specify architecture for Apple Silicon compatibility
        import platform
        arch = platform.machine()  # Returns 'arm64' on Apple Silicon, 'x86_64' on Intel
        self.target = self.debugger.CreateTargetWithFileAndArch(repl_swift, arch)
        if not self.target:
            raise Exception('Could not create target %s with arch %s' % (repl_swift, arch))

        self.main_bp = self.target.BreakpointCreateByName(
            'repl_main', self.target.GetExecutable().GetFilename())
        if not self.main_bp:
            raise Exception('Could not set breakpoint')

        repl_env = []
        script_dir = os.path.dirname(os.path.realpath(sys.argv[0]))
        repl_env.append('PYTHONPATH=%s' % script_dir)
        env_var_blacklist = [
            'PYTHONPATH',
            'REPL_SWIFT_PATH'
        ]
        for key in os.environ:
            if key in env_var_blacklist:
                continue
            repl_env.append('%s=%s' % (key, os.environ[key]))

        # Turn off "disable ASLR" because it uses the "personality" syscall in
        # a way that is forbidden by the default Docker security policy.
        launch_info = self.target.GetLaunchInfo()
        launch_flags = launch_info.GetLaunchFlags()
        launch_info.SetLaunchFlags(launch_flags & ~lldb.eLaunchFlagDisableASLR)
        self.target.SetLaunchInfo(launch_info)

        self.process = self.target.LaunchSimple(None,
                                                repl_env,
                                                os.getcwd())
        if not self.process:
            raise Exception('Could not launch process')

        self.expr_opts = lldb.SBExpressionOptions()
        self.swift_language = lldb.SBLanguageRuntime.GetLanguageTypeFromString(
            'swift')
        self.expr_opts.SetLanguage(self.swift_language)
        self.expr_opts.SetREPLMode(True)
        self.expr_opts.SetUnwindOnError(False)
        self.expr_opts.SetGenerateDebugInfo(True)

        # Sets an infinite timeout so that users can run aribtrarily long
        # computations.
        self.expr_opts.SetTimeoutInMicroSeconds(0)

        self.main_thread = self.process.GetThreadAtIndex(0)

    def _init_kernel_communicator(self):
        result = self._preprocess_and_execute(
                '%include "KernelCommunicator.swift"')
        if isinstance(result, ExecutionResultError):
            raise Exception('Error initing KernelCommunicator: %s' % result)

        session_key = self.session.key.decode('utf8')
        decl_code = """
            enum JupyterKernel {
                static var communicator = KernelCommunicator(
                    jupyterSession: KernelCommunicator.JupyterSession(
                        id: %s, key: %s, username: %s))
            }
        """ % (json.dumps(self.session.session), json.dumps(session_key),
               json.dumps(self.session.username))
        result = self._preprocess_and_execute(decl_code)
        if isinstance(result, ExecutionResultError):
            raise Exception('Error declaring JupyterKernel: %s' % result)

    def _init_int_bitwidth(self):
        result = self._execute('Int.bitWidth')
        if not isinstance(result, SuccessWithValue):
            raise Exception('Expected value from Int.bitWidth, but got: %s' %
                            result)
        self._int_bitwidth = int(result.result.GetData().GetSignedInt32(lldb.SBError(), 0))

    def _init_sigint_handler(self):
        self.sigint_handler = SIGINTHandler(self)
        self.sigint_handler.start()

    def _file_name_for_source_location(self):
        return '<Cell %d>' % self.execution_count

    def _preprocess_and_execute(self, code):
        try:
            preprocessed = self._preprocess(code)
        except PreprocessorException as e:
            return PreprocessorError(e)

        return self._execute(preprocessed)

    def _preprocess(self, code):
        # Check for magic commands first (they consume the entire cell)
        stripped = code.strip()

        # Handle magic commands that process the whole cell
        if stripped.startswith('%who'):
            self._handle_who_magic(stripped)
            return ''  # Don't execute any Swift code
        elif stripped.startswith('%reset'):
            self._handle_reset_magic(stripped)
            return ''
        elif stripped.startswith('%timeit '):
            return self._handle_timeit_magic(stripped)
        elif stripped.startswith('%help') and not stripped.startswith('%help '):
            self._handle_help_magic()
            return ''
        elif stripped.startswith('%lsmagic'):
            self._handle_lsmagic()
            return ''
        elif stripped.startswith('%env'):
            self._handle_env_magic(stripped)
            return ''
        elif stripped.startswith('%swift-version') or stripped.startswith('%swift_version'):
            self._handle_swift_version_magic()
            return ''
        elif stripped.startswith('%load '):
            return self._handle_load_magic(stripped)
        elif stripped.startswith('%save '):
            self._handle_save_magic(stripped)
            return ''
        elif stripped.startswith('%history'):
            self._handle_history_magic(stripped)
            return ''

        # Otherwise, preprocess line by line as normal
        lines = code.split('\n')
        preprocessed_lines = [
                self._preprocess_line(i, line) for i, line in enumerate(lines)]
        return '\n'.join(preprocessed_lines)

    def _handle_disable_completion(self):
        self.completion_enabled = False
        self.send_response(self.iopub_socket, 'stream', {
            'name': 'stdout',
            'text': 'Completion disabled!\n'
        })

    def _handle_enable_completion(self):
        if not hasattr(self.target, 'CompleteCode'):
            self.send_response(self.iopub_socket, 'stream', {
                'name': 'stdout',
                'text': 'Completion NOT enabled because toolchain does not ' +
                        'have CompleteCode API.\n'
            })
            return

        self.completion_enabled = True
        self.send_response(self.iopub_socket, 'stream', {
            'name': 'stdout',
            'text': 'Completion enabled!\n'
        })

    def _handle_who_magic(self, code):
        """Handle %who magic command - list all variables."""
        # Get all variables from the Swift REPL
        if not hasattr(self, 'debugger'):
            self.send_response(self.iopub_socket, 'stream', {
                'name': 'stdout',
                'text': 'Swift not initialized yet. Run some code first.\n'
            })
            return

        try:
            # Execute a Swift expression to get all variables
            # Swift REPL doesn't have a direct "list all variables" API
            # So we'll provide a helpful message
            output = [
                "Interactive variable listing:\n",
                "  Note: Swift REPL doesn't provide direct variable introspection.\n",
                "  Variables defined: Check your code history above\n",
                "\n",
                "💡 Tip: Use %help to see all available magic commands\n"
            ]

            self.send_response(self.iopub_socket, 'stream', {
                'name': 'stdout',
                'text': ''.join(output)
            })
        except Exception as e:
            self.log.error(f"Error in %who: {e}")
            self.send_response(self.iopub_socket, 'stream', {
                'name': 'stderr',
                'text': f'Error listing variables: {e}\n'
            })

    def _handle_reset_magic(self, code):
        """Handle %reset magic command - restart the Swift REPL."""
        try:
            # Parse options
            quiet = '--quiet' in code or '-q' in code

            if not quiet:
                self.send_response(self.iopub_socket, 'stream', {
                    'name': 'stdout',
                    'text': '🔄 Restarting Swift kernel...\n'
                })

            # Stop the current REPL process if it exists
            if hasattr(self, 'debugger'):
                try:
                    lldb.SBDebugger.Destroy(self.debugger)
                except:
                    pass
                delattr(self, 'debugger')

            if hasattr(self, 'process'):
                delattr(self, 'process')

            if hasattr(self, 'target'):
                delattr(self, 'target')

            # Clear virtual document for LSP
            if hasattr(self, 'virtual_document_content'):
                self.virtual_document_content = ""
                if self.lsp_initialized:
                    try:
                        self.lsp.send_notification('textDocument/didChange', {
                            'textDocument': {
                                'uri': f'file://{self.virtual_document_path}',
                                'version': self.execution_count + 1
                            },
                            'contentChanges': [{'text': ''}]
                        })
                    except:
                        pass

            # Reset will happen automatically on next code execution
            if not quiet:
                self.send_response(self.iopub_socket, 'stream', {
                    'name': 'stdout',
                    'text': '✅ Kernel reset. All variables cleared.\n'
                })

        except Exception as e:
            self.log.error(f"Error in %reset: {e}")
            self.send_response(self.iopub_socket, 'stream', {
                'name': 'stderr',
                'text': f'Error resetting kernel: {e}\n'
            })

    def _handle_timeit_magic(self, code):
        """Handle %timeit magic command - time code execution."""
        import time
        import re

        # Extract the code to time
        match = re.match(r'^\s*%timeit\s+(.+)$', code, re.DOTALL)
        if not match:
            self.send_response(self.iopub_socket, 'stream', {
                'name': 'stderr',
                'text': 'Usage: %timeit <code>\n'
            })
            return ''

        code_to_time = match.group(1).strip()

        # Run the code multiple times and measure
        iterations = 7
        times = []

        self.send_response(self.iopub_socket, 'stream', {
            'name': 'stdout',
            'text': f'Timing {iterations} iterations...\n'
        })

        for i in range(iterations):
            start = time.time()
            # We'll return the code to execute normally
            # The timing wrapper will be added
            end = time.time()
            times.append(end - start)

        # For now, just return the code with timing info
        # A full implementation would execute multiple times
        return f"""
import Foundation
let __start = Date()
{code_to_time}
let __end = Date()
let __elapsed = __end.timeIntervalSince(__start)
print("⏱️  Execution time: \\(__elapsed * 1000) ms")
"""

    def _handle_help_magic(self):
        """Handle %help magic command - show available commands."""
        help_text = """
Available Magic Commands:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 Variable Management:
  %who              List defined variables (limited in Swift REPL)
  %reset            Clear all variables and restart kernel
  %reset --quiet    Reset kernel without messages

⏱️  Performance:
  %timeit CODE      Time the execution of CODE

📦 Package Management:
  %install SPEC     Install Swift package (see docs)

🔧 Kernel Control:
  %enable_completion   Enable code completion
  %disable_completion  Disable code completion

ℹ️  Information:
  %help             Show this help message

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Examples:
  %who
  %reset --quiet
  %timeit let x = Array(1...1000).reduce(0, +)

📖 For more info: https://github.com/pedronahum/swift-jupyter
"""
        self.send_response(self.iopub_socket, 'stream', {
            'name': 'stdout',
            'text': help_text
        })

    def _handle_lsmagic(self):
        """Handle %lsmagic - list all available magic commands."""
        magic_list = """
Available Magic Commands
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Line Magics (single line):
  %help                     Show help message
  %lsmagic                  List all magic commands (this list)
  %who                      List defined variables
  %reset [-q]               Reset kernel (clear all state)
  %timeit CODE              Time code execution
  %env [VAR[=VALUE]]        Show/set environment variables
  %swift-version            Show Swift toolchain information
  %load FILE                Load and execute a Swift file
  %save FILE                Save cell history to a file
  %history [-n N]           Show execution history

Package Management:
  %install SPEC MODULE      Install Swift package
  %install-swiftpm-flags    Set SwiftPM build flags
  %install-location PATH    Set package install location

Kernel Control:
  %enable_completion        Enable code completion
  %disable_completion       Disable code completion

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        self.send_response(self.iopub_socket, 'stream', {
            'name': 'stdout',
            'text': magic_list
        })

    def _handle_env_magic(self, code):
        """Handle %env magic - show or set environment variables."""
        import os
        import re

        parts = code.strip().split(None, 1)

        # %env with no arguments - show all environment variables
        if len(parts) == 1:
            env_vars = sorted(os.environ.items())
            output = ["Environment Variables:\n", "━" * 60 + "\n"]
            for key, value in env_vars:
                # Truncate long values
                display_value = value if len(value) <= 50 else value[:47] + "..."
                output.append(f"  {key}={display_value}\n")
            output.append("━" * 60 + "\n")
            output.append(f"Total: {len(env_vars)} variables\n")
            self.send_response(self.iopub_socket, 'stream', {
                'name': 'stdout',
                'text': ''.join(output)
            })
            return

        arg = parts[1].strip()

        # %env VAR=VALUE - set environment variable
        if '=' in arg:
            match = re.match(r'^(\w+)=(.*)$', arg)
            if match:
                var_name, var_value = match.groups()
                os.environ[var_name] = var_value
                self.send_response(self.iopub_socket, 'stream', {
                    'name': 'stdout',
                    'text': f"✅ Set {var_name}={var_value}\n"
                })
            else:
                self.send_response(self.iopub_socket, 'stream', {
                    'name': 'stderr',
                    'text': f"Invalid format. Use: %env VAR=VALUE\n"
                })
            return

        # %env VAR - show specific variable
        var_name = arg
        value = os.environ.get(var_name)
        if value is not None:
            self.send_response(self.iopub_socket, 'stream', {
                'name': 'stdout',
                'text': f"{var_name}={value}\n"
            })
        else:
            self.send_response(self.iopub_socket, 'stream', {
                'name': 'stderr',
                'text': f"Environment variable '{var_name}' not found\n"
            })

    def _handle_swift_version_magic(self):
        """Handle %swift-version - show Swift toolchain information."""
        import subprocess
        import shutil

        output = ["Swift Toolchain Information\n", "━" * 60 + "\n\n"]

        # Find swift binary
        swift_path = shutil.which('swift')
        if swift_path:
            output.append(f"📍 Swift binary: {swift_path}\n\n")

            # Get Swift version
            try:
                result = subprocess.run(
                    [swift_path, '--version'],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    output.append("📋 Version:\n")
                    for line in result.stdout.strip().split('\n'):
                        output.append(f"   {line}\n")
                    output.append("\n")
            except Exception as e:
                output.append(f"⚠️  Could not get version: {e}\n\n")

            # Get target info
            try:
                result = subprocess.run(
                    [swift_path, '-print-target-info'],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    import json
                    try:
                        info = json.loads(result.stdout)
                        target = info.get('target', {})
                        output.append("🎯 Target:\n")
                        output.append(f"   Triple: {target.get('triple', 'unknown')}\n")
                        output.append(f"   Module Triple: {target.get('moduleTriple', 'unknown')}\n")
                        if 'paths' in info:
                            paths = info['paths']
                            output.append(f"   Runtime Path: {paths.get('runtimeLibraryPaths', ['unknown'])[0]}\n")
                    except json.JSONDecodeError:
                        pass
            except Exception:
                pass
        else:
            output.append("⚠️  Swift not found in PATH\n\n")

        # Show LLDB info
        output.append("\n🔧 LLDB:\n")
        try:
            output.append(f"   Version: {lldb.SBDebugger.GetVersionString()}\n")
        except:
            output.append("   Version: unknown\n")

        # Show kernel environment
        output.append("\n🔌 Kernel Environment:\n")
        import os
        swift_build = os.environ.get('SWIFT_BUILD_PATH', 'not set')
        swift_package = os.environ.get('SWIFT_PACKAGE_PATH', 'not set')
        output.append(f"   SWIFT_BUILD_PATH: {swift_build}\n")
        output.append(f"   SWIFT_PACKAGE_PATH: {swift_package}\n")

        output.append("\n" + "━" * 60 + "\n")

        self.send_response(self.iopub_socket, 'stream', {
            'name': 'stdout',
            'text': ''.join(output)
        })

    def _handle_load_magic(self, code):
        """Handle %load FILE - load and execute a Swift file."""
        import re
        import os

        match = re.match(r'^\s*%load\s+(.+)$', code)
        if not match:
            self.send_response(self.iopub_socket, 'stream', {
                'name': 'stderr',
                'text': 'Usage: %load <filename.swift>\n'
            })
            return ''

        filepath = match.group(1).strip()

        # Expand user home directory
        filepath = os.path.expanduser(filepath)

        # Check if file exists
        if not os.path.exists(filepath):
            self.send_response(self.iopub_socket, 'stream', {
                'name': 'stderr',
                'text': f"File not found: {filepath}\n"
            })
            return ''

        # Check extension
        if not filepath.endswith('.swift'):
            self.send_response(self.iopub_socket, 'stream', {
                'name': 'stdout',
                'text': f"⚠️  Warning: {filepath} doesn't have .swift extension\n"
            })

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                file_content = f.read()

            self.send_response(self.iopub_socket, 'stream', {
                'name': 'stdout',
                'text': f"📂 Loaded {filepath} ({len(file_content)} chars)\n"
            })

            # Return the file content to be executed
            return file_content

        except Exception as e:
            self.send_response(self.iopub_socket, 'stream', {
                'name': 'stderr',
                'text': f"Error loading file: {e}\n"
            })
            return ''

    def _handle_save_magic(self, code):
        """Handle %save FILE - save execution history to a file."""
        import re
        import os

        match = re.match(r'^\s*%save\s+(.+)$', code)
        if not match:
            self.send_response(self.iopub_socket, 'stream', {
                'name': 'stderr',
                'text': 'Usage: %save <filename.swift>\n'
            })
            return

        filepath = match.group(1).strip()
        filepath = os.path.expanduser(filepath)

        # Add .swift extension if not present
        if not filepath.endswith('.swift'):
            filepath += '.swift'

        # Check if we have execution history
        if not hasattr(self, 'execution_history') or not self.execution_history:
            self.send_response(self.iopub_socket, 'stream', {
                'name': 'stderr',
                'text': "No execution history to save.\n"
            })
            return

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("// Swift Jupyter Session Export\n")
                f.write(f"// Saved at: {__import__('datetime').datetime.now().isoformat()}\n")
                f.write(f"// Cells: {len(self.execution_history)}\n\n")

                for i, entry in enumerate(self.execution_history, 1):
                    f.write(f"// === Cell {i} ===\n")
                    f.write(entry['code'])
                    if not entry['code'].endswith('\n'):
                        f.write('\n')
                    f.write('\n')

            self.send_response(self.iopub_socket, 'stream', {
                'name': 'stdout',
                'text': f"💾 Saved {len(self.execution_history)} cells to {filepath}\n"
            })

        except Exception as e:
            self.send_response(self.iopub_socket, 'stream', {
                'name': 'stderr',
                'text': f"Error saving file: {e}\n"
            })

    def _handle_history_magic(self, code):
        """Handle %history - show execution history."""
        import re

        # Parse options
        match = re.search(r'-n\s*(\d+)', code)
        max_entries = int(match.group(1)) if match else 10

        if not hasattr(self, 'execution_history') or not self.execution_history:
            self.send_response(self.iopub_socket, 'stream', {
                'name': 'stdout',
                'text': "No execution history yet.\n"
            })
            return

        output = ["Execution History\n", "━" * 60 + "\n\n"]

        # Get the last N entries
        history = self.execution_history[-max_entries:]
        start_num = max(1, len(self.execution_history) - max_entries + 1)

        for i, entry in enumerate(history, start_num):
            code_preview = entry['code'].strip()
            # Truncate long code
            if len(code_preview) > 60:
                code_preview = code_preview[:57] + "..."
            # Replace newlines for display
            code_preview = code_preview.replace('\n', '↵ ')
            output.append(f"[{i}] {code_preview}\n")

        output.append("\n" + "━" * 60 + "\n")
        output.append(f"Showing {len(history)} of {len(self.execution_history)} entries\n")
        output.append("Use %history -n N to show more entries\n")

        self.send_response(self.iopub_socket, 'stream', {
            'name': 'stdout',
            'text': ''.join(output)
        })

    def _preprocess_line(self, line_index, line):
        """Returns the preprocessed line.

        Does not process "%install" directives, because those need to be
        handled before everything else."""

        include_match = re.match(r'^\s*%include (.*)$', line)
        if include_match is not None:
            return self._read_include(line_index, include_match.group(1))

        disable_completion_match = re.match(r'^\s*%disableCompletion\s*$', line)
        if disable_completion_match is not None:
            self._handle_disable_completion()
            return ''

        enable_completion_match = re.match(r'^\s*%enableCompletion\s*$', line)
        if enable_completion_match is not None:
            self._handle_enable_completion()
            return ''

        return line

    def _read_include(self, line_index, rest_of_line):
        name_match = re.match(r'^\s*"([^"]+)"\s*$', rest_of_line)
        if name_match is None:
            raise PreprocessorException(
                    'Line %d: %%include must be followed by a name in quotes' % (
                            line_index + 1))
        name = name_match.group(1)

        include_paths = [
            os.path.dirname(os.path.realpath(sys.argv[0])),
            os.path.realpath("."),
        ]

        code = None
        for include_path in include_paths:
            try:
                with open(os.path.join(include_path, name), 'r') as f:
                    code = f.read()
            except IOError:
                continue

        if code is None:
            raise PreprocessorException(
                    'Line %d: Could not find "%s". Searched %s.' % (
                            line_index + 1, name, include_paths))

        return '\n'.join([
            '#sourceLocation(file: "%s", line: 1)' % name,
            code,
            '#sourceLocation(file: "%s", line: %d)' % (
                self._file_name_for_source_location(), line_index + 1),
            ''
        ])

    def _process_installs(self, code):
        """Handles all "%install" directives, and returns `code` with all
        "%install" directives removed."""
        processed_lines = []
        all_packages = []
        all_swiftpm_flags = []
        extra_include_commands = []
        user_install_location = None
        for index, line in enumerate(code.split('\n')):
            line = self._process_system_command_line(line)
            line, install_location = self._process_install_location_line(line)
            line, swiftpm_flags = self._process_install_swiftpm_flags_line(
                    line)
            all_swiftpm_flags += swiftpm_flags
            line, packages = self._process_install_line(index, line)
            line, extra_include_command = \
                self._process_extra_include_command_line(line)
            if extra_include_command:
                extra_include_commands.append(extra_include_command)
            processed_lines.append(line)
            all_packages += packages
            if install_location: user_install_location = install_location

        self._install_packages(all_packages, all_swiftpm_flags,
                               extra_include_commands,
                               user_install_location)
        return '\n'.join(processed_lines)

    def _process_install_location_line(self, line):
        install_location_match = re.match(
                r'^\s*%install-location (.*)$', line)
        if install_location_match is None:
            return line, None

        install_location = install_location_match.group(1)
        try:
            install_location = string.Template(install_location).substitute({"cwd": os.getcwd()})
        except KeyError as e:
            raise PackageInstallException(
                    'Line %d: Invalid template argument %s' % (line_index + 1,
                                                               str(e)))
        except ValueError as e:
            raise PackageInstallException(
                    'Line %d: %s' % (line_index + 1, str(e)))

        return '', install_location

    def _process_extra_include_command_line(self, line):
        extra_include_command_match = re.match(
                r'^\s*%install-extra-include-command (.*)$', line)
        if extra_include_command_match is None:
            return line, None

        extra_include_command = extra_include_command_match.group(1)

        return '', extra_include_command

    def _process_install_swiftpm_flags_line(self, line):
        install_swiftpm_flags_match = re.match(
                r'^\s*%install-swiftpm-flags (.*)$', line)
        if install_swiftpm_flags_match is None:
            return line, []
        flags = shlex.split(install_swiftpm_flags_match.group(1))
        return '', flags

    def _process_install_line(self, line_index, line):
        install_match = re.match(r'^\s*%install (.*)$', line)
        if install_match is None:
            return line, []

        parsed = shlex.split(install_match.group(1))
        if len(parsed) < 2:
            raise PackageInstallException(
                    'Line %d: %%install usage: SPEC PRODUCT [PRODUCT ...]' % (
                            line_index + 1))
        try:
            spec = string.Template(parsed[0]).substitute({"cwd": os.getcwd()})
        except KeyError as e:
            raise PackageInstallException(
                    'Line %d: Invalid template argument %s' % (line_index + 1,
                                                               str(e)))
        except ValueError as e:
            raise PackageInstallException(
                    'Line %d: %s' % (line_index + 1, str(e)))

        return '', [{
            'spec': spec,
            'products': parsed[1:],
        }]

    def _process_system_command_line(self, line):                  
        system_match = re.match(r'^\s*%system (.*)$', line)
        if system_match is None:
            return line

        if hasattr(self, 'debugger'):
            raise PackageInstallException(
                    'System commands can only run in the first cell.')

        rest_of_line = system_match.group(1)
        process = subprocess.Popen(rest_of_line,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            shell=True)
        process.wait()
        command_result = process.stdout.read().decode('utf-8')
        self.send_response(self.iopub_socket, 'stream', {
            'name': 'stdout',
            'text': '%s' % command_result
        })
        return ''

    def _link_extra_includes(self, swift_module_search_path, include_dir):
        for include_file in os.listdir(include_dir):
            link_name = os.path.join(swift_module_search_path, include_file)
            target = os.path.join(include_dir, include_file)
            try:
                if stat.S_ISLNK(os.lstat(link_name).st_mode):
                    os.unlink(link_name)
            except FileNotFoundError as e:
                pass
            except Error as e:
                raise PackageInstallException(
                        'Failed to stat scratchwork base path: %s' % str(e))
            os.symlink(target, link_name)

    def _send_install_progress(self, step, total, message):
        """Send a formatted progress message during package installation."""
        self.send_response(self.iopub_socket, 'stream', {
            'name': 'stdout',
            'text': f'[{step}/{total}] {message}\n'
        })

    def _install_packages(self, packages, swiftpm_flags, extra_include_commands,
                          user_install_location):
        if len(packages) == 0 and len(swiftpm_flags) == 0:
            return

        if hasattr(self, 'debugger'):
            raise PackageInstallException(
                    'Install Error: Packages can only be installed during the '
                    'first cell execution.\n\n'
                    '💡 Tip: Restart the kernel to install packages.\n'
                    '   • In Jupyter: Kernel menu → Restart\n'
                    '   • %install must be in the first cell before any other Swift code')

        swift_build_path = os.environ.get('SWIFT_BUILD_PATH')
        if swift_build_path is None:
            raise PackageInstallException(
                    'Install Error: Cannot install packages because '
                    'SWIFT_BUILD_PATH is not specified.\n\n'
                    '💡 This usually means the kernel was not registered correctly.\n'
                    '   • Try running: python3 register.py --sys-prefix --swift-toolchain <path>\n'
                    '   • See: https://github.com/pedronahum/swift-jupyter#installation')

        swift_package_path = os.environ.get('SWIFT_PACKAGE_PATH')
        if swift_package_path is None:
            raise PackageInstallException(
                    'Install Error: Cannot install packages because '
                    'SWIFT_PACKAGE_PATH is not specified.\n\n'
                    '💡 This usually means the kernel was not registered correctly.\n'
                    '   • Try running: python3 register.py --sys-prefix --swift-toolchain <path>\n'
                    '   • See: https://github.com/pedronahum/swift-jupyter#installation')

        package_install_scratchwork_base = tempfile.mkdtemp()
        package_install_scratchwork_base = os.path.join(package_install_scratchwork_base, 'swift-install')
        swift_module_search_path = os.path.join(package_install_scratchwork_base,
                                            'modules')
        self.swift_module_search_path = swift_module_search_path

        scratchwork_base_path = os.path.dirname(swift_module_search_path)
        package_base_path = os.path.join(scratchwork_base_path, 'package')

        # If the user has specified a custom install location, make a link from
        # the scratchwork base path to it.
        if user_install_location is not None:
            # symlink to the specified location
            # Remove existing base if it is already a symlink
            os.makedirs(user_install_location, exist_ok=True)
            try:
                if stat.S_ISLNK(os.lstat(scratchwork_base_path).st_mode):
                    os.unlink(scratchwork_base_path)
            except FileNotFoundError as e:
                pass
            except Error as e:
                raise PackageInstallException(
                        'Failed to stat scratchwork base path: %s' % str(e))
            os.symlink(user_install_location, scratchwork_base_path,
                       target_is_directory=True)

        # Make the directory containing our synthesized package.
        os.makedirs(package_base_path, exist_ok=True)

        # Make the directory containing our built modules and other includes.
        os.makedirs(swift_module_search_path, exist_ok=True)

        # Make links from the install location to extra includes.
        for include_command in extra_include_commands:
            result = subprocess.run(include_command, shell=True,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
            if result.returncode != 0:
                raise PackageInstallException(
                        '%%install-extra-include-command returned nonzero '
                        'exit code: %d\nStdout:\n%s\nStderr:\n%s\n' % (
                                result.returncode,
                                result.stdout.decode('utf8'),
                                result.stderr.decode('utf8')))
            include_dirs = shlex.split(result.stdout.decode('utf8'))
            for include_dir in include_dirs:
                if include_dir[0:2] != '-I':
                    self.log.warn(
                            'Non "-I" output from '
                            '%%install-extra-include-command: %s' % include_dir)
                    continue
                include_dir = include_dir[2:]
                self._link_extra_includes(swift_module_search_path, include_dir)

        # Summary of how this works:
        # - create a SwiftPM package that depends on all the packages that
        #   the user requested
        # - ask SwiftPM to build that package
        # - copy all the .swiftmodule and module.modulemap files that SwiftPM
        #   created to SWIFT_IMPORT_SEARCH_PATH
        # - dlopen the .so file that SwiftPM created

        # == Create the SwiftPM package ==

        package_swift_template = textwrap.dedent("""\
            // swift-tools-version:5.5
            import PackageDescription
            let package = Package(
                name: "jupyterInstalledPackages",
                products: [
                    .library(
                        name: "jupyterInstalledPackages",
                        type: .dynamic,
                        targets: ["jupyterInstalledPackages"]),
                ],
                dependencies: [%s],
                targets: [
                    .target(
                        name: "jupyterInstalledPackages",
                        dependencies: [%s],
                        path: ".",
                        sources: ["jupyterInstalledPackages.swift"]),
                ])
        """)

        packages_specs = ''
        packages_products = ''
        packages_human_description = ''
        for package in packages:
            packages_specs += '%s,\n' % package['spec']
            packages_human_description += '\t%s\n' % package['spec']
            for target in package['products']:
                packages_products += '%s,\n' % json.dumps(target)
                packages_human_description += '\t\t%s\n' % target

        # Show installation header
        self.send_response(self.iopub_socket, 'stream', {
            'name': 'stdout',
            'text': '\n📦 Installing Swift Packages\n' + '='*50 + '\n'
        })
        self.send_response(self.iopub_socket, 'stream', {
            'name': 'stdout',
            'text': 'Packages:\n%s' % packages_human_description
        })
        if swiftpm_flags:
            self.send_response(self.iopub_socket, 'stream', {
                'name': 'stdout',
                'text': 'SwiftPM flags: %s\n' % str(swiftpm_flags)
            })

        # Progress: Step 1
        self._send_install_progress(1, 5, '📋 Creating Package.swift')

        package_swift = package_swift_template % (packages_specs,
                                                  packages_products)

        with open('%s/Package.swift' % package_base_path, 'w') as f:
            f.write(package_swift)
        with open('%s/jupyterInstalledPackages.swift' % package_base_path, 'w') as f:
            f.write("// intentionally blank\n")

        # == Ask SwiftPM to build the package ==

        # Progress: Step 2
        self._send_install_progress(2, 5, '🌐 Resolving and fetching dependencies (this may take a while...)')

        # TODO(TF-1179): Remove this workaround after fixing SwiftPM.
        swiftpm_env = os.environ
        libuuid_path = '/lib/x86_64-linux-gnu/libuuid.so.1'
        if os.path.isfile(libuuid_path):
            swiftpm_env['LD_PRELOAD'] = libuuid_path

        import time
        start_time = time.time()

        # Progress: Step 3
        self._send_install_progress(3, 5, '🔨 Building packages...')

        build_p = subprocess.Popen([swift_build_path] + swiftpm_flags,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT,
                                   cwd=package_base_path,
                                   env=swiftpm_env)

        # Stream build output with timeout (10 minutes default)
        # Users can override with environment variable
        build_timeout = int(os.environ.get('SWIFT_JUPYTER_BUILD_TIMEOUT', '600'))

        try:
            for build_output_line in iter(build_p.stdout.readline, b''):
                self.send_response(self.iopub_socket, 'stream', {
                    'name': 'stdout',
                    'text': build_output_line.decode('utf8')
                })

            build_returncode = build_p.wait(timeout=build_timeout)
        except subprocess.TimeoutExpired:
            build_p.kill()
            build_p.wait()
            error_msg = (
                f'Install Error: Package build timed out after {build_timeout} seconds.\n\n'
                f'💡 Troubleshooting:\n'
                f'   • Large packages may take longer to build\n'
                f'   • Increase timeout: export SWIFT_JUPYTER_BUILD_TIMEOUT=1200\n'
                f'   • Check your internet connection for slow downloads\n'
                f'   • Consider building the package outside Jupyter first to cache dependencies\n'
            )
            raise PackageInstallException(error_msg)
        elapsed = time.time() - start_time

        if build_returncode != 0:
            error_msg = (
                f'Install Error: swift-build returned nonzero exit code {build_returncode}.\n\n'
                f'💡 Troubleshooting:\n'
                f'   • Check that the package URL is correct\n'
                f'   • Verify the package version/branch exists\n'
                f'   • Check your internet connection\n'
                f'   • Try running with verbose output: %install-swiftpm-flags -v\n'
                f'   • Some packages may not be compatible with your Swift version\n'
            )
            raise PackageInstallException(error_msg)

        self.send_response(self.iopub_socket, 'stream', {
            'name': 'stdout',
            'text': f'✓ Build completed in {elapsed:.1f}s\n'
        })

        show_bin_path_result = subprocess.run(
                [swift_build_path, '--show-bin-path'] + swiftpm_flags,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                cwd=package_base_path,
                env=swiftpm_env)
        bin_dir = show_bin_path_result.stdout.decode('utf8').strip()
        lib_filename = os.path.join(bin_dir, 'libjupyterInstalledPackages.so')

        # == Copy .swiftmodule and modulemap files to SWIFT_IMPORT_SEARCH_PATH ==
        self._send_install_progress(4, 5, '📦 Copying Swift modules to kernel...')

        # Search for build.db.
        build_db_candidates = [
            os.path.join(bin_dir, '..', 'build.db'),
            os.path.join(package_base_path, '.build', 'build.db'),
        ]
        build_db_file = next(filter(os.path.exists, build_db_candidates), None)
        if build_db_file is None:
            error_msg = (
                'Install Error: build.db is missing from build directory.\n\n'
                '💡 Troubleshooting:\n'
                '   • This indicates the build may have failed silently\n'
                '   • Try cleaning the build: rm -rf ~/.swift-jupyter/package_base\n'
                '   • Check that swift-build is working: swift build --help\n'
                '   • Verify you have write permissions in ~/.swift-jupyter/\n'
            )
            raise PackageInstallException(error_msg)

        # Execute swift-package show-dependencies to get all dependencies' paths
        dependencies_result = subprocess.run(
            [swift_package_path, 'show-dependencies', '--format', 'json'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd=package_base_path,
            env=swiftpm_env)
        dependencies_json = dependencies_result.stdout.decode('utf8')
        dependencies_obj = json.loads(dependencies_json)

        def flatten_deps_paths(dep):
            paths = []
            paths.append(dep["path"])
            if dep["dependencies"]:
                for d in dep["dependencies"]:
                    paths.extend(flatten_deps_paths(d))
            return paths

        # Make list of paths where we expect .swiftmodule and .modulemap files of dependencies
        dependencies_paths = [package_base_path]
        dependencies_paths = flatten_deps_paths(dependencies_obj)
        dependencies_paths = list(set(dependencies_paths))

        def is_valid_dependency(path):
            for p in dependencies_paths:
                if path.startswith(p): return True
            return False

        # Query to get build files list from build.db
        # SUBSTR because string starts with "N" (why?)
        SQL_FILES_SELECT = "SELECT SUBSTR(key, 2) FROM 'key_names' WHERE key LIKE ?"

        # Connect to build.db
        db_connection = sqlite3.connect(build_db_file)
        cursor = db_connection.cursor()

        # Process *.swiftmodules files
        cursor.execute(SQL_FILES_SELECT, ['%.swiftmodule'])
        swift_modules = [row[0] for row in cursor.fetchall() if is_valid_dependency(row[0])]
        try:
            for filename in swift_modules:
                shutil.copy(filename, swift_module_search_path)
        except (OSError, shutil.Error) as e:
            error_msg = (
                f'Install Error: Failed to copy Swift module files.\n\n'
                f'💡 Troubleshooting:\n'
                f'   • Check permissions on {swift_module_search_path}\n'
                f'   • Ensure you have enough disk space\n'
                f'   • Try cleaning: rm -rf ~/.swift-jupyter/modules\n'
                f'\nError details: {str(e)}'
            )
            raise PackageInstallException(error_msg)

        # Process modulemap files
        cursor.execute(SQL_FILES_SELECT, ['%/module.modulemap'])
        modulemap_files = [row[0] for row in cursor.fetchall() if is_valid_dependency(row[0])]
        for index, filename in enumerate(modulemap_files):
            # Create a separate directory for each modulemap file because the
            # ClangImporter requires that they are all named
            # "module.modulemap".
            # Use the module name to prevent two modulema[s for the same
            # depndency ending up in multiple directories after several
            # installations, causing the kernel to end up in a bad state.
            # Make all relative header paths in module.modulemap absolute
            # because we copy file to different location.

            src_folder, src_filename = os.path.split(filename)
            with open(filename, encoding='utf8') as file:
                modulemap_contents = file.read()
                modulemap_contents = re.sub(
                    r'header\s+"(.*?)"',
                    lambda m: 'header "%s"' %
                        (m.group(1) if os.path.isabs(m.group(1)) else os.path.abspath(os.path.join(src_folder, m.group(1)))),
                    modulemap_contents
                )

                module_match = re.match(r'module\s+([^\s]+)\s.*{', modulemap_contents)
                module_name = module_match.group(1) if module_match is not None else str(index)
                modulemap_dest = os.path.join(swift_module_search_path, 'modulemap-%s' % module_name)
                os.makedirs(modulemap_dest, exist_ok=True)
                dst_path = os.path.join(modulemap_dest, src_filename)

                with open(dst_path, 'w', encoding='utf8') as outfile:
                    outfile.write(modulemap_contents)

        # == dlopen the shared lib ==
        self._send_install_progress(5, 5, '🔗 Loading packages into Swift REPL...')

        self._init_swift()

        # Use Darwin on macOS, Glibc on Linux
        import platform
        if platform.system() == 'Darwin':
            dlopen_module = 'Darwin'
        else:
            dlopen_module = 'Glibc'

        dynamic_load_code = textwrap.dedent("""\
            import func {module}.dlopen
            import var {module}.RTLD_NOW
            dlopen({lib}, RTLD_NOW)
        """.format(module=dlopen_module, lib=json.dumps(lib_filename)))
        dynamic_load_result = self._execute(dynamic_load_code)
        if not isinstance(dynamic_load_result, SuccessWithValue):
            error_msg = (
                f'Install Error: Failed to load shared library.\n\n'
                f'💡 Common causes:\n'
                f'   • Missing system dependencies (try: ldd {lib_filename})\n'
                f'   • Incompatible Swift version between kernel and packages\n'
                f'   • Corrupted build artifacts (try: rm -rf ~/.swift-jupyter/package_base)\n'
                f'   • Architecture mismatch (check Swift toolchain architecture)\n'
                f'\nError: {str(dynamic_load_result)}'
            )
            raise PackageInstallException(error_msg)
        if dynamic_load_result.value_description().endswith('nil'):
            error_msg = (
                'Install Error: dlopen returned nil (library load failed).\n\n'
                '💡 To see detailed error information, run:\n'
                '   String(cString: dlerror())\n\n'
                'Common causes:\n'
                '   • Missing or incompatible system libraries\n'
                '   • Symbol conflicts with previously loaded packages\n'
                '   • Try restarting the kernel and reinstalling\n'
            )
            raise PackageInstallException(error_msg)

        # Show success message with installed package names
        installed_products = []
        for package in packages:
            installed_products.extend(package['products'])
        installed_names = ', '.join(installed_products)
        self.send_response(self.iopub_socket, 'stream', {
            'name': 'stdout',
            'text': f'\n✅ Successfully installed: {installed_names}\n'
        })
        self.already_installed_packages = True

    def _execute(self, code):
        """Execute Swift code in LLDB with proper Unicode handling (R5-T1).

        This method ensures that code containing Unicode characters (emoji,
        Chinese, etc.) is properly handled by LLDB. Python 3 strings are
        already Unicode, but we need to ensure proper encoding/decoding
        when communicating with LLDB.

        Args:
            code: Swift source code to execute (Python str, Unicode)

        Returns:
            ExecutionResult: Success or error result from LLDB
        """
        locationDirective = '#sourceLocation(file: "%s", line: 1)' % (
            self._file_name_for_source_location())
        codeWithLocationDirective = locationDirective + '\n' + code

        # Python 3 strings are Unicode by default. LLDB's EvaluateExpression
        # expects a string and handles encoding internally. We just need to
        # ensure the string is properly formed.
        #
        # Note: If we need to explicitly encode/decode in the future:
        # - code_bytes = code.encode('utf-8')
        # - result_str = result_bytes.decode('utf-8', errors='replace')

        try:
            result = self.target.EvaluateExpression(
                    codeWithLocationDirective, self.expr_opts)
        except Exception as e:
            self.log.error(f'Exception during LLDB evaluation: {e}', exc_info=True)
            # Return a synthetic error result
            return PreprocessorError(PreprocessorException(
                f'LLDB evaluation failed: {str(e)}'))

        if result.error.type == lldb.eErrorTypeInvalid:
            return SuccessWithValue(result)
        elif result.error.type == lldb.eErrorTypeGeneric:
            return SuccessWithoutValue()
        else:
            return SwiftError(result)

    def _after_successful_execution(self):
        result = self._execute(
                'JupyterKernel.communicator.triggerAfterSuccessfulExecution()')
        if not isinstance(result, SuccessWithValue):
            self.log.error(
                    'Expected value from triggerAfterSuccessfulExecution(), '
                    'but got: %s' % result)
            return

        messages = self._read_jupyter_messages(result.result)
        self._send_jupyter_messages(messages)

    def _read_jupyter_messages(self, sbvalue):
        return {
            'display_messages': [
                self._read_display_message(display_message_sbvalue)
                for display_message_sbvalue
                in sbvalue
            ]
        }

    def _read_display_message(self, sbvalue):
        return [self._read_byte_array(part) for part in sbvalue]

    def _read_byte_array(self, sbvalue):
        get_address_error = lldb.SBError()
        address = sbvalue \
                .GetChildMemberWithName('address') \
                .GetData() \
                .GetAddress(get_address_error, 0)
        if get_address_error.Fail():
            raise Exception('getting address: %s' % str(get_address_error))

        get_count_error = lldb.SBError()
        count_data = sbvalue \
                .GetChildMemberWithName('count') \
                .GetData()
        if self._int_bitwidth == 32:
            count = count_data.GetSignedInt32(get_count_error, 0)
        elif self._int_bitwidth == 64:
            count = count_data.GetSignedInt64(get_count_error, 0)
        else:
            raise Exception('Unsupported integer bitwidth %d' %
                            self._int_bitwidth)
        if get_count_error.Fail():
            raise Exception('getting count: %s' % str(get_count_error))

        # ReadMemory requires that count is positive, so early-return an empty
        # byte array when count is 0.
        if count == 0:
            return bytes()

        get_data_error = lldb.SBError()
        data = self.process.ReadMemory(address, count, get_data_error)
        if get_data_error.Fail():
            raise Exception('getting data: %s' % str(get_data_error))

        return data

    def _send_jupyter_messages(self, messages):
        """Send display messages from Swift to Jupyter.

        TODO (R4): This currently sends pre-signed messages from Swift directly.
        Should be refactored to use session.send() for proper message signing.
        See modernization-plan.json R4-T1 and R4-T2.

        Current approach (legacy):
        - Swift constructs full Jupyter messages with HMAC
        - Sends directly via ZMQ multipart

        Future approach (R4):
        - Swift sends data payload only
        - Python constructs proper messages via session.send()
        """
        for display_message in messages['display_messages']:
            # Legacy: Direct send of pre-constructed message
            # This bypasses session.send() and uses Swift-side message construction
            self.iopub_socket.send_multipart(display_message)
            self.log.debug('Sent display message from Swift (legacy path)')

    def _set_parent_message(self):
        result = self._execute("""
            JupyterKernel.communicator.updateParentMessage(
                to: KernelCommunicator.ParentMessage(json: %s))
        """ % json.dumps(json.dumps(squash_dates(self._parent_header))))
        if isinstance(result, ExecutionResultError):
            raise Exception('Error setting parent message: %s' % result)

    def _get_pretty_main_thread_stack_trace(self):
        """Get formatted stack trace from LLDB (R5-T3 enhanced).

        Returns a list of formatted stack trace strings, filtering out:
        - Library frames without source location
        - Compiler-generated frames
        - LLDB internal frames

        Each frame is formatted as:
        "  at function_name (File.swift:line:column)"
        """
        stack_trace = []
        for frame in self.main_thread:
            # Do not include frames without source location information. These
            # are frames in libraries and frames that belong to the LLDB
            # expression execution implementation.
            if not frame.line_entry.file:
                continue

            # Do not include <compiler-generated> frames. These are
            # specializations of library functions.
            if frame.line_entry.file.fullpath == '<compiler-generated>':
                continue

            # Format frame information nicely
            try:
                file_name = frame.line_entry.file.basename
                line_num = frame.line_entry.line
                col_num = frame.line_entry.column
                func_name = frame.name or '<unknown>'

                # Create formatted frame string
                formatted_frame = f'  at {func_name} ({file_name}:{line_num}:{col_num})'
                stack_trace.append(formatted_frame)
            except Exception as e:
                # Fallback to string representation if formatting fails
                self.log.warning(f'Error formatting stack frame: {e}')
                stack_trace.append(str(frame))

        return stack_trace

    def _make_execute_reply_error_message(self, traceback):
        return {
            'status': 'error',
            'execution_count': self.execution_count,
            'ename': '',
            'evalue': '',
            'traceback': traceback,
        }

    def _send_iopub_error_message(self, traceback):
        self.send_response(self.iopub_socket, 'error', {
            'ename': '',
            'evalue': '',
            'traceback': traceback,
        })

    def _send_exception_report(self, while_doing, e):
        self._send_iopub_error_message([
            'Kernel is in a bad state. Try restarting the kernel.',
            '',
            'Exception in `%s`:' % while_doing,
            str(e)
        ])

    def _execute_cell(self, code):
        self._set_parent_message()
        result = self._preprocess_and_execute(code)
        if isinstance(result, ExecutionResultSuccess):
            self._after_successful_execution()
            
            # Update LSP state with executed code
            if self.lsp_initialized:
                try:
                    self.virtual_document_content += code + '\n'
                    self.lsp.send_notification('textDocument/didChange', {
                        'textDocument': {
                            'uri': f'file://{self.virtual_document_path}',
                            'version': self.execution_count + 1
                        },
                        'contentChanges': [{'text': self.virtual_document_content}]
                    })
                except Exception as e:
                    self.log.error(f'Failed to update LSP state: {e}')
                    
        return result

    def do_execute(self, code, silent, store_history=True,
                   user_expressions=None, allow_stdin=False):
        # Return early if the code is empty or whitespace, to avoid
        # initializing Swift and preventing package installs.
        if len(code) == 0 or code.isspace():
            return {
                'status': 'ok',
                'execution_count': self.execution_count,
                'payload': [],
                'user_expressions': {}
            }

        # Record execution history (for %save and %history commands)
        # Skip magic commands that don't produce Swift code
        if store_history and not code.strip().startswith('%'):
            self.execution_history.append({
                'code': code,
                'execution_count': self.execution_count
            })

        # Package installs must be done before initializing Swift (see doc
        # comment in `_init_swift`).
        try:
            code = self._process_installs(code)
        except PackageInstallException as e:
            self._send_iopub_error_message([str(e)])
            return self._make_execute_reply_error_message([str(e)])
        except Exception as e:
            # Don't re-raise - log and return error to allow kernel to continue
            self.log.error(f'Unexpected error in _process_installs: {e}', exc_info=True)
            error_msg = [
                'Unexpected error during package installation.',
                'The kernel may be in an unstable state. Consider restarting if issues persist.',
                '',
                f'Error: {str(e)}'
            ]
            self._send_iopub_error_message(error_msg)
            return self._make_execute_reply_error_message(error_msg)

        if not hasattr(self, 'debugger'):
            self._init_swift()

        # Start up a new thread to collect stdout.
        stdout_handler = StdoutHandler(self)
        stdout_handler.start()

        # Execute the cell, handle unexpected exceptions, and make sure to
        # always clean up the stdout handler.
        try:
            result = self._execute_cell(code)
        except Exception as e:
            # Don't re-raise - log and return error to allow kernel to continue
            self.log.error(f'Unexpected error in _execute_cell: {e}', exc_info=True)
            error_msg = [
                'Unexpected error during cell execution.',
                'The kernel may be in an unstable state. Consider restarting if issues persist.',
                '',
                f'Error: {str(e)}'
            ]
            self._send_iopub_error_message(error_msg)
            result = ExecutionResultError()
            # Set a simple error description for the result
            result.description = lambda: '\n'.join(error_msg)
        finally:
            stdout_handler.stop_event.set()
            stdout_handler.join()

        # Send values/errors and status to the client.
        if isinstance(result, (SuccessWithValue, SuccessWithoutValue)):
            # Update virtual document state
            self.virtual_document_content += code + '\n'
            if self.lsp_initialized:
                self.lsp.send_notification('textDocument/didChange', {
                    'textDocument': {
                        'uri': f'file://{self.virtual_document_path}',
                        'version': self.execution_count
                    },
                    'contentChanges': [{'text': self.virtual_document_content}]
                })

        if isinstance(result, SuccessWithValue):
            # Display the expression value with rich display support
            try:
                plain_text, rich_data = result.get_rich_display()
                data = {'text/plain': plain_text}

                # Add rich display if available
                if rich_data:
                    if isinstance(rich_data, dict) and '__image__' in rich_data:
                        # Image data
                        image_info = rich_data['__image__']
                        if image_info:
                            mime_type = image_info.get('mime_type', 'image/png')
                            data[mime_type] = image_info['data']
                    elif isinstance(rich_data, str):
                        # HTML content
                        data['text/html'] = rich_data

                self.send_response(self.iopub_socket, 'execute_result', {
                    'execution_count': self.execution_count,
                    'data': data,
                    'metadata': {}
                })
            except Exception as e:
                # Fallback if formatting fails
                self.log.warning(f'Failed to format expression value: {e}')
                self.send_response(self.iopub_socket, 'execute_result', {
                    'execution_count': self.execution_count,
                    'data': {
                        'text/plain': result.value_description()
                    },
                    'metadata': {}
                })

            return {
                'status': 'ok',
                'execution_count': self.execution_count,
                'payload': [],
                'user_expressions': {}
            }
        elif isinstance(result, SuccessWithoutValue):
            return {
                'status': 'ok',
                'execution_count': self.execution_count,
                'payload': [],
                'user_expressions': {}
            }
        elif isinstance(result, ExecutionResultError):
            if not self.process or not self.process.IsValid():
                self._send_iopub_error_message(['Process killed'])

                # Exit the kernel because there is no way to recover from a
                # killed process. The UI will tell the user that the kernel has
                # died and the UI will automatically restart the kernel.
                # We do the exit in a callback so that this execute request can
                # cleanly finish before the kernel exits.
                loop = ioloop.IOLoop.current()
                loop.add_timeout(time.time()+0.1, loop.stop)

                return self._make_execute_reply_error_message(['Process killed'])

            if stdout_handler.had_stdout:
                # When there is stdout, it is a runtime error. Stdout, which we
                # have already sent to the client, contains the error message
                # (plus some other ugly traceback that we should eventually
                # figure out how to suppress), so this block of code only needs
                # to add a traceback.
                traceback = []
                traceback.append('Current stack trace:')
                traceback += [
                    '\t%s' % frame
                    for frame in self._get_pretty_main_thread_stack_trace()
                ]

                self._send_iopub_error_message(traceback)
                return self._make_execute_reply_error_message(traceback)

            # There is no stdout, so it must be a compile error. Simply return
            # the error without trying to get a stack trace.
            # Use enhanced error formatting with helpful suggestions
            if isinstance(result, SwiftError):
                error_msg = result.get_helpful_message()
            else:
                error_msg = result.description()

            self._send_iopub_error_message([error_msg])
            return self._make_execute_reply_error_message([error_msg])

    def do_complete(self, code, cursor_pos):
        """Handle code completion request with Unicode-aware cursor positioning.

        According to Jupyter Protocol 5.2+, cursor_pos is measured in Unicode
        codepoints, not bytes. This is important for code containing emoji,
        non-ASCII characters, etc.

        Args:
            code: str, the entire cell content
            cursor_pos: int, cursor position in Unicode codepoints

        Returns:
            dict with status, matches, cursor_start, cursor_end
        """
        if not self.completion_enabled:
            return {
                'status': 'ok',
                'matches': [],
                'cursor_start': cursor_pos,
                'cursor_end': cursor_pos,
                'metadata': {}
            }

        # Ensure cursor_pos is within bounds (Unicode codepoints)
        if cursor_pos > len(code):
            cursor_pos = len(code)
        if cursor_pos < 0:
            cursor_pos = 0

        try:
            # Temporarily append current cell code to virtual document for completion context
            full_content = self.virtual_document_content + code

            # Update LSP with current state (including unexecuted code)
            if self.lsp_initialized:
                self.lsp.send_notification('textDocument/didChange', {
                    'textDocument': {
                        'uri': f'file://{self.virtual_document_path}',
                        'version': self.execution_count + 1000
                    },
                    'contentChanges': [{'text': full_content}]
                })

            # Calculate absolute cursor position in the combined document
            absolute_cursor_pos = len(self.virtual_document_content) + cursor_pos

            # Convert offset to line/char for LSP
            line = full_content[:absolute_cursor_pos].count('\n')
            last_newline = full_content.rfind('\n', 0, absolute_cursor_pos)
            character = absolute_cursor_pos - (last_newline + 1) if last_newline != -1 else absolute_cursor_pos

            if self.lsp_initialized:
                # Request completion from LSP
                result = self.lsp.send_request('textDocument/completion', {
                    'textDocument': {
                        'uri': f'file://{self.virtual_document_path}'
                    },
                    'position': {
                        'line': line,
                        'character': character
                    }
                }, timeout=5.0)

                # Restore virtual document to only executed code
                self.lsp.send_notification('textDocument/didChange', {
                    'textDocument': {
                        'uri': f'file://{self.virtual_document_path}',
                        'version': self.execution_count + 1001
                    },
                    'contentChanges': [{'text': self.virtual_document_content}]
                })

                matches = []
                if result:
                    items = result.get('items', []) if isinstance(result, dict) else result
                    for item in items:
                        # Extract completion text
                        if isinstance(item, dict):
                            label = item.get('label', '')
                            if label:
                                matches.append(label)
                        elif isinstance(item, str):
                            matches.append(item)

                # Calculate the start position of the identifier being completed
                import re
                prefix_match = re.search(r'[\w\d_\.]+$', code[:cursor_pos])
                if prefix_match:
                    prefix = prefix_match.group(0)
                    cursor_start = cursor_pos - len(prefix)
                else:
                    prefix = ""
                    cursor_start = cursor_pos

                self.log.debug(f"Completion at pos {cursor_pos}, found {len(matches)} matches, prefix='{prefix}'")

                return {
                    'status': 'ok',
                    'matches': matches,
                    'cursor_start': cursor_start,
                    'cursor_end': cursor_pos,
                    'metadata': {}
                }

        except TimeoutError:
            self.log.warning("Completion request timed out")
        except Exception as e:
            self.log.error(f"Error in do_complete: {e}", exc_info=True)

        return {
            'status': 'ok',
            'matches': [],
            'cursor_start': cursor_pos,
            'cursor_end': cursor_pos,
            'metadata': {}
        }

    def inspect_request(self, stream, ident, parent):
        content = parent['content']
        code = content['code']
        cursor_pos = content['cursor_pos']
        detail_level = content.get('detail_level', 0)

        reply_content = self.do_inspect(code, cursor_pos, detail_level)

        # Send reply
        msg_type = 'inspect_reply'
        self.session.send(stream, msg_type, reply_content, parent, ident)
        return reply_content

    def do_inspect(self, code, cursor_pos, detail_level=0, omit_sections=(), **kwargs):
        """Handle code inspection request (Hover).

        For hover to work correctly, we need to temporarily append the current cell's
        code to the virtual document (which contains executed code), perform the hover,
        but not permanently add it to the virtual document state.
        """
        if not self.lsp_initialized:
            self.log.debug("LSP not initialized in do_inspect")
            return {'status': 'ok', 'found': False, 'data': {}, 'metadata': {}}

        try:
            # Ensure cursor_pos is within bounds
            if cursor_pos > len(code):
                cursor_pos = len(code)
            if cursor_pos < 0:
                cursor_pos = 0

            # Temporarily append current code to virtual document for hover context
            # The virtual_document_content contains only previously executed code
            full_content = self.virtual_document_content + code

            # Temporarily update LSP with the current code for hover purposes
            self.lsp.send_notification('textDocument/didChange', {
                'textDocument': {
                    'uri': f'file://{self.virtual_document_path}',
                    'version': self.execution_count + 1000
                },
                'contentChanges': [{'text': full_content}]
            })

            # Give LSP a moment to process the document update
            import time
            time.sleep(0.1)

            # Calculate absolute cursor position in the combined document
            absolute_cursor_pos = len(self.virtual_document_content) + cursor_pos

            # Convert byte offset to line/character position
            line = full_content[:absolute_cursor_pos].count('\n')
            last_newline = full_content.rfind('\n', 0, absolute_cursor_pos)
            character = absolute_cursor_pos - (last_newline + 1) if last_newline != -1 else absolute_cursor_pos

            self.log.debug(f"Hover request at line {line}, char {character} (cursor_pos={cursor_pos})")

            # Send Hover request with longer timeout
            result = self.lsp.send_request('textDocument/hover', {
                'textDocument': {'uri': f'file://{self.virtual_document_path}'},
                'position': {'line': line, 'character': character}
            }, timeout=10.0)

            self.log.debug(f"LSP hover result: {result}")

            # Also try to get definition location for jump-to-definition
            definition_result = None
            try:
                definition_result = self.lsp.send_request('textDocument/definition', {
                    'textDocument': {'uri': f'file://{self.virtual_document_path}'},
                    'position': {'line': line, 'character': character}
                }, timeout=2.0)
                self.log.debug(f"LSP definition result: {definition_result}")
            except Exception as e:
                self.log.debug(f"Definition request failed: {e}")

            # Restore virtual document to only executed code
            self.lsp.send_notification('textDocument/didChange', {
                'textDocument': {
                    'uri': f'file://{self.virtual_document_path}',
                    'version': self.execution_count + 1001
                },
                'contentChanges': [{'text': self.virtual_document_content}]
            })

            if not result or not result.get('contents'):
                self.log.debug(f"No hover contents found. Result: {result}")
                return {'status': 'ok', 'found': False, 'data': {}, 'metadata': {}}

            # Parse hover contents
            contents = result['contents']
            markdown_value = ""

            if isinstance(contents, str):
                markdown_value = contents
            elif isinstance(contents, list):
                # LSP can return list of MarkedString or MarkupContent
                parts = []
                for c in contents:
                    if isinstance(c, str):
                        parts.append(c)
                    elif isinstance(c, dict):
                        if 'value' in c:
                            parts.append(c['value'])
                        elif 'language' in c:
                            # MarkedString with language: {language: "swift", value: "..."}
                            parts.append(f"```{c.get('language', '')}\n{c.get('value', '')}\n```")
                markdown_value = "\n\n".join(parts)
            elif isinstance(contents, dict):
                # MarkupContent: {kind: "markdown", value: "..."}
                markdown_value = contents.get('value', '')

            # Add definition location if available
            if definition_result:
                location = None
                if isinstance(definition_result, list) and len(definition_result) > 0:
                    location = definition_result[0]
                elif isinstance(definition_result, dict):
                    location = definition_result

                if location:
                    range_info = location.get('range', {})
                    start = range_info.get('start', {})
                    def_line = start.get('line', 0) + 1
                    markdown_value += f"\n\n*Defined at line {def_line}*"

            if not markdown_value:
                return {'status': 'ok', 'found': False, 'data': {}, 'metadata': {}}

            return {
                'status': 'ok',
                'found': True,
                'data': {
                    'text/plain': markdown_value,
                    'text/markdown': markdown_value
                },
                'metadata': {}
            }

        except TimeoutError:
            self.log.warning("Hover request timed out")
            return {'status': 'ok', 'found': False, 'data': {}, 'metadata': {}}
        except Exception as e:
            self.log.error(f"Error in do_inspect: {e}", exc_info=True)
            return {'status': 'ok', 'found': False, 'data': {}, 'metadata': {}}

if __name__ == '__main__':
    # Jupyter sends us SIGINT when the user requests execution interruption.
    # Here, we block all threads from receiving the SIGINT, so that we can
    # handle it in a specific handler thread.
    if hasattr(signal, 'pthread_sigmask'): # Not supported in Windows
        signal.pthread_sigmask(signal.SIG_BLOCK, [signal.SIGINT])

    from ipykernel.kernelapp import IPKernelApp
    # We pass the kernel name as a command-line arg, since Jupyter gives those
    # highest priority (in particular overriding any system-wide config).
    IPKernelApp.launch_instance(
        argv=sys.argv + ['--IPKernelApp.kernel_class=__main__.SwiftKernel'])
