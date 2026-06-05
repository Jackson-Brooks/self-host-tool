import time
import psutil
from config import DATA_DIR

def get_system_stats():
    """
    Gathers host system metrics for CPU, memory, persistent disk, and uptime.
    """
    try:
        # Non-blocking CPU percent read
        cpu_percent = psutil.cpu_percent(interval=None)
        
        # RAM usage details
        ram = psutil.virtual_memory()
        
        # Disk usage of the volume where we store self-hosted app configs and files
        disk = psutil.disk_usage(str(DATA_DIR))
        
        # System uptime calculation
        boot_time = psutil.boot_time()
        uptime_seconds = time.time() - boot_time
        
        return {
            "cpu": {
                "percent": cpu_percent
            },
            "memory": {
                "percent": ram.percent,
                "used": ram.used,
                "total": ram.total,
                "available": ram.available
            },
            "disk": {
                "percent": disk.percent,
                "used": disk.used,
                "total": disk.total,
                "free": disk.free
            },
            "uptime": int(uptime_seconds)
        }
    except Exception as e:
        return {
            "cpu": {"percent": 0.0},
            "memory": {"percent": 0.0, "used": 0, "total": 0, "available": 0},
            "disk": {"percent": 0.0, "used": 0, "total": 0, "free": 0},
            "uptime": 0,
            "error": str(e)
        }
