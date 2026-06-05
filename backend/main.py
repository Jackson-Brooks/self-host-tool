from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Dict, Any

import tailscale_manager
import system_manager
import app_manager

app = FastAPI(title="Self Host Tool Self-Hosting Portal API", version="1.0.0")

@app.exception_handler(ValueError)
async def value_error_exception_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)},
    )

@app.exception_handler(PermissionError)
async def permission_error_exception_handler(request, exc):
    return JSONResponse(
        status_code=403,
        content={"detail": str(exc)},
    )

# Restrict origins to localhost and authenticated Tailscale VPN range to prevent CSRF / cross-site attacks
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=(
        r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$|"
        r"^https?://100\.(6[4-9]|[7-9]\d|1[0-1]\d|12[0-7])\.\d+\.\d+(:\d+)?$|"
        r"^https?://[a-zA-Z0-9-]+\.[a-zA-Z0-9-]+\.ts\.net$"
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/system/stats")
def api_get_system_stats():
    """
    Get system utilization metrics (CPU, RAM, Disk, Uptime).
    """
    return system_manager.get_system_stats()

@app.get("/api/tailscale/status")
def api_get_tailscale_status():
    """
    Get the Tailscale connection status, local IP, and MagicDNS name of the host.
    """
    return tailscale_manager.get_tailscale_status()

@app.get("/api/apps/available")
def api_get_available_apps():
    """
    Get all available templates in the App Store catalog.
    """
    return app_manager.get_available_apps()

@app.get("/api/apps/installed")
def api_get_installed_apps():
    """
    Get a list of all currently installed apps along with their active container states.
    """
    return app_manager.get_installed_apps()

@app.post("/api/apps/{app_id}/install")
def api_install_app(app_id: str, config: Dict[str, Any] = Body(default={})):
    """
    Write Compose files and dynamically initiate container builds for an app.
    """
    try:
        return app_manager.install_app(app_id, config)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/apps/{app_id}/logs")
def api_get_install_logs(app_id: str):
    """
    Stream live installation log output for a building app.
    """
    return {"logs": app_manager.get_install_logs(app_id)}

@app.post("/api/apps/{app_id}/start")
def api_start_app(app_id: str):
    """
    Start the containers of an already installed app.
    """
    try:
        return app_manager.start_app(app_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/apps/{app_id}/stop")
def api_stop_app(app_id: str):
    """
    Stop the containers of a running app.
    """
    try:
        return app_manager.stop_app(app_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/apps/{app_id}/uninstall")
def api_uninstall_app(app_id: str):
    """
    Shutdown containers, delete volumes, and remove the app's files from disk.
    """
    try:
        return app_manager.uninstall_app(app_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


