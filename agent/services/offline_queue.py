"""
Offline Queue for InfraMind AI Windows Agent.

Purpose:
  When the backend is unreachable the agent cannot simply drop telemetry —
  it queues payloads to a JSONL file and replays them once connectivity
  is restored.

Design decisions:
  - JSONL format (one JSON object per line) allows efficient append-only writes
    and line-by-line replay without loading the entire file into memory.
  - Queue is stored at `agent/offline_queue.jsonl` by default.
  - Max size (configurable) prevents unbounded disk growth during long outages.
  - When the queue is full, the oldest entry is evicted (FIFO).
  - The queue is locked with a threading.Lock so it is safe for background threads.
"""

import json
import threading
from pathlib import Path
from typing import List, Optional

from agent.utils.logger import get_logger
from agent.config.settings import get_settings

QUEUE_FILE = Path(__file__).resolve().parent.parent / "offline_queue.jsonl"
_lock = threading.Lock()
_logger = get_logger("services.offline_queue")


class OfflineQueue:
    """Thread-safe JSONL-based offline payload queue."""

    def __init__(self, queue_file: Path = QUEUE_FILE, max_size: int = 100):
        self.queue_file = queue_file
        self.max_size = max_size

    # ── Write ─────────────────────────────────────────────────────────────────
    def enqueue(self, payload_dict: dict) -> None:
        """Append a payload JSON object to the offline queue file."""
        with _lock:
            try:
                entries = self._load_all()
                entries.append(payload_dict)
                # Evict oldest entries if over limit
                if len(entries) > self.max_size:
                    evicted = len(entries) - self.max_size
                    entries = entries[evicted:]
                    _logger.warning(f"Offline queue full — evicted {evicted} oldest entries.")
                self._save_all(entries)
                _logger.debug(f"Queued offline payload. Queue size: {len(entries)}")
            except Exception as e:
                _logger.error(f"Failed to write to offline queue: {e}")

    # ── Read & Drain ──────────────────────────────────────────────────────────
    def drain(self) -> List[dict]:
        """
        Returns all queued payloads and clears the queue file.
        Call this when the backend becomes available again.
        """
        with _lock:
            try:
                entries = self._load_all()
                if entries:
                    self.queue_file.write_text("", encoding="utf-8")
                    _logger.info(f"Drained {len(entries)} queued payloads from offline queue.")
                return entries
            except Exception as e:
                _logger.error(f"Failed to drain offline queue: {e}")
                return []

    def size(self) -> int:
        """Return current number of queued entries."""
        with _lock:
            return len(self._load_all())

    # ── Internal helpers ──────────────────────────────────────────────────────
    def _load_all(self) -> List[dict]:
        """Load all JSONL entries from disk. Returns empty list if file missing."""
        if not self.queue_file.exists():
            return []
        entries: List[dict] = []
        for line in self.queue_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                _logger.warning(f"Skipping malformed offline queue entry: {line[:80]}")
        return entries

    def _save_all(self, entries: List[dict]) -> None:
        """Rewrite the queue file with the given list of entries."""
        content = "\n".join(json.dumps(e, default=str) for e in entries)
        self.queue_file.write_text(content + "\n" if content else "", encoding="utf-8")
