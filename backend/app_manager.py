import subprocess
import threading
import shutil
from pathlib import Path
import json
import logging
import re
from config import APPS_DIR, TEMPLATES_DIR, DATA_DIR

logger = logging.getLogger(__name__)

# Thread-safe in-memory cache for live installation logs
INSTALL_LOGS = {}
INSTALL_LOGS_LOCK = threading.Lock()

def validate_app_id(app_id: str) -> str:
    """
    Validates that the app_id is strictly alphanumeric (plus underscores/dashes)
    and stays inside the sandbox directory to prevent path traversal.
    """
    if not re.match(r"^[a-zA-Z0-9_-]+$", app_id):
        raise ValueError("Invalid App ID format")
    
    # Anchor check
    resolved_path = (APPS_DIR / app_id).resolve()
    try:
        if not resolved_path.is_relative_to(APPS_DIR.resolve()):
            raise PermissionError("Path traversal attempt detected")
    except ValueError:
        raise PermissionError("Path traversal attempt detected")
    
    return app_id

def validate_template_id(app_id: str) -> str:
    """
    Validates that the template ID is strictly alphanumeric and stays inside the templates directory.
    """
    if not re.match(r"^[a-zA-Z0-9_-]+$", app_id):
        raise ValueError("Invalid template ID format")
    
    resolved_path = (TEMPLATES_DIR / f"{app_id}.json").resolve()
    try:
        if not resolved_path.is_relative_to(TEMPLATES_DIR.resolve()):
            raise PermissionError("Path traversal attempt detected")
    except ValueError:
        raise PermissionError("Path traversal attempt detected")
    
    return app_id

def sanitize_user_input(value: any) -> str:
    """
    Sanitizes user input to prevent YAML/Compose injections.
    Only allows strings without newline or carriage return characters.
    """
    if not isinstance(value, (str, int, float, bool)):
        raise ValueError("Invalid input type")
    
    val_str = str(value)
    if "\n" in val_str or "\r" in val_str:
        raise ValueError("Newlines and carriage returns are not allowed in configuration values")
    
    return val_str


def get_available_apps():
    """
    Reads the templates/ folder and returns a list of available app metadata.
    """
    apps = []
    for filepath in TEMPLATES_DIR.glob("*.json"):
        try:
            with open(filepath, "r") as f:
                app_data = json.load(f)
                apps.append({
                    "id": app_data["id"],
                    "name": app_data["name"],
                    "description": app_data["description"],
                    "category": app_data["category"],
                    "icon": app_data["icon"],
                    "fields": app_data.get("fields", []),
                    "open_path": app_data.get("open_path", f"/{app_data['id']}")
                })
        except Exception as e:
            logger.error(f"Error reading app template {filepath}: {e}")
    return apps

def get_app_template(app_id: str):
    """
    Reads a specific app template JSON from disk.
    """
    try:
        validate_template_id(app_id)
    except Exception as e:
        logger.error(f"Template validation failed for {app_id}: {e}")
        return None

    filepath = TEMPLATES_DIR / f"{app_id}.json"
    if not filepath.exists():
        return None
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error reading app template {app_id}: {e}")
        return None

def get_installed_apps():
    """
    Scans the data/apps/ folder to detect installed applications and queries
    the Docker socket to fetch their actual live running statuses.
    """
    import docker
    docker_client = None
    try:
        docker_client = docker.from_env()
    except Exception as e:
        logger.error(f"Could not connect to Docker SDK: {e}")

    installed = []
    if not APPS_DIR.exists():
        return installed

    for app_dir in APPS_DIR.iterdir():
        if app_dir.is_dir() and (app_dir / "docker-compose.yml").exists():
            app_id = app_dir.name
            template = get_app_template(app_id)
            if not template:
                continue

            status = "stopped"
            # In our templates, container_name is 'selfhost-<app_id>'
            container_id = f"selfhost-{app_id}"

            if docker_client:
                try:
                    container = docker_client.containers.get(container_id)
                    status = container.status  # 'running', 'exited', 'stopped', etc.
                except docker.errors.NotFound:
                    status = "stopped"
                except Exception as e:
                    logger.error(f"Error getting container status for {app_id}: {e}")
                    status = "unknown"

            installed.append({
                "id": app_id,
                "name": template["name"],
                "description": template["description"],
                "category": template["category"],
                "icon": template["icon"],
                "status": status,
                "open_path": template.get("open_path", f"/{app_id}")
            })
    return installed

def install_app(app_id: str, config_values: dict):
    """
    Renders an app's templates, creates the config directories, writes
    the docker-compose.yml and Caddyfile routing rules, and executes
    'docker compose up' in a separate thread to avoid blocking the main server thread.
    """
    validate_app_id(app_id)
    validate_template_id(app_id)

    template = get_app_template(app_id)
    if not template:
        raise ValueError(f"App template {app_id} not found")

    app_dir = APPS_DIR / app_id
    app_dir.mkdir(parents=True, exist_ok=True)
    try:
        import os
        os.chmod(app_dir, 0o777)
    except Exception as e:
        logger.error(f"Failed to chmod app_dir {app_dir}: {e}")
    # Base substitution variables (resolving host-side paths if running in Docker-in-Docker)
    import os
    HOST_DATA_DIR = os.getenv("HOST_DATA_DIR")
    PORTAL_DOMAIN = os.getenv("PORTAL_DOMAIN", "localhost")
    if HOST_DATA_DIR:
        host_app_dir = Path(HOST_DATA_DIR) / "apps" / app_id
        app_data_dir_str = str(host_app_dir)
        data_dir_str = str(HOST_DATA_DIR)
    else:
        app_data_dir_str = str(app_dir)
        data_dir_str = str(DATA_DIR)

    subs = {
        "APP_DATA_DIR": app_data_dir_str,
        "DATA_DIR": data_dir_str,
        "PORTAL_DOMAIN": PORTAL_DOMAIN
    }
    # Extract user configurations or apply defaults
    for field in template.get("fields", []):
        key = field["key"]
        val = config_values.get(key, field.get("default", ""))
        subs[key] = sanitize_user_input(val)

    # Render docker-compose template
    compose_content = template["compose_template"]
    for key, val in subs.items():
        compose_content = compose_content.replace(f"{{{{{key}}}}}", str(val))

    # Render Caddy dynamic routing template
    caddy_content = template["caddy_template"]
    for key, val in subs.items():
        caddy_content = caddy_content.replace(f"{{{{{key}}}}}", str(val))

    # For code-server, set up a custom-cont-init.d script to remove "Password was set from $PASSWORD" from the login page
    if app_id == "code-server":
        import os
        init_dir = app_dir / "config" / "custom-cont-init.d"
        init_dir.mkdir(parents=True, exist_ok=True)
        # Ensure fully permissive permissions for container user compatibility
        os.chmod(app_dir / "config", 0o777)
        os.chmod(app_dir / "config" / "custom-cont-init.d", 0o777)
        
        script_file = init_dir / "clean-login.sh"
        with open(script_file, "w") as f:
            f.write("#!/bin/bash\n"
                    "if [ -f /app/code-server/src/browser/pages/login.html ]; then\n"
                    "    sed -i 's/ {{PASSWORD_MSG}}//g' /app/code-server/src/browser/pages/login.html\n"
                    "fi\n")
        os.chmod(script_file, 0o777)

    # Automatically pre-create and chmod 777 any subdirectories under {{APP_DATA_DIR}} referenced in the compose template

    import re
    matches = re.findall(r'\{\{APP_DATA_DIR\}\}/([a-zA-Z0-9_\-\/]+)', template["compose_template"])
    for match in matches:
        subpath = app_dir / match
        if '.' in subpath.name:
            subpath = subpath.parent
        try:
            subpath.mkdir(parents=True, exist_ok=True)
            import os
            os.chmod(subpath, 0o777)
        except Exception as e:
            logger.error(f"Failed to pre-create and chmod directory {subpath}: {e}")

    # Save rendered configurations
    with open(app_dir / "docker-compose.yml", "w") as f:
        f.write(compose_content)

    # Write Caddy route file
    from caddy_manager import write_caddy_route
    write_caddy_route(app_id, caddy_content)

    # For filebrowser, pre-initialize the sqlite database if it doesn't exist to set default credentials to admin / admin
    if app_id == "filebrowser":
        db_dir = app_dir / "database"
        db_dir.mkdir(parents=True, exist_ok=True)
        db_file = db_dir / "filebrowser.db"
        if not db_file.exists():
            try:
                if HOST_DATA_DIR:
                    host_db_dir = Path(HOST_DATA_DIR) / "apps" / "filebrowser" / "database"
                    host_db_dir_str = str(host_db_dir)
                else:
                    host_db_dir_str = str(db_dir.resolve())

                logger.info("Initializing File Browser database...")
                # 1. config init
                subprocess.run(
                    [
                        "docker", "run", "--rm",
                        "-v", f"{host_db_dir_str}:/database",
                        "filebrowser/filebrowser:v2.32.0",
                        "config", "init",
                        "-d", "/database/filebrowser.db"
                    ],
                    capture_output=True, check=True
                )
                # 2. users add admin admin
                subprocess.run(
                    [
                        "docker", "run", "--rm",
                        "-v", f"{host_db_dir_str}:/database",
                        "filebrowser/filebrowser:v2.32.0",
                        "users", "add", "admin", "admin",
                        "-d", "/database/filebrowser.db",
                        "--perm.admin"
                    ],
                    capture_output=True, check=True
                )
                import os
                os.chmod(db_file, 0o777)
                logger.info("Successfully pre-initialized File Browser database with admin/admin.")
            except Exception as e:
                logger.error(f"Failed to pre-initialize filebrowser database: {e}")

    # For jellyfin, pre-initialize the network.xml configuration file to set the BaseUrl to /jellyfin
    if app_id == "jellyfin":
        config_dir = app_dir / "config" / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        network_xml = config_dir / "network.xml"
        if not network_xml.exists():
            try:
                with open(network_xml, "w") as f:
                    f.write('<?xml version="1.0" encoding="utf-8"?>\n'
                            '<NetworkConfiguration xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">\n'
                            '  <BaseUrl>/jellyfin</BaseUrl>\n'
                            '</NetworkConfiguration>\n')
                import os
                os.chmod(network_xml, 0o777)
                logger.info("Successfully pre-initialized Jellyfin network.xml with basepath /jellyfin.")
            except Exception as e:
                logger.error(f"Failed to pre-create Jellyfin network.xml: {e}")

    # Initialize dynamic logger
    with INSTALL_LOGS_LOCK:
        INSTALL_LOGS[app_id] = [
            "Initiating installation of " + template["name"] + "...\n",
            "Creating configuration directories...\n"
        ]

    # Asynchronous runner
    def run_docker_compose():
        try:
            logger.info(f"Starting docker compose for {app_id}...")
            
            # Spin up containers
            process = subprocess.Popen(
                ["docker", "compose", "up", "-d", "--remove-orphans"],
                cwd=str(app_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )

            # Consume lines of logs as they stream from Docker
            for line in process.stdout:
                with INSTALL_LOGS_LOCK:
                    INSTALL_LOGS[app_id].append(line)
                logger.info(f"[{app_id} install log]: {line.strip()}")

            process.wait()

            if process.returncode == 0:
                with INSTALL_LOGS_LOCK:
                    INSTALL_LOGS[app_id].append("\nInstallation completed successfully! 🎉\n")
                logger.info(f"Successfully installed and started {app_id}")
                
                # Reload Caddy to serve the new route
                from caddy_manager import reload_caddy
                reload_caddy()
            else:
                with INSTALL_LOGS_LOCK:
                    INSTALL_LOGS[app_id].append(f"\nInstallation failed with exit code {process.returncode}\n")
                logger.error(f"Docker Compose failed for {app_id} with exit code {process.returncode}")

        except Exception as e:
            with INSTALL_LOGS_LOCK:
                INSTALL_LOGS[app_id].append(f"\nFatal error occurred during installation: {str(e)}\n")
            logger.error(f"Docker Compose execution failed: {e}")

    threading.Thread(target=run_docker_compose, daemon=True).start()
    return {"status": "started", "message": "Installation started"}

def get_install_logs(app_id: str):
    """
    Returns the accumulated installation logs for an app.
    """
    validate_app_id(app_id)
    with INSTALL_LOGS_LOCK:
        logs = INSTALL_LOGS.get(app_id, [])
        return "".join(logs)

def start_app(app_id: str):
    """
    Boots the container of an already-installed app.
    """
    validate_app_id(app_id)
    app_dir = APPS_DIR / app_id
    if not app_dir.exists() or not (app_dir / "docker-compose.yml").exists():
        raise FileNotFoundError(f"App {app_id} is not installed")

    try:
        process = subprocess.run(
            ["docker", "compose", "up", "-d"],
            cwd=str(app_dir),
            capture_output=True,
            text=True
        )
        if process.returncode == 0:
            from caddy_manager import reload_caddy
            reload_caddy()
            return {"status": "success", "message": f"{app_id} started"}
        else:
            return {"status": "error", "message": process.stderr}
    except Exception as e:
        logger.error(f"Failed to start app {app_id}: {e}")
        raise

def stop_app(app_id: str):
    """
    Stops the containers of an installed app.
    """
    validate_app_id(app_id)
    app_dir = APPS_DIR / app_id
    if not app_dir.exists() or not (app_dir / "docker-compose.yml").exists():
        raise FileNotFoundError(f"App {app_id} is not installed")

    try:
        process = subprocess.run(
            ["docker", "compose", "stop"],
            cwd=str(app_dir),
            capture_output=True,
            text=True
        )
        if process.returncode == 0:
            return {"status": "success", "message": f"{app_id} stopped"}
        else:
            return {"status": "error", "message": process.stderr}
    except Exception as e:
        logger.error(f"Failed to stop app {app_id}: {e}")
        raise

def uninstall_app(app_id: str):
    """
    Shuts down and deletes containers and volumes of the app, cleans up
    Caddy rules, and cleans the local installation directory from host.
    """
    validate_app_id(app_id)
    app_dir = APPS_DIR / app_id
    if not app_dir.exists():
        return {"status": "success", "message": "App not installed"}

    try:
        # Run docker compose down with volumes deletion
        if (app_dir / "docker-compose.yml").exists():
            subprocess.run(
                ["docker", "compose", "down", "-v"],
                cwd=str(app_dir),
                capture_output=True
            )

        # Remove Caddy dynamic routing configuration
        from caddy_manager import delete_caddy_route, reload_caddy
        delete_caddy_route(app_id)
        reload_caddy()

        # Delete local configuration folders
        shutil.rmtree(app_dir)
        
        # Clear installation log cache if present
        with INSTALL_LOGS_LOCK:
            if app_id in INSTALL_LOGS:
                del INSTALL_LOGS[app_id]

        return {"status": "success", "message": f"{app_id} successfully uninstalled"}
    except Exception as e:
        logger.error(f"Failed to uninstall app {app_id}: {e}")
        raise
