#!/usr/bin/env python3
"""
SystemMonitor Integration Examples

This file shows how easy it is to integrate SystemMonitor into any application.
"""

import time
import logging
from SystemMonitor import quick_monitor, monitor_context, monitor_app


# Example 1: Simplest integration - just add one line
def simple_app():
    """The simplest way to add monitoring to any app."""
    print("Starting my application...")

    # One line to start monitoring with sensible defaults
    monitor = quick_monitor()
    monitor.start()

    # Your app logic here
    for i in range(10):
        print(f"Working... {i+1}/10")
        time.sleep(2)

    monitor.stop()
    print("Application finished!")


# Example 2: Context manager - automatic start/stop
def context_manager_app():
    """Using context manager for automatic lifecycle management."""
    print("Starting app with context manager...")

    with monitor_context() as monitor:
        # Monitor runs automatically in background
        print("App is running with monitoring...")

        # Simulate some work
        time.sleep(5)

        # Get current system state anytime
        state = monitor.state()
        print(f"Current CPU: {state.cpu:.1f}%, RAM: {state.ram:.1f}%")

    print("App finished - monitoring stopped automatically!")


# Example 3: Decorator for automatic monitoring
@monitor_app()
def decorated_app():
    """Using decorator for zero-effort monitoring."""
    print("This function is automatically monitored!")

    # Simulate app work
    time.sleep(3)

    print("Function completed!")


# Example 4: Custom alerts in a web app
def web_app_example():
    """Example integration in a web application."""

    def custom_alert_handler(message):
        # In a real web app, you might send to logging, email, etc.
        print(f"[WEB APP ALERT] {message}")
        # Could also send to monitoring dashboard, etc.

    monitor = quick_monitor(
        cpu_limit=70,
        ram_limit=80,
        alert_handler=custom_alert_handler
    )
    monitor.start()

    print("Web server started with monitoring...")

    # Simulate handling requests
    for request in range(5):
        print(f"Handling request {request + 1}")
        time.sleep(1)

    monitor.stop()


# Example 5: Environment variable configuration
def env_config_example():
    """
    Configure monitoring via environment variables.

    Set these before running:
    export SYSTEM_MONITOR_CPU_LIMIT=75
    export SYSTEM_MONITOR_RAM_LIMIT=85
    export SYSTEM_MONITOR_LOG_LEVEL=DEBUG
    """
    print("Using environment variable configuration...")

    # quick_monitor() automatically reads env vars
    monitor = quick_monitor()
    print(f"CPU limit from env: {monitor.cpu_limit}%")
    print(f"RAM limit from env: {monitor.ram_limit}%")

    monitor.start()
    time.sleep(2)
    monitor.stop()


# Example 6: Integration with Flask-like framework
def flask_like_app():
    """Example of integrating with a Flask-like web framework."""

    # Custom alert handler that logs to app logger
    app_logger = logging.getLogger('my_flask_app')
    app_logger.setLevel(logging.INFO)

    def app_alert_handler(message):
        app_logger.warning(f"System Alert: {message}")

    monitor = quick_monitor(alert_handler=app_alert_handler)
    monitor.start()

    print("Flask-like app started...")

    # Simulate Flask app
    routes = ['/', '/api/users', '/api/data']

    for route in routes:
        print(f"GET {route}")
        time.sleep(0.5)

    monitor.stop()
    print("Flask-like app finished!")


if __name__ == "__main__":
    print("SystemMonitor Integration Examples")
    print("=" * 40)

    examples = [
        ("Simple Integration", simple_app),
        ("Context Manager", context_manager_app),
        ("Decorator", decorated_app),
        ("Web App with Custom Alerts", web_app_example),
        ("Environment Config", env_config_example),
        ("Flask-like Framework", flask_like_app),
    ]

    for name, func in examples:
        print(f"\n--- {name} ---")
        try:
            func()
        except KeyboardInterrupt:
            print("Interrupted")
        print()

    print("All examples completed!")