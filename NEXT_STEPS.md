# Next Steps to Improve swift-jupyter

## Current Status

The Swift Jupyter kernel is now **functional** with these improvements:
- ✅ Works with system Python 3.9.6 (compatible with LLDB)
- ✅ Apple Silicon architecture fix for LLDB target creation
- ✅ Modern kernel registration with `interrupt_mode: message`
- ✅ Protocol 5.3 compliance (partial 5.4)
- ✅ Display layer delegated to Session (no manual HMAC)
- ✅ Unicode handling and interrupt support
- ✅ Test infrastructure with pytest
- ✅ 16/22 tests passing

## Priority 1: Complete Protocol 5.4 Compliance (R3)

### What's Needed

**R3-T1: Upgrade kernel_info to Protocol 5.4** ⚠️ INCOMPLETE
- Current: Returns protocol_version: '5.3'
- Target: Return protocol_version: '5.4'
- Location: `swift_kernel.py` line ~1232 in `do_kernel_info()`
- Change:
  ```python
  'protocol_version': '5.4',  # Update from 5.3
  ```

**R3-T2: Add control channel interrupt_request handler** ⚠️ MISSING
- Current: Only signal-based interrupts (SIGINT)
- Target: Message-based interrupts via control channel
- Add this method to `SwiftKernel` class:
  ```python
  def interrupt_request(self, stream, ident, parent):
      """Handle interrupt_request on control channel (Protocol 5.4)."""
      self.log.info('Received interrupt_request on control channel')
      try:
          # Use existing SIGINTHandler mechanism
          if hasattr(self, 'sigint_handler'):
              self.sigint_handler.interrupted = True
              if self.process and self.process.IsValid():
                  self.process.SendAsyncInterrupt()
          content = {'status': 'ok'}
      except Exception as e:
          self.log.error(f'Interrupt failed: {e}')
          content = {'status': 'error'}
      self.session.send(stream, 'interrupt_reply', content, parent, ident)
  ```

**R3-T4: Unicode-aware completion** ⚠️ INCOMPLETE
- Current: May have issues with Unicode cursor positions
- Target: Ensure `do_complete()` handles Unicode codepoint positions correctly
- Test with: `'💡let x = 5\nx.'` (cursor after '.')

### Validation

Run after completing R3:
```bash
/usr/bin/python3 test/fast_test.py SwiftKernelTests -v
# Should have more tests passing, especially interrupt tests
```

## Priority 2: Fix Failing Tests (R6)

### Currently Failing Tests (6 failures)

1. **test_graphics_matplotlib** - Needs Python interop setup
2. **test_interrupt_execution** - Timing issue, may be fixed by R3-T2
3. **test_show_tensor** - Needs Swift for TensorFlow
4. **test_swift_completion** - Code completion not working
5. **test_gradient_across_cells** - Needs differentiation support
6. **test_gradient_across_cells_error** - Needs differentiation support

### Actions

**Fix interrupt test (depends on R3-T2):**
```bash
# After implementing R3-T2, test:
/usr/bin/python3 test/fast_test.py SwiftKernelTests.test_interrupt_execution
```

**Fix completion:**
- Debug why `test_swift_completion` returns empty matches
- Check if LLDB's completion API is available
- Location: `swift_kernel.py` `do_complete()` method

**Document TensorFlow limitations:**
- Update README to note Swift for TensorFlow is optional
- Mark tests as `@pytest.mark.skip(reason="Requires Swift for TensorFlow")`

## Priority 3: Python Version Compatibility (Critical)

### Current Limitation

**The kernel only works with system Python 3.9.6** because:
- LLDB's Python module is compiled for Apple's Python 3.9.6
- Conda Python 3.9.23 causes **segmentation faults** when importing LLDB
- This is a binary compatibility issue

### Solutions

**Option A: Document the requirement** (Quick, recommended)
- Update README with clear Python version requirements
- Add to [HOW_TO_TEST.md](HOW_TO_TEST.md)
- Create troubleshooting guide

**Option B: Create Python wrapper** (Medium effort)
- Create a launcher script that uses system Python
- Allow conda environments for other dependencies
- Keep LLDB imports in system Python context

**Option C: Build LLDB for conda Python** (High effort)
- Compile LLDB with conda Python 3.9
- Package as conda package
- Significant build complexity

**Recommended:** Start with Option A, document clearly

## Priority 4: Documentation & UX

### Update Documentation

**README.md:**
```markdown
## Requirements

- **Python**: System Python 3.9.6 (macOS) or matching LLDB Python version
  - ⚠️ **Do not use conda/virtualenv Python** - causes LLDB import failures
  - Check version: `/usr/bin/python3 --version`
- **Swift Toolchain**: 6.3+ with LLDB Python 3 bindings
- **Jupyter**: Install via: `/usr/bin/python3 -m pip install --user jupyter`

## Installation

```bash
# Use system Python
/usr/bin/python3 -m pip install --user jupyter ipykernel

# Register kernel
/usr/bin/python3 register.py --sys-prefix \\
  --swift-toolchain /path/to/toolchain
```

## Troubleshooting

### Kernel dies on startup
- **Cause**: Using wrong Python version
- **Fix**: Ensure using system Python 3.9.6, not conda Python
- **Check**: `cat ~/Library/Jupyter/kernels/swift/kernel.json | grep python`
```

**Create TROUBLESHOOTING.md:**
- Common issues and solutions
- Python version mismatches
- LLDB import errors
- Kernel registration problems

### Better Error Messages

Add validation to `swift_kernel.py` startup:
```python
# Add at top of SwiftKernel.__init__()
import sys
import platform

# Warn if not using system Python on macOS
if platform.system() == 'Darwin':
    if 'conda' in sys.executable or 'virtualenv' in sys.executable:
        self.log.warning(
            f'⚠️  Using {sys.executable} which may not be compatible with LLDB. '
            f'Consider using system Python: /usr/bin/python3'
        )
```

## Priority 5: CI/CD & Automation

### GitHub Actions Workflow

Create `.github/workflows/test.yml`:
```yaml
name: Test Swift Jupyter Kernel

on: [push, pull_request]

jobs:
  test-macos:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install Swift toolchain
        run: |
          # Download and install Swift toolchain

      - name: Install Jupyter
        run: |
          /usr/bin/python3 -m pip install --user jupyter pytest

      - name: Register kernel
        run: |
          /usr/bin/python3 register.py --user --swift-toolchain /path

      - name: Run tests
        run: |
          /usr/bin/python3 -m pytest test/fast_test.py -v
```

### Pre-commit Hooks

Create `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black
        language_version: python3.9

  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.1.14
    hooks:
      - id: ruff
```

## Priority 6: Conda Package (Optional)

### Create conda-forge Package

This would solve the Python version compatibility issue by:
1. Building LLDB Python bindings for conda Python
2. Packaging everything together
3. Enabling: `conda install -c conda-forge swift-jupyter`

**Effort**: High (2-3 weeks)
**Impact**: Very high (much better UX)

## Priority 7: Docker Updates (R7)

### Modernize Dockerfile

Update `docker/Dockerfile` to use:
- Ubuntu 22.04 or Swift official base image
- System Python (not conda) for LLDB compatibility
- Modern Jupyter stack
- Health checks

**Test Command:**
```bash
docker build -t swift-jupyter:latest .
docker run -p 8888:8888 swift-jupyter:latest
```

## Quick Wins (Can Do Now)

### 1. Fix Deprecation Warning
Location: `swift_kernel.py:1291`
```python
# Replace:
self._parent_header

# With:
self.get_parent()
```

### 2. Add Version Info
```python
# Add to swift_kernel.py
__version__ = '0.4.0'
```

### 3. Clean Up Test Output
Add `-q` flag to pytest for cleaner output

### 4. Add Examples
Create `examples/` directory with:
- `01_basics.ipynb` - Variables, functions, print
- `02_data_structures.ipynb` - Arrays, dictionaries
- `03_display.ipynb` - Display outputs
- `04_error_handling.ipynb` - Error messages

## Summary Timeline

| Priority | Task | Effort | Impact | Status |
|----------|------|--------|--------|--------|
| 1 | Complete R3 (Protocol 5.4) | 2-3 hours | High | In Progress |
| 2 | Fix failing tests | 3-4 hours | Medium | Pending |
| 3 | Document Python requirement | 1 hour | High | Pending |
| 4 | Improve documentation | 2-3 hours | High | Pending |
| 5 | Add CI/CD | 2-3 hours | Medium | Pending |
| 6 | Conda package | 2-3 weeks | Very High | Future |
| 7 | Docker updates | 2-3 hours | Low | Future |

## Getting Started

**To continue the modernization:**

```bash
cd /Users/pedro/programming/swift/swift-jupyter

# 1. Complete Protocol 5.4
# Edit swift_kernel.py and implement R3-T1, R3-T2, R3-T4

# 2. Run tests
/usr/bin/python3 test/fast_test.py SwiftKernelTests -v

# 3. Update documentation
# Edit README.md, create TROUBLESHOOTING.md

# 4. Commit progress
git add -A
git commit -m "Complete Protocol 5.4 compliance (R3)"
git tag v0.4.0-r3-complete
```

## Questions?

See:
- [HOW_TO_TEST.md](HOW_TO_TEST.md) - Testing instructions
- [modernization-plan.json](modernization-plan.json) - Full modernization plan
- [R2_COMPLETION_REPORT.md](R2_COMPLETION_REPORT.md) - Previous progress
- [R5_COMPLETION_REPORT.md](R5_COMPLETION_REPORT.md) - LLDB improvements
- [R6_COMPLETION_REPORT.md](R6_COMPLETION_REPORT.md) - Test infrastructure
