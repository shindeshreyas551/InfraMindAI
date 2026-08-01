"""
Upgraded Running Process Collector for InfraMind AI Windows Agent v0.2
"""

import os
import psutil
from typing import List, Tuple
from agent.collectors.base_collector import BaseCollector
from agent.models.metrics import ProcessMetrics, ProcessInfo


class ProcessCollector(BaseCollector):
    """Upgraded Collector for process metrics, top CPU/Memory consumers, zombie counts, and anomaly heuristics."""

    SUSPICIOUS_PATHS = [
        "\\temp\\",
        "\\appdata\\local\\temp\\",
        "\\users\\public\\",
    ]

    def __init__(self, max_processes: int = 15):
        super().__init__(name="process")
        self.max_processes = max_processes

    def collect(self) -> ProcessMetrics:
        """
        Iterates active processes, checks CPU/Memory, counts zombies, and evaluates security heuristics.
        
        :return: ProcessMetrics Pydantic instance.
        """
        process_list: List[ProcessInfo] = []
        total_count = 0
        zombie_count = 0
        suspicious_list: List[ProcessInfo] = []

        try:
            self.logger.debug("Collecting Running Process metrics v0.2...")
            
            for proc in psutil.process_iter(attrs=['pid', 'name', 'status', 'username', 'exe']):
                try:
                    total_count += 1
                    status = proc.info.get('status') or "unknown"
                    
                    if status in (psutil.STATUS_ZOMBIE, psutil.STATUS_DEAD):
                        zombie_count += 1

                    # Fetch memory & CPU info safely
                    mem_info = proc.memory_info()
                    mem_rss = mem_info.rss if mem_info else 0
                    mem_percent = round(proc.memory_percent(), 2) if hasattr(proc, 'memory_percent') else 0.0
                    cpu_percent = round(proc.cpu_percent(interval=None), 2)
                    
                    p_info = proc.info
                    exe_path = p_info.get('exe') or ""
                    username = p_info.get('username')

                    # Evaluate suspicious process heuristics
                    is_suspicious, reasons = self._evaluate_suspicious_heuristics(
                        name=p_info['name'] or "",
                        exe_path=exe_path,
                        cpu_percent=cpu_percent,
                        mem_percent=mem_percent
                    )

                    proc_item = ProcessInfo(
                        pid=p_info['pid'],
                        name=p_info['name'] or "Unknown",
                        cpu_percent=cpu_percent,
                        memory_percent=mem_percent,
                        memory_rss_bytes=mem_rss,
                        status=status,
                        username=username,
                        exe_path=exe_path,
                        is_suspicious=is_suspicious,
                        suspicious_reasons=reasons
                    )

                    process_list.append(proc_item)
                    if is_suspicious:
                        suspicious_list.append(proc_item)

                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
                except Exception as pe:
                    self.logger.warning(f"Could not inspect process details: {pe}")
                    continue

            # Sort top processes
            top_memory_consumers = sorted(process_list, key=lambda x: x.memory_rss_bytes, reverse=True)[:self.max_processes]
            top_cpu_consumers = sorted(process_list, key=lambda x: x.cpu_percent, reverse=True)[:self.max_processes]

            return ProcessMetrics(
                total_processes=total_count,
                zombie_processes=zombie_count,
                suspicious_count=len(suspicious_list),
                top_cpu_consumers=top_cpu_consumers,
                top_memory_consumers=top_memory_consumers,
                suspicious_processes=suspicious_list
            )

        except Exception as e:
            self.logger.error(f"Error collecting Process metrics: {e}", exc_info=True)
            return ProcessMetrics(
                total_processes=0,
                zombie_processes=0,
                suspicious_count=0,
                top_cpu_consumers=[],
                top_memory_consumers=[],
                suspicious_processes=[]
            )

    @classmethod
    def _evaluate_suspicious_heuristics(cls, name: str, exe_path: str, cpu_percent: float, mem_percent: float) -> Tuple[bool, List[str]]:
        """
        Applies basic security heuristics to flag potential suspicious process activity.
        """
        reasons: List[str] = []
        exe_lower = exe_path.lower()
        name_lower = name.lower()

        # Check execution from temp directories
        for s_path in cls.SUSPICIOUS_PATHS:
            if s_path in exe_lower:
                reasons.append(f"Executable running from temporary directory: {exe_path}")
                break

        # Check suspicious process naming patterns e.g. double extension (.pdf.exe, .png.exe)
        if name_lower.endswith((".pdf.exe", ".doc.exe", ".png.exe", ".txt.exe", ".zip.exe")):
            reasons.append(f"Suspicious double file extension detected: {name}")

        is_suspicious = len(reasons) > 0
        return is_suspicious, reasons
