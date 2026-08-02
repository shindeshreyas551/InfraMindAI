"""
Interactive First-Time Authentication Setup Dialog for InfraMind AI Windows Agent.
Uses Tkinter GUI to prompt user for email + password on first launch.
"""

import sys
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Tuple

import httpx


class AuthSetupDialog:
    """Sleek Tkinter modal for agent authentication setup."""

    def __init__(self, backend_url: str):
        self.backend_url = backend_url.rstrip("/")
        self.result: Optional[Tuple[str, str, str]] = None  # (email, access_token, refresh_token)

    def show(self) -> Optional[Tuple[str, str, str]]:
        """Show the modal dialog. Returns (email, access_token, refresh_token) on success."""
        root = tk.Tk()
        root.title("InfraMind AI — Windows Agent Setup")
        root.geometry("420x480")
        root.resizable(False, False)
        root.configure(bg="#0f172a")

        # Center window on screen
        root.eval('tk::PlaceWindow . center')

        # Styling
        style = ttk.Style()
        style.theme_use("clam")

        # Header Frame
        header = tk.Frame(root, bg="#1e1b4b", height=90)
        header.pack(fill="x")

        title_lbl = tk.Label(
            header,
            text="🛡️ InfraMind AI",
            font=("Segoe UI", 18, "bold"),
            fg="#ffffff",
            bg="#1e1b4b",
        )
        title_lbl.pack(pady=(15, 2))

        sub_lbl = tk.Label(
            header,
            text="Connect Windows Endpoint to your Dashboard",
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#1e1b4b",
        )
        sub_lbl.pack(pady=(0, 15))

        # Main Body Frame
        body = tk.Frame(root, bg="#0f172a", padx=30, pady=20)
        body.pack(fill="both", expand=True)

        info_lbl = tk.Label(
            body,
            text="Sign in with your InfraMind AI account to claim\nand monitor this Windows endpoint.",
            font=("Segoe UI", 9),
            fg="#cbd5e1",
            bg="#0f172a",
            justify="center",
        )
        info_lbl.pack(pady=(0, 20))

        # Email Field
        tk.Label(
            body, text="Account Email", font=("Segoe UI", 9, "bold"), fg="#94a3b8", bg="#0f172a"
        ).pack(anchor="w")
        email_entry = tk.Entry(
            body,
            font=("Segoe UI", 11),
            bg="#1e293b",
            fg="#ffffff",
            insertbackground="white",
            bd=0,
            highlightthickness=1,
            highlightbackground="#334155",
            highlightcolor="#6366f1",
        )
        email_entry.pack(fill="x", ipady=6, pady=(4, 15))
        email_entry.insert(0, "admin@inframind.ai")

        # Password Field
        tk.Label(
            body, text="Account Password", font=("Segoe UI", 9, "bold"), fg="#94a3b8", bg="#0f172a"
        ).pack(anchor="w")
        pwd_entry = tk.Entry(
            body,
            show="•",
            font=("Segoe UI", 11),
            bg="#1e293b",
            fg="#ffffff",
            insertbackground="white",
            bd=0,
            highlightthickness=1,
            highlightbackground="#334155",
            highlightcolor="#6366f1",
        )
        pwd_entry.pack(fill="x", ipady=6, pady=(4, 20))
        pwd_entry.insert(0, "SecurePass123")

        # Status Message Label
        status_lbl = tk.Label(
            body, text="", font=("Segoe UI", 9), fg="#f87171", bg="#0f172a"
        )
        status_lbl.pack(pady=(0, 10))

        def _do_login():
            email = email_entry.get().strip()
            pwd = pwd_entry.get().strip()

            if not email or not pwd:
                status_lbl.config(text="Please enter both email and password.", fg="#f87171")
                return

            status_lbl.config(text="Authenticating with backend...", fg="#818cf8")
            root.update_idletasks()

            try:
                with httpx.Client(timeout=10.0) as client:
                    resp = client.post(
                        f"{self.backend_url}/auth/login",
                        json={"email": email, "password": pwd},
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        self.result = (email, data["access_token"], data["refresh_token"])
                        root.destroy()
                    elif resp.status_code == 401:
                        status_lbl.config(text="Invalid email or password.", fg="#f87171")
                    else:
                        status_lbl.config(text=f"Authentication error (HTTP {resp.status_code}).", fg="#f87171")
            except Exception as e:
                status_lbl.config(text=f"Connection failed: {str(e)[:40]}", fg="#f87171")

        # Connect Button
        btn = tk.Button(
            body,
            text="Connect Agent →",
            font=("Segoe UI", 10, "bold"),
            bg="#6366f1",
            fg="#ffffff",
            activebackground="#4f46e5",
            activeforeground="#ffffff",
            bd=0,
            cursor="hand2",
            command=_do_login,
        )
        btn.pack(fill="x", ipady=8)

        root.mainloop()
        return self.result


def prompt_gui_or_cli_auth(backend_url: str) -> Optional[Tuple[str, str, str]]:
    """Tries GUI prompt first, falls back to terminal prompt if headless."""
    try:
        dialog = AuthSetupDialog(backend_url)
        return dialog.show()
    except Exception:
        print("\n--- InfraMind AI Windows Agent Setup ---")
        email = input("Account Email [admin@inframind.ai]: ").strip() or "admin@inframind.ai"
        pwd = input("Account Password [SecurePass123]: ").strip() or "SecurePass123"
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(f"{backend_url.rstrip('/')}/auth/login", json={"email": email, "password": pwd})
                if resp.status_code == 200:
                    data = resp.json()
                    return (email, data["access_token"], data["refresh_token"])
        except Exception as e:
            print(f"Authentication failed: {e}")
        return None
