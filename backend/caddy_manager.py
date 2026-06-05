import logging
from pathlib import Path
import docker
from config import CADDY_DIR

logger = logging.getLogger(__name__)

def write_caddy_route(app_id: str, route_content: str):
    """
    Writes a Caddy routing snippet to the dynamic caddy directory.
    """
    route_file = CADDY_DIR / f"{app_id}.caddy"
    try:
        with open(route_file, "w") as f:
            f.write(route_content)
        logger.info(f"Wrote Caddy routing snippet for {app_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to write Caddy routing snippet for {app_id}: {e}")
        return False

def delete_caddy_route(app_id: str):
    """
    Deletes the dynamic Caddy routing snippet for an app.
    """
    route_file = CADDY_DIR / f"{app_id}.caddy"
    if route_file.exists():
        try:
            route_file.unlink()
            logger.info(f"Deleted Caddy routing snippet for {app_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete Caddy routing snippet for {app_id}: {e}")
            return False
    return True

def reload_caddy():
    """
    Triggers a hot reload of Caddy inside the running gateway container.
    """
    try:
        client = docker.from_env()
        # Find our Caddy container
        caddy_container = client.containers.get("selfhost-caddy")
        
        # Run caddy reload command inside the container
        exit_code, output = caddy_container.exec_run(
            "caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile"
        )
        
        if exit_code == 0:
            logger.info("Caddy successfully reloaded dynamic configuration")
            return True
        else:
            logger.error(f"Caddy reload failed (exit code {exit_code}): {output.decode()}")
            return False
    except docker.errors.NotFound:
        logger.warning("Caddy container (selfhost-caddy) not found. Dynamic routing will load on next startup.")
        return False
    except Exception as e:
        logger.error(f"Failed to trigger Caddy container reload: {e}")
        return False
