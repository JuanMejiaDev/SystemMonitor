import unittest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from SystemMonitor import Monitor, State, utils
from SystemMonitor.monitor import PrintAlertHandler


class TestSystemMonitor(unittest.TestCase):

    def test_monitor_creation(self):
        """Test Monitor initialization."""
        monitor = Monitor()
        self.assertIsInstance(monitor, Monitor)
        self.assertEqual(monitor.cpu_limit, 70.0)
        self.assertEqual(monitor.ram_limit, 70.0)
        self.assertEqual(monitor.disk_limit, 80.0)

    def test_state_creation(self):
        """Test State snapshot creation."""
        monitor = Monitor()
        state = monitor.state()
        self.assertIsInstance(state, State)
        self.assertIsInstance(state.cpu, float)
        self.assertIsInstance(state.ram, float)
        self.assertIsInstance(state.disks, dict)
        self.assertIsInstance(state.gpus, list)
        self.assertIsInstance(state.temperatures, dict)
        self.assertIsInstance(state.fans, dict)
        self.assertIsInstance(state.network_interfaces, dict)

    def test_alerts_generation(self):
        """Test alerts generation."""
        monitor = Monitor(cpu_limit=0, ram_limit=0, disk_limit=0)  # Low limits to trigger alerts
        alerts = monitor.alerts()
        self.assertIsInstance(alerts, list)
        # Should have alerts since limits are 0
        self.assertGreater(len(alerts), 0)

    def test_utils_functions(self):
        """Test utility functions."""
        uptime = utils.uptime()
        self.assertIsInstance(uptime, str)
        self.assertIn('d', uptime) or self.assertIn('h', uptime) or self.assertIn('m', uptime)

        gpus = utils.gpus()
        self.assertIsInstance(gpus, list)

        network = utils.network()
        self.assertIsInstance(network, dict)
        self.assertIn('sent_mb', network)
        self.assertIn('recv_mb', network)

        temperatures = utils.temperatures()
        self.assertIsInstance(temperatures, dict)

        fans = utils.fans()
        self.assertIsInstance(fans, dict)

        network_interfaces = utils.network_interfaces()
        self.assertIsInstance(network_interfaces, dict)

    def test_handlers(self):
        """Test alert handlers."""
        handler = PrintAlertHandler()
        # Should not raise exception
        handler("Test alert")

    def test_state_to_dict(self):
        """Test State to_dict conversion."""
        monitor = Monitor()
        state = monitor.state()
        data = state.to_dict()
        self.assertIsInstance(data, dict)
        self.assertIn('cpu', data)
        self.assertIn('ram', data)
        self.assertIn('temperatures', data)
        self.assertIn('fans', data)
        self.assertIn('network_interfaces', data)

    def test_state_to_json(self):
        """Test State to_json conversion."""
        monitor = Monitor()
        state = monitor.state()
        json_str = state.to_json()
        self.assertIsInstance(json_str, str)
        self.assertIn('"cpu"', json_str)

    def test_quick_monitor(self):
        """Test quick_monitor function."""
        from SystemMonitor import quick_monitor
        monitor = quick_monitor()
        self.assertIsInstance(monitor, Monitor)
        self.assertEqual(monitor.cpu_limit, 80)
        self.assertEqual(monitor.ram_limit, 85)

    def test_monitor_context(self):
        """Test monitor_context context manager."""
        from SystemMonitor import monitor_context
        with monitor_context() as monitor:
            self.assertIsInstance(monitor, Monitor)
            self.assertTrue(monitor.is_running)
        # Should be stopped after context
        self.assertFalse(monitor.is_running)

    def test_monitor_decorator(self):
        """Test monitor_app decorator."""
        from SystemMonitor import monitor_app

        @monitor_app()
        def dummy_function():
            return "test"

        result = dummy_function()
        self.assertEqual(result, "test")


if __name__ == '__main__':
    unittest.main()