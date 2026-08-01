"""
Abstract Base Collector for InfraMind AI Monitoring Agent
"""

from abc import ABC, abstractmethod
from typing import Any
from agent.utils.logger import get_logger


class BaseCollector(ABC):
    """
    Abstract Base Class for all metric collectors.
    Enforces interface consistency and safe execution.
    """

    def __init__(self, name: str):
        self.name = name
        self.logger = get_logger(f"collector.{name}")

    @abstractmethod
    def collect(self) -> Any:
        """
        Abstract method to collect metrics. Must be implemented by concrete collectors.
        
        :return: Pydantic model representing collected metrics.
        """
        pass
