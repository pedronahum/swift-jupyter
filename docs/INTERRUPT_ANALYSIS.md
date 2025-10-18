# Swift-Jupyter Interrupt Mechanism Analysis & Fix Proposal

**Date**: October 17, 2025
**Issue**: R3-T2 interrupt handler not working properly
**Current Status**: Using signal-based interrupts (`interrupt_mode: signal`)
**Target**: Message-based interrupts (`interrupt_mode: message`) per Jupyter Protocol 5.4

## Current Implementation Analysis

### 1. Current Interrupt Mode
```json
{
  "interrupt_mode": "signal"
}
```

### 2. Current SIGINT-Based Mechanism

**Location**: `swift_kernel.py:113-129`

```python
class SIGINTHandler(threading.Thread):
    """Interrupts currently-executing code whenever the process receives a SIGINT."""

    daemon = True

    def __init__(self, kernel):
        super(SIGINTHandler, self).__init__()
        self.kernel = kernel

    def run(self):
        try:
            while True:
                signal.sigwait([signal.SIGINT])
                self.kernel.process.SendAsyncInterrupt()  # LLDB async interrupt
        except Exception as e:
            self.kernel.log.error('Exception in SIGINTHandler: %s' % str(e))
```

**Main thread signal blocking** (`swift_kernel.py:1088-1089`):
```python
if hasattr(signal, 'pthread_sigmask'):
    signal.pthread_sigmask(signal.SIG_BLOCK, [signal.SIGINT])
```

### 3. How It Currently Works

1. **Main thread blocks SIGINT** using `pthread_sigmask`
2. **SIGINTHandler thread** waits for SIGINT using `signal.sigwait([signal.SIGINT])`
3. **When SIGINT arrives**, the handler calls `kernel.process.SendAsyncInterrupt()`
4. **LLDB interrupts** the Swift execution

### 4. Issues with Signal-Based Approach

According to Jupyter Protocol 5.4 and the modernization plan:

1. **Not portable**: Signal-based interrupts don't work well on Windows
2. **Not reliable**: Signals can be lost or delayed
3. **No confirmation**: No way to confirm interrupt was received and processed
4. **Race conditions**: Signals can arrive at inopportune times
5. **Modern protocol**: Jupyter Protocol 5.4 prefers message-based interrupts

## Modernization Plan Requirements (R3-T2)

From `modernization-plan.json` lines 489-508:

### Required Implementation

```python
def interrupt_request(self, stream, ident, parent):
    """Handle interrupt_request on control channel (protocol 5.4).

    This is called when user clicks interrupt in Jupyter UI.
    Should interrupt current execution and return interrupt_reply.
    """
    self.log.info('Received interrupt_request on control channel')

    try:
        # Signal the LLDB/Swift execution to stop
        self._interrupt_execution()

        content = {'status': 'ok'}
    except Exception as e:
        self.log.error(f'Interrupt failed: {e}')
        content = {'status': 'error', 'ename': str(type(e).__name__), 'evalue': str(e)}

    # Send interrupt_reply on control channel
    self.session.send(stream, 'interrupt_reply', content, parent, ident)

def _interrupt_execution(self):
    """Interrupt current LLDB execution."""
    if hasattr(self, '_swift_shell'):
        self._swift_shell.interrupt()
```

### Integration Points

From the plan (lines 498-502):
- May need to add `interrupt()` method to swift_shell
- Consider using `threading.Event` for interrupt flag
- LLDB may need signal handling setup

## Problem Diagnosis

### Why Current Approach Doesn't Work with `interrupt_mode: message`

1. **No `interrupt_request` handler**: The kernel doesn't implement the control channel handler
2. **Kernel.json mismatch**: Set to `signal` mode but plan requires `message` mode
3. **No control channel**: Need to verify kernel has control channel socket
4. **LLDB async interrupt**: `process.SendAsyncInterrupt()` works but needs proper invocation

## Proposed Fix (Phased Approach)

### Phase 1: Add Message-Based Handler (Keep Signal Fallback)

**Step 1.1**: Add `interrupt_request` method to SwiftKernel class

```python
def interrupt_request(self, stream, ident, parent):
    """Handle interrupt_request on control channel (Jupyter Protocol 5.4).

    Called when user clicks interrupt button in Jupyter UI.
    This is the modern, message-based interrupt mechanism.
    """
    self.log.info('🛑 Received interrupt_request on control channel')

    try:
        # Use existing LLDB interrupt mechanism
        if hasattr(self, 'process') and self.process:
            self.log.info('Sending async interrupt to LLDB process')
            self.process.SendAsyncInterrupt()
            content = {'status': 'ok'}
        else:
            self.log.warning('No LLDB process to interrupt')
            content = {'status': 'error',
                      'ename': 'NoProcess',
                      'evalue': 'No Swift process running'}
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
```

**Step 1.2**: Add to SwiftKernel class initialization

Verify control channel is available (it should be automatically created by ipykernel).

**Step 1.3**: Keep existing SIGINTHandler as fallback

Don't remove the signal-based handler yet - it provides backward compatibility.

### Phase 2: Update kernel.json

**File**: Generated by `register.py` (per R2-T2)

```json
{
  "interrupt_mode": "message",
  "metadata": {
    "debugger": true
  }
}
```

This tells Jupyter to send `interrupt_request` messages instead of SIGINT signals.

### Phase 3: Enhanced LLDB Interrupt Support

From modernization plan R5-T2 (lines 689-704):

```python
class LLDBExecutor:
    def __init__(self):
        self.debugger = lldb.SBDebugger.Create()
        self.process = None
        self.interrupted = False
        self.interrupt_lock = threading.Lock()

    def interrupt(self):
        """Interrupt current execution."""
        with self.interrupt_lock:
            self.interrupted = True

            if self.process and self.process.IsValid():
                # Option 1: Use LLDB's async interrupt
                self.process.SendAsyncInterrupt()

                # Option 2: If that doesn't work, try Stop()
                # self.process.Stop()

        self.log.info('Interrupt signal sent to LLDB')

    def check_interrupted(self):
        """Check if execution should be interrupted."""
        with self.interrupt_lock:
            return self.interrupted

    def clear_interrupt(self):
        """Clear interrupt flag."""
        with self.interrupt_lock:
            self.interrupted = False
```

## Implementation Strategy

### Recommended Approach: Hybrid Mode

1. **Implement message-based handler** (R3-T2 requirement)
2. **Keep signal-based handler** as fallback for compatibility
3. **Update kernel.json** to `"interrupt_mode": "message"`
4. **Test both mechanisms** work

### Why Hybrid?

- **Forward compatible**: Works with modern Jupyter Protocol 5.4
- **Backward compatible**: Still works if signals are sent
- **Robust**: Double interrupt mechanism increases reliability
- **Safe migration**: Can switch back if issues arise

## Testing Plan

### Test 1: Message-Based Interrupt
```python
import jupyter_client

km, kc = jupyter_client.manager.start_new_kernel(kernel_name='swift')

# Start long-running code
msg_id = kc.execute('while true { Thread.sleep(forTimeInterval: 0.1) }')

# Wait a bit
import time
time.sleep(2)

# Send interrupt via control channel
kc.interrupt()

# Check for interrupt_reply
# Execution should stop
```

### Test 2: Signal-Based Fallback
```python
import os
import signal

# Get kernel PID
pid = km.kernel.pid

# Send SIGINT
os.kill(pid, signal.SIGINT)

# Should also interrupt
```

### Test 3: Quick Interrupt Response
```python
# Measure time from interrupt to stop
# Should be < 2 seconds per R3-T2 validation
```

## Risks and Mitigation

### Risk 1: LLDB doesn't respond to interrupt
**Probability**: Medium
**Impact**: High
**Mitigation**:
- Add timeout mechanism
- Consider process.Stop() as stronger alternative
- Document limitation if unavoidable

### Risk 2: Control channel not available
**Probability**: Low (ipykernel should create it)
**Impact**: High
**Mitigation**:
- Verify control channel in kernel initialization
- Log warning if missing
- Fall back to signal mode

### Risk 3: Race conditions
**Probability**: Medium
**Impact**: Medium
**Mitigation**:
- Use threading.Lock for interrupt flag
- Careful ordering of interrupt operations
- Test thoroughly

## LLDB-Specific Considerations

### SendAsyncInterrupt() Behavior

From LLDB documentation:
- **Non-blocking**: Returns immediately
- **Async**: Interrupt happens "soon" (not immediate)
- **May require multiple calls**: First interrupt might not catch everything
- **Platform-dependent**: Works differently on macOS vs Linux

### Alternative: process.Stop()

```python
def _interrupt_execution_strong(self):
    """Stronger interrupt mechanism."""
    if self.process and self.process.IsValid():
        # Try async interrupt first
        self.process.SendAsyncInterrupt()

        # If still running after 1 second, use Stop()
        time.sleep(1)
        if self.process.GetState() == lldb.eStateRunning:
            self.log.warning('Async interrupt insufficient, using Stop()')
            self.process.Stop()
```

## Code Locations

### Files to Modify

1. **swift_kernel.py**:
   - Add `interrupt_request()` method (~line 400-450, near other request handlers)
   - Keep existing `SIGINTHandler` class (line 113)
   - Optionally enhance with interrupt flags

2. **register.py** (R2 work):
   - Update kernel.json generation to include `"interrupt_mode": "message"`

3. **swift_shell/__init__.py** (R5 work, optional):
   - Add `interrupt()` method to shell interface
   - Add interrupt flag support

## Quick Win: Minimal Implementation

For immediate fix, add this to SwiftKernel class:

```python
def interrupt_request(self, stream, ident, parent):
    """Handle interrupt_request (Protocol 5.4)."""
    self.log.info('Interrupt requested')
    try:
        if hasattr(self, 'process') and self.process:
            self.process.SendAsyncInterrupt()
            status = 'ok'
        else:
            status = 'error'
    except:
        status = 'error'

    self.session.send(stream, 'interrupt_reply',
                     {'status': status}, parent, ident)
```

Then update kernel.json to:
```json
{
  "interrupt_mode": "message"
}
```

## References

- Jupyter Protocol 5.4: https://jupyter-client.readthedocs.io/en/stable/messaging.html#kernel-interrupt
- Modernization Plan: `modernization-plan.json` R3-T2 (lines 489-508)
- LLDB Python API: https://lldb.llvm.org/use/python-reference.html
- ipykernel source: Control channel handler examples

## Conclusion

The interrupt handler issue stems from:
1. **Missing `interrupt_request` handler** for Protocol 5.4
2. **kernel.json configured for signal mode** instead of message mode
3. **Need to bridge** message-based interrupts to LLDB's `SendAsyncInterrupt()`

**Recommended fix**: Implement message-based handler (Phase 1) with existing LLDB mechanism, update kernel.json to message mode (Phase 2), and enhance with proper interrupt state management (Phase 3) if needed.

**Priority**: High - Critical for R3 completion
**Complexity**: Medium - Core mechanism exists, needs proper protocol integration
**Risk**: Low-Medium - LLDB interrupt behavior may vary by platform
