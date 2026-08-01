# 🤖 AI-Powered Real-Time Inventory Management System

> **Predict Demand. Prevent Stockouts. Automate Reorders.**

An end-to-end intelligent inventory management platform that uses **Apache Spark Structured Streaming**, **PySpark MLlib (Random Forest)**, **FastAPI**, and a **React + TypeScript** dashboard to provide real-time demand predictions, stock-out risk analysis, and automated reorder recommendations for retail stores.

---

## 📋 Table of Contents

- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Architecture](#-architecture)
- [Project Structure](#-project-structure)
- [Prerequisites](#-prerequisites)
- [Installation & Setup](#-installation--setup)
- [Running the System](#-running-the-system)
- [Complete Workflow](#-complete-workflow)
- [API Reference](#-api-reference)
- [Data Schema](#-data-schema)
- [Machine Learning Model](#-machine-learning-model)
- [Frontend Dashboard](#-frontend-dashboard)
- [Docker Deployment](#-docker-deployment)
- [Configuration](#-configuration)
- [Troubleshooting](#-troubleshooting)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **Real-Time Data Streaming** | TCP socket server generates retail sales events (JSON) at ~1 event/sec for 5 stores × 50 products |
| **Spark Structured Streaming** | 5-minute sliding window aggregation with watermarking, fault-tolerant checkpointing, and Parquet output |
| **ML Demand Prediction** | Random Forest regression trained on streaming aggregates to predict per-SKU daily demand |
| **4-Tier Risk Classification** | CRITICAL / HIGH / MEDIUM / LOW based on current stock vs. predicted demand × lead time |
| **Smart Reorder Engine** | Calculates optimal reorder quantities, maps to suppliers, supports auto-confirm workflows |
| **Automated Model Retraining** | APScheduler cron job retrains the RF model daily at 1 AM IST |
| **REST API Backend** | FastAPI with token auth, CORS support, and 7 RESTful endpoints |
| **Interactive Dashboard** | React + shadcn/ui with KPI cards, risk donut charts, filterable tables, and reorder management |
| **Mock Data Fallback** | Frontend gracefully falls back to mock data if backend is unavailable |
| **Docker Compose** | Containerized streaming pipeline for reproducible deployment |

---

## 🛠 Tech Stack

### Data & Processing Layer
| Technology | Version | Purpose |
|------------|---------|---------|
| **Python** | 3.11+ | Core language for backend, streaming, and ML |
| **Apache Spark** | 3.5.x | Distributed stream processing engine |
| **PySpark** | 3.5.0 | Python API for Spark |
| **PySpark MLlib** | 3.5.0 | Machine learning library (Random Forest, Pipeline, Evaluators) |
| **Pandas** | 3.0.3 | Data manipulation in backend services |
| **PyArrow** | 24.0.0 | High-performance Parquet I/O |

### Backend Layer
| Technology | Version | Purpose |
|------------|---------|---------|
| **FastAPI** | 0.116.1 | High-performance async REST API framework |
| **Uvicorn** | 0.35.0 | ASGI server for FastAPI |
| **APScheduler** | 3.11.0 | Background job scheduling (model retraining cron) |
| **python-dotenv** | 1.1.1 | Environment variable management |

### Frontend Layer
| Technology | Version | Purpose |
|------------|---------|---------|
| **React** | 18.3 | UI component library |
| **TypeScript** | 5.8 | Type-safe JavaScript |
| **Vite** | 5.4 | Build tool and dev server |
| **TailwindCSS** | 3.4 | Utility-first CSS framework |
| **shadcn/ui** | Latest | Radix-based accessible component library |
| **Recharts** | 2.15 | Charting library (Line, Area, Bar, Pie) |
| **TanStack Query** | 5.83 | Server state management and data fetching |
| **React Router** | 6.30 | Client-side routing |
| **Sonner** | 1.7 | Toast notifications |
| **Lucide React** | 0.462 | Icon library |
| **Zod** | 3.25 | Schema validation |

### Infrastructure
| Technology | Purpose |
|------------|---------|
| **Docker / Docker Compose** | Container orchestration for streaming pipeline |
| **WinUtils / hadoop.dll** | Windows-compatible Hadoop utilities for Spark |

---

## 🏗 Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     PRESENTATION LAYER                        │
│    React 18 + TypeScript + Vite + TailwindCSS + shadcn/ui    │
│    KPIs · Health Table · Risk Chart · Reorder Management      │
│    Pages: Home | Demand | Analytics | Reorder                 │
└──────────────────────────┬───────────────────────────────────┘
                           │ REST / JSON (port 5173 → 8000)
┌──────────────────────────▼───────────────────────────────────┐
│                     APPLICATION LAYER                         │
│    FastAPI · Token Authentication · CORS · APScheduler        │
│    Endpoints: /home · /demand · /analytics · /reorder · /stock│
└──────────────────────────┬───────────────────────────────────┘
                           │ PySpark + File I/O
┌──────────────────────────▼───────────────────────────────────┐
│                    INTELLIGENCE LAYER                          │
│    Spark MLlib Random Forest Regressor (Pipeline)             │
│    Demand Prediction · Risk Classification · Reorder Engine   │
│    Auto-Retrain: Daily 1 AM IST via APScheduler               │
└──────────────────────────┬───────────────────────────────────┘
                           │ Reads Parquet
┌──────────────────────────▼───────────────────────────────────┐
│                    PROCESSING LAYER                            │
│    Spark Structured Streaming · Socket Source (port 9999)      │
│    5-min Window · 1-min Slide · 10-min Watermark              │
│    Output: Parquet (partitioned by store_id/product_id)       │
│    Checkpoint: checkpoints/retail_streaming/                   │
└──────────────────────────┬───────────────────────────────────┘
                           │ TCP Socket
┌──────────────────────────▼───────────────────────────────────┐
│                       DATA LAYER                               │
│    TCP Stream Server (localhost:9999) · JSON Events            │
│    CSV: current_inventory.csv · seller_master.csv              │
│    Parquet: output/retail_aggregations/                        │
│    Model: models/demand_rf_model/                              │
│    State: backend_api/state/retrain_status.json                │
└──────────────────────────────────────────────────────────────┘
```

### Data Flow

```
Sales Events (TCP:9999)
        │
        ▼
   ┌─────────┐    JSON     ┌─────────────────────┐
   │  Sales   │───────────▶│  Spark Structured    │
   │  Stream  │            │  Streaming           │
   │  Server  │            │  (5-min window agg)  │
   └─────────┘             └──────────┬───────────┘
                                      │ Parquet
                                      ▼
                           ┌─────────────────────┐
                           │  output/             │
                           │  retail_aggregations │
                           │  (partitioned)       │
                           └──────────┬───────────┘
                                      │
                     ┌────────────────┼────────────────┐
                     │                │                 │
                     ▼                ▼                 ▼
              ┌────────────┐  ┌────────────┐  ┌──────────────┐
              │  RF Model  │  │  Decision  │  │  FastAPI     │
              │  Training  │  │  Engine    │  │  (live pred) │
              └────────────┘  └────────────┘  └──────┬───────┘
                                                     │ REST
                                                     ▼
                                              ┌──────────────┐
                                              │  React       │
                                              │  Dashboard   │
                                              └──────────────┘
```

---

## 📁 Project Structure

```
inventory_ai/
├── backend_api/                    # FastAPI REST API server
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app, routes, startup/shutdown
│   │   ├── services.py             # Core business logic (Spark + ML integration)
│   │   ├── schemas.py              # Pydantic request/response models
│   │   ├── auth.py                 # API token authentication
│   │   ├── scheduler.py            # APScheduler config (daily retrain)
│   │   └── state.py                # Retrain status JSON file management
│   ├── state/
│   │   └── retrain_status.json     # Persistent retrain state
│   └── requirements.txt            # Python dependencies
│
├── data/                           # Static data files
│   ├── current_inventory.csv       # Inventory: store × product × stock × lead time
│   └── seller_master.csv           # Seller mapping: supplier name, contact, auto-confirm
│
├── data_stream/                    # Real-time event generator
│   └── sales_stream.py             # TCP server pushing JSON sales events on port 9999
│
├── spark_jobs/                     # PySpark processing scripts
│   ├── spark_socket_stream.py      # Debug: reads socket → prints to console
│   ├── windowed_aggregation.py     # Console output windowed aggregation
│   ├── retail_streaming_aggregation.py  # Production: windowed agg → Parquet output
│   ├── demand_prediction_rf.py     # ML: trains Random Forest model
│   └── inventory_decision_engine.py # Decision: predicts demand → risk → reorder
│
├── models/                         # Trained ML models
│   └── demand_rf_model/            # Saved PipelineModel (VectorAssembler + RF)
│
├── output/                         # Streaming output
│   └── retail_aggregations/        # Parquet files partitioned by store/product
│
├── checkpoints/                    # Spark streaming checkpoints
│   └── retail_streaming/           # Fault-tolerance state
│
├── hadoop/                         # Windows Hadoop compatibility
│   └── bin/
│       ├── winutils.exe            # Required for Spark on Windows
│       └── hadoop.dll
│
├── frontend/
│   └── inventory-insights/         # React + TypeScript + Vite app
│       ├── src/
│       │   ├── App.tsx             # Route definitions
│       │   ├── pages/
│       │   │   ├── HomePage.tsx    # KPI cards, inventory health, risk donut
│       │   │   ├── DemandPage.tsx  # Demand chart, model status, retrain
│       │   │   ├── AnalyticsPage.tsx # Sales/demand/reorder trends
│       │   │   └── ReorderPage.tsx # Reorder queue with PO actions
│       │   ├── components/
│       │   │   ├── dashboard/      # KpiCard, RiskBadge, FilterBar, etc.
│       │   │   └── ui/             # shadcn/ui components
│       │   └── lib/
│       │       ├── api.ts          # Backend API client with mock fallback
│       │       ├── types.ts        # TypeScript interfaces
│       │       └── mock-data.ts    # Fallback data when API unavailable
│       ├── package.json
│       └── vite.config.ts
│
├── docker-compose.yml              # Container orchestration
├── DEMO_README.md                  # Quick demo guide
├── gamma_ppt_prompt_5min.md        # Presentation generator prompt
└── README.md                       # ← This file
```

---

## 📦 Prerequisites

- **Python 3.11+** with pip
- **Java 8 or 11** (required by Apache Spark)
- **Node.js 18+** with npm
- **Docker & Docker Compose** (optional, for containerized deployment)

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `API_TOKEN` | `dev-token` | Authentication token for API requests |
| `VITE_API_BASE_URL` | `http://localhost:8000` | Backend API URL for frontend |
| `VITE_API_TOKEN` | `dev-token` | API token sent by frontend |
| `HADOOP_HOME` | Auto-detected | Path to Hadoop binaries (Windows) |

---

## 🚀 Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/naveenkrishnan276/Inventory_ai.git
cd inventory_ai
```

### 2. Set Up Python Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (macOS/Linux)
source .venv/bin/activate

# Install dependencies
pip install -r backend_api/requirements.txt
```

### 3. Set Up Frontend

```bash
cd frontend/inventory-insights
npm install
cd ../..
```

### 4. Verify Java Installation

```bash
java -version
# Should show Java 8 or 11
```

---

## ▶️ Running the System

The system requires **4 services** running simultaneously. Open **4 separate terminals**:

### Terminal 1 — Data Stream Producer

```bash
# Starts TCP server on localhost:9999
# Generates ~1 sale event per second
python data_stream/sales_stream.py
```

**Expected output:**
```
Sales stream server listening on localhost:9999
Waiting for clients (e.g. PySpark) to connect …

[2026-07-07T13:45:01] STORE_003 | PROD_025 (Beverages) | ₹45.50 × 3 | UPI
[2026-07-07T13:45:02] STORE_001 | PROD_042 (Personal Care) | ₹89.99 × 1 | Card
[2026-07-07T13:45:03] STORE_005 | PROD_015 (Snacks) | ₹320.00 × 25 | Cash ** ANOMALY **
```

### Terminal 2 — Spark Streaming Aggregation

```bash
# Connects to TCP stream, aggregates in 5-min windows
# Writes Parquet to output/retail_aggregations/
python spark_jobs/retail_streaming_aggregation.py
```

> ⏱ **Wait 5+ minutes** for the first window to complete and write Parquet data.

### Terminal 3 — Backend API Server

```bash
cd backend_api
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Started reloader process
```

**Verify:** Open `http://localhost:8000/health` → `{"status": "ok"}`

### Terminal 4 — Frontend Dev Server

```bash
cd frontend/inventory-insights
npm run dev
```

**Access Dashboard:** Open `http://localhost:5173` in your browser.

---

## 🔄 Complete Workflow (End-to-End)

### Phase 1: Data Ingestion

1. **`sales_stream.py`** starts a TCP server on `localhost:9999`
2. It generates **realistic retail sales events** as JSON:
   ```json
   {
     "event_time": "2026-07-07T13:45:01.123Z",
     "store_id": "STORE_003",
     "product_id": "PROD_025",
     "category": "Beverages",
     "unit_price": 45.50,
     "quantity": 3,
     "payment_mode": "UPI",
     "is_anomaly": false
   }
   ```
3. Events are broadcast to all connected TCP clients
4. **5 stores** (`STORE_001` to `STORE_005`), **50 products** (`PROD_001` to `PROD_050`), **5 categories** (Rice, Snacks, Beverages, Dairy, Personal Care)
5. **5% anomaly injection**: random price spikes (2x-5x) and high quantities for robustness testing

### Phase 2: Stream Processing (Spark Structured Streaming)

1. **`retail_streaming_aggregation.py`** connects to `localhost:9999` as a Spark socket source
2. **JSON parsing**: Each line is parsed using an explicit schema (`StructType`)
3. **Data validation**: Filters out records with negative price or quantity
4. **Watermarking**: 10-minute watermark on `event_time` to handle late-arriving data
5. **Sliding window aggregation**:
   - Window duration: **5 minutes**
   - Slide interval: **1 minute**
   - Group by: `store_id`, `product_id`
6. **Computed aggregates per window**:
   | Metric | Formula |
   |--------|---------|
   | `total_units_sold` | `SUM(quantity)` |
   | `total_revenue` | `SUM(quantity × unit_price)` |
   | `transaction_count` | `COUNT(*)` |
   | `avg_units_per_minute` | `total_units_sold / 5` |
7. **Output**: Parquet format, partitioned by `store_id` and `product_id`
   ```
   output/retail_aggregations/
   ├── store_id=STORE_001/
   │   ├── product_id=PROD_005/
   │   │   └── part-00000.parquet
   │   └── product_id=PROD_006/
   │       └── part-00000.parquet
   └── store_id=STORE_002/
       └── ...
   ```
8. **Checkpointing**: Fault-tolerant state saved to `checkpoints/retail_streaming/`
9. **Micro-batch trigger**: Every 5 seconds

### Phase 3: Machine Learning — Model Training

1. **`demand_prediction_rf.py`** reads aggregated Parquet data from `output/retail_aggregations/`
2. **Data exploration**: Counts records, checks for null values
3. **Data cleaning**: Drops rows with null values
4. **Feature engineering**:
   | Feature | Type |
   |---------|------|
   | `total_units_sold` | Numeric |
   | `total_revenue` | Numeric |
   | `avg_units_per_minute` | Numeric |
   | `transaction_count` | Numeric |
5. **ML Pipeline**:
   ```
   Stage 1: VectorAssembler (4 features → "features" vector)
   Stage 2: RandomForestRegressor (100 trees, maxDepth=10, seed=42)
   ```
6. **Train/Test split**: 80/20 with seed=42
7. **Model evaluation**:
   | Metric | Description |
   |--------|-------------|
   | RMSE | Root Mean Squared Error |
   | MAE | Mean Absolute Error |
   | R² | Coefficient of Determination |
8. **Feature importance**: Printed to console, sorted by importance
9. **Model saved** to `models/demand_rf_model/` as a PySpark `PipelineModel`

### Phase 4: Intelligence — Decision Engine

The decision engine runs **inside the FastAPI backend** (in `services.py`) on every API request:

1. **Load inventory**: Reads `data/current_inventory.csv` (store, product, stock, lead_time)
2. **Load streaming data**: Reads latest Parquet from `output/retail_aggregations/`
3. **Join**: Inventory ← LEFT JOIN → Streaming aggregates on `(store_id, product_id)`
4. **Predict**: Runs the trained RF model on joined data → gets 5-min demand prediction
5. **Scale to daily**: `predicted_daily_demand = prediction × 288` (288 five-minute windows per day)
6. **Risk classification**:
   | Risk Level | Condition |
   |------------|-----------|
   | `CRITICAL` | `days_of_cover ≤ 1` |
   | `HIGH` | `days_of_cover ≤ 2` |
   | `MEDIUM` | `days_of_cover ≤ 4` |
   | `LOW` | `days_of_cover > 4` |

   Where `days_of_cover = current_stock / predicted_daily_demand`

7. **Reorder calculation**:
   ```
   buffer_days = 2
   target_stock = (lead_time_days + buffer_days) × predicted_daily_demand
   reorder_qty = max(target_stock - current_stock, 0)
   ```

### Phase 5: Backend API (FastAPI)

The backend serves the intelligence layer to the frontend via REST endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/home/summary` | GET | KPIs, inventory health table, risk distribution, top at-risk |
| `/api/demand/predictions` | GET | Per-SKU predicted vs actual demand |
| `/api/demand/retrain` | POST | Trigger asynchronous model retraining |
| `/api/demand/retrain-status` | GET | Current retrain job status |
| `/api/analytics/trends` | GET | Sales/demand/reorder time-series + risk breakdown |
| `/api/reorder/list` | GET | At-risk items with seller info + reorder recommendations |
| `/api/inventory/update-stock` | POST | Manually update stock levels |

**Authentication**: All `/api/*` endpoints require `x-api-token: dev-token` header.

**Startup behavior**:
1. Ensures state files exist
2. Starts APScheduler for daily retrain at 1 AM IST
3. Initializes lazy Spark session on first API call

### Phase 6: Frontend Dashboard (React)

| Page | Features |
|------|----------|
| **Home** | 4 KPI cards (inventory, at-risk, revenue, stockout %), inventory health table with filters, risk donut chart, top at-risk widget, stock update modal |
| **Demand** | Predicted vs actual line chart, model status panel (version, RMSE, R²), retrain button with polling, paginated predictions table with search |
| **Analytics** | Date range toggle (7d/14d/30d), 4 KPI cards, sales/demand area charts, reorder bar chart, risk pie chart, top movers table |
| **Reorder** | Reorder queue table with checkboxes, bulk draft PO action, per-item create draft / auto-confirm buttons, detail slide-out drawer, seller info display |

**Navigation**: Sidebar with icons for Home, Demand, Analytics, Reorder.

**Data flow**: `TanStack Query` → `api.ts` → `fetch(backend)` → fallback to `mock-data.ts` on error.

### Phase 7: Automated Retraining

1. **APScheduler** runs a cron job daily at **1:00 AM IST**
2. The job calls `run_retrain_job()` which:
   - Sets status to `"running"` in `state/retrain_status.json`
   - Runs `spark_jobs/demand_prediction_rf.py` as a subprocess
   - Parses stdout for RMSE and R² metrics
   - On success: updates status, model version, and metrics
   - On failure: preserves previous metrics, records error
3. **Manual retrain**: Available via `POST /api/demand/retrain` or the dashboard button
4. **Thread-safe**: Uses `threading.Lock` to prevent concurrent retraining

---

## 📡 API Reference

### GET `/api/home/summary`

**Response:**
```json
{
  "total_inventory_units": 48520,
  "at_risk_products": 7,
  "today_sales_revenue": 12480.50,
  "stockout_risk_percent": 13.46,
  "last_refresh": "2026-07-07T13:45:00Z",
  "model_version": "demand_rf_model_20260707_010000",
  "inventory_health": [
    {
      "store_id": "STORE_001",
      "product_id": "PROD_005",
      "current_stock": 10000,
      "predicted_daily_demand": 432.5,
      "days_of_cover": 23.12,
      "risk_level": "LOW"
    }
  ],
  "risk_distribution": { "LOW": 30, "MEDIUM": 10, "HIGH": 8, "CRITICAL": 7 },
  "top_at_risk": [...]
}
```

### GET `/api/demand/predictions?limit=200`

Returns per-SKU demand predictions with timestamps.

### POST `/api/demand/retrain`

Triggers asynchronous model retraining. Returns immediately.

### GET `/api/analytics/trends?range_days=7`

Returns time-series data for sales, demand, and reorder trends.

### GET `/api/reorder/list`

Returns at-risk items with supplier details and reorder recommendations.

### POST `/api/inventory/update-stock`

**Request:**
```json
{
  "store_id": "STORE_001",
  "product_id": "PROD_005",
  "current_stock": 5000
}
```

---

## 📊 Data Schema

### current_inventory.csv

| Column | Type | Description |
|--------|------|-------------|
| `store_id` | String | Store identifier (STORE_001 to STORE_005) |
| `product_id` | String | Product identifier (PROD_001 to PROD_050) |
| `current_stock` | Integer | Current stock units available |
| `lead_time_days` | Integer | Supplier delivery lead time in days |

### seller_master.csv

| Column | Type | Description |
|--------|------|-------------|
| `store_id` | String | Store identifier |
| `product_id` | String | Product identifier |
| `seller_name` | String | Supplier company name |
| `seller_contact` | String | Supplier phone number |
| `auto_confirm_eligible` | Boolean | Whether PO can be auto-confirmed |

### Streaming Event Schema

| Field | Type | Description |
|-------|------|-------------|
| `event_time` | String (ISO 8601) | Timestamp of the sale |
| `store_id` | String | Store where sale occurred |
| `product_id` | String | Product sold |
| `category` | String | Product category (Rice, Snacks, Beverages, Dairy, Personal Care) |
| `unit_price` | Double | Price per unit (INR) |
| `quantity` | Integer | Units sold |
| `payment_mode` | String | UPI / Card / Cash |
| `is_anomaly` | Boolean | Whether this is a simulated anomaly |

---

## 🧠 Machine Learning Model

### Model: Random Forest Regressor

| Parameter | Value |
|-----------|-------|
| Algorithm | Random Forest Regression |
| Library | PySpark MLlib |
| Number of Trees | 100 |
| Max Depth | 10 |
| Min Instances per Node | 1 |
| Subsampling Rate | 0.8 |
| Feature Subset Strategy | Auto |
| Seed | 42 |

### Features Used

| Feature | Description |
|---------|-------------|
| `total_units_sold` | Sum of units sold in the time window |
| `total_revenue` | Total revenue generated in the window |
| `avg_units_per_minute` | Average units sold per minute |
| `transaction_count` | Number of transactions in the window |

### Label

`total_units_sold` — used as a proxy for next-window demand.

### Daily Demand Conversion

The model predicts demand for a **5-minute window**. To convert to daily demand:

```
predicted_daily_demand = model_prediction × 288
```

Where 288 = 24 hours × 60 minutes ÷ 5 minutes per window.

---

## 🖥 Frontend Dashboard

### Pages

#### Home Page (`/`)
- **4 KPI Cards**: Total Inventory, At-Risk Products, Today's Revenue (₹), Stockout Risk %
- **Inventory Health Table**: Filterable by store, product, risk level — shows stock, demand, days of cover
- **Risk Donut Chart**: Visual distribution of CRITICAL/HIGH/MEDIUM/LOW
- **Top At-Risk Widget**: Top 5 products closest to stockout
- **Update Stock Modal**: Manually adjust stock for any store-product

#### Demand Page (`/demand`)
- **Line Chart**: Predicted vs Actual demand trend
- **Model Status Panel**: Current version, RMSE, R², last run timestamp
- **Retrain Button**: Triggers re-training with progress polling
- **Predictions Table**: Paginated, searchable, filterable

#### Analytics Page (`/analytics`)
- **Range Toggle**: 7-day / 14-day / 30-day views
- **Area Charts**: Sales rate and demand rate trends
- **Bar Chart**: Reorder events over time
- **Pie Chart**: Risk distribution
- **Top Movers Table**: Fastest-selling products with trend indicators

#### Reorder Page (`/reorder`)
- **Reorder Queue**: Filterable table of at-risk items
- **Bulk Selection**: Checkbox-based multi-select for batch operations
- **Actions**: Create Draft PO / Auto-Confirm (for eligible sellers)
- **Detail Drawer**: Slide-out panel with full item details

---

## 🐳 Docker Deployment

### Using Docker Compose

```bash
# Start streaming pipeline (sales generator + Spark aggregation)
docker-compose up -d

# Check logs
docker-compose logs -f sales-stream
docker-compose logs -f spark-windowed-aggregation

# Stop
docker-compose down
```

### Services

| Service | Image | Port | Description |
|---------|-------|------|-------------|
| `sales-stream` | python:3.11-slim | 9999 (host) | TCP event producer |
| `spark-windowed-aggregation` | apache/spark:3.5.1 | — | Spark streaming consumer |

---

## ⚙️ Configuration

### Backend (`backend_api/.env`)

```env
API_TOKEN=dev-token
```

### Frontend (`frontend/inventory-insights/.env`)

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_API_TOKEN=dev-token
```

### Spark Configurations

| Config | Value | Purpose |
|--------|-------|---------|
| `spark.sql.shuffle.partitions` | 4 | Optimized for local mode |
| `spark.sql.streaming.schemaInference` | false | Explicit schema enforcement |
| Processing trigger | 5 seconds | Micro-batch interval |
| Watermark duration | 10 minutes | Late data tolerance |

---

## 🔧 Troubleshooting

### Common Issues

| Problem | Solution |
|---------|----------|
| **Spark fails on Windows** | Ensure `hadoop/bin/winutils.exe` exists and `HADOOP_HOME` is set |
| **No Parquet data** | Wait 5+ minutes after starting streaming for first window to complete |
| **Backend can't load model** | Run `demand_prediction_rf.py` first to train and save the model |
| **Frontend shows mock data** | Check backend is running on port 8000 and API token matches |
| **Port 9999 in use** | Kill existing process: `netstat -ano | findstr 9999` then `taskkill /PID <pid> /F` |
| **Java not found** | Install JDK 8/11 and add to PATH |
| **Retrain fails** | Check `output/retail_aggregations/` has Parquet data |

### Verify Each Layer

```bash
# 1. Check stream is running
curl http://localhost:9999  # Should see JSON events

# 2. Check Parquet output exists
ls output/retail_aggregations/store_id=*/product_id=*/

# 3. Check backend health
curl http://localhost:8000/health

# 4. Check API with auth
curl -H "x-api-token: dev-token" http://localhost:8000/api/home/summary

# 5. Check frontend
# Open http://localhost:5173
```

---

## 📄 License

This project is built for educational and demonstration purposes.

---

## 👥 Team

Built with ❤️ using Apache Spark, PySpark MLlib, FastAPI, and React.

**Tagline:** _Predict. Optimize. Never Stock Out._
