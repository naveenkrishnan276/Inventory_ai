# Inventory AI Working Demo Guide

This guide explains how to run a live demo of Inventory AI using GitHub Codespaces or any cloud VM.

---

## 1. Open GitHub Codespace
- Go to your GitHub repo and click "Code" → "Open with Codespaces".
- Start a new Codespace.

---

## 2. Start All Services in Separate Terminals

### a. Streaming Producer
```
cd ~/workspace/inventory_ai/data_stream
python sales_stream.py
```

### b. Spark Streaming Aggregation
```
cd ~/workspace/inventory_ai/spark_jobs
python retail_streaming_aggregation.py
```

### c. Backend (FastAPI)
```
cd ~/workspace/inventory_ai/backend_api
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### d. Frontend (React/Vite)
```
cd ~/workspace/inventory_ai/frontend/inventory-insights
npm install
npm run dev -- --host 0.0.0.0 --port 8080
```

---

## 3. Access the Demo
- Codespaces will show URLs for ports 8000 (backend) and 8080 (frontend).
- Click the frontend URL to open your Inventory AI dashboard.

---

## 4. Share the Demo
- Share the Codespaces frontend URL for others to view the dashboard (while Codespace is open).

---

## Summary
- Use Codespaces for a live, working demo.
- Run each service in its own terminal.
- Use the provided URLs to access and share the dashboard.

---

*For a permanent demo, deploy backend and frontend to cloud platforms like Render, Vercel, or AWS.*
