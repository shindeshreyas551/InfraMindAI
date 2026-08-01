"""
Memory Metric Collector for InfraMind AI Windows Agent
"""

import psutil
from agent.collectors.base_collector import BaseCollector
from agent.models.metrics import MemoryMetrics


class MemoryCollector(BaseCollector):
    """Collector for RAM and Swap memory metrics using psutil."""

    def __init__(self):
        super().__init__(name="memory")

    def collect(self) -> MemoryMetrics:
        """
        Collects real RAM and Swap memory metrics.
        
        :return: MemoryMetrics Pydantic instance.
        """
        try:
            self.logger.debug("Collecting Memory metrics...")
            
            vmem = psutil.virtual_memory()
            swap = psutil.swap_memory()

            return MemoryMetrics(
                total_bytes=vmem.total,
                available_bytes=vmem.available,
                used_bytes=vmem.used,
                usage_percent=vmem.percent,
                swap_total_bytes=swap.total,
                swap_used_bytes=swap.used,
                swap_free_bytes=swap.free,
                swap_percent=swap.percent
            )

        except Exception as e:
            self.logger.error(f"Error collecting Memory metrics: {e}", exc_info=True)
            return MemoryMetrics(
                total_bytes=0,
                available_bytes=0,
                used_bytes=0,
                usage_percent=0.0,
                swap_total_bytes=0,
                swap_used_bytes=0,
                swap_free_bytes=0,
                swap_percent=0.0
            )
