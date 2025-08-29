import psutil
import platform
import datetime
import threading
import time
import subprocess
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable


@dataclass
class State:
    """Estado del sistema en un momento dado."""
    cpu: float
    ram: float
    disks: Dict[str, Dict[str, float]]
    gpus: List[str]
    timestamp: datetime.datetime


class Monitor:
    """Monitor sencillo de recursos del sistema."""

    def __init__(
        self,
        cpu_limit: float = 70.0,
        ram_limit: float = 70.0,
        disk_limit: float = 80.0,
        interval: int = 60,
        on_alert: Optional[Callable[[str], None]] = None
    ):
        self.cpu_limit = cpu_limit
        self.ram_limit = ram_limit
        self.disk_limit = disk_limit
        self.interval = interval
        self._running = False
        self._on_alert = on_alert or print  # por defecto imprime

    # --- Estado general ---
    def state(self) -> State:
        """Devuelve estado general del sistema."""
        cpu = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory().percent
        disks = self.disks()
        gpus = self._get_gpus()
        return State(cpu=cpu, ram=ram, disks=disks, gpus=gpus,
                     timestamp=datetime.datetime.now())

    def alerts(self, state: Optional[State] = None) -> List[str]:
        """Genera alertas si se superan límites."""
        s = state or self.state()
        alerts: List[str] = []

        if s.cpu > self.cpu_limit:
            alerts.append(f"⚠️ CPU alta: {s.cpu:.0f}%")
        if s.ram > self.ram_limit:
            alerts.append(f"⚠️ RAM alta: {s.ram:.0f}%")
        for mount, info in s.disks.items():
            if info["percent"] > self.disk_limit:
                alerts.append(f"⚠️ Disco casi lleno en {mount}: {info['percent']:.0f}%")

        for msg in alerts:
            try:
                self._on_alert(msg)
            except Exception:
                pass

        return alerts

    # --- Recursos individuales ---
    def disks(self) -> Dict[str, Dict[str, float]]:
        """Info detallada de discos: % usado, total, usado, libre (GB)."""
        result: Dict[str, Dict[str, float]] = {}
        for part in psutil.disk_partitions(all=False):
            try:
                du = psutil.disk_usage(part.mountpoint)
                result[part.mountpoint] = {
                    "percent": round(du.percent, 1),
                    "total_gb": round(du.total / 1024**3, 2),
                    "used_gb": round(du.used / 1024**3, 2),
                    "free_gb": round(du.free / 1024**3, 2),
                }
            except Exception:
                pass
        return result

    def uptime(self) -> str:
        """Tiempo encendido del sistema (string legible)."""
        boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
        delta = datetime.datetime.now() - boot_time
        days, seconds = delta.days, delta.seconds
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{days}d {hours}h {minutes}m"

    def processes(self, top: int = 5) -> List[Dict[str, str]]:
        """Procesos más pesados en CPU/RAM."""
        procs = []
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                procs.append(p.info)
            except Exception:
                pass
        procs.sort(key=lambda x: (x["cpu_percent"], x["memory_percent"]), reverse=True)
        return procs[:top]

    def network(self) -> Dict[str, float]:
        """Uso de red en bytes enviados/recibidos desde arranque."""
        io = psutil.net_io_counters()
        return {"sent_mb": io.bytes_sent / 1024**2, "recv_mb": io.bytes_recv / 1024**2}

    def battery(self) -> Optional[Dict[str, float]]:
        """Info de batería (si aplica)."""
        bat = psutil.sensors_battery()
        if not bat:
            return None
        return {"percent": bat.percent, "plugged": bat.power_plugged}

    # --- Loop automático ---
    def start(self) -> None:
        """Inicia monitoreo automático en segundo plano."""
        if self._running:
            return
        self._running = True

        def loop():
            while self._running:
                self.alerts()
                time.sleep(self.interval)

        threading.Thread(target=loop, daemon=True).start()

    def stop(self) -> None:
        """Detiene el monitoreo automático."""
        self._running = False

    # --- Helpers internos ---
    def _get_gpus(self) -> List[str]:
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
