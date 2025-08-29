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
    try:
        if platform.system() == "Windows":
            out = subprocess.check_output(
                ["wmic", "path", "win32_VideoController", "get", "Name"],
                text=True, stderr=subprocess.DEVNULL
            ).splitlines()
            return [line.strip() for line in out[1:] if line.strip()]
        elif platform.system() == "Linux":
            out = subprocess.check_output(["lspci"], text=True)
            return [line for line in out.splitlines() if "VGA" in line or "3D" in line]
        elif platform.system() == "Darwin":
            out = subprocess.check_output(["system_profiler", "SPDisplaysDataType"], text=True)
            return [line.strip() for line in out.splitlines() if "Chipset Model" in line]
    except Exception:
        return ["Not detected"]
    return ["Not detected"]

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
