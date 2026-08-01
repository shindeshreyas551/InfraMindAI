"""
Upgraded System Metadata & Uptime Collector for InfraMind AI Windows Agent v0.2
"""

import getpass
import platform
import socket
import sys
import time
from datetime import datetime, timezone
import psutil
from agent.collectors.base_collector import BaseCollector
from agent.models.metrics import SystemMetrics


class SystemCollector(BaseCollector):
    """Upgraded collector for host OS metadata, logged-in user, Python version, Windows build, and totals."""

    def __init__(self):
        super().__init__(name="system")

    def collect(self) -> SystemMetrics:
        """
        Collects comprehensive host system metadata.
        
        :return: SystemMetrics Pydantic instance.
        """
        try:
            self.logger.debug("Collecting System metadata v0.2...")
            
            # Host & User details
            hostname = socket.gethostname()
            logged_in_user = getpass.getuser()
            os_name = platform.system()
            os_release = platform.release()
            os_version = platform.version()
            windows_build = platform.version()  # Build string e.g. 10.0.26200
            architecture = platform.machine()
            processor = platform.processor() or "Unknown"
            python_version = platform.python_version()

            # Timezone offset
            tz_str = time.strftime("%z (%Z)")

            # Total RAM & Disk
            total_ram_bytes = psutil.virtual_memory().total
            
            total_disk_bytes = 0
            try:
                for part in psutil.disk_partitions(all=False):
                    if 'cdrom' not in part.opts and part.fstype:
                        try:
                            total_disk_bytes += psutil.disk_usage(part.mountpoint).total
                        except Exception:
                            pass
            except Exception:
                pass

            # Boot time & Uptime calculation
            boot_timestamp = psutil.boot_time()
            boot_datetime_utc = datetime.fromtimestamp(boot_timestamp, tz=timezone.utc)
            boot_time_utc = boot_datetime_utc.isoformat()
            
            current_time = time.time()
            uptime_seconds = round(current_time - boot_timestamp, 2)
            uptime_formatted = self._format_uptime(uptime_seconds)

            return SystemMetrics(
                hostname=hostname,
                logged_in_user=logged_in_user,
                os=os_name,
                os_release=os_release,
                os_version=os_version,
                windows_build=windows_build,
                architecture=architecture,
                processor=processor,
                python_version=python_version,
                timezone=tz_str,
                total_ram_bytes=total_ram_bytes,
                total_disk_bytes=total_disk_bytes,
                boot_time_utc=boot_time_utc,
                uptime_seconds=uptime_seconds,
                uptime_formatted=uptime_formatted
            )

        except Exception as e:
            self.logger.error(f"Error collecting System metrics: {e}", exc_info=True)
            return SystemMetrics(
                hostname=socket.gethostname() if hasattr(socket, 'gethostname') else "unknown-host",
                logged_in_user="unknown",
                os=platform.system(),
                os_release="unknown",
                os_version="unknown",
                windows_build="unknown",
                architecture="unknown",
                processor="unknown",
                python_version=platform.python_version(),
                timezone="UTC",
                total_ram_bytes=0,
                total_disk_bytes=0,
                boot_time_utc=datetime.now(timezone.utc).isoformat(),
                uptime_seconds=0.0,
                uptime_formatted="0m 0s"
            )

    @staticmethod
    def _format_uptime(seconds: float) -> str:
        """Helper to format uptime seconds into human-readable string."""
        total_seconds = int(seconds)
        days, remainder = divmod(total_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, secs = divmod(remainder, 60)

        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0 or days > 0:
            parts.append(f"{hours}h")
        if minutes > 0 or hours > 0 or days > 0:
            parts.append(f"{minutes}m")
        parts.append(f"{secs}s")

        return " ".join(parts)
