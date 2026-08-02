"""
Download API endpoints — download Windows Agent installer and check for auto-updates.
"""

from pathlib import Path
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

router = APIRouter(prefix="/download", tags=["Download & Updates"])

# Root directory of backend
BASE_DIR = Path(__file__).resolve().parents[4]  # backend directory
INSTALLER_PATH = BASE_DIR / "downloads" / "InfraMindAgentSetup.exe"
DIR_EXE_PATH = BASE_DIR / "downloads" / "InfraMindAgent.exe"
EXE_PATH = BASE_DIR / "downloads" / "InfraMindAgent.exe"


@router.get(
    "/agent",
    summary="Download Windows Agent Installer / Executable",
)
def download_agent():
    """
    Serves the compiled InfraMindAgentSetup.exe or InfraMindAgent.exe binary
    for users downloading the Windows Agent from the web dashboard.
    """
    target_file = None
    filename = "InfraMindAgentSetup.exe"

    if INSTALLER_PATH.exists():
        target_file = INSTALLER_PATH
        filename = "InfraMindAgentSetup.exe"
    elif DIR_EXE_PATH.exists():
        target_file = DIR_EXE_PATH
        filename = "InfraMindAgent.exe"
    elif EXE_PATH.exists():
        target_file = EXE_PATH
        filename = "InfraMindAgent.exe"

    if not target_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Windows Agent installer build is pending. Please build dist/InfraMindAgent.exe using PyInstaller.",
        )

    return FileResponse(
        path=target_file,
        filename=filename,
        media_type="application/octet-stream",
    )


@router.get(
    "/version",
    summary="Get latest Windows Agent release version for auto-updates",
)
def check_version():
    """Returns latest agent version and download URL for auto-update checks."""
    return {
        "latest_version": "0.3.0",
        "download_url": "/api/v1/download/agent",
        "mandatory_update": False,
        "release_notes": "Added MAC/IP telemetry, system tray icon, autostart, and enterprise device controls.",
    }
