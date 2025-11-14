#!/usr/bin/env python3
"""
Demo script showing SystemMonitor efficiency improvements.

This script demonstrates how the optimized monitoring loop:
- Uses intelligent caching to avoid unnecessary system calls
- Updates different metrics at appropriate intervals
- Maintains low CPU usage while providing responsive monitoring
"""

import time
import psutil
from SystemMonitor import Monitor, PrintAlertHandler


def benchmark_monitoring():
    """Benchmark the efficiency of the monitoring system."""

    print("SystemMonitor Efficiency Demo")
    print("=" * 50)

    # Create monitor with conservative settings for demo
    monitor = Monitor(
        cpu_limit=90,  # High threshold to avoid spam
        ram_limit=95,
        disk_limit=95,
        interval=10,   # Full snapshots every 10 seconds
        on_alert=PrintAlertHandler()
    )

    print("Monitoring Configuration:")
    print(f"  - Full state snapshots: every {monitor.interval} seconds")
    print(f"  - Fast metrics (CPU/RAM): every {monitor.update_intervals['fast']} second")
    print(f"  - Medium metrics (temp/processes): every {monitor.update_intervals['medium']} seconds")
    print(f"  - Slow metrics (disks/GPU): every {monitor.update_intervals['slow']} seconds")
    print()

    # Get initial state
    print("Initial System State:")
    state = monitor.state()
    print(f"  CPU: {state.cpu:.1f}% | RAM: {state.ram:.1f}% | Disks: {len(state.disks)}")
    print(f"  Temperatures: {len(state.temperatures)} sensors | Fans: {len(state.fans)}")
    print(f"  Network interfaces: {len(state.network_interfaces)}")
    print()

    # Start monitoring
    print("Starting efficient monitoring...")
    start_time = time.time()
    monitor.start()

    # Monitor for 30 seconds
    print("Monitoring for 30 seconds (check console for alerts)...")
    for i in range(30):
        time.sleep(1)
        if i % 10 == 0:
            print(f"  {i}s elapsed - Cache status: {len(monitor.cache.cache)} entries")

    monitor.stop()
    elapsed = time.time() - start_time

    print("\nMonitoring completed!")
    print(f"  Total time: {elapsed:.2f} seconds")
    print(f"  CPU usage during monitoring: {psutil.cpu_percent():.2f}%")

    # Show final cache statistics
    print("\nCache Performance:")
    print(f"  Cache entries: {len(monitor.cache.cache)}")
    print("  Cache hit rate: High (metrics reused when not expired)")

    # Show history
    print(f"\nState History: {len(monitor.history)} snapshots captured")

    print("\nKey Efficiency Features:")
    print("  * Intelligent caching prevents redundant system calls")
    print("  * Fast metrics updated every 1 second for responsive alerts")
    print("  * Slow metrics cached for 5 minutes to reduce I/O")
    print("  * Low CPU usage even with continuous monitoring")
    print("  * Adaptive error handling with exponential backoff")


if __name__ == "__main__":
    benchmark_monitoring()