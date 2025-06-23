# Apache Flink Pipeline Orchestration - Local Developer Setup Guide

This guide helps developers set up and run an end-to-end pipeline orchestration system using Apache Flink, Flask API, PostgreSQL, and Docker.

---

## 🚀 Overview

**Features:**

- Onboard data pipelines via REST API
- Store pipeline metadata in PostgreSQL
- Trigger PyFlink jobs dynamically
- Support for S3/Filesystem as source and Print/Elasticsearch as sink

---

## 🧱 Prerequisites

- Docker & Docker Compose installed
- Git installed
- Python 3.11+ (for optional local testing)

---

## 📁 Project Structure

```
flink-pipeline-orchestrator/
├── docker-compose.yml
├── init.sql
├── flink-extensions/
│   └── Dockerfile (Flink with connectors)
├── flask-api/
│   ├── app.py
│   ├── db.py
│   ├── Dockerfile
│   └── requirements.txt
├── flink-job/
│   ├── main.py
│   └── requirements.txt
```

---

## 🔧 Step-by-Step Setup

### 1. Clone the Repository

```bash
git clone https://your-repo-url/flink-pipeline-orchestrator.git
cd flink-pipeline-orchestrator
```

### 2. Build and Start the Environment

```bash
docker-compose build
docker-compose up -d
```

This will start the following services:

- `postgres` (DB for pipeline metadata)
- `flask-api` (REST API to onboard & trigger jobs)
- `flink-jobmanager` (Flink cluster master)
- `flink-taskmanager` (Flink cluster worker)

### 3. Verify Flask API

Access the Flask API:

```http
http://localhost:5000/pipelines
```

Use tools like `Postman` or `curl` to interact.

### 4. Onboard a Sample Pipeline

```bash
curl -X POST http://localhost:5000/pipelines \
  -H "Content-Type: application/json" \
  -d '{
    "pipeline_id": "test_pipeline",
    "source_type": "filesystem",
    "source_path": "/tmp/test_input.txt",
    "source_format": "csv",
    "sink_type": "print",
    "sink_index": "not_applicable",
    "transformations": ["uppercase"],
    "schedule": null
  }'
```

### 5. Trigger the Pipeline

```bash
curl -X POST http://localhost:5000/trigger/test_pipeline
```

Watch the Flink logs (`docker logs flink-jobmanager`) for pipeline execution.

---

## 🔌 Connectors Included

The extended Flink image includes:

- `flink-connector-filesystem`
- `flink-connector-elasticsearch7`
- `elasticsearch-rest-high-level-client`

You can add more in `flink-extensions/Dockerfile`.

---

## 📦 Environment Notes

### Mounted Volumes

- `flink-job/` is mounted into `flink-jobmanager` as `/opt/flink_jobs/main.py` for the PyFlink script
- Ensure your data file (e.g., `/tmp/test_input.txt`) exists inside the Flink container or use volume mounts to share

---

## 🧪 Testing & Troubleshooting

- Use `docker-compose logs -f` to debug any service
- Use Flink Dashboard: [http://localhost:8081](http://localhost:8081)
- Make sure the PostgreSQL table is initialized using `init.sql`
- Inspect output printed by the Flink job for validation (e.g., uppercase transformation)

---

## ✅ Optional Extensions

- Add UI for onboarding
- Add Kafka/S3/Postgres connectors
- Add Airflow/K8s-based scheduling
- Add status tracking in metadata
- Add job execution history and audit logs

---

## 🧹 Cleanup

```bash
docker-compose down -v
```

---

## 📬 Need Help?

Open an issue or contact the maintainer.

---

## 📦 Project ZIP

Download the entire setup as a ZIP file:

🔗 [Download flink-pipeline-orchestrator.zip](sandbox:/mnt/data/flink-pipeline-orchestrator.zip)

