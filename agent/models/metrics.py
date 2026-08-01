"""
Pydantic schemas for InfraMind AI Windows Agent v0.2 telemetry & health data
"""

from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class CpuMetrics(BaseModel):
    """CPU telemetry data structure."""
    usage_percent: float = Field(..., description="Overall CPU usage percentage")
    per_core_percent: List[float] = Field(default_factory=list, description="CPU usage percentage per logical core")
    physical_cores: int = Field(..., description="Number of physical CPU cores")
    logical_cores: int = Field(..., description="Number of logical CPU cores")
    current_frequency_mhz: Optional[float] = Field(None, description="Current CPU frequency in MHz")
    min_frequency_mhz: Optional[float] = Field(None, description="Minimum CPU frequency in MHz")
    max_frequency_mhz: Optional[float] = Field(None, description="Maximum CPU frequency in MHz")


class MemoryMetrics(BaseModel):
    """RAM & Swap memory telemetry data structure."""
    total_bytes: int = Field(..., description="Total physical RAM in bytes")
    available_bytes: int = Field(..., description="Available RAM in bytes")
    used_bytes: int = Field(..., description="Used RAM in bytes")
    usage_percent: float = Field(..., description="RAM usage percentage")
    swap_total_bytes: int = Field(..., description="Total swap memory in bytes")
    swap_used_bytes: int = Field(..., description="Used swap memory in bytes")
    swap_free_bytes: int = Field(..., description="Free swap memory in bytes")
    swap_percent: float = Field(..., description="Swap memory usage percentage")


class DiskPartitionMetrics(BaseModel):
    """Single disk partition telemetry data structure."""
    device: str = Field(..., description="Device path e.g. C:\\")
    mountpoint: str = Field(..., description="Mount point path")
    fstype: str = Field(..., description="File system type e.g. NTFS")
    total_bytes: int = Field(..., description="Total partition storage in bytes")
    used_bytes: int = Field(..., description="Used partition storage in bytes")
    free_bytes: int = Field(..., description="Free partition storage in bytes")
    usage_percent: float = Field(..., description="Partition usage percentage")


class DiskIoMetrics(BaseModel):
    """Disk I/O telemetry data structure."""
    read_bytes: int = Field(..., description="Total bytes read from disk")
    write_bytes: int = Field(..., description="Total bytes written to disk")
    read_count: int = Field(..., description="Total read operations")
    write_count: int = Field(..., description="Total write operations")


class DiskMetrics(BaseModel):
    """Aggregated disk telemetry data structure."""
    partitions: List[DiskPartitionMetrics] = Field(default_factory=list)
    total_storage_bytes: int = Field(0, description="Sum total disk space across partitions")
    io_counters: Optional[DiskIoMetrics] = None


class NetworkMetrics(BaseModel):
    """Upgraded Network telemetry data structure for Agent v0.2."""
    local_ip: str = Field(..., description="Active interface IPv4 address")
    mac_address: str = Field(..., description="Hardware MAC address")
    active_interface: str = Field(..., description="Name of active primary network adapter")
    upload_speed_bps: float = Field(..., description="Calculated upload speed in Bytes per second")
    download_speed_bps: float = Field(..., description="Calculated download speed in Bytes per second")
    bytes_sent: int = Field(..., description="Total bytes sent across interfaces")
    bytes_recv: int = Field(..., description="Total bytes received across interfaces")
    packets_sent: int = Field(..., description="Total packets sent")
    packets_recv: int = Field(..., description="Total packets received")
    errin: int = Field(..., description="Total incoming errors")
    errout: int = Field(..., description="Total outgoing errors")
    dropin: int = Field(..., description="Total incoming dropped packets")
    dropout: int = Field(..., description="Total outgoing dropped packets")


class BatteryMetrics(BaseModel):
    """Battery & Power telemetry data structure."""
    has_battery: bool = Field(..., description="True if system has a battery (laptops), False for desktop PCs")
    percentage: Optional[float] = Field(None, description="Battery charge percentage (0 to 100)")
    power_plugged: Optional[bool] = Field(None, description="True if connected to AC power")
    seconds_left: Optional[int] = Field(None, description="Estimated battery seconds remaining")
    formatted_time_left: Optional[str] = Field(None, description="Formatted battery remaining time")


class ProcessInfo(BaseModel):
    """Single running process metadata & suspicious activity flag."""
    pid: int = Field(..., description="Process Identifier")
    name: str = Field(..., description="Executable name")
    cpu_percent: float = Field(..., description="Process CPU usage percentage")
    memory_percent: float = Field(..., description="Process Memory usage percentage")
    memory_rss_bytes: int = Field(..., description="Resident Set Size memory in bytes")
    status: str = Field(..., description="Process status e.g. running, sleeping")
    username: Optional[str] = Field(None, description="User executing the process")
    exe_path: Optional[str] = Field(None, description="Full binary executable path")
    is_suspicious: bool = Field(False, description="Flag indicating potential suspicious process behavior")
    suspicious_reasons: List[str] = Field(default_factory=list, description="List of suspicious heuristic rules triggered")


class ProcessMetrics(BaseModel):
    """Upgraded Process telemetry data structure for Agent v0.2."""
    total_processes: int = Field(..., description="Total count of active processes")
    zombie_processes: int = Field(0, description="Count of zombie or dead processes")
    suspicious_count: int = Field(0, description="Count of suspicious processes detected")
    top_cpu_consumers: List[ProcessInfo] = Field(default_factory=list, description="Top processes sorted by CPU usage")
    top_memory_consumers: List[ProcessInfo] = Field(default_factory=list, description="Top processes sorted by Memory usage")
    suspicious_processes: List[ProcessInfo] = Field(default_factory=list, description="Detected suspicious processes")


class SystemMetrics(BaseModel):
    """Upgraded System metadata & OS info for Agent v0.2."""
    hostname: str = Field(..., description="Host system hostname")
    logged_in_user: str = Field(..., description="Active logged-in OS user")
    os: str = Field(..., description="Operating System name")
    os_release: str = Field(..., description="OS release version")
    os_version: str = Field(..., description="OS detailed version string")
    windows_build: str = Field(..., description="Windows build number string")
    architecture: str = Field(..., description="System machine architecture e.g. AMD64")
    processor: str = Field(..., description="Processor brand/model description")
    python_version: str = Field(..., description="Python environment version running the agent")
    timezone: str = Field(..., description="System timezone offset string")
    total_ram_bytes: int = Field(..., description="Total system RAM in bytes")
    total_disk_bytes: int = Field(..., description="Total system storage space in bytes")
    boot_time_utc: str = Field(..., description="System boot time in UTC ISO 8601 format")
    uptime_seconds: float = Field(..., description="System uptime in seconds")
    uptime_formatted: str = Field(..., description="Human readable uptime e.g. '2 days, 4 hours, 12 mins'")


class CollectorHealth(BaseModel):
    """Health status of an individual metric collector."""
    name: str = Field(..., description="Name of metric collector")
    status: str = Field(..., description="'ok' or 'error'")
    error_message: Optional[str] = Field(None, description="Error detail if status is 'error'")


class AgentHealth(BaseModel):
    """Agent Health Service status payload."""
    agent_version: str = Field(..., description="Agent software version")
    device_id: str = Field(..., description="Persistent unique device ID")
    running_status: str = Field(..., description="Overall agent status: 'healthy', 'degraded', or 'critical'")
    last_collection_utc: str = Field(..., description="UTC ISO timestamp of latest collection pass")
    collectors: Dict[str, CollectorHealth] = Field(default_factory=dict, description="Status breakdown of all collectors")


class AgentPayload(BaseModel):
    """Top-level JSON payload returned by InfraMind Agent v0.2."""
    device_id: str = Field(..., description="Persistent unique device UUID")
    agent_name: str = Field(..., description="Agent software name")
    agent_version: str = Field(..., description="Agent version string")
    timestamp_utc: str = Field(..., description="Collection timestamp in UTC ISO 8601 format")
    health: AgentHealth
    system: SystemMetrics
    cpu: CpuMetrics
    memory: MemoryMetrics
    disk: DiskMetrics
    network: NetworkMetrics
    battery: BatteryMetrics
    processes: ProcessMetrics

    def to_json(self, indent: int = 2) -> str:
        """Serializes payload model to formatted JSON string."""
        return self.model_dump_json(indent=indent)
