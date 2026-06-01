#!/bin/bash
# EC2 setup script for Amazon Linux 2
# Run once after launching a new EC2 instance
# Usage: bash ec2_setup.sh

set -e
echo "Setting up Ohio Credit Intelligence Platform on EC2..."

# Update system
sudo yum update -y

# Install Docker
sudo yum install -y docker
sudo service docker start
sudo usermod -aG docker ec2-user
sudo systemctl enable docker

# Install Docker Compose plugin
sudo mkdir -p /usr/local/lib/docker/cli-plugins
sudo curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 \
    -o /usr/local/lib/docker/cli-plugins/docker-compose
sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# Install Git
sudo yum install -y git

# Install AWS CLI (for ECR pulls)
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
rm -rf awscliv2.zip aws/

# Clone the repo
git clone https://github.com/SIDDARTHAREDDY8/ohio-credit-intelligence.git
cd ohio-credit-intelligence

echo ""
echo "Setup complete. Next steps:"
echo "1. Create .env file: cp .env.example .env && nano .env"
echo "2. Add your ANTHROPIC_API_KEY and AWS credentials to .env"
echo "3. Log out and back in for docker group to take effect"
echo "4. Start services: docker compose up -d"
echo "5. Check health: curl http://localhost:8000/health"
