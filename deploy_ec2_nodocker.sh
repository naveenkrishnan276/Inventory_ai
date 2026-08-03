#!/bin/bash
# ==============================================================================
# AWS Free-Tier Non-Docker One-Click Deployment Script for Inventory AI
# Target OS: Ubuntu 22.04 / 24.04 LTS (Amazon EC2 t2.micro / t3.micro)
# ==============================================================================

set -e

echo "🚀 Starting Non-Docker AWS Deployment for Inventory AI..."

# ------------------------------------------------------------------------------
# 1. Enable 2 GB Swap Memory (Prevents PySpark Java OOM on 1 GB RAM EC2)
# ------------------------------------------------------------------------------
if free | grep -q 'Swap:[[:space:]]*0'; then
    echo "🧠 Allocating 2 GB Swap Space for memory optimization..."
    sudo fallocate -l 2G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile swap swap defaults 0 0' | sudo tee -a /etc/fstab
    echo "✅ Swap Memory configured successfully."
else
    echo "✅ Swap Memory already enabled."
fi

# ------------------------------------------------------------------------------
# 2. Install System Dependencies (Python 3, OpenJDK 11, Node.js)
# ------------------------------------------------------------------------------
echo "📦 Installing system packages (Python, Java OpenJDK, Node.js)..."
sudo apt-get update -y
sudo apt-get install -y python3-pip python3-venv openjdk-11-jre-headless curl git build-essential

if ! command -v node &> /dev/null; then
    echo "📦 Installing Node.js LTS..."
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
    sudo apt-get install -y nodejs
fi

echo "✅ Python Version: $(python3 --version)"
echo "✅ Java Version: $(java -version 2>&1 | head -n 1)"
echo "✅ Node Version: $(node -version)"

# ------------------------------------------------------------------------------
# 3. Create Virtual Environment & Install Python Requirements
# ------------------------------------------------------------------------------
echo "🐍 Setting up Python Virtual Environment..."
python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install -r backend_api/requirements.txt
pip install serve  # Static file server for frontend

mkdir -p output/retail_aggregations checkpoints models logs

# ------------------------------------------------------------------------------
# 4. Launch Pipeline Components in Background
# ------------------------------------------------------------------------------
echo "⚡ Launching Sales Generator Stream (Port 9999)..."
nohup venv/bin/python data_stream/sales_stream.py > logs/stream.log 2>&1 &

echo "⚡ Launching PySpark Structured Streaming Windowed Aggregation..."
nohup venv/bin/python spark_jobs/windowed_aggregation.py > logs/spark.log 2>&1 &

echo "⚡ Launching FastAPI Backend (Port 8000)..."
cd backend_api
nohup ../venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 > ../logs/backend.log 2>&1 &
cd ..

# ------------------------------------------------------------------------------
# 5. Build and Serve Frontend Dashboard
# ------------------------------------------------------------------------------
echo "🎨 Building React + Vite Frontend Dashboard..."
cd frontend/inventory-insights
npm install
npm run build

echo "⚡ Serving Frontend Dashboard on Port 8080..."
nohup npx serve -s dist -l 8080 > ../../logs/frontend.log 2>&1 &
cd ../..

echo "=============================================================================="
echo "🎉 NON-DOCKER AWS DEPLOYMENT COMPLETE!"
echo "------------------------------------------------------------------------------"
echo "📌 Frontend Dashboard : http://$(curl -s ifconfig.me):8080"
echo "📌 Backend REST API   : http://$(curl -s ifconfig.me):8000"
echo "📌 API Documentation  : http://$(curl -s ifconfig.me):8000/docs"
echo "------------------------------------------------------------------------------"
echo "🔍 View logs via:"
echo "  tail -f logs/stream.log"
echo "  tail -f logs/spark.log"
echo "  tail -f logs/backend.log"
echo "  tail -f logs/frontend.log"
echo "=============================================================================="
