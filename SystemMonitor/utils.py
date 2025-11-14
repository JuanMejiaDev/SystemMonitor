import psutil
import datetime
import platform
import subprocess
from typing import List, Dict
from .state import ProcessInfo

def uptime() -> str:
    """Return system uptime as a human-readable string."""
    boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
    delta = datetime.datetime.now() - boot_time
    days, seconds = delta.days, delta.seconds
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{days}d {hours}h {minutes}m"

def gpus() -> List[str]:
    """Return a list of detected GPUs."""
    gpus_list = []

    # Try GPUtil first for better GPU info
    try:
        import GPUtil
        gpus = GPUtil.getGPUs()
        gpus_list.extend([f"{gpu.name} ({gpu.memoryUsed}MB/{gpu.memoryTotal}MB)" for gpu in gpus])
    except ImportError:
        pass  # GPUtil not installed, fallback to system commands

    # Fallback to system commands if no GPUs found or GPUtil not available
    if not gpus_list:
        try:
            if platform.system() == "Windows":
                out = subprocess.check_output(
                    ["wmic", "path", "win32_VideoController", "get", "Name"],
                    text=True, stderr=subprocess.DEVNULL
                ).splitlines()
                gpus_list = [line.strip() for line in out[1:] if line.strip()]
            elif platform.system() == "Linux":
                out = subprocess.check_output(["lspci"], text=True)
                gpus_list = [line for line in out.splitlines() if "VGA" in line or "3D" in line]
            elif platform.system() == "Darwin":
                out = subprocess.check_output(["system_profiler", "SPDisplaysDataType"], text=True)
                gpus_list = [line.strip() for line in out.splitlines() if "Chipset Model" in line]
        except Exception:
            gpus_list = ["Not detected"]

    return gpus_list if gpus_list else ["Not detected"]

def network() -> Dict[str, float]:
    """Return total sent/received network data in MB since boot."""
    io = psutil.net_io_counters()
    return {"sent_mb": io.bytes_sent / 1024**2, "recv_mb": io.bytes_recv / 1024**2}

def battery() -> Dict[str, float] | None:
    """Return battery percentage and charging status (if available)."""
    bat = psutil.sensors_battery()
    if not bat:
        return None
    return {"percent": bat.percent, "plugged": bat.power_plugged}

def processes(top: int = 5) -> List[ProcessInfo]:
    """Return the top N processes sorted by CPU/RAM usage."""
    procs = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
        try:
            procs.append(ProcessInfo(
                pid=p.info["pid"],
                name=p.info["name"] or "Unknown",
                cpu=p.info["cpu_percent"],
                memory=p.info["memory_percent"]
            ))
        except Exception:
            pass
    procs.sort(key=lambda x: (x.cpu, x.memory), reverse=True)
    return procs[:top]


def temperatures() -> Dict[str, List[Dict[str, float]]]:
    """Return temperatures from sensors (CPU, GPU, etc.)."""
    try:
        temps = psutil.sensors_temperatures()
        result = {}
        for sensor_name, entries in temps.items():
            result[sensor_name] = [{"label": e.label or sensor_name, "current": e.current, "high": e.high, "critical": e.critical} for e in entries]
        return result
    except AttributeError:
        return {}


def fans() -> Dict[str, List[Dict[str, float]]]:
    """Return fan speeds."""
    try:
        fans_data = psutil.sensors_fans()
        result = {}
        for fan_name, entries in fans_data.items():
            result[fan_name] = [{"label": e.label or fan_name, "current": e.current} for e in entries]
        return result
    except AttributeError:
        return {}


def network_interfaces() -> Dict[str, Dict[str, float]]:
    """Return network I/O counters per interface."""
    io_counters = psutil.net_io_counters(pernic=True)
    result = {}
    for interface, io in io_counters.items():
        result[interface] = {
            "sent_mb": io.bytes_sent / 1024**2,
            "recv_mb": io.bytes_recv / 1024**2,
            "packets_sent": io.packets_sent,
            "packets_recv": io.packets_recv,
            "errin": io.errin,
            "errout": io.errout,
            "dropin": io.dropin,
            "dropout": io.dropout
        }
    return result
