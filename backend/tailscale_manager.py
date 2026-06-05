import socket
import http.client
import json
import logging
from pathlib import Path
from config import TAILSCALE_SOCKET

logger = logging.getLogger(__name__)

class UnixHTTPConnection(http.client.HTTPConnection):
    """
    HTTP Connection subclass that uses a Unix domain socket instead of a TCP port.
    """
    def __init__(self, socket_path):
        super().__init__("local-tailscaled.sock")
        self.socket_path = socket_path

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(str(self.socket_path))

class UnixHTTPClient:
    """
    Simple HTTP client operating over a Unix socket.
    """
    def __init__(self, socket_path):
        self.socket_path = socket_path

    def get(self, path):
        if not Path(self.socket_path).exists():
            logger.warning(f"Tailscale socket not found at {self.socket_path}")
            return None
        conn = None
        try:
            conn = UnixHTTPConnection(self.socket_path)
            conn.request("GET", path)
            response = conn.getresponse()
            if response.status == 200:
                return json.loads(response.read().decode())
            logger.error(f"Tailscale local API returned status {response.status}")
            return None
        except Exception as e:
            logger.error(f"Failed to communicate with Tailscale socket: {e}")
            return None
        finally:
            if conn:
                conn.close()

def get_tailscale_status():
    """
    Queries tailscaled.sock to get the node status, IP, and MagicDNS name.
    """
    client = UnixHTTPClient(TAILSCALE_SOCKET)
    data = client.get("/localapi/v0/status")
    
    if not data:
        return {
            "connected": False,
            "ip": "N/A",
            "magic_dns": "N/A",
            "device_name": "N/A",
            "tailnet": "N/A"
        }
    
    self_node = data.get("Self", {})
    online = self_node.get("Online", False)
    
    # Grab the first IPv4 address
    addresses = self_node.get("TailscaleIPs", self_node.get("Addresses", []))
    ip = "N/A"
    for addr in addresses:
        if "/" in addr:
            addr = addr.split("/")[0]
        # Basic IPv4 validation
        if addr.count(".") == 3:
            ip = addr
            break
            
    dns_name = self_node.get("DNSName", "N/A")
    if dns_name.endswith("."):
        dns_name = dns_name[:-1]
        
    host_name = self_node.get("HostName", "N/A")
    
    tailnet = "N/A"
    if "." in dns_name:
        parts = dns_name.split(".", 1)
        if len(parts) > 1:
            tailnet = parts[1]
            
    return {
        "connected": online,
        "ip": ip,
        "magic_dns": dns_name,
        "device_name": host_name,
        "tailnet": tailnet
    }
