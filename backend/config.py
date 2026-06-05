import os
from pathlib import Path

# Base workspace directory (mounted as /app/data inside the container)
DATA_DIR = Path(os.getenv("DATA_DIR", "/app/data"))

# App storage directories
APPS_DIR = DATA_DIR / "apps"
CADDY_DIR = DATA_DIR / "caddy"
CONFIG_DIR = DATA_DIR / "config"

# Templates directory
TEMPLATES_DIR = Path(__file__).parent / "templates"

# Tailscale socket path on the host, mounted in the container
TAILSCALE_SOCKET = Path(os.getenv("TAILSCALE_SOCKET", "/var/run/tailscale/tailscaled.sock"))

# Ensure paths exist
APPS_DIR.mkdir(parents=True, exist_ok=True)
CADDY_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
