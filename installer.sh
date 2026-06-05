#!/bin/bash

# Self Host Tool Installer Script
# Designed for Linux (Mini PC / VPS)

set -e

# Terminal styling codes
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${CYAN}${BOLD}"
echo "=========================================================="
echo "          Installing Self Host Tool Self-Hosting Portal          "
echo "=========================================================="
echo -e "${NC}"

# 1. OS Verification
if [ "$(uname)" != "Linux" ]; then
    echo -e "${RED}Error: Self Host Tool is only supported on Linux systems (VPS or Mini PCs).${NC}"
    exit 1
fi

# Helper to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Ensure curl is installed
echo -e "${BLUE}Checking curl installation...${NC}"
if ! command_exists curl; then
    echo -e "${YELLOW}curl not found. Installing curl...${NC}"
    if command_exists apt-get; then
        sudo apt-get update && sudo apt-get install -y curl
    elif command_exists dnf; then
        sudo dnf install -y curl
    elif command_exists yum; then
        sudo yum install -y curl
    elif command_exists zypper; then
        sudo zypper install -y curl
    elif command_exists pacman; then
        sudo pacman -Sy --noconfirm curl
    else
        echo -e "${RED}Error: curl is required but could not be installed automatically. Please install curl and try again.${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ curl installed successfully.${NC}"
else
    echo -e "${GREEN}✓ curl is already installed.${NC}"
fi

# 2. Check & Install Docker
echo -e "${BLUE}[1/5] Checking Docker installation...${NC}"
if command_exists docker; then
    echo -e "${GREEN}✓ Docker is already installed.${NC}"
else
    echo -e "${YELLOW}Docker not found. Installing Docker using official script...${NC}"
    curl -fsSL https://get.docker.com | sh
    sudo systemctl enable --now docker
    echo -e "${GREEN}✓ Docker installed successfully.${NC}"
fi

# Add current user to docker group if they aren't already in it
if ! groups "$USER" | grep -q '\bdocker\b'; then
    echo -e "${YELLOW}Adding user $USER to the docker group...${NC}"
    sudo usermod -aG docker "$USER" || true
    echo -e "${GREEN}✓ Added $USER to docker group. (Note: You may need to log out and back in for this to take effect.)${NC}"
fi

# Determine if we need sudo to run docker commands
if docker ps >/dev/null 2>&1; then
    DOCKER_CMD="docker compose"
else
    DOCKER_CMD="sudo docker compose"
fi

# 3. Check & Install Docker Compose Plugin
echo -e "${BLUE}[2/5] Checking Docker Compose...${NC}"
if docker compose version >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Docker Compose plugin is available.${NC}"
else
    echo -e "${YELLOW}Docker Compose plugin not found. Installing docker-compose-plugin...${NC}"
    # Install compose plugin on Debian/Ubuntu systems
    if command_exists apt-get; then
        sudo apt-get update && sudo apt-get install -y docker-compose-plugin
    elif command_exists dnf; then
        sudo dnf install -y docker-compose-plugin
    else
        echo -e "${RED}Error: Could not install Docker Compose automatically. Please install docker-compose-plugin manually.${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Docker Compose installed successfully.${NC}"
fi

# 4. Check & Install Tailscale
echo -e "${BLUE}[3/5] Checking Tailscale...${NC}"
if command_exists tailscale; then
    echo -e "${GREEN}✓ Tailscale is already installed.${NC}"
else
    echo -e "${YELLOW}Tailscale not found. Installing Tailscale...${NC}"
    curl -fsSL https://tailscale.com/install.sh | sh
    echo -e "${GREEN}✓ Tailscale installed successfully.${NC}"
fi

# Ensure tailscaled service is running
echo -e "${BLUE}Ensuring Tailscale daemon (tailscaled) is enabled and running...${NC}"
if command_exists systemctl; then
    sudo systemctl enable --now tailscaled
elif command_exists service; then
    sudo service tailscaled start
else
    if ! pgrep -x tailscaled >/dev/null; then
        sudo tailscaled >/dev/null 2>&1 &
        sleep 2
    fi
fi

# 5. Authenticate Tailscale
echo -e "${BLUE}[4/5] Checking Tailscale authentication status...${NC}"
if tailscale status --json 2>/dev/null | grep -q '"BackendState": "Running"'; then
    echo -e "${GREEN}✓ Tailscale is authenticated and active.${NC}"
else
    echo -e "${YELLOW}Tailscale is installed but not authenticated. Starting Tailscale auth...${NC}"
    echo -e "${CYAN}Please click the link below to authenticate this machine on your Tailnet:${NC}"
    sudo tailscale up --accept-dns=true
    echo -e "${GREEN}✓ Tailscale authenticated successfully.${NC}"
fi

# 6. Set Up Repository Directories
echo -e "${BLUE}[5/5] Configuring storage volumes and launching containers...${NC}"
mkdir -p data/apps data/caddy data/config
# Give permissive write rights so container UID 1000/root can read/write config
sudo chmod -R 777 data

# Fetch active MagicDNS or IP to configure the portal domain
MAGIC_DNS=$(tailscale status --json 2>/dev/null | grep -o '"DNSName": "[^"]*' | head -n 1 | cut -d'"' -f4 | sed 's/\.$//' || true)
TS_IP=$(tailscale ip -4 | head -n 1 || true)

# Save portal domain and host directory configurations for Docker Compose
echo "PORTAL_DOMAIN=${MAGIC_DNS:-localhost}" > .env
echo "HOST_DIR=$(pwd)" >> .env

# Create shared docker network for the portal and apps
echo -e "${BLUE}Creating shared docker network selfhost-network...${NC}"
docker network create selfhost-network >/dev/null 2>&1 || sudo docker network create selfhost-network >/dev/null 2>&1 || true

# Start the core compose stack
$DOCKER_CMD up -d --build

# Wait for 3 seconds to let backend boot
sleep 3

echo -e "\n${GREEN}${BOLD}"
echo "=========================================================="
echo "   Self Host Tool Self-Hosting Portal Deployed Successfully!  "
echo "=========================================================="
echo -e "${NC}"
echo -e "Your private portal is running in the background and is fully secured."
echo -e "You can access your dashboard from any device on your Tailnet at:"

if [[ -n "$MAGIC_DNS" ]]; then
    echo -e "  🔗 Secure Domain:   ${CYAN}${BOLD}https://$MAGIC_DNS${NC}"
fi

if [[ -n "$TS_IP" ]]; then
    echo -e "  🔗 Secure VPN IP:   ${CYAN}${BOLD}http://$TS_IP${NC}"
fi

echo -e "\n${YELLOW}Useful commands:${NC}"
if [[ "$DOCKER_CMD" == "sudo docker compose" ]]; then
    echo -e "  - View logs:        ${BOLD}sudo docker compose logs -f${NC}"
    echo -e "  - Stop portal:      ${BOLD}sudo docker compose down${NC}"
    echo -e "  - Start portal:     ${BOLD}sudo docker compose up -d${NC}"
else
    echo -e "  - View logs:        ${BOLD}docker compose logs -f${NC}"
    echo -e "  - Stop portal:      ${BOLD}docker compose down${NC}"
    echo -e "  - Start portal:     ${BOLD}docker compose up -d${NC}"
fi
echo "=========================================================="
echo ""
