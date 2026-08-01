"""
CPU Metric Collector for InfraMind AI Windows Agent
"""

import psutil
from agent.collectors.base_collector import BaseCollector
from agent.models.metrics import CpuMetrics


class CpuCollector(BaseCollector):
    """Collector for CPU metrics using psutil."""

    def __init__(self, sample_interval_sec: float = 1.0):
        super().__init__(name="cpu")
        self.sample_interval_sec = sample_interval_sec

    def collect(self) -> CpuMetrics:
        """
        Collects real CPU metrics.
        
        :return: CpuMetrics Pydantic instance.
        """
        try:
            self.logger.debug("Collecting CPU metrics...")
            
            # CPU usage percentages (overall and per core)
            usage_percent = psutil.cpu_percent(interval=self.sample_interval_sec)
            per_core_percent = psutil.cpu_percent(interval=None, percpu=True)
            
            # Core counts
            physical_cores = psutil.cpu_count(logical=False) or 1
            logical_cores = psutil.cpu_count(logical=True) or 1
            
            # Frequency info (if supported/accessible)
            freq_curr, freq_min, freq_max = None, None, None
            try:
                freq_info = psutil.cpu_freq()
                if freq_info:
                    freq_curr = round(freq_info.current, 2)
                    freq_min = round(freq_info.min, 2) if freq_info.min > 0 else None
                    freq_max = round(freq_info.max, 2) if freq_info.max > 0 else None
            except Exception as e:
                self.logger.warning(f"Could not retrieve CPU frequency details: {e}")

            return CpuMetrics(
                usage_percent=usage_percent,
                per_core_percent=per_core_percent,
                physical_cores=physical_cores,
                logical_cores=logical_cores,
                current_frequency_mhz=freq_curr,
                min_frequency_mhz=freq_min,
                max_frequency_mhz=freq_max
            )

        except Exception as e:
            self.logger.error(f"Error collecting CPU metrics: {e}", exc_info=True)
            # Fallback safe default
            return CpuMetrics(
                usage_percent=0.0,
                per_core_percent=[],
                physical_cores=1,
                logical_cores=1
            )
