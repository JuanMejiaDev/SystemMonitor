from dataclasses import dataclass
from typing import Dict, List, Optional
import datetime

@dataclass
class DiskInfo:
    mount: str
    percent: float
    total_gb: float
    used_gb: float
    free_gb: float

    def __str__(self):
        return f"{self.mount}: {self.percent:.0f}% used ({self.free_gb:.1f} GB free)"

@dataclass
class ProcessInfo:
    pid: int
    name: str
    cpu: float
    memory: float

    def __str__(self):
        return f"{self.name} (PID {self.pid}) CPU: {self.cpu:.1f}% | RAM: {self.memory:.1f}%"

@dataclass
class State:
    cpu: float
    ram: float
    disks: Dict[str, DiskInfo]
    gpus: List[str]
    uptime: str
    network: Dict[str, float]
    battery: Optional[Dict[str, float]]
    top_processes: List[ProcessInfo]
    temperatures: Dict[str, List[Dict[str, float]]]
    fans: Dict[str, List[Dict[str, float]]]
    network_interfaces: Dict[str, Dict[str, float]]
    timestamp: datetime.datetime

    def __str__(self):
        disks_str = "\n  ".join(str(d) for d in self.disks.values())
        gpus_str = ", ".join(self.gpus)
        procs_str = "\n  ".join(str(p) for p in self.top_processes)
        bat_str = (
            f"{self.battery['percent']}% (plugged: {self.battery['plugged']})"
            if self.battery else "N/A"
        )
        temps_str = "\n  ".join("{}: {}".format(k, ", ".join("{0} {1}°C".format(t['label'], t['current']) for t in v)) for k, v in self.temperatures.items())
        fans_str = "\n  ".join("{}: {}".format(k, ", ".join("{0} {1} RPM".format(f['label'], f['current']) for f in v)) for k, v in self.fans.items())
        net_if_str = "\n  ".join("{}: Sent {:.1f} MB / Recv {:.1f} MB".format(k, v['sent_mb'], v['recv_mb']) for k, v in self.network_interfaces.items())
        return (
            f"=== System State @ {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')} ===\n"
            f"CPU: {self.cpu:.0f}% | RAM: {self.ram:.0f}% | Uptime: {self.uptime}\n"
            f"Network: Sent {self.network['sent_mb']:.1f} MB / Recv {self.network['recv_mb']:.1f} MB\n"
            f"Battery: {bat_str}\n"
            f"Disks:\n  {disks_str}\n"
            f"GPUs: {gpus_str}\n"
            f"Temperatures:\n  {temps_str}\n"
            f"Fans:\n  {fans_str}\n"
            f"Network Interfaces:\n  {net_if_str}\n"
            f"Top processes:\n  {procs_str}\n"
        )
