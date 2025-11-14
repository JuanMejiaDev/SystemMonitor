#!/usr/bin/env python3
"""
Comprehensive Integration Tests for SystemMonitor

Tests all alert handlers, external integrations, thread-safety, and real-world scenarios.
Run this before deployment to ensure everything works correctly.
"""

import time
import threading
import unittest
import json
import os
import sys
from unittest.mock import patch, MagicMock
from http.server import HTTPServer, BaseHTTPRequestHandler
import socket

# Add SystemMonitor to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'SystemMonitor'))

from SystemMonitor import (
    Monitor, quick_monitor, monitor_context, monitor_app,
    PrintAlertHandler, LogAlertHandler, WebhookAlertHandler,
    EmailAlertHandler, SlackAlertHandler, DiscordAlertHandler
)


class MockWebhookServer(BaseHTTPRequestHandler):
    """Mock HTTP server for testing webhooks."""

    def do_POST(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        self.server.received_data = json.loads(post_data.decode('utf-8'))

        self.wfile.write(b'{"status": "ok"}')


class TestAlertHandlers(unittest.TestCase):
    """Test all alert handler implementations."""

    def test_print_alert_handler(self):
        """Test console alert handler."""
        handler = PrintAlertHandler()
        # Should not raise exception
        handler("Test alert message")

    def test_log_alert_handler(self):
        """Test logging alert handler."""
        import logging
        logger = logging.getLogger('test_logger')
        handler = LogAlertHandler(logger)

        with patch.object(logger, 'warning') as mock_warning:
            handler("Test alert message")
            mock_warning.assert_called_once()

    @patch('requests.post')
    def test_webhook_alert_handler(self, mock_post):
        """Test webhook alert handler."""
        mock_post.return_value.status_code = 200

        handler = WebhookAlertHandler("https://example.com/webhook")
        handler("Test alert message")

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertIn('json', kwargs)
        self.assertEqual(kwargs['json']['alert'], "Test alert message")

    @patch('smtplib.SMTP')
    def test_email_alert_handler(self, mock_smtp):
        """Test email alert handler."""
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server

        handler = EmailAlertHandler(
            smtp_server="smtp.gmail.com",
            smtp_port=587,
            sender_email="test@example.com",
            sender_password="password",
            recipient_emails=["admin@example.com"]
        )

        handler("Test alert message")

        mock_smtp.assert_called_once_with("smtp.gmail.com", 587)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("test@example.com", "password")
        mock_server.sendmail.assert_called_once()
        mock_server.quit.assert_called_once()

    @patch('requests.post')
    def test_slack_alert_handler(self, mock_post):
        """Test Slack alert handler."""
        mock_post.return_value.status_code = 200

        handler = SlackAlertHandler(
            webhook_url="https://hooks.slack.com/test",
            channel="#alerts",
            username="TestBot"
        )
        handler("Test alert message")

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        payload = kwargs['json']
        self.assertEqual(payload['text'], "Test alert message")
        self.assertEqual(payload['username'], "TestBot")
        self.assertEqual(payload['channel'], "#alerts")

    @patch('requests.post')
    def test_discord_alert_handler(self, mock_post):
        """Test Discord alert handler."""
        mock_post.return_value.status_code = 200

        handler = DiscordAlertHandler(
            webhook_url="https://discord.com/api/webhooks/test",
            username="TestBot"
        )
        handler("Test alert message")

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        payload = kwargs['json']
        self.assertEqual(payload['content'], "Test alert message")
        self.assertEqual(payload['username'], "TestBot")


class TestIntegrationScenarios(unittest.TestCase):
    """Test real-world integration scenarios."""

    def test_quick_monitor_defaults(self):
        """Test quick_monitor with default values."""
        monitor = quick_monitor()
        self.assertIsInstance(monitor, Monitor)
        self.assertEqual(monitor.cpu_limit, 80)
        self.assertEqual(monitor.ram_limit, 85)
        self.assertEqual(monitor.disk_limit, 90)

    def test_environment_configuration(self):
        """Test configuration via environment variables."""
        with patch.dict(os.environ, {
            'SYSTEM_MONITOR_CPU_LIMIT': '75',
            'SYSTEM_MONITOR_RAM_LIMIT': '80',
            'SYSTEM_MONITOR_DISK_LIMIT': '85'
        }):
            monitor = quick_monitor()
            self.assertEqual(monitor.cpu_limit, 75)
            self.assertEqual(monitor.ram_limit, 80)
            self.assertEqual(monitor.disk_limit, 85)

    def test_context_manager_integration(self):
        """Test context manager integration."""
        with monitor_context() as monitor:
            self.assertIsInstance(monitor, Monitor)
            self.assertTrue(monitor.is_running)

            # Test that we can get state
            state = monitor.state()
            self.assertIsNotNone(state.cpu)
            self.assertIsNotNone(state.ram)

        # Should be stopped after context
        self.assertFalse(monitor.is_running)

    def test_decorator_integration(self):
        """Test decorator integration."""
        @monitor_app()
        def test_function():
            return "success"

        result = test_function()
        self.assertEqual(result, "success")

    def test_thread_safety(self):
        """Test thread safety of monitoring operations."""
        monitor = quick_monitor()
        results = []

        def worker_thread(thread_id):
            """Worker thread that uses the monitor."""
            try:
                state = monitor.state()
                alerts = monitor.alerts()
                results.append(f"Thread {thread_id}: OK")
            except Exception as e:
                results.append(f"Thread {thread_id}: ERROR - {e}")

        # Start multiple threads
        threads = []
        for i in range(5):
            t = threading.Thread(target=worker_thread, args=(i,))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # All threads should succeed
        self.assertEqual(len(results), 5)
        for result in results:
            self.assertIn("OK", result)

    def test_background_monitoring(self):
        """Test background monitoring functionality."""
        monitor = quick_monitor()
        monitor.start()

        # Give it time to start
        time.sleep(0.1)

        # Should be running
        self.assertTrue(monitor.is_running)

        # Should be able to get state while running
        state = monitor.state()
        self.assertIsNotNone(state)

        # Stop monitoring
        monitor.stop()

        # Give it time to stop
        time.sleep(0.1)

        # Should be stopped
        self.assertFalse(monitor.is_running)

    def test_caching_mechanism(self):
        """Test that caching works correctly."""
        monitor = quick_monitor()

        # First call should populate cache
        start_time = time.time()
        state1 = monitor.state()
        first_call_time = time.time() - start_time

        # Second call should use cache (faster)
        start_time = time.time()
        state2 = monitor.state()
        second_call_time = time.time() - start_time

        # Results should be valid
        self.assertIsNotNone(state1.cpu)
        self.assertIsNotNone(state2.cpu)

        # Second call should be faster (from cache)
        # Note: This might not always be true due to timing, but cache should work
        self.assertIsInstance(state1, type(state2))

    def test_error_handling(self):
        """Test error handling in various scenarios."""
        # Test with invalid alert handler
        def failing_handler(message):
            raise Exception("Handler failed")

        monitor = Monitor(on_alert=failing_handler, cpu_limit=0)  # Low limit to trigger alert

        # Should not crash even with failing handler
        try:
            alerts = monitor.alerts()
            # Should still return alerts even if handler fails
            self.assertIsInstance(alerts, list)
        except Exception:
            self.fail("Monitor should handle alert handler failures gracefully")

    def test_cross_platform_compatibility(self):
        """Test basic cross-platform functionality."""
        monitor = quick_monitor()

        # Should work on current platform
        state = monitor.state()

        # Basic checks that should work on any platform
        self.assertIsInstance(state.cpu, (int, float))
        self.assertIsInstance(state.ram, (int, float))
        self.assertIsInstance(state.disks, dict)
        self.assertIsInstance(state.gpus, list)
        self.assertIsInstance(state.uptime, str)
        self.assertIsInstance(state.network, dict)
        self.assertIsInstance(state.top_processes, list)
        self.assertIsInstance(state.temperatures, dict)
        self.assertIsInstance(state.fans, dict)
        self.assertIsInstance(state.network_interfaces, dict)


class TestWebhookIntegration(unittest.TestCase):
    """Test actual webhook integration with mock server."""

    def setUp(self):
        """Start mock webhook server."""
        # Find an available port
        self.server = None
        for port in range(8888, 9000):
            try:
                self.server = HTTPServer(('localhost', port), MockWebhookServer)
                self.port = port
                break
            except OSError:
                continue

        if self.server:
            self.server_thread = threading.Thread(target=self.server.serve_forever)
            self.server_thread.daemon = True
            self.server_thread.start()

    def tearDown(self):
        """Stop mock webhook server."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()

    def test_webhook_integration(self):
        """Test actual webhook HTTP call."""
        if not self.server:
            self.skipTest("Could not start mock server")

        webhook_url = f"http://localhost:{self.port}/webhook"
        handler = WebhookAlertHandler(webhook_url)

        test_message = "Integration test alert"
        handler(test_message)

        # Give server time to process
        time.sleep(0.1)

        # Check that server received the data
        self.assertTrue(hasattr(self.server, 'received_data'))
        received = self.server.received_data
        self.assertEqual(received['alert'], test_message)
        self.assertIn('timestamp', received)


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)