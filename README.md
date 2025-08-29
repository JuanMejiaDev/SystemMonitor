# 🖥️ System Monitor

[![PyPI](https://img.shields.io/pypi/v/system-monitor.svg)](https://pypi.org/project/system-monitor/)
[![Python](https://img.shields.io/pypi/pyversions/system-monitor.svg)](https://pypi.org/project/system-monitor/)
[![License](https://img.shields.io/pypi/l/system-monitor.svg)](LICENSE)

Lightweight **system monitoring and alerting** library for Python apps.  
Perfect for building task managers, monitoring tools, or embedding resource checks in your projects.

---

## ✨ Features
- Snapshot system state (CPU, RAM, disks, network, GPU, processes).
- Alerting with thresholds (CPU, RAM, disk).
- Built-in handlers:
  - ✅ Print alerts to console
  - 📜 Log alerts with `logging`
  - 🌐 Send alerts to a webhook
- Background monitoring with retries & backoff.
- Export state as **dict** or **JSON**.
- Cross-platform (Windows, Linux, macOS).

---

## 📦 Installation

```bash
pip install system-monitor
```

Or for development (local install):

```bash
pip install -e .
```

---

## 🚀 Quickstart

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
  "gpus": ["NVIDIA GeForce GTX 1050 Ti"],
  "uptime": "4d 2h 35m",
  "network": {"sent_mb": 2075.5, "recv_mb": 32660.1},
  "battery": null,
  "top_processes": [
    {"pid": 22816, "name": "chrome.exe", "cpu": 0.0, "memory": 2.2}
  ]
}
```

---

### 2. Continuous monitoring with alerts

```python
from system_monitor import Monitor, LogAlertHandler
import logging

logger = logging.getLogger("monitor")

monitor = Monitor(
    cpu_limit=50.0, 
    ram_limit=70.0, 
    disk_limit=80.0,
    interval=10,
    on_alert=LogAlertHandler(logger)
)

monitor.run_forever()  # blocking loop
```

Example alert:

```
2025-08-29 12:04:24 [WARNING] ⚠️ High CPU usage: 54%
```

---

### 3. Run in background

```python
from system_monitor import Monitor

monitor = Monitor(interval=30)
monitor.start()   # non-blocking

# your app keeps running...
import time
time.sleep(120)

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

monitor.run_forever()
```

---

## 🧩 Handlers

- `PrintAlertHandler` → console output  
- `LogAlertHandler(logger)` → Python logging  
- `WebhookAlertHandler(url)` → send alerts via HTTP POST  

You can also implement your own:

```python
class CustomHandler:
    def __call__(self, message: str):
        # e.g. send to Slack, Discord, email
        print(f"[CUSTOM] {message}")

monitor = Monitor(on_alert=CustomHandler())
```

---

## 📜 License
MIT – free to use and modify.  
Made with ❤️ for developers who want **simple system monitoring**.

---
