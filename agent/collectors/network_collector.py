"""
Upgraded Network Metric Collector for InfraMind AI Windows Agent v0.2
"""

import socket
import time
import psutil
from typing import Tuple, Optional
from agent.collectors.base_collector import BaseCollector
from agent.models.metrics import NetworkMetrics


class NetworkCollector(BaseCollector):
    """Upgraded Collector for network speed, local IP, MAC, and interface statistics."""

    def __init__(self):
        super().__init__(name="network")
        self._last_net_io = None
        self._last_sample_time = None

    def collect(self) -> NetworkMetrics:
        """
        Collects active local IP, MAC, upload/download bandwidth speed, and total traffic.
        
        :return: NetworkMetrics Pydantic instance.
        """
        try:
            self.logger.debug("Collecting Network metrics v0.2...")
            
            # Current time & IO counters
            current_time = time.time()
            net_io = psutil.net_io_counters()

            # Calculate bandwidth upload/download speeds
            upload_speed_bps = 0.0
            download_speed_bps = 0.0

            if self._last_net_io is not None and self._last_sample_time is not None:
                time_delta = current_time - self._last_sample_time
                if time_delta > 0:
                    bytes_sent_delta = net_io.bytes_sent - self._last_net_io.bytes_sent
                    bytes_recv_delta = net_io.bytes_recv - self._last_net_io.bytes_recv
                    upload_speed_bps = max(0.0, round(bytes_sent_delta / time_delta, 2))
                    download_speed_bps = max(0.0, round(bytes_recv_delta / time_delta, 2))

            # Store state for next delta calculation
            self._last_net_io = net_io
            self._last_sample_time = current_time

            # Active interface, local IP, and MAC address
            local_ip, mac_address, active_interface = self._get_active_interface_details()

            return NetworkMetrics(
                local_ip=local_ip,
                mac_address=mac_address,
                active_interface=active_interface,
                upload_speed_bps=upload_speed_bps,
                download_speed_bps=download_speed_bps,
                bytes_sent=net_io.bytes_sent,
                bytes_recv=net_io.bytes_recv,
                packets_sent=net_io.packets_sent,
                packets_recv=net_io.packets_recv,
                errin=net_io.errin,
                errout=net_io.errout,
                dropin=net_io.dropin,
                dropout=net_io.dropout
            )

        except Exception as e:
            self.logger.error(f"Error collecting Network metrics: {e}", exc_info=True)
            return NetworkMetrics(
                local_ip="127.0.0.1",
                mac_address="00:00:00:00:00:00",
                active_interface="Unknown",
                upload_speed_bps=0.0,
                download_speed_bps=0.0,
                bytes_sent=0,
                bytes_recv=0,
                packets_sent=0,
                packets_recv=0,
                errin=0,
                errout=0,
                dropin=0,
                dropout=0
            )

    @staticmethod
    def _get_active_interface_details() -> Tuple[str, str, str]:
        """
        Determines the active primary interface, local IPv4, and MAC address.
        """
        local_ip = "127.0.0.1"
        mac_address = "00:00:00:00:00:00"
        active_interface = "Loopback"

        # Attempt socket connection to determine default route IP
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.5)
            s.connect(("8.8.8.8", 80))
            detected_ip = s.getsockname()[0]
            s.close()
            if detected_ip:
                local_ip = detected_ip
        except Exception:
            pass

        # Inspect psutil network interface addresses
        try:
            net_addrs = psutil.net_if_addrs()
            net_stats = psutil.net_if_stats()

            for iface_name, addrs in net_addrs.items():
                is_up = net_stats.get(iface_name).isup if iface_name in net_stats else False
                if not is_up:
                    continue

                iface_mac = None
                iface_ip = None

                for addr in addrs:
                    if addr.family == psutil.AF_LINK:
                        iface_mac = addr.address
                    elif addr.family == socket.AF_INET and not addr.address.startswith("127."):
                        iface_ip = addr.address

                # Match with detected socket IP or fallback to first up interface
                if iface_ip and iface_ip == local_ip:
                    active_interface = iface_name
                    if iface_mac:
                        mac_address = iface_mac.replace("-", ":").upper()
                    break
                elif iface_ip and active_interface == "Loopback":
                    local_ip = iface_ip
                    active_interface = iface_name
                    if iface_mac:
                        mac_address = iface_mac.replace("-", ":").upper()

        except Exception:
            pass

        return local_ip, mac_address, active_interface
