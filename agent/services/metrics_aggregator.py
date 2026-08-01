"""
Metrics Aggregator Service for InfraMind AI Windows Agent v0.2
"""

from datetime import datetime, timezone
from agent.config.settings import get_settings, AgentSettings
from agent.utils.device_identity import DeviceIdentityManager
from agent.utils.logger import get_logger
from agent.services.health_service import HealthService

from agent.collectors.cpu_collector import CpuCollector
from agent.collectors.memory_collector import MemoryCollector
from agent.collectors.disk_collector import DiskCollector
from agent.collectors.network_collector import NetworkCollector
from agent.collectors.system_collector import SystemCollector
from agent.collectors.battery_collector import BatteryCollector
from agent.collectors.process_collector import ProcessCollector

from agent.models.metrics import AgentPayload


class MetricsAggregator:
    """
    Orchestrates execution of individual collectors, manages device identity,
    monitors health service, and constructs the unified AgentPayload.
    """

    def __init__(self, settings: AgentSettings = get_settings):
        self.settings = settings
        self.logger = get_logger("services.MetricsAggregator", settings=self.settings)
        
        # Initialize device identity
        self.device_identity = DeviceIdentityManager()
        self.device_id = self.device_identity.get_or_create_device_id()
        self.logger.info(f"Agent Device ID: {self.device_id}")

        # Initialize Health Service
        self.health_service = HealthService(
            agent_version=self.settings.agent_version,
            device_id=self.device_id
        )
        
        # Initialize collectors
        self.cpu_collector = CpuCollector(sample_interval_sec=self.settings.cpu_sample_interval_sec)
        self.memory_collector = MemoryCollector()
        self.disk_collector = DiskCollector()
        self.network_collector = NetworkCollector()
        self.system_collector = SystemCollector()
        self.battery_collector = BatteryCollector()
        self.process_collector = ProcessCollector(max_processes=self.settings.max_processes_to_collect)

    def collect_all(self) -> AgentPayload:
        """
        Executes all collectors safely. Logs exceptions without crashing.
        
        :return: AgentPayload Pydantic object.
        """
        self.logger.info("Starting telemetry collection pass v0.2...")

        # System Metrics
        system_metrics = self._safe_collect("system", self.system_collector)
        # CPU Metrics
        cpu_metrics = self._safe_collect("cpu", self.cpu_collector)
        # Memory Metrics
        memory_metrics = self._safe_collect("memory", self.memory_collector)
        # Disk Metrics
        disk_metrics = self._safe_collect("disk", self.disk_collector)
        # Network Metrics
        network_metrics = self._safe_collect("network", self.network_collector)
        # Battery Metrics
        battery_metrics = self._safe_collect("battery", self.battery_collector)
        # Process Metrics
        process_metrics = self._safe_collect("process", self.process_collector)

        timestamp_utc = datetime.now(timezone.utc).isoformat()
        health_payload = self.health_service.get_agent_health()

        payload = AgentPayload(
            device_id=self.device_id,
            agent_name=self.settings.agent_name,
            agent_version=self.settings.agent_version,
            timestamp_utc=timestamp_utc,
            health=health_payload,
            system=system_metrics,
            cpu=cpu_metrics,
            memory=memory_metrics,
            disk=disk_metrics,
            network=network_metrics,
            battery=battery_metrics,
            processes=process_metrics
        )

        self.logger.info(f"Telemetry pass finished. Health Status: {health_payload.running_status.upper()}")
        return payload

    def _safe_collect(self, name: str, collector_instance):
        """
        Helper method to execute a collector safely.
        Catches exceptions and reports health status.
        """
        try:
            metrics = collector_instance.collect()
            self.health_service.record_collector_status(name=name, success=True)
            return metrics
        except Exception as e:
            self.logger.error(f"Collector '{name}' failed during collection pass: {e}", exc_info=True)
            self.health_service.record_collector_status(name=name, success=False, error_message=str(e))
            # Return safe fallback instance
            return collector_instance.collect()
