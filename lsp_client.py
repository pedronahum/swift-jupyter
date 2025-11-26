import json
import os
import subprocess
import threading
import logging
import time

class LSPClient:
    def __init__(self, executable_path, args=None, log=None, env=None):
        self.executable_path = executable_path
        self.args = args or []
        self.process = None
        self.log = log or logging.getLogger(__name__)
        self.env = env
        self.lock = threading.Lock()
        self.request_id = 0
        self.responses = {}
        self.response_events = {}
        self.running = False
        self.reader_thread = None
        self.stderr_thread = None
        self.diagnostics_callback = None  # Callback for diagnostics notifications

    def start(self):
        """Start the LSP server process."""
        try:
            cmd = [self.executable_path] + self.args
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=self.env,
                bufsize=0  # Unbuffered
            )
            self.running = True
            
            # Start stdout reader
            self.reader_thread = threading.Thread(target=self._read_loop)
            self.reader_thread.daemon = True
            self.reader_thread.start()
            
            # Start stderr reader
            self.stderr_thread = threading.Thread(target=self._stderr_loop)
            self.stderr_thread.daemon = True
            self.stderr_thread.start()
            
            self.log.info(f"Started LSP server: {self.executable_path}")
        except Exception as e:
            self.log.error(f"Failed to start LSP server: {e}")
            raise

    def stop(self):
        """Stop the LSP server process."""
        self.running = False
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except Exception as e:
                self.log.error(f"Error stopping LSP server: {e}")
                if self.process:
                    self.process.kill()

    def _read_loop(self):
        """Read messages from the LSP server stdout."""
        while self.running and self.process:
            try:
                # Read Content-Length header
                header = self._read_header()
                if not header:
                    break
                
                content_length = int(header.get('Content-Length', 0))
                if content_length == 0:
                    continue

                # Read content
                content = self.process.stdout.read(content_length)
                if not content:
                    break

                message = json.loads(content.decode('utf-8'))
                self._handle_message(message)

            except Exception as e:
                self.log.error(f"Error in LSP read loop: {e}")
                break

    def _stderr_loop(self):
        """Read messages from the LSP server stderr."""
        while self.running and self.process:
            try:
                line = self.process.stderr.readline()
                if not line:
                    break
                self.log.warning(f"LSP Stderr: {line.decode('utf-8', errors='replace').strip()}")
            except Exception as e:
                self.log.error(f"Error in LSP stderr loop: {e}")
                break

    def _read_header(self):
        """Read HTTP-style headers from stdout."""
        headers = {}
        while True:
            line = self.process.stdout.readline()
            if not line:
                return None
            line = line.decode('utf-8').strip()
            if not line:
                break
            parts = line.split(':', 1)
            if len(parts) == 2:
                headers[parts[0].strip()] = parts[1].strip()
        return headers

    def _handle_message(self, message):
        """Handle an incoming JSON-RPC message."""
        if 'id' in message:
            request_id = message['id']
            with self.lock:
                if request_id in self.response_events:
                    self.responses[request_id] = message
                    self.response_events[request_id].set()
        else:
            # Notification or log message
            method = message.get('method', '')
            if method == 'window/logMessage':
                self.log.debug(f"LSP Log: {message.get('params', {})}")
            elif method == 'textDocument/publishDiagnostics':
                # Handle diagnostics notification
                if self.diagnostics_callback:
                    try:
                        self.diagnostics_callback(message.get('params', {}))
                    except Exception as e:
                        self.log.error(f"Error in diagnostics callback: {e}")

    def send_request(self, method, params, timeout=15.0):
        """Send a JSON-RPC request and wait for the response."""
        with self.lock:
            self.request_id += 1
            request_id = self.request_id
            event = threading.Event()
            self.response_events[request_id] = event

        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params
        }

        self._send_message(request)

        if event.wait(timeout):
            with self.lock:
                response = self.responses.pop(request_id)
                del self.response_events[request_id]
            
            if 'error' in response:
                raise Exception(f"LSP Error: {response['error']}")
            return response.get('result')
        else:
            with self.lock:
                del self.response_events[request_id]
            raise TimeoutError(f"LSP request {method} timed out after {timeout}s")

    def send_notification(self, method, params):
        """Send a JSON-RPC notification (no response expected)."""
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }
        self._send_message(notification)

    def _send_message(self, message):
        """Send a raw JSON message with headers."""
        content = json.dumps(message).encode('utf-8')
        header = f"Content-Length: {len(content)}\r\n\r\n".encode('utf-8')
        try:
            with self.lock:
                self.process.stdin.write(header)
                self.process.stdin.write(content)
                self.process.stdin.flush()
        except Exception as e:
            self.log.error(f"Failed to send message: {e}")
            raise

    def initialize(self, root_path):
        """Initialize the LSP session."""
        params = {
            "processId": os.getpid(),
            "rootUri": f"file://{root_path}",
            "capabilities": {
                "textDocument": {
                    "completion": {
                        "completionItem": {
                            "snippetSupport": False
                        }
                    },
                    "hover": {
                        "contentFormat": ["markdown", "plaintext"]
                    },
                    "publishDiagnostics": {
                        "relatedInformation": True,
                        "tagSupport": {"valueSet": [1, 2]},
                        "versionSupport": True
                    },
                    "synchronization": {
                        "dynamicRegistration": False,
                        "willSave": False,
                        "didSave": False,
                        "didSaveWaitUntil": False
                    }
                }
            }
        }
        result = self.send_request("initialize", params)
        self.send_notification("initialized", {})
        return result

    def set_diagnostics_callback(self, callback):
        """Set a callback function to be called when diagnostics are received.

        Args:
            callback: Function that takes a diagnostics params dict
        """
        self.diagnostics_callback = callback
