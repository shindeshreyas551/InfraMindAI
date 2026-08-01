"""
Disk Metric Collector for InfraMind AI Windows Agent
"""

import psutil
from typing import List, Optional
from agent.collectors.base_collector import BaseCollector
from agent.models.metrics import DiskMetrics, DiskPartitionMetrics, DiskIoMetrics


class DiskCollector(BaseCollector):
    """Collector for Disk storage partitions and I/O metrics using psutil."""

    def __init__(self):
        super().__init__(name="disk")

    def collect(self) -> DiskMetrics:
        """
        Collects partition usage and disk I/O metrics.
        
        :return: DiskMetrics Pydantic instance.
        """
        partition_metrics: List[DiskPartitionMetrics] = []
        io_metrics: Optional[DiskIoMetrics] = None

        try:
            self.logger.debug("Collecting Disk metrics...")
            
            # Iterate through accessible disk partitions
            partitions = psutil.disk_partitions(all=False)
            for partition in partitions:
                # Skip cdrom or empty drives on Windows
                if 'cdrom' in partition.opts or not partition.fstype:
                    continue

                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    partition_metrics.append(
                        DiskPartitionMetrics(
                            device=partition.device,
                            mountpoint=partition.mountpoint,
                            fstype=partition.fstype,
                            total_bytes=usage.total,
                            used_bytes=usage.used,
                            free_bytes=usage.free,
                            usage_percent=usage.percent
                        )
                    )
                except (PermissionError, FileNotFoundError, OSError) as pe:
                    self.logger.warning(f"Skipping partition {partition.mountpoint} due to access restriction: {pe}")

            # Collect global Disk I/O metrics
            try:
                io_counters = psutil.disk_io_counters()
                if io_counters:
                    io_metrics = DiskIoMetrics(
                        read_bytes=io_counters.read_bytes,
                        write_bytes=io_counters.write_bytes,
                        read_count=io_counters.read_count,
                        write_count=io_counters.write_count
                    )
            except Exception as ioe:
                self.logger.warning(f"Could not retrieve Disk I/O counters: {ioe}")

            return DiskMetrics(
                partitions=partition_metrics,
                io_counters=io_metrics
            )

        except Exception as e:
            self.logger.error(f"Error collecting Disk metrics: {e}", exc_info=True)
            return DiskMetrics(partitions=[], io_counters=None)
