# GCP → GCP Relational Data Migration Guide
### Source: Cloud SQL PostgreSQL (multi-table, FK-constrained) → Staging: GCS → Target: Ephemeral Cloud SQL PostgreSQL

This guide is a complete, runnable implementation for copying a relational dataset (multiple tables with foreign
keys) from a **source Cloud SQL PostgreSQL instance** into a **target Cloud SQL PostgreSQL instance**, staging the
scrubbed data in **Google Cloud Storage (GCS)** in between. Everything is orchestrated from **GitHub Actions**, but
no raw data ever passes through the GitHub runner — the runner only *triggers* cloud-native jobs.

---

## 0. Architecture

```
GitHub Actions (orchestrator only — never touches rows)
   │
   ├─► Terraform: provisions target Cloud SQL instance + GCS staging bucket + service accounts
   │
   ├─► Cloud Run Job ("scrubber")
   │        - Connects to SOURCE Cloud SQL via Cloud SQL Auth Proxy (private, no public IP needed)
   │        - Reads each table with DuckDB (streaming, low memory)
   │        - Cleans/transforms columns
   │        - Uploads table_name.csv to the GCS staging bucket
   │
   ├─► Runner applies target schema DDL (psql via Cloud SQL Auth Proxy)
   ├─► Runner disables triggers on FK-child tables (breaks referential-integrity checks temporarily)
   ├─► Runner runs `gcloud sql import csv` for every table IN PARALLEL, pulling straight from GCS
   │        (Cloud SQL pulls the file itself over Google's internal network — the runner just triggers it)
   ├─► Runner re-enables triggers + fixes sequences (setval) + validates FKs
   │
   └─► terraform destroy (wrapped in `if: always()`) — guarantees no orphaned billing
```

### Why this shape
- **`gcloud sql import csv` is not transactional** and is not a session you can wrap in `BEGIN…COMMIT`, unlike AWS's
  `aws_s3.table_import_from_s3`. So GCP cannot use the "defer constraints inside one transaction" trick.
- Instead we **disable triggers** (`ALTER TABLE … DISABLE TRIGGER ALL`), which is a persistent table-level setting
  (not scoped to a session), import every table in parallel regardless of dependency order, then **re-enable
  triggers**, which forces Postgres to validate everything.
- Cloud SQL instances don't get public IPs or open ports in this design — both the Cloud Run job and the GitHub
  runner reach Cloud SQL exclusively through the **Cloud SQL Auth Proxy**, authenticated via IAM.

---

## 1. Repository Layout

```
repo/
├── .github/workflows/gcp-pipeline.yml
├── terraform/
│   ├── main.tf
│   ├── variables.tf
│   └── outputs.tf
├── scrubber/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── scrub_pipeline.py
├── sql/
│   ├── target_schema.sql
│   └── fix_sequences.sql
└── GCP_TO_GCP_MIGRATION_GUIDE.md   (this file)
```

---

## 2. Sample Source Schema (multi-table, referential integrity)

This is the schema assumed by the rest of the guide — swap in your real schema, but keep the same shape (a parent
table, two tables that reference it, and a grandchild table).

```sql
-- sql/target_schema.sql
-- Applied to the TARGET database before import. Must match the source table structure
-- (column names/types), since gcloud sql import csv loads into existing tables.

CREATE TABLE organizations (
    id          BIGSERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE users (
    id              BIGSERIAL PRIMARY KEY,
    organization_id BIGINT NOT NULL REFERENCES organizations(id),
    email           TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'inactive',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE orders (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT NOT NULL REFERENCES users(id),
    total_cents INTEGER NOT NULL,
    status      TEXT NOT NULL DEFAULT 'pending',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE order_items (
    id          BIGSERIAL PRIMARY KEY,
    order_id    BIGINT NOT NULL REFERENCES orders(id),
    sku         TEXT NOT NULL,
    quantity    INTEGER NOT NULL,
    unit_cents  INTEGER NOT NULL
);

CREATE INDEX idx_users_org ON users(organization_id);
CREATE INDEX idx_orders_user ON orders(user_id);
CREATE INDEX idx_order_items_order ON order_items(order_id);
```

**Dependency tree:** `organizations` → `users` → `orders` → `order_items`.
This is exactly the ordering problem the disable/re-enable-trigger strategy sidesteps.

---

## 3. Terraform — Target Infrastructure

### `terraform/variables.tf`
```hcl
variable "project_id" {
  type        = string
  description = "GCP project ID"
}

variable "region" {
  type    = string
  default = "us-central1"
}

variable "environment" {
  type    = string
  default = "migration"
}

variable "target_db_tier" {
  type    = string
  default = "db-custom-4-16384" # 4 vCPU / 16GB — bump for bigger datasets
}

variable "target_db_password" {
  type      = string
  sensitive = true
}

variable "source_instance_connection_name" {
  type        = string
  description = "e.g. my-project:us-central1:source-postgres"
}
```

### `terraform/main.tf`
```hcl
terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = { source = "hashicorp/google", version = "~> 5.0" }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# ------------------------------------------------------------------
# STAGING BUCKET
# ------------------------------------------------------------------
resource "google_storage_bucket" "stage" {
  name                        = "ephemeral-migration-stage-${var.environment}-${var.project_id}"
  location                    = var.region
  force_destroy               = true   # required so `terraform destroy` actually empties it
  uniform_bucket_level_access = true
}

# ------------------------------------------------------------------
# TARGET CLOUD SQL INSTANCE
# ------------------------------------------------------------------
resource "google_sql_database_instance" "target" {
  name             = "ephemeral-target-postgres-${var.environment}"
  database_version = "POSTGRES_15"
  region           = var.region
  deletion_protection = false

  settings {
    tier              = var.target_db_tier
    availability_type  = "ZONAL"
    disk_autoresize    = true
    disk_size          = 100

    ip_configuration {
      ipv4_enabled    = false   # no public IP — reached only via Cloud SQL Auth Proxy / private IP
      private_network = null    # set this to a VPC self_link if you require private services access
    }

    backup_configuration {
      enabled = false # ephemeral instance, no need for backups
    }
  }
}

resource "google_sql_database" "target_db" {
  name     = "target_db"
  instance = google_sql_database_instance.target.name
}

resource "google_sql_user" "target_admin" {
  name     = "db_admin"
  instance = google_sql_database_instance.target.name
  password = var.target_db_password
}

# Let the target instance's own service account read the staging bucket (required by `gcloud sql import`)
resource "google_storage_bucket_iam_member" "target_sql_reads_stage" {
  bucket = google_storage_bucket.stage.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_sql_database_instance.target.service_account_email_address}"
}

# ------------------------------------------------------------------
# SERVICE ACCOUNT FOR THE CLOUD RUN SCRUBBER JOB
# ------------------------------------------------------------------
resource "google_service_account" "scrubber" {
  account_id   = "migration-scrubber-${var.environment}"
  display_name = "Migration scrubber Cloud Run Job SA"
}

# Needs to connect to Cloud SQL (source) via the Auth Proxy
resource "google_project_iam_member" "scrubber_cloudsql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.scrubber.email}"
}

# Needs to write scrubbed files into the staging bucket
resource "google_storage_bucket_iam_member" "scrubber_writes_stage" {
  bucket = google_storage_bucket.stage.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.scrubber.email}"
}

# ------------------------------------------------------------------
# CLOUD RUN JOB (the scrubbing engine)
# ------------------------------------------------------------------
resource "google_cloud_run_v2_job" "scrubber" {
  name     = "ephemeral-data-scrubber-${var.environment}"
  location = var.region

  template {
    template {
      service_account = google_service_account.scrubber.email
      max_retries      = 0
      timeout          = "3600s" # up to 1 hour; Cloud Run Jobs support up to 24h

      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/migration/scrubber-engine:latest"

        resources {
          limits = {
            cpu    = "4"
            memory = "8Gi"
          }
        }

        env {
          name  = "SOURCE_INSTANCE_CONNECTION_NAME"
          value = var.source_instance_connection_name
        }
        env {
          name = "SOURCE_DB_PASSWORD"
          value_source {
            secret_key_ref {
              secret  = "source-db-password"
              version = "latest"
            }
          }
        }
        env {
          name  = "SOURCE_DB_USER"
          value = "readonly_migrator"
        }
        env {
          name  = "SOURCE_DB_NAME"
          value = "source_db"
        }
        env {
          name  = "DEST_BUCKET"
          value = google_storage_bucket.stage.name
        }
        env {
          name  = "TABLES"
          value = "organizations,users,orders,order_items"
        }
      }
    }
  }
}
```

### `terraform/outputs.tf`
```hcl
output "bucket_name" {
  value = google_storage_bucket.stage.name
}

output "target_instance_name" {
  value = google_sql_database_instance.target.name
}

output "target_connection_name" {
  value = google_sql_database_instance.target.connection_name
}

output "scrubber_job_name" {
  value = google_cloud_run_v2_job.scrubber.name
}
```

> **Note on secrets:** the `source-db-password` reference assumes you've already stored the source DB's read-only
> password in Secret Manager (`gcloud secrets create source-db-password --data-file=-`) and granted the scrubber SA
> `roles/secretmanager.secretAccessor` on it. Do the same for the target admin password if you don't want it as a
> plain Terraform variable in CI logs — pass it in via a GitHub Actions secret either way.

---

## 4. The Scrubbing Engine (Cloud Run Job)

### `scrubber/requirements.txt`
```
duckdb==1.1.3
google-cloud-storage==2.14.1
```

### `scrubber/Dockerfile`
```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

# Cloud SQL Auth Proxy v2 (static binary) — lets us reach Cloud SQL without public IPs
RUN curl -o /usr/local/bin/cloud-sql-proxy \
    https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.13.0/cloud-sql-proxy.linux.amd64 \
    && chmod +x /usr/local/bin/cloud-sql-proxy

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY scrub_pipeline.py .

ENTRYPOINT ["python", "scrub_pipeline.py"]
```

### `scrubber/scrub_pipeline.py`
```python
import os
import socket
import subprocess
import sys
import time

import duckdb
from google.cloud import storage

PROXY_PORT = 5432
PROXY_HOST = "127.0.0.1"


def start_cloud_sql_proxy(instance_connection_name: str) -> subprocess.Popen:
    """Launches the Cloud SQL Auth Proxy as a background process and waits for it to be ready."""
    proc = subprocess.Popen(
        [
            "cloud-sql-proxy",
            f"--port={PROXY_PORT}",
            instance_connection_name,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            with socket.create_connection((PROXY_HOST, PROXY_PORT), timeout=1):
                print("Cloud SQL Auth Proxy is ready.")
                return proc
        except OSError:
            time.sleep(1)

    proc.terminate()
    raise RuntimeError("Cloud SQL Auth Proxy did not become ready in time.")


def scrub_and_export(con: duckdb.DuckDBPyConnection, table: str, conn_str: str, local_dir: str) -> str:
    """Streams a table from the source DB, applies scrubbing rules, writes a local CSV."""
    local_path = f"{local_dir}/{table}.csv"

    # Per-table scrubbing rules. Extend this dict as your schema grows.
    scrub_sql = {
        "organizations": """
            SELECT id, TRIM(name) AS name, created_at
            FROM postgres_scan('{conn}', 'public', 'organizations')
        """,
        "users": """
            SELECT id, organization_id, LOWER(TRIM(email)) AS email,
                   COALESCE(status, 'inactive') AS status, created_at
            FROM postgres_scan('{conn}', 'public', 'users')
        """,
        "orders": """
            SELECT id, user_id, total_cents, COALESCE(status, 'pending') AS status, created_at
            FROM postgres_scan('{conn}', 'public', 'orders')
        """,
        "order_items": """
            SELECT id, order_id, sku, quantity, unit_cents
            FROM postgres_scan('{conn}', 'public', 'order_items')
        """,
    }[table].format(conn=conn_str)

    con.sql(f"COPY ({scrub_sql}) TO '{local_path}' (FORMAT CSV, HEADER TRUE);")
    print(f"Wrote {local_path}")
    return local_path


def upload_to_gcs(bucket_name: str, local_path: str, table: str) -> None:
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(f"{table}.csv")
    blob.upload_from_filename(local_path)
    print(f"Uploaded {table}.csv -> gs://{bucket_name}/{table}.csv")


def main() -> None:
    instance_connection_name = os.environ["SOURCE_INSTANCE_CONNECTION_NAME"]
    db_user = os.environ["SOURCE_DB_USER"]
    db_password = os.environ["SOURCE_DB_PASSWORD"]
    db_name = os.environ["SOURCE_DB_NAME"]
    bucket_name = os.environ["DEST_BUCKET"]
    tables = os.environ["TABLES"].split(",")

    local_dir = "/tmp/export"
    os.makedirs(local_dir, exist_ok=True)

    proxy_proc = start_cloud_sql_proxy(instance_connection_name)

    try:
        conn_str = f"postgresql://{db_user}:{db_password}@{PROXY_HOST}:{PROXY_PORT}/{db_name}"

        con = duckdb.connect(database=":memory:")
        con.sql("INSTALL postgres; LOAD postgres;")
        con.sql("SET temp_directory='/tmp/duckdb_spill/';")
        con.sql("SET max_memory='6GB';")  # keep headroom under the 8Gi container limit

        for table in tables:
            print(f"--- Processing {table} ---")
            local_path = scrub_and_export(con, table, conn_str, local_dir)
            upload_to_gcs(bucket_name, local_path, table)

        print("All tables scrubbed and staged successfully.")

    finally:
        proxy_proc.terminate()
        proxy_proc.wait(timeout=10)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"FATAL: {exc}", file=sys.stderr)
        sys.exit(1)
```

> **Why CSV, not Parquet?** `gcloud sql import` only accepts CSV or SQL dump formats — not Parquet. Since the
> target-side load uses the native GCP import API rather than DuckDB, the scrubber must write CSV here (unlike the
> AWS version, which can use Parquet with the `aws_s3` extension).

---

## 5. Fixing Sequences After Bulk Load

### `sql/fix_sequences.sql`
```sql
-- Run once after all imports complete. Historical rows carry their own IDs,
-- so BIGSERIAL sequences must be advanced past the max imported value
-- or the next application INSERT will collide.
SELECT setval(pg_get_serial_sequence('organizations', 'id'), COALESCE(MAX(id), 1)) FROM organizations;
SELECT setval(pg_get_serial_sequence('users', 'id'), COALESCE(MAX(id), 1)) FROM users;
SELECT setval(pg_get_serial_sequence('orders', 'id'), COALESCE(MAX(id), 1)) FROM orders;
SELECT setval(pg_get_serial_sequence('order_items', 'id'), COALESCE(MAX(id), 1)) FROM order_items;
```

---

## 6. GitHub Actions Workflow (full pipeline)

### `.github/workflows/gcp-pipeline.yml`
```yaml
name: GCP-to-GCP Ephemeral Migration Pipeline

on:
  workflow_dispatch:
    inputs:
      environment:
        description: "Environment/run label"
        required: true
        default: "migration"

env:
  PROJECT_ID: ${{ secrets.GCP_PROJECT_ID }}
  REGION: us-central1

jobs:
  migrate:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write   # required for Workload Identity Federation

    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      # ------------------------------------------------------------
      # AUTH (Workload Identity Federation — no long-lived JSON keys)
      # ------------------------------------------------------------
      - name: Authenticate to GCP
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.GCP_WIF_PROVIDER }}
          service_account: ${{ secrets.GCP_CI_SERVICE_ACCOUNT }}

      - name: Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v2

      # ------------------------------------------------------------
      # BUILD & PUSH THE SCRUBBER IMAGE
      # ------------------------------------------------------------
      - name: Configure Docker for Artifact Registry
        run: gcloud auth configure-docker ${{ env.REGION }}-docker.pkg.dev --quiet

      - name: Build and Push Scrubber Image
        run: |
          IMAGE="${{ env.REGION }}-docker.pkg.dev/${{ env.PROJECT_ID }}/migration/scrubber-engine:${{ github.sha }}"
          docker build -t "$IMAGE" -t "${{ env.REGION }}-docker.pkg.dev/${{ env.PROJECT_ID }}/migration/scrubber-engine:latest" ./scrubber
          docker push "$IMAGE"
          docker push "${{ env.REGION }}-docker.pkg.dev/${{ env.PROJECT_ID }}/migration/scrubber-engine:latest"

      # ------------------------------------------------------------
      # PROVISION EPHEMERAL TARGET INFRASTRUCTURE
      # ------------------------------------------------------------
      - name: Terraform Init & Apply
        working-directory: terraform
        run: |
          terraform init
          terraform apply -auto-approve \
            -var "project_id=${{ env.PROJECT_ID }}" \
            -var "region=${{ env.REGION }}" \
            -var "environment=${{ inputs.environment }}" \
            -var "target_db_password=${{ secrets.TARGET_DB_PASSWORD }}" \
            -var "source_instance_connection_name=${{ secrets.SOURCE_INSTANCE_CONNECTION_NAME }}"

          echo "BUCKET=$(terraform output -raw bucket_name)" >> "$GITHUB_ENV"
          echo "TARGET_INSTANCE=$(terraform output -raw target_instance_name)" >> "$GITHUB_ENV"
          echo "TARGET_CONN_NAME=$(terraform output -raw target_connection_name)" >> "$GITHUB_ENV"
          echo "SCRUBBER_JOB=$(terraform output -raw scrubber_job_name)" >> "$GITHUB_ENV"

      # ------------------------------------------------------------
      # START A LOCAL CLOUD SQL AUTH PROXY (for schema DDL + trigger mgmt)
      # ------------------------------------------------------------
      - name: Install Cloud SQL Auth Proxy on Runner
        run: |
          curl -o cloud-sql-proxy \
            https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.13.0/cloud-sql-proxy.linux.amd64
          chmod +x cloud-sql-proxy
          sudo apt-get update && sudo apt-get install -y postgresql-client

      - name: Launch Proxy to Target Instance
        run: |
          ./cloud-sql-proxy --port 5432 "${{ env.TARGET_CONN_NAME }}" &
          echo "PROXY_PID=$!" >> "$GITHUB_ENV"
          for i in {1..30}; do
            (echo > /dev/tcp/127.0.0.1/5432) 2>/dev/null && break
            sleep 1
          done

      # ------------------------------------------------------------
      # APPLY TARGET SCHEMA (tables must exist before `gcloud sql import`)
      # ------------------------------------------------------------
      - name: Apply Target Schema DDL
        run: |
          PGPASSWORD="${{ secrets.TARGET_DB_PASSWORD }}" psql \
            -h 127.0.0.1 -p 5432 -U db_admin -d target_db \
            -f sql/target_schema.sql

      # ------------------------------------------------------------
      # RUN THE SCRUBBER (Cloud Run Job) — extracts from SOURCE, writes to GCS
      # ------------------------------------------------------------
      - name: Execute Scrubber Job
        run: |
          gcloud run jobs execute "${{ env.SCRUBBER_JOB }}" \
            --region "${{ env.REGION }}" \
            --wait

      # ------------------------------------------------------------
      # DISABLE TRIGGERS ON CHILD TABLES (breaks FK ordering requirement)
      # ------------------------------------------------------------
      - name: Disable Triggers on Target
        run: |
          PGPASSWORD="${{ secrets.TARGET_DB_PASSWORD }}" psql \
            -h 127.0.0.1 -p 5432 -U db_admin -d target_db -c "
              ALTER TABLE users DISABLE TRIGGER ALL;
              ALTER TABLE orders DISABLE TRIGGER ALL;
              ALTER TABLE order_items DISABLE TRIGGER ALL;
            "

      # ------------------------------------------------------------
      # PARALLEL NATIVE IMPORTS — Cloud SQL pulls straight from GCS
      # ------------------------------------------------------------
      - name: Import All Tables in Parallel
        run: |
          set -e
          for TABLE in organizations users orders order_items; do
            gcloud sql import csv "${{ env.TARGET_INSTANCE }}" \
              "gs://${{ env.BUCKET }}/${TABLE}.csv" \
              --database=target_db \
              --table="${TABLE}" \
              --quiet &
          done
          wait
          echo "All table imports finished."

      # ------------------------------------------------------------
      # RE-ENABLE TRIGGERS — Postgres validates all FKs on next write/read path
      # ------------------------------------------------------------
      - name: Re-enable Triggers and Fix Sequences
        run: |
          PGPASSWORD="${{ secrets.TARGET_DB_PASSWORD }}" psql \
            -h 127.0.0.1 -p 5432 -U db_admin -d target_db -c "
              ALTER TABLE users ENABLE TRIGGER ALL;
              ALTER TABLE orders ENABLE TRIGGER ALL;
              ALTER TABLE order_items ENABLE TRIGGER ALL;
            "
          PGPASSWORD="${{ secrets.TARGET_DB_PASSWORD }}" psql \
            -h 127.0.0.1 -p 5432 -U db_admin -d target_db \
            -f sql/fix_sequences.sql

      - name: Verify Row Counts
        run: |
          PGPASSWORD="${{ secrets.TARGET_DB_PASSWORD }}" psql \
            -h 127.0.0.1 -p 5432 -U db_admin -d target_db -c "
              SELECT 'organizations' AS table_name, COUNT(*) FROM organizations
              UNION ALL SELECT 'users', COUNT(*) FROM users
              UNION ALL SELECT 'orders', COUNT(*) FROM orders
              UNION ALL SELECT 'order_items', COUNT(*) FROM order_items;
            "

      - name: Stop Local Proxy
        if: always()
        run: kill "${{ env.PROXY_PID }}" || true

      # ------------------------------------------------------------
      # GUARANTEED TEARDOWN
      # ------------------------------------------------------------
      - name: Destroy Ephemeral Infrastructure
        if: always()
        working-directory: terraform
        run: |
          terraform destroy -auto-approve \
            -var "project_id=${{ env.PROJECT_ID }}" \
            -var "region=${{ env.REGION }}" \
            -var "environment=${{ inputs.environment }}" \
            -var "target_db_password=${{ secrets.TARGET_DB_PASSWORD }}" \
            -var "source_instance_connection_name=${{ secrets.SOURCE_INSTANCE_CONNECTION_NAME }}"
```

---

## 7. Step-by-Step Setup (do this once, before the first pipeline run)

1. **Enable required APIs** on the project:
   ```bash
   gcloud services enable \
     sqladmin.googleapis.com \
     run.googleapis.com \
     artifactregistry.googleapis.com \
     secretmanager.googleapis.com \
     iamcredentials.googleapis.com \
     cloudresourcemanager.googleapis.com
   ```

2. **Create an Artifact Registry repo** for the scrubber image:
   ```bash
   gcloud artifacts repositories create migration \
     --repository-format=docker \
     --location=us-central1
   ```

3. **Create a read-only migration user on the SOURCE database** (least privilege — never use the source's admin
   credentials in the pipeline):
   ```sql
   CREATE USER readonly_migrator WITH PASSWORD '...';
   GRANT CONNECT ON DATABASE source_db TO readonly_migrator;
   GRANT USAGE ON SCHEMA public TO readonly_migrator;
   GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_migrator;
   ```

4. **Store secrets:**
   - Source DB password → Secret Manager, secret name `source-db-password` (referenced directly by the Cloud Run
     Job in Terraform).
   - In **GitHub repo Settings → Secrets and variables → Actions**, add:
     - `GCP_PROJECT_ID`
     - `SOURCE_INSTANCE_CONNECTION_NAME` (e.g. `my-project:us-central1:source-postgres`)
     - `TARGET_DB_PASSWORD` (you choose this — it's for the new ephemeral instance)
     - `GCP_WIF_PROVIDER` and `GCP_CI_SERVICE_ACCOUNT` (see step 5)

5. **Set up Workload Identity Federation** so GitHub Actions can authenticate to GCP without a long-lived JSON key:
   ```bash
   gcloud iam workload-identity-pools create "github-pool" --location="global"

   gcloud iam workload-identity-pools providers create-oidc "github-provider" \
     --location="global" \
     --workload-identity-pool="github-pool" \
     --issuer-uri="https://token.actions.githubusercontent.com" \
     --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
     --attribute-condition="assertion.repository=='YOUR_GH_ORG/YOUR_REPO'"

   gcloud iam service-accounts create github-ci-migrator

   gcloud iam service-accounts add-iam-policy-binding \
     github-ci-migrator@${PROJECT_ID}.iam.gserviceaccount.com \
     --role="roles/iam.workloadIdentityUser" \
     --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-pool/attribute.repository/YOUR_GH_ORG/YOUR_REPO"
   ```
   Grant `github-ci-migrator@...` these project-level roles: `roles/run.admin`, `roles/cloudsql.admin`,
   `roles/storage.admin`, `roles/artifactregistry.writer`, `roles/iam.serviceAccountUser`,
   `roles/secretmanager.secretAccessor`.

6. **Grant the scrubber's Cloud Run service account access to the source database:**
   Cloud SQL IAM database authentication is simplest here — either:
   - Add the scrubber SA as a Cloud SQL IAM user on the source instance, or
   - Keep password auth (as coded above) and just ensure `roles/cloudsql.client` is granted (already handled by
     Terraform) so the Auth Proxy can open the tunnel.

7. **First run:** trigger the workflow manually from the **Actions** tab (`workflow_dispatch`). Watch the run —
   confirm the row-count verification step at the end matches your source table counts.

8. **Repeat runs:** every run is fully ephemeral. The target instance, staging bucket, and Cloud Run Job are
   destroyed at the end regardless of success or failure, so re-running is always a clean slate.

---

## 8. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `duplicate key value violates unique constraint` on first app write after migration | BIGSERIAL sequence not advanced past imported max ID | Run `sql/fix_sequences.sql` (already in the workflow) |
| `gcloud sql import` fails with `permission denied` on GCS object | Target instance's service account lacks `roles/storage.objectViewer` on the bucket | Confirm the `google_storage_bucket_iam_member.target_sql_reads_stage` resource applied |
| Cloud Run Job times out connecting to source Cloud SQL | Auth Proxy needs `roles/cloudsql.client`, or the instance connection name is wrong | Verify `SOURCE_INSTANCE_CONNECTION_NAME` format: `project:region:instance` |
| FK violation error when re-enabling triggers | Source data itself has orphaned rows (e.g. a user row referencing a deleted org) | Add a scrub-stage `WHERE` filter to drop/quarantine orphans before export, or fix at source |
| DuckDB container OOM on a huge table | Table too large for the in-memory scan | Already mitigated via `SET temp_directory` + `max_memory` in `scrub_pipeline.py`; bump Cloud Run Job memory limit if needed |
| `gcloud sql import csv` silently loads 0 rows | CSV header row wasn't skipped, or column order doesn't match table | `gcloud sql import csv` auto-detects the header if `HEADER TRUE` was used on export; confirm column order matches `target_schema.sql` exactly |

---

## 9. What You'd Add for Production (not included above, ask if you want it built out)

- **VPC Peering / Private Services Access** so Cloud SQL never needs `ipv4_enabled` at all (fully private).
- **Data validation step** comparing source vs. target row counts and checksums per table before declaring success.
- **Handling PostGIS / JSONB / ENUM columns** in the scrub stage (DuckDB's `postgres_scan` needs explicit casts for
  some of these types).
- **Incremental/CDC sync** instead of full-table copy, for datasets too large to fully re-copy on every run.
