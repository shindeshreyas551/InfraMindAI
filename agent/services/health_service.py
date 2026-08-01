"""
Health Check Service for InfraMind AI Windows Agent
"""

from datetime import datetime, timezone
from typing import Dict
from agent.models.metrics import AgentHealth, CollectorHealth


class HealthService:
    """
    Monitors overall health and individual collector status for the agent.
    """

    def __init__(self, agent_version: str, device_id: str):
        self.agent_version = agent_version
        self.device_id = device_id
        self.collector_states: Dict[str, CollectorHealth] = {}
        self.last_collection_utc: str = datetime.now(timezone.utc).isoformat()

    def record_collector_status(self, name: str, success: bool, error_message: str = None) -> None:
        """
        Records the health result of a collector execution pass.
        
        :param name: Collector identifier (e.g. 'cpu', 'network').
        :param success: True if collection completed without unhandled error.
        :param error_message: Exception details if failed.
        """
        status_str = "ok" if success else "error"
        self.collector_states[name] = CollectorHealth(
            name=name,
            status=status_str,
            error_message=error_message
        )

    def get_agent_health(self) -> AgentHealth:
        """
        Evaluates overall agent status based on recorded collector health states.
        
        :return: AgentHealth Pydantic model.
        """
        self.last_collection_utc = datetime.now(timezone.utc).isoformat()

        if not self.collector_states:
            running_status = "healthy"
        else:
            failed_count = sum(1 for c in self.collector_states.values() if c.status == "error")
            if failed_count == 0:
                running_status = "healthy"
            elif failed_count < len(self.collector_states):
                running_status = "degraded"
            else:
                running_status = "critical"

        return AgentHealth(
            agent_version=self.agent_version,
            device_id=self.device_id,
            running_status=running_status,
            last_collection_utc=self.last_collection_utc,
            collectors=self.collector_states
        )
