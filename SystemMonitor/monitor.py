import psutil
import threading
import time
import datetime
import logging
import json
import requests
import os
from typing import Optional, List, Callable, Dict, Any
from collections import deque
from dataclasses import dataclass
from contextlib import contextmanager
from threading import Lock, Event
from .state import State, DiskInfo
from . import utils


@dataclass
class CachedMetric:
    """Cache for expensive metrics with TTL."""
    value: Any
    timestamp: float
    ttl: float

    def is_expired(self) -> bool:
        return time.time() - self.timestamp > self.ttl


class MetricsCache:
    """Thread-safe intelligent caching system for system metrics."""

    def __init__(self):
        self.cache: Dict[str, CachedMetric] = {}
        self._lock = Lock()

    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired."""
        with self._lock:
            if key in self.cache and not self.cache[key].is_expired():
                return self.cache[key].value
        return None

    def set(self, key: str, value: Any, ttl: float):
        """Cache a value with TTL."""
        with self._lock:
            self.cache[key] = CachedMetric(value, time.time(), ttl)

    def clear_expired(self):
        """Remove expired entries."""
        with self._lock:
            current_time = time.time()
            expired_keys = [k for k, v in self.cache.items() if current_time - v.timestamp > v.ttl]
            for k in expired_keys:
                del self.cache[k]


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


class EmailAlertHandler:
    def __init__(self, smtp_server: str, smtp_port: int, sender_email: str, sender_password: str, recipient_emails: List[str]):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.recipient_emails = recipient_emails

    def __call__(self, message: str):
        try:
            import smtplib
            from email.mime.text import MIMEText

            msg = MIMEText(message)
            msg['Subject'] = 'System Monitor Alert'
            msg['From'] = self.sender_email
            msg['To'] = ', '.join(self.recipient_emails)

            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            server.sendmail(self.sender_email, self.recipient_emails, msg.as_string())
            server.quit()
        except Exception as e:
            print(f"Failed to send email alert: {e}")


class SlackAlertHandler:
    def __init__(self, webhook_url: str, channel: str = None, username: str = "SystemMonitor"):
        self.webhook_url = webhook_url
        self.channel = channel
        self.username = username

    def __call__(self, message: str):
        try:
            payload = {
                "text": message,
                "username": self.username,
                "icon_emoji": ":warning:"
            }
            if self.channel:
                payload["channel"] = self.channel
            requests.post(self.webhook_url, json=payload)
        except Exception as e:
            print(f"Failed to send Slack alert: {e}")


class DiscordAlertHandler:
    def __init__(self, webhook_url: str, username: str = "SystemMonitor"):
        self.webhook_url = webhook_url
        self.username = username

    def __call__(self, message: str):
        try:
            payload = {
                "content": message,
                "username": self.username
            }
            requests.post(self.webhook_url, json=payload)
        except Exception as e:
            print(f"Failed to send Discord alert: {e}")


class Monitor:
    """
    Main system monitor class.

    Modes:
    - Snapshot mode: state() / alerts()
    - Background monitoring: start()/stop() (non-blocking)
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

        # Intelligent caching system
        self.cache = MetricsCache()

        # Update intervals for different metric types (in seconds)
        self.update_intervals = {
            'fast': 1,      # CPU, RAM, network interfaces (real-time)
            'medium': 30,   # temperatures, fans, processes
            'slow': 300,    # disks, gpus, uptime, battery (5 minutes)
        }

        # Last update timestamps
        self.last_updates = {k: 0 for k in self.update_intervals.keys()}

        # Thread synchronization
        self._running_lock = Lock()
        self._stop_event = Event()
        self._cache_lock = Lock()
        self._monitoring_thread = None

    @property
    def is_running(self) -> bool:
        """Check if monitoring is currently running."""
        with self._running_lock:
            return (self._monitoring_thread is not None and
                    self._monitoring_thread.is_alive() and
                    not self._stop_event.is_set())

    # --- Snapshot mode ---
    def _get_fast_metrics(self) -> Dict[str, Any]:
        """Get fast-changing metrics (CPU, RAM, network interfaces)."""
        cache_key = 'fast_metrics'
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        metrics = {
            'cpu': psutil.cpu_percent(interval=0.1),
            'ram': psutil.virtual_memory().percent,
            'network_interfaces': utils.network_interfaces()
        }

        self.cache.set(cache_key, metrics, self.update_intervals['fast'])
        return metrics

    def _get_medium_metrics(self) -> Dict[str, Any]:
        """Get medium-changing metrics (temperatures, fans, processes)."""
        cache_key = 'medium_metrics'
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        metrics = {
            'temperatures': utils.temperatures(),
            'fans': utils.fans(),
            'top_processes': utils.processes()
        }

        self.cache.set(cache_key, metrics, self.update_intervals['medium'])
        return metrics

    def _get_slow_metrics(self) -> Dict[str, Any]:
        """Get slow-changing metrics (disks, gpus, uptime, battery)."""
        cache_key = 'slow_metrics'
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

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

        metrics = {
            'disks': disks,
            'gpus': utils.gpus(),
            'uptime': utils.uptime(),
            'battery': utils.battery(),
            'network': utils.network()
        }

        self.cache.set(cache_key, metrics, self.update_intervals['slow'])
        return metrics

    def state(self) -> State:
        """Return a snapshot of the current system state."""
        # Get metrics from cache or refresh as needed
        fast = self._get_fast_metrics()
        medium = self._get_medium_metrics()
        slow = self._get_slow_metrics()

        s = State(
            cpu=fast['cpu'],
            ram=fast['ram'],
            disks=slow['disks'],
            gpus=slow['gpus'],
            uptime=slow['uptime'],
            network=slow['network'],
            battery=slow['battery'],
            top_processes=medium['top_processes'],
            temperatures=medium['temperatures'],
            fans=medium['fans'],
            network_interfaces=fast['network_interfaces'],
            timestamp=datetime.datetime.now()
        )

        # Save in history
        self.history.append(s)
        return s

    def alerts(self, state: Optional[State] = None, force_full_check: bool = False) -> List[str]:
        """Check thresholds and return list of alerts. Efficiently uses cached metrics."""
        alerts = []

        # Always check fast metrics (CPU, RAM)
        fast_metrics = self._get_fast_metrics()
        if fast_metrics['cpu'] > self.cpu_limit:
            alerts.append(f"High CPU usage: {fast_metrics['cpu']:.0f}%")
        if fast_metrics['ram'] > self.ram_limit:
            alerts.append(f"High RAM usage: {fast_metrics['ram']:.0f}%")

        # Check slow metrics (disks) only if forced or cache expired
        if force_full_check or self.cache.get('slow_metrics') is None:
            slow_metrics = self._get_slow_metrics()
            for disk in slow_metrics['disks'].values():
                if disk.percent > self.disk_limit:
                    alerts.append(f"Low disk space on {disk.mount}: {disk.percent:.0f}% used")

        # If we have a full state, check everything
        if state:
            # Check temperatures for critical values
            for sensor_name, sensor_data in state.temperatures.items():
                for temp_info in sensor_data:
                    if temp_info.get('critical') and temp_info['current'] >= temp_info['critical']:
                        alerts.append(f"Critical temperature: {sensor_name} {temp_info['current']}°C")
                    elif temp_info.get('high') and temp_info['current'] >= temp_info['high']:
                        alerts.append(f"High temperature: {sensor_name} {temp_info['current']}°C")

        for msg in alerts:
            # Run alert handler in a separate thread to avoid blocking
            def _deliver_alert(message):
                try:
                    self._on_alert(message)
                except Exception as e:
                    self.logger.error(f"Failed to deliver alert: {e}")

            alert_thread = threading.Thread(target=_deliver_alert, args=(msg,), daemon=True)
            alert_thread.start()

        return alerts

    def _monitoring_loop(self):
        """Thread-safe monitoring loop that updates metrics at appropriate intervals."""
        last_check = time.time()
        consecutive_errors = 0
        max_consecutive_errors = 5

        while not self._stop_event.is_set():
            try:
                current_time = time.time()

                # Always check fast metrics and alerts (non-blocking)
                self.alerts(force_full_check=False)

                # Periodically refresh caches based on their TTL
                self.cache.clear_expired()

                # Force full state update every main interval for history
                if current_time - last_check >= self.interval:
                    self.state()  # This will refresh all caches as needed
                    last_check = current_time

                # Sleep for a short time to be responsive but not waste CPU
                # Use wait with timeout to be interruptible
                self._stop_event.wait(min(1, self.interval / 10))

                # Reset error counter on success
                consecutive_errors = 0

            except Exception as e:
                consecutive_errors += 1
                self.logger.error(f"Error in monitoring loop: {e}")

                if consecutive_errors >= max_consecutive_errors:
                    self.logger.error(f"Too many consecutive errors ({consecutive_errors}), stopping monitoring")
                    break

                # Exponential backoff with jitter, but respect stop event
                backoff = min(self.interval * (2 ** consecutive_errors), self.interval * 10)
                backoff += (backoff * 0.1) * (time.time() % 1)  # Add jitter
                self.logger.info(f"Backing off for {backoff:.1f} seconds")

                # Wait but allow interruption
                if self._stop_event.wait(backoff):
                    break  # Stop event was set

    # --- Monitoring mode ---
    def start(self) -> None:
        """Start background monitoring loop (non-blocking, thread-safe)."""
        with self._running_lock:
            if self._stop_event.is_set():
                return
            if (self._monitoring_thread is not None and
                self._monitoring_thread.is_alive()):
                return

            self._stop_event.clear()
            self._monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True, name="SystemMonitor")
            self._monitoring_thread.start()
            self.logger.info("Monitoring started in background.")

    def stop(self) -> None:
        """Stop background monitoring loop."""
        with self._running_lock:
            if not self._stop_event.is_set():
                self._stop_event.set()
                if self._monitoring_thread is not None:
                    self._monitoring_thread.join(timeout=2.0)  # Wait up to 2 seconds for clean shutdown
                self.logger.info("Monitoring stopped.")



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
        "temperatures": self.temperatures,
        "fans": self.fans,
        "network_interfaces": self.network_interfaces,
    }



def state_to_json(self, indent: Optional[int] = None) -> str:
    return json.dumps(self.to_dict(), indent=indent)


# Monkey-patch methods into State
State.to_dict = state_to_dict
State.to_json = state_to_json


# --- Easy Integration Functions ---

def quick_monitor(
    cpu_limit: float = None,
    ram_limit: float = None,
    disk_limit: float = None,
    alert_handler: Callable[[str], None] = None,
    log_level: str = "INFO"
) -> Monitor:
    """
    Create a monitor with sensible defaults for quick integration.

    Args:
        cpu_limit: CPU usage threshold (default: 80%)
        ram_limit: RAM usage threshold (default: 85%)
        disk_limit: Disk usage threshold (default: 90%)
        alert_handler: Custom alert handler (default: print to console)
        log_level: Logging level (default: INFO)

    Returns:
        Configured Monitor instance ready to use
    """
    # Use environment variables or sensible defaults
    cpu_limit = cpu_limit or int(os.getenv('SYSTEM_MONITOR_CPU_LIMIT', '80'))
    ram_limit = ram_limit or int(os.getenv('SYSTEM_MONITOR_RAM_LIMIT', '85'))
    disk_limit = disk_limit or int(os.getenv('SYSTEM_MONITOR_DISK_LIMIT', '90'))

    # Setup logging
    log_level = getattr(logging, os.getenv('SYSTEM_MONITOR_LOG_LEVEL', log_level).upper())
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logger = logging.getLogger('SystemMonitor')

    # Default alert handler
    if alert_handler is None:
        alert_handler = PrintAlertHandler()

    return Monitor(
        cpu_limit=cpu_limit,
        ram_limit=ram_limit,
        disk_limit=disk_limit,
        interval=60,  # Check every minute
        on_alert=alert_handler,
        logger=logger,
        history_size=50  # Keep last 50 states
    )


@contextmanager
def monitor_context(
    cpu_limit: float = None,
    ram_limit: float = None,
    disk_limit: float = None,
    alert_handler: Callable[[str], None] = None
):
    """
    Context manager for easy monitoring integration.

    Usage:
        with monitor_context() as monitor:
            # Your app code here
            # Monitor runs automatically in background
            pass
    """
    monitor = quick_monitor(
        cpu_limit=cpu_limit,
        ram_limit=ram_limit,
        disk_limit=disk_limit,
        alert_handler=alert_handler
    )

    try:
        monitor.start()
        yield monitor
    finally:
        monitor.stop()


def monitor_app(
    app_function: Callable = None,
    *,
    cpu_limit: float = None,
    ram_limit: float = None,
    disk_limit: float = None,
    alert_handler: Callable[[str], None] = None
):
    """
    Decorator to add monitoring to any application.

    Usage:
        @monitor_app()
        def my_app():
            # Your app code
            pass

        my_app()  # Runs with monitoring
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            with monitor_context(
                cpu_limit=cpu_limit,
                ram_limit=ram_limit,
                disk_limit=disk_limit,
                alert_handler=alert_handler
            ) as monitor:
                return func(*args, **kwargs)
        return wrapper
    return decorator(app_function) if app_function else decorator