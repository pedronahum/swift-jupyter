"""Pytest configuration and fixtures for Swift-Jupyter testing (R6-T1).

This module provides shared fixtures for all test modules, including
kernel management, client setup, and common test utilities.

Created: October 17, 2025
Region: R6 - Testing Infrastructure
"""

import pytest
import jupyter_client
import os
import time
import logging

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.fixture(scope='session')
def kernel_manager():
    """Start Swift kernel for testing session.

    This fixture starts a kernel once per test session and shares it
    across all tests. The kernel is shut down after all tests complete.

    Yields:
        tuple: (KernelManager, KernelClient)
    """
    logger.info('🚀 Starting Swift kernel for test session...')

    try:
        km, kc = jupyter_client.manager.start_new_kernel(
            kernel_name='swift',
            startup_timeout=60
        )
        logger.info('✅ Swift kernel started successfully')

        # Wait for kernel to be ready
        kc.wait_for_ready(timeout=60)
        logger.info('✅ Kernel is ready')

        yield km, kc

    finally:
        logger.info('🛑 Shutting down Swift kernel...')
        try:
            if 'km' in locals():
                km.shutdown_kernel(now=True)
                logger.info('✅ Kernel shut down successfully')
        except Exception as e:
            logger.error(f'Error shutting down kernel: {e}')


@pytest.fixture
def kernel_client(kernel_manager):
    """Get kernel client for a test.

    This fixture provides a kernel client for individual tests.
    Each test gets the same client (from session-scoped kernel_manager).

    Args:
        kernel_manager: Session-scoped kernel manager fixture

    Returns:
        KernelClient: Client for communicating with the kernel
    """
    _, kc = kernel_manager

    # Clear any pending messages before test
    while True:
        try:
            kc.get_iopub_msg(timeout=0.1)
        except Exception:
            break

    return kc


@pytest.fixture
def execute_code(kernel_client):
    """Helper fixture for executing code and waiting for result.

    Args:
        kernel_client: Kernel client fixture

    Returns:
        function: Function that executes code and returns result
    """
    def _execute(code, timeout=10):
        """Execute code and return result.

        Args:
            code: Swift code to execute
            timeout: Maximum time to wait for execution

        Returns:
            dict: Execution result with status, output, and error
        """
        kc = kernel_client
        msg_id = kc.execute(code, silent=False, store_history=True)

        result = {
            'status': None,
            'output': [],
            'error': None,
            'execution_count': None
        }

        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                msg = kc.get_iopub_msg(timeout=1.0)
                msg_type = msg['msg_type']
                content = msg['content']

                if msg_type == 'status':
                    status = content.get('execution_state')
                    if status == 'idle':
                        # Execution finished, get shell reply
                        reply = kc.get_shell_msg(timeout=1.0)
                        result['status'] = reply['content']['status']
                        result['execution_count'] = reply['content'].get('execution_count')
                        return result

                elif msg_type == 'stream':
                    result['output'].append({
                        'type': 'stream',
                        'name': content['name'],
                        'text': content['text']
                    })

                elif msg_type == 'execute_result':
                    result['output'].append({
                        'type': 'execute_result',
                        'data': content['data'],
                        'execution_count': content['execution_count']
                    })

                elif msg_type == 'error':
                    result['error'] = {
                        'ename': content['ename'],
                        'evalue': content['evalue'],
                        'traceback': content['traceback']
                    }

                elif msg_type == 'display_data':
                    result['output'].append({
                        'type': 'display_data',
                        'data': content['data'],
                        'metadata': content.get('metadata', {})
                    })

            except Exception as e:
                # Timeout or other error
                logger.debug(f'Exception while waiting for message: {e}')
                continue

        # Timeout
        result['status'] = 'timeout'
        return result

    return _execute


@pytest.fixture
def wait_for_idle(kernel_client):
    """Helper fixture to wait for kernel to become idle.

    Args:
        kernel_client: Kernel client fixture

    Returns:
        function: Function that waits for idle state
    """
    def _wait(timeout=10):
        """Wait for kernel to become idle.

        Args:
            timeout: Maximum time to wait

        Returns:
            bool: True if kernel became idle, False if timeout
        """
        kc = kernel_client
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                msg = kc.get_iopub_msg(timeout=0.5)
                if msg['msg_type'] == 'status':
                    if msg['content']['execution_state'] == 'idle':
                        return True
            except Exception:
                continue

        return False

    return _wait


# Test markers for categorization
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "protocol: tests for Jupyter protocol compliance (R3)"
    )
    config.addinivalue_line(
        "markers", "unicode: tests for Unicode handling (R5)"
    )
    config.addinivalue_line(
        "markers", "interrupt: tests for interrupt functionality (R3+R5)"
    )
    config.addinivalue_line(
        "markers", "display: tests for display functionality (R4)"
    )
    config.addinivalue_line(
        "markers", "error: tests for error handling (R5)"
    )
    config.addinivalue_line(
        "markers", "slow: tests that take more than 5 seconds"
    )
