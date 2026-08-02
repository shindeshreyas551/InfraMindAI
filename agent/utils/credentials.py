"""
Secure Credential & Token Storage Manager for InfraMind AI Windows Agent.
Stores and encrypts JWT tokens locally in agent/.device_token.
"""

import json
import base64
import os
from pathlib import Path
from typing import Optional, Dict

TOKEN_FILE = Path(__file__).resolve().parent.parent / ".device_token"

# Windows DPAPI encryption if available, otherwise machine-keyed Base64 obfuscation
try:
    import win32crypt  # type: ignore
    HAS_DPAPI = True
except ImportError:
    HAS_DPAPI = False


def _get_machine_key() -> str:
    """Returns a machine-specific key for local obfuscation fallback."""
    import platform
    import socket
    raw = f"{socket.gethostname()}-{platform.machine()}-{platform.node()}-inframind-agent-secret"
    return raw


def _encrypt(data_str: str) -> str:
    """Encrypt a string payload using DPAPI or Base64 XOR fallback."""
    if HAS_DPAPI:
        try:
            encrypted_bytes = win32crypt.CryptProtectData(data_str.encode("utf-8"), "InfraMindToken", None, None, None, 0)
            return base64.b64encode(encrypted_bytes).decode("utf-8")
        except Exception:
            pass

    key = _get_machine_key()
    data_bytes = data_str.encode("utf-8")
    key_bytes = key.encode("utf-8")
    xor_bytes = bytes([b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(data_bytes)])
    return base64.b64encode(xor_bytes).decode("utf-8")


def _decrypt(encrypted_str: str) -> Optional[str]:
    """Decrypt an encrypted string payload."""
    try:
        raw_bytes = base64.b64decode(encrypted_str.encode("utf-8"))
        if HAS_DPAPI:
            try:
                _, decrypted_bytes = win32crypt.CryptUnprotectData(raw_bytes, None, None, None, 0)
                return decrypted_bytes.decode("utf-8")
            except Exception:
                pass

        key = _get_machine_key()
        key_bytes = key.encode("utf-8")
        decrypted_bytes = bytes([b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(raw_bytes)])
        return decrypted_bytes.decode("utf-8")
    except Exception:
        return None


def save_credentials(email: str, access_token: str, refresh_token: str) -> None:
    """Save encrypted credentials to TOKEN_FILE."""
    payload = {
        "email": email,
        "access_token": access_token,
        "refresh_token": refresh_token,
    }
    encrypted = _encrypt(json.dumps(payload))
    TOKEN_FILE.write_text(encrypted, encoding="utf-8")


def load_credentials() -> Optional[Dict[str, str]]:
    """Load and decrypt saved credentials from TOKEN_FILE."""
    if not TOKEN_FILE.exists():
        return None
    try:
        raw = TOKEN_FILE.read_text(encoding="utf-8").strip()
        decrypted = _decrypt(raw)
        if not decrypted:
            return None
        return json.loads(decrypted)
    except Exception:
        return None


def clear_credentials() -> None:
    """Delete saved token file."""
    if TOKEN_FILE.exists():
        try:
            TOKEN_FILE.unlink()
        except Exception:
            pass
