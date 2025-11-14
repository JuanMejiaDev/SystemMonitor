# 🖥️ System Monitor

[![PyPI](https://img.shields.io/pypi/v/system-monitor.svg)](https://pypi.org/project/system-monitor/)
[![Python](https://img.shields.io/pypi/pyversions/system-monitor.svg)](https://pypi.org/project/system-monitor/)
[![License](https://img.shields.io/pypi/l/system-monitor.svg)](LICENSE)

Lightweight **system monitoring and alerting** library for Python apps.
Perfect for building task managers, monitoring tools, or embedding resource checks in your projects.

## ✨ Easy Integration

Add monitoring to any Python application with just **one line of code**:

```python
from SystemMonitor import quick_monitor

monitor = quick_monitor()  # Sensible defaults
monitor.start()            # Runs in background
```

Or use the decorator for zero-effort monitoring:

```python
from SystemMonitor import monitor_app

@monitor_app()
def my_app():
    pass  # Automatically monitored
```

---

## ✨ Features
- Snapshot system state (CPU, RAM, disks, network, GPU, processes, temperatures, fans, network interfaces).
- Alerting with thresholds (CPU, RAM, disk, temperatures).
- Built-in handlers:
  - ✅ Print alerts to console
  - 📜 Log alerts with `logging`
  - 🌐 Send alerts to a webhook
  - 📧 Send alerts via email
  - 💬 Send alerts to Slack
  - 🎮 Send alerts to Discord
- **Thread-safe background monitoring** with intelligent caching and adaptive intervals.
- **Non-blocking operation** - never interferes with main application thread.
- **Only background mode** - designed for seamless integration without blocking.
- Export state as **dict** or **JSON**.
- Cross-platform (Windows, Linux, macOS).
- Optional GPU monitoring with GPUtil.

---

## 📦 Installation

```bash
pip install system-monitor
```

Or for development (local install):

```bash
pip install -e .
```

For enhanced GPU monitoring:

```bash
pip install system-monitor[gpu]
```

For email alerts:

```bash
pip install system-monitor[email]
```

---


## 🚀 Quickstart

### ⚡ One-Line Integration (Simplest)

```python
from SystemMonitor import quick_monitor

# Start monitoring with one line
monitor = quick_monitor()
monitor.start()

# Your app code here...

monitor.stop()
```

### 1. Take a system snapshot

```python
from system_monitor import Monitor

monitor = Monitor()
state = monitor.state()

print(state.to_dict())   # raw dict
print(state.to_json(2))  # pretty JSON
```

Example output:

```json
{
  "timestamp": "2025-08-29T12:10:32.345678",
  "cpu": 12.1,
  "ram": 66.0,
  "disks": {
    "C:\\": {
      "mount": "C:\\",
      "percent": 39.6,
      "total_gb": 893.37,
      "used_gb": 353.51,
      "free_gb": 539.86
    }
  },
  "gpus": ["NVIDIA GeForce GTX 1050 Ti (1024MB/4096MB)"],
  "uptime": "4d 2h 35m",
  "network": {"sent_mb": 2075.5, "recv_mb": 32660.1},
  "battery": null,
  "top_processes": [
    {"pid": 22816, "name": "chrome.exe", "cpu": 0.0, "memory": 2.2}
  ],
  "temperatures": {
    "cpu_thermal": [{"label": "CPU", "current": 45.0, "high": 80.0, "critical": 90.0}]
  },
  "fans": {
    "cpu_fan": [{"label": "CPU Fan", "current": 1200}]
  },
  "network_interfaces": {
    "Ethernet": {"sent_mb": 2075.5, "recv_mb": 32660.1, "packets_sent": 15000, "packets_recv": 25000, "errin": 0, "errout": 0, "dropin": 0, "dropout": 0}
  }
}
```

---

### 2. Background monitoring with alerts

```python
from system_monitor import Monitor, LogAlertHandler
import logging

logger = logging.getLogger("monitor")

monitor = Monitor(
    cpu_limit=50.0,
    ram_limit=70.0,
    disk_limit=80.0,
    interval=60,  # Check every minute
    on_alert=LogAlertHandler(logger)
)

monitor.start()  # Non-blocking background monitoring

# Your app continues running...
# Monitor automatically checks alerts in background
```

Example alert:

```
2025-08-29 12:04:24 [WARNING] High CPU usage: 54%
```

---

### 3. Efficient background monitoring

```python
from system_monitor import Monitor

# Optimized monitoring with intelligent caching
monitor = Monitor(
    interval=60,  # Full state snapshots every minute
    cpu_limit=80,
    ram_limit=85
)

monitor.start()   # Efficient non-blocking monitoring

# Your app keeps running...
# Monitor automatically:
# - Checks CPU/RAM every 1 second
# - Updates temperatures every 30 seconds
# - Refreshes disks/GPU every 5 minutes
# - Sends alerts only when thresholds exceeded

import time
time.sleep(300)  # Monitor for 5 minutes

monitor.stop()
```

---

### 4. Send alerts to a webhook

```python
from system_monitor import Monitor, WebhookAlertHandler

monitor = Monitor(
    cpu_limit=60,
    on_alert=WebhookAlertHandler("https://example.com/webhook")
)

monitor.start()  # Background monitoring with webhook alerts
```

---

### 5. Send alerts via email

```python
from system_monitor import Monitor, EmailAlertHandler

monitor = Monitor(
    cpu_limit=60,
    on_alert=EmailAlertHandler(
        smtp_server="smtp.gmail.com",
        smtp_port=587,
        sender_email="your-email@gmail.com",
        sender_password="your-app-password",
        recipient_emails=["admin@example.com"]
    )
)

monitor.start()  # Background monitoring with email alerts
```

---

### 6. Send alerts to Slack

```python
from system_monitor import Monitor, SlackAlertHandler

monitor = Monitor(
    cpu_limit=60,
    on_alert=SlackAlertHandler(
        webhook_url="https://hooks.slack.com/services/...",
        channel="#alerts",
        username="SystemMonitor"
    )
)

monitor.start()  # Background monitoring with Slack alerts
```

---

### 7. Send alerts to Discord

```python
from system_monitor import Monitor, DiscordAlertHandler

monitor = Monitor(
    cpu_limit=60,
    on_alert=DiscordAlertHandler(
        webhook_url="https://discord.com/api/webhooks/...",
        username="SystemMonitor"
    )
)

monitor.start()  # Background monitoring with Discord alerts
```

---

### 8. Context Manager (Automatic lifecycle)

```python
from SystemMonitor import monitor_context

# Monitor starts automatically, stops when exiting
with monitor_context() as monitor:
    # Your app code here
    # Monitor runs in background automatically
    pass
```

### 9. Decorator (Zero-effort integration)

```python
from SystemMonitor import monitor_app

@monitor_app()
def my_application():
    # Your app code
    # Monitoring is completely automatic
    pass

my_application()  # Runs with monitoring
```

### 10. Environment Variable Configuration

Configure monitoring without code changes:

```bash
export SYSTEM_MONITOR_CPU_LIMIT=75
export SYSTEM_MONITOR_RAM_LIMIT=85
export SYSTEM_MONITOR_LOG_LEVEL=WARNING
```

```python
from SystemMonitor import quick_monitor

# Automatically uses environment variables
monitor = quick_monitor()
```

---

## 🧩 Handlers

- `PrintAlertHandler` → console output
- `LogAlertHandler(logger)` → Python logging
- `WebhookAlertHandler(url)` → send alerts via HTTP POST
- `EmailAlertHandler(...)` → send alerts via email
- `SlackAlertHandler(...)` → send alerts to Slack
- `DiscordAlertHandler(...)` → send alerts to Discord

You can also implement your own:

```python
class CustomHandler:
    def __call__(self, message: str):
        # e.g. send to Slack, Discord, email
        print(f"[CUSTOM] {message}")

monitor = Monitor(on_alert=CustomHandler())
```

---

## ⚡ Performance & Thread Safety

SystemMonitor is optimized for production use with intelligent caching, adaptive monitoring, and guaranteed thread safety:

- **Smart Caching**: Metrics are cached with different TTL based on update frequency
  - Fast metrics (CPU, RAM): 1 second cache
  - Medium metrics (temperatures, processes): 30 seconds cache
  - Slow metrics (disks, GPU info): 5 minutes cache

- **Thread-Safe Monitoring Loop**:
  - Checks alerts continuously without blocking main thread
  - Only refreshes metrics when cache expires
  - Uses Event objects for clean shutdown signaling
  - Adaptive backoff with jitter on errors
  - Low CPU usage even with frequent monitoring

- **Non-Blocking Architecture**:
  - Daemon threads prevent application hangs
  - Alert handlers run in separate threads
  - Proper synchronization with locks and events
  - No interference with main application thread
  - Graceful shutdown with timeout handling

- **Resource Conscious**:
  - Minimal memory footprint
  - Thread-safe cache operations
  - Graceful error handling and recovery

---


## 🧪 Testing & Demo

### Efficiency Demo
Run the efficiency demo to see the optimized monitoring in action:

```bash
python efficiency_demo.py
```

This demonstrates:
- Intelligent caching behavior
- Different update frequencies for various metrics
- Low CPU usage during monitoring
- Responsive alert system

### Integration Examples
See how easy it is to integrate SystemMonitor into any application:

```bash
python integration_examples.py
```

Examples include:
- One-line integration
- Context manager usage
- Decorator patterns
- Web framework integration
- Environment variable configuration

---

## 📦 Project Status

For now, the repository is available; it will be released on PyPI soon.

## 📜 License
MIT – free to use and modify.
Made with ❤️ for developers who want **efficient system monitoring**.

---
