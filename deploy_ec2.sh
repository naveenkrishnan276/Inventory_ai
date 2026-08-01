#!/bin/bash
# ==============================================================================
# AWS Free-Tier EC2 One-Click Deployment Script for Inventory AI Pipeline
# Target OS: Ubuntu 22.04 / 24.04 LTS (Amazon EC2 t2.micro / t3.micro)
# ==============================================================================

set -e

echo "🚀 Starting System Package Updates & Docker Setup..."
sudo apt-get update -y
sudo apt-get install -y ca-certificates curl gnupg lsb-release git

# Install Docker Engine & Docker Compose Plugin
if ! command -v docker &> /dev/null; then
    echo "📦 Installing Docker..."
    sudo mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    sudo apt-get update -y
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    sudo usermod -aG docker $USER
fi

echo "✅ Docker Version: $(docker --version)"

# Ensure working directories exist
mkdir -p output/retail_aggregations checkpoints models

echo "🐳 Launching Containerized Streaming Pipeline via Docker Compose..."
sudo docker compose up -d --build

echo "=============================================================================="
echo "🎉 DEPLOYMENT COMPLETE!"
echo "Streaming Server running on: tcp://0.0.0.0:9999"
echo "Spark Windowed Aggregation: Active & Writing to ./output/retail_aggregations"
echo "=============================================================================="
