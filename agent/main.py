"""
InfraMind AI - Windows Monitoring Agent Entry Point (v0.3)

Run modes:
  python main.py              → continuous upload loop (production mode)
  python main.py --once       → single collection pass, print JSON, exit
  python main.py --output x   → single pass, save JSON to file, exit
"""

import sys
import signal
import argparse
from pathlib import Path

# Ensure project root is on PYTHONPATH when running directly
AGENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = AGENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent.config.settings import get_settings
from agent.services.metrics_aggregator import MetricsAggregator
from agent.services.uploader import MetricsUploader
from agent.utils.logger import get_logger
from agent.utils.credentials import load_credentials, save_credentials
from agent.gui.auth_dialog import prompt_gui_or_cli_auth
from agent.gui.tray import AgentSystemTray


def _setup_windows_autostart() -> None:
    """Register agent binary in Windows CurrentVersion/Run registry key."""
    if sys.platform == "win32":
        try:
            import winreg  # type: ignore
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE,
            )
            executable = sys.executable if getattr(sys, 'frozen', False) else f'"{sys.executable}" "{Path(__file__).resolve()}"'
            winreg.SetValueEx(key, "InfraMindAgent", 0, winreg.REG_SZ, executable)
            winreg.CloseKey(key)
        except Exception:
            pass


def main() -> None:
    """InfraMind AI Windows Agent entry point."""
    parser = argparse.ArgumentParser(
        description="InfraMind AI Windows Monitoring Agent v0.3"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Collect one pass, print JSON, and exit (no upload)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="(with --once) Save JSON telemetry to this file path",
    )
    args = parser.parse_args()

    settings = get_settings
    logger = get_logger("agent.main", settings=settings)

    logger.info("=" * 50)
    logger.info(f"Initializing {settings.agent_name} v{settings.agent_version}")
    logger.info(f"Log File: {settings.absolute_log_file_path}")
    logger.info("=" * 50)

    # ── Single-pass mode (--once / --output) ─────────────────────────────────
    if args.once or args.output:
        _run_once(settings, logger, args.output)
        return

    # ── Windows Autostart Registry Registration ──────────────────────────────
    _setup_windows_autostart()

    # ── Ensure Authenticated Credentials ─────────────────────────────────────
    creds = load_credentials()
    if not creds or not creds.get("access_token"):
        logger.info("No saved user token found. Launching first-time onboarding GUI setup...")
        res = prompt_gui_or_cli_auth(settings.backend_api_url)
        if res:
            email, access_tok, refresh_tok = res
            save_credentials(email, access_tok, refresh_tok)
            logger.info(f"Agent successfully registered to account: {email}")
        else:
            logger.warning("First-time authentication skipped. Agent running in anonymous mode.")

    # ── Initialize System Tray Application ────────────────────────────────────
    dashboard_url = "https://inframindai.vercel.app/dashboard"
    tray = AgentSystemTray(
        dashboard_url=dashboard_url,
        on_exit=lambda: sys.exit(0),
    )
    tray.start()

    # ── Continuous upload loop (production mode) ──────────────────────────────
    uploader = MetricsUploader(settings=settings)

    # Graceful shutdown on Ctrl+C / SIGTERM
    def _handle_shutdown(sig, frame):
        logger.info(f"Received signal {sig} — shutting down...")
        tray.stop()
        uploader.stop()

    signal.signal(signal.SIGINT, _handle_shutdown)
    signal.signal(signal.SIGTERM, _handle_shutdown)

    logger.info(
        f"Starting continuous upload loop -> {settings.backend_api_url} "
        f"(every {settings.upload_interval_sec}s)"
    )

    try:
        uploader.run()  # Blocks until stop() is called
    except Exception as e:
        logger.critical(f"Unhandled agent error: {e}", exc_info=True)
        sys.exit(1)

    logger.info("Agent shut down gracefully.")


def _run_once(settings, logger, output_path: str | None) -> None:
    """Single collection pass — prints or saves JSON, no HTTP upload."""
    try:
        aggregator = MetricsAggregator(settings=settings)
        payload = aggregator.collect_all()
        json_output = payload.to_json(indent=2)

        logger.info(f"Device ID      : {payload.device_id}")
        logger.info(f"Health Status  : {payload.health.running_status.upper()}")
        logger.info(f"Host           : {payload.system.hostname}")
        logger.info(f"CPU Usage      : {payload.cpu.usage_percent}%")
        logger.info(f"RAM Usage      : {payload.memory.usage_percent}%")
        logger.info(f"Uptime         : {payload.system.uptime_formatted}")
        logger.info(f"Processes      : {payload.processes.total_processes} active "
                    f"| Suspicious: {payload.processes.suspicious_count}")

        if output_path:
            out = Path(output_path)
            out.write_text(json_output, encoding="utf-8")
            logger.info(f"Telemetry saved to: {out.resolve()}")
        else:
            print("\n--- Telemetry JSON Payload ---")
            print(json_output)
            print("-----------------------------\n")

    except Exception as e:
        logger.critical(f"Collection error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
