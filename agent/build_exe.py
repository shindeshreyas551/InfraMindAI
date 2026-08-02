"""
PyInstaller Packaging Automation Script for InfraMind AI Windows Agent.
Compiles main.py and all collector/service dependencies into dist/InfraMindAgent.exe.
"""

import sys
import subprocess
from pathlib import Path

AGENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = AGENT_DIR.parent
DIST_DIR = AGENT_DIR / "dist"
BUILD_DIR = AGENT_DIR / "build"


def build_executable():
    """Executes PyInstaller to bundle agent into single executable."""
    print("=" * 60)
    print("Building InfraMindAgent.exe with PyInstaller...")
    print("=" * 60)

    DIST_DIR.mkdir(exist_ok=True)

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onedir",  # Package as directory containing InfraMindAgent.exe
        "--windowed", # Windows GUI application (no visible CMD console window)
        "--name=InfraMindAgent",
        f"--distpath={DIST_DIR}",
        f"--workpath={BUILD_DIR}",
        f"--paths={PROJECT_ROOT}",
        f"--paths={AGENT_DIR}",
        "--hidden-import=pystray",
        "--hidden-import=PIL",
        "--hidden-import=httpx",
        "--hidden-import=psutil",
        "--hidden-import=pydantic",
        str(AGENT_DIR / "main.py"),
    ]

    try:
        subprocess.check_call(cmd, cwd=str(AGENT_DIR))
        print("\n[SUCCESS] PyInstaller Build Complete!")
        print(f"Executable output: {DIST_DIR / 'InfraMindAgent' / 'InfraMindAgent.exe'}")
    except Exception as e:
        print(f"\n[ERROR] PyInstaller Build Failed: {e}")


if __name__ == "__main__":
    build_executable()
