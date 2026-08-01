"""
InfraMind AI - Windows Monitoring Agent Configuration
"""

from dataclasses import dataclass
import logging


@dataclass(frozen=True)
class AgentConfig:
    """Agent configuration parameters."""

    agent_name: str = "InfraMind-Windows-Agent"
    agent_version: str = "0.1.0"
    log_level: int = logging.INFO
    log_format: str = "%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
    
    # Collector features toggle
    collect_cpu: bool = True
    collect_memory: bool = True
    collect_disk: bool = True
    collect_network: bool = True
    collect_system: bool = True
    collect_battery: bool = True
    collect_processes: bool = True

    # Process Collector Settings
    max_processes_to_collect: int = 15  # Limit top processes sorted by memory usage

    # Performance / Interval settings
    cpu_sample_interval_sec: float = 1.0  # Time window for psutil.cpu_percent calculations


# Default configuration instance
DEFAULT_CONFIG = AgentConfig()
