import psutil
import threading
import time
import datetime
import logging
import json
import requests
from typing import Optional, List, Callable
from collections import deque
from .state import State, DiskInfo
from . import utils


# --- Alert Handlers ---
class PrintAlertHandler:
    def __call__(self, message: str):
        print(message)


class LogAlertHandler:
    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def __call__(self, message: str):
        safe_message = message.encode("ascii", errors="ignore").decode()
        self.logger.warning(safe_message)


class WebhookAlertHandler:
    def __init__(self, url: str):
        self.url = url

    def __call__(self, message: str):
        try:
            requests.post(self.url, json={"alert": message, "timestamp": datetime.datetime.now().isoformat()})
        except Exception as e:
            print(f"Failed to send alert to webhook: {e}")


class Monitor:
    """
    Main system monitor class.

    Modes:
    - Snapshot mode: state() / alerts()
    - Monitoring mode: start()/stop() (background), run_forever() (blocking)
    """

    def __init__(
        self,
        cpu_limit: float = 70.0,
        ram_limit: float = 70.0,
        disk_limit: float = 80.0,
        interval: int = 60,
        on_alert: Optional[Callable[[str], None]] = None,
        logger: Optional[logging.Logger] = None,
        history_size: int = 100
    ):
        self.cpu_limit = cpu_limit
        self.ram_limit = ram_limit
        self.disk_limit = disk_limit
        self.interval = interval
        self._running = False
        self._on_alert = on_alert or PrintAlertHandler()

        # Setup logger (console by default)
        if logger:
            self.logger = logger
        else:
            logging.basicConfig(
                level=logging.INFO,
                format="%(asctime)s [%(levelname)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            self.logger = logging.getLogger("SystemMonitor")

        # History of states (bounded queue)
        self.history = deque(maxlen=history_size)

    # --- Snapshot mode ---
    def state(self) -> State:
        """Return a snapshot of the current system state."""
        cpu = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory().percent

        disks = {}
        for part in psutil.disk_partitions(all=False):
            try:
                du = psutil.disk_usage(part.mountpoint)
                disks[part.mountpoint] = DiskInfo(
                    mount=part.mountpoint,
                    percent=round(du.percent, 1),
                    total_gb=round(du.total / 1024**3, 2),
                    used_gb=round(du.used / 1024**3, 2),
                    free_gb=round(du.free / 1024**3, 2)
                )
            except Exception:
                pass

        s = State(
            cpu=cpu,
            ram=ram,
            disks=disks,
            gpus=utils.gpus(),
            uptime=utils.uptime(),
            network=utils.network(),
            battery=utils.battery(),
            top_processes=utils.processes(),
            timestamp=datetime.datetime.now()
        )

        # Save in history
        self.history.append(s)
        return s

    def alerts(self, state: Optional[State] = None) -> List[str]:
        """Check thresholds and return list of alerts."""
        s = state or self.state()
        alerts = []
        if s.cpu > self.cpu_limit:
            alerts.append(f"High CPU usage: {s.cpu:.0f}%")
        if s.ram > self.ram_limit:
            alerts.append(f"High RAM usage: {s.ram:.0f}%")
        for disk in s.disks.values():
            if disk.percent > self.disk_limit:
                alerts.append(f"Low disk space on {disk.mount}: {disk.percent:.0f}% used")

        for msg in alerts:
            try:
                self._on_alert(msg)
            except Exception as e:
                self.logger.error(f"Failed to deliver alert: {e}")

        return alerts

    # --- Monitoring mode ---
    def start(self) -> None:
        """Start background monitoring loop (non-blocking, resilient)."""
        if self._running:
            return
        self._running = True

        def loop():
            backoff = self.interval
            while self._running:
                try:
                    self.alerts()
                    time.sleep(self.interval)
                    backoff = self.interval  # reset after success
                except Exception as e:
                    self.logger.error(f"Error in monitoring loop: {e}")
                    backoff = min(backoff * 2, self.interval * 5)
                    time.sleep(backoff)

        threading.Thread(target=loop, daemon=True).start()
        self.logger.info("Monitoring started in background.")

    def stop(self) -> None:
        """Stop background monitoring loop."""
        self._running = False
        self.logger.info("Monitoring stopped.")

    def run_forever(self) -> None:
        """Run monitoring in a blocking loop until interrupted (Ctrl+C)."""
        backoff = self.interval
        self.logger.info("Monitoring started in blocking mode. Press Ctrl+C to stop.")
        try:
            while True:
                try:
                    self.alerts()
                    time.sleep(self.interval)
                    backoff = self.interval
                except Exception as e:
                    self.logger.error(f"Error in monitoring loop: {e}")
                    backoff = min(backoff * 2, self.interval * 5)
                    time.sleep(backoff)
        except KeyboardInterrupt:
            self.logger.info("Monitoring stopped by user.")


# --- Extend State with dict/json export ---
def state_to_dict(self) -> dict:
    return {
        "timestamp": self.timestamp.isoformat(),
        "cpu": self.cpu,
        "ram": self.ram,
        "disks": {k: v.__dict__ for k, v in self.disks.items()},
        "gpus": self.gpus,
        "uptime": self.uptime,
        "network": self.network,
        "battery": self.battery,
        "top_processes": [p.__dict__ for p in self.top_processes],
    }



def state_to_json(self, indent: Optional[int] = None) -> str:
    return json.dumps(self.to_dict(), indent=indent)


# Monkey-patch methods into State
State.to_dict = state_to_dict
State.to_json = state_to_json