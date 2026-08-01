"""
Metrics Uploader for InfraMind AI Windows Agent.

Responsibilities:
  1. On startup: register the device with the backend.
  2. Every `upload_interval_sec`: collect metrics, build the API payload,
     POST to /metrics/ingest via BackendHTTPClient.
  3. On failure: store the payload in the offline queue and attempt replay
     on the next successful cycle.
  4. Heartbeat: piggybacks on the ingest call (metric ingest updates last_seen_at).

Lifecycle:
  - `MetricsUploader.run()` is a blocking loop. Run it in the main thread
    (or a dedicated thread) after the rest of the agent initialises.
  - Call `MetricsUploader.stop()` from another thread (e.g. signal handler)
    to trigger a clean shutdown.

Payload mapping:
  The API's MetricIngest schema expects:
    - device_uuid, timestamp_utc (strings)
    - cpu_usage_percent, ram_usage_percent, etc. (extracted flat fields)
    - raw_payload (full AgentPayload as a dict)
"""

import json
import time
import threading
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from agent.config.settings import get_settings, AgentSettings
from agent.models.metrics import AgentPayload
from agent.services.metrics_aggregator import MetricsAggregator
from agent.services.http_client import BackendHTTPClient
from agent.services.offline_queue import OfflineQueue
from agent.utils.logger import get_logger


class MetricsUploader:
    """Orchestrates collection → upload → offline-queue loop."""

    def __init__(self, settings: AgentSettings = get_settings):
        self.settings = settings
        self.logger = get_logger("services.uploader", settings=settings)
        self.aggregator = MetricsAggregator(settings=settings)
        self.client = BackendHTTPClient(settings=settings)
        self.queue = OfflineQueue(max_size=settings.offline_queue_max_size)
        self._stop_event = threading.Event()
        self._device_registered = False

    # ── Public control ────────────────────────────────────────────────────────
    def run(self) -> None:
        """
        Main blocking loop. Collects and uploads metrics every
        `upload_interval_sec`. Exits cleanly when stop() is called.
        """
        self.logger.info(
            f"Starting upload loop — interval: {self.settings.upload_interval_sec}s"
        )

        # Authenticate before the loop
        if not self.client.login():
            self.logger.critical(
                "Cannot authenticate with backend — check BACKEND_EMAIL / BACKEND_PASSWORD. "
                "Agent will continue collecting locally and queue payloads."
            )

        # Register device once on startup
        self._register_device()

        # Replay any queued payloads from previous offline period
        self._replay_offline_queue()

        while not self._stop_event.is_set():
            cycle_start = time.monotonic()
            self._upload_cycle()
            elapsed = time.monotonic() - cycle_start
            sleep_for = max(0.0, self.settings.upload_interval_sec - elapsed)
            self._stop_event.wait(timeout=sleep_for)

        self.logger.info("Upload loop stopped cleanly.")
        self.client.close()

    def stop(self) -> None:
        """Signal the upload loop to exit after the current cycle."""
        self.logger.info("Stop signal received — finishing current cycle...")
        self._stop_event.set()

    # ── Device registration ───────────────────────────────────────────────────
    def _register_device(self) -> None:
        """Sends device metadata to POST /devices/register."""
        try:
            # Collect system metrics just for registration metadata
            payload = self.aggregator.collect_all()
            reg_payload = {
                "device_uuid": payload.device_id,
                "hostname": payload.system.hostname,
                "os_name": payload.system.os,
                "os_version": f"{payload.system.os_release} (Build {payload.system.windows_build})",
                "architecture": payload.system.architecture,
                "agent_version": payload.agent_version,
            }
            success = self.client.register_device(reg_payload)
            if success:
                self._device_registered = True
                self.logger.info(
                    f"Device registered: {payload.device_id} ({payload.system.hostname})"
                )
            else:
                self.logger.warning(
                    "Device registration failed — will retry next cycle."
                )
        except Exception as e:
            self.logger.error(f"Device registration error: {e}", exc_info=True)

    # ── Upload cycle ──────────────────────────────────────────────────────────
    def _upload_cycle(self) -> None:
        """Single collection + upload iteration."""
        # Register device if we haven't successfully yet
        if not self._device_registered:
            self._register_device()

        try:
            payload = self.aggregator.collect_all()
            api_payload = self._build_api_payload(payload)
            success = self.client.ingest_metric(api_payload)

            if success:
                self.logger.debug(
                    f"Metrics uploaded | CPU {payload.cpu.usage_percent}% "
                    f"RAM {payload.memory.usage_percent}%"
                )
                # Replay queued offline payloads after a successful upload
                if self.queue.size() > 0:
                    self._replay_offline_queue()
            else:
                self.logger.warning("Upload failed — queuing payload offline.")
                self.queue.enqueue(api_payload)

        except Exception as e:
            self.logger.error(f"Upload cycle error: {e}", exc_info=True)

    # ── Offline queue replay ──────────────────────────────────────────────────
    def _replay_offline_queue(self) -> None:
        """Send previously queued payloads when the backend becomes available."""
        queued = self.queue.drain()
        if not queued:
            return

        self.logger.info(f"Replaying {len(queued)} offline-queued payloads...")
        re_queue: list = []

        for entry in queued:
            success = self.client.ingest_metric(entry)
            if not success:
                re_queue.append(entry)

        # Re-queue any that still failed
        for entry in re_queue:
            self.queue.enqueue(entry)

        sent = len(queued) - len(re_queue)
        self.logger.info(
            f"Offline replay: {sent} succeeded, {len(re_queue)} re-queued."
        )

    # ── Payload builder ───────────────────────────────────────────────────────
    @staticmethod
    def _build_api_payload(payload: AgentPayload) -> Dict[str, Any]:
        """
        Maps the AgentPayload to the MetricIngest schema expected by the API.

        Extracts hot numeric fields to top-level keys for fast DB queries,
        and includes the full payload as `raw_payload` for forensic replay.
        """
        # Average disk usage across all partitions
        disk_pct: Optional[float] = None
        if payload.disk.partitions:
            disk_pct = round(
                sum(p.usage_percent for p in payload.disk.partitions)
                / len(payload.disk.partitions),
                2,
            )

        return {
            "device_uuid": payload.device_id,
            "timestamp_utc": payload.timestamp_utc,
            "cpu_usage_percent": payload.cpu.usage_percent,
            "ram_usage_percent": payload.memory.usage_percent,
            "disk_usage_percent": disk_pct,
            "network_bytes_sent": payload.network.bytes_sent,
            "network_bytes_recv": payload.network.bytes_recv,
            "upload_speed_bps": payload.network.upload_speed_bps,
            "download_speed_bps": payload.network.download_speed_bps,
            "battery_percent": (
                payload.battery.percentage if payload.battery.has_battery else None
            ),
            "uptime_seconds": payload.system.uptime_seconds,
            "total_processes": payload.processes.total_processes,
            "suspicious_process_count": payload.processes.suspicious_count,
            # Full snapshot stored verbatim for forensic replay
            "raw_payload": json.loads(payload.to_json()),
        }
