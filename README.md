# Tracker Server API

Modular FastAPI server template with scalable architecture, configuration management, middlewares, services, data models, Docker, and Docker Compose setup.

---

## 📁 Directory Structure

```text
tracker-server/
├── app/
│   ├── config/             # Settings & Environment configurations
│   │   ├── __init__.py
│   │   └── settings.py
│   ├── models/             # Pydantic schemas & Data models
│   │   ├── __init__.py
│   │   └── item.py
│   ├── services/           # Business logic & Data layer
│   │   ├── __init__.py
│   │   └── item_service.py
│   ├── routes/             # API Endpoint Routers
│   │   ├── __init__.py
│   │   ├── health.py
│   │   └── items.py
│   ├── middlewares/        # Custom ASGI Middlewares
│   │   ├── __init__.py
│   │   └── logging_middleware.py
│   ├── utils/              # Helper functions & utilities
│   │   ├── __init__.py
│   │   └── helpers.py
│   ├── __init__.py
│   └── main.py             # FastAPI App instance & entrypoint
├── .dockerignore
├── .env
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## 🚀 Quick Start (Local Setup)

### 1. Prerequisites
- Python 3.10+
- Virtualenv (`python3 -m venv venv`)

### 2. Setup & Installation

```bash
# Navigate to directory
cd tracker-server

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file if not present
cp .env.example .env
```

### 3. Run Development Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Access API Documentation:
- **Interactive Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

---

## 🐳 Docker & Docker Compose Setup

### Running with Docker Compose (Recommended)

```bash
# Build and run containers in detached mode
docker compose up -d --build

# View container logs
docker compose logs -f

# Stop container
docker compose down
```

### Running with Plain Docker

```bash
# Build Docker image
docker build -t tracker-server .

# Run Docker container
docker run -d -p 8000:8000 --name tracker_fastapi_container tracker-server
```

---

## 📌 API Endpoints Summary

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Root greeting & API info |
| `GET` | `/health` | Server health status |
| `GET` | `/api/v1/items` | Fetch all items |
| `GET` | `/api/v1/items/{id}` | Fetch item by ID |
| `POST` | `/api/v1/items` | Create a new item |
| `PUT` | `/api/v1/items/{id}` | Update item by ID |
| `DELETE` | `/api/v1/items/{id}` | Delete item by ID |
