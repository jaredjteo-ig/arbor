#!/bin/bash
# Arbor Server Setup — Run on a fresh Amazon Linux 2023 instance
# Usage: ssh ec2-user@<IP> 'bash -s' < deploy/setup-server.sh
set -euo pipefail

echo "=== Arbor Server Setup ==="

# Install Docker
echo "Installing Docker..."
sudo dnf update -y -q
sudo dnf install -y -q docker git
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker ec2-user

# Install Docker Compose plugin
echo "Installing Docker Compose..."
sudo mkdir -p /usr/local/lib/docker/cli-plugins
COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep '"tag_name"' | sed -E 's/.*"v([^"]+)".*/\1/')
sudo curl -sL "https://github.com/docker/compose/releases/download/v${COMPOSE_VERSION}/docker-compose-linux-x86_64" -o /usr/local/lib/docker/cli-plugins/docker-compose
sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

echo "Docker Compose v${COMPOSE_VERSION} installed"

# Create app directory
sudo mkdir -p /opt/arbor
sudo chown ec2-user:ec2-user /opt/arbor

echo "=== Setup complete ==="
echo "Next steps:"
echo "  1. Log out and back in (for docker group)"
echo "  2. Clone the repo: cd /opt/arbor && git clone <repo-url> ."
echo "  3. Create .env: cp deploy/.env.prod.example deploy/.env.prod"
echo "  4. Edit deploy/.env.prod with real credentials"
echo "  5. Deploy: cd deploy && docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build"
