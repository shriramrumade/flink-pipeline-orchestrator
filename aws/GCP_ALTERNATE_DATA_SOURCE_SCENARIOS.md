# Alternate Data-Source Scenarios (GCP Target)

This extends `GCP_TO_GCP_MIGRATION_GUIDE.md`. Both scenarios below reuse the **same target Cloud SQL
provisioning, schema DDL, trigger disable/re-enable strategy, sequence fix, and teardown** from that guide — only
the "how do the CSVs get into the staging bucket" step changes. Where a step is unchanged, it's referenced instead
of repeated.

```
Scenario 1: Pre-staged files          Scenario 2: Synthetic data
┌─────────────────┐                   ┌──────────────────┐
│ Source team's    │  copy/reference   │ Cloud Run Job     │  calls
│ GCS bucket        │ ───────────────► │ "synth-generator" │ ───────► AI agent (Claude API)
│ (already exported)│                  │                    │ ◄─────── generates rows as JSON
└─────────────────┘                   └──────────────────┘
         │                                       │
         ▼                                       ▼
   [ Migration staging GCS bucket ] ──────────────
                     │
                     ▼
        Same target-load pipeline: schema DDL → disable triggers →
        parallel `gcloud sql import csv` → re-enable triggers → fix sequences → teardown
```

---

## Scenario 1: Files Already Staged by the Source Team

**When this applies:** another team already exports `organizations.csv`, `users.csv`, `orders.csv`,
`order_items.csv` (or a full dump) into their own GCS bucket on a schedule you don't control. You are not
extracting from a live database at all — you're consuming an artifact someone else produces.

### 1.1 What changes vs. the main guide
- **No Cloud Run scrubbing job, no DuckDB, no source Cloud SQL connection.** There is no "source database" in
  this pipeline's scope — that responsibility belongs to the other team's export job.
- The pipeline's job shrinks to: **verify the files are present and look sane → copy them into your own
  ephemeral staging bucket → run the same import/trigger/sequence steps as before.**
- Copying into your own bucket (rather than importing directly from theirs) is deliberate: it gives you an
  isolated, versioned snapshot for this run, and avoids needing to grant your target Cloud SQL instance's service
  account long-term access to another team's bucket.

### 1.2 Terraform additions

```hcl
# terraform/variables.tf (add)
variable "source_bucket_name" {
  type        = string
  description = "Name of the source team's existing GCS bucket (not managed by this Terraform config)"
}

variable "source_file_prefix" {
  type    = string
  default = "" # e.g. "exports/2026-07-23/" if files are under a dated folder
}
```

```hcl
# terraform/main.tf (add) — reference the existing bucket, don't create it
data "google_storage_bucket" "source" {
  name = var.source_bucket_name
}

# Grant the CI service account (the one GitHub Actions runs as) read access,
# scoped only to this bucket, only for the duration this Terraform state exists.
# In practice this is usually a one-time grant the source team makes on their side —
# this resource documents the requirement even if applied out-of-band.
resource "google_storage_bucket_iam_member" "ci_reads_source" {
  bucket = data.google_storage_bucket.source.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${var.ci_service_account_email}"
}
```

> The Cloud Run scrubber job resource, its service account, and the `SOURCE_INSTANCE_CONNECTION_NAME` /
> `SOURCE_DB_*` variables from the main guide are **removed entirely** in this scenario — there's nothing for
> them to connect to.

### 1.3 GitHub Actions workflow

```yaml
name: GCP Import from Pre-Staged Files

on:
  workflow_dispatch:
    inputs:
      source_bucket:
        description: "Source team's bucket name"
        required: true
      source_prefix:
        description: "Optional folder prefix, e.g. exports/2026-07-23/"
        required: false
        default: ""

env:
  PROJECT_ID: ${{ secrets.GCP_PROJECT_ID }}
  REGION: us-central1
  TABLES: "organizations users orders order_items"

jobs:
  import-pipeline:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write
    steps:
      - uses: actions/checkout@v4

      - name: Authenticate to GCP
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.GCP_WIF_PROVIDER }}
          service_account: ${{ secrets.GCP_CI_SERVICE_ACCOUNT }}

      - uses: google-github-actions/setup-gcloud@v2

      # ------------------------------------------------------------
      # PROVISION TARGET DB + OWN STAGING BUCKET (same as main guide,
      # minus the scrubber Cloud Run job / source DB variables)
      # ------------------------------------------------------------
      - name: Terraform Init & Apply
        working-directory: terraform
        run: |
          terraform init
          terraform apply -auto-approve \
            -var "project_id=${{ env.PROJECT_ID }}" \
            -var "target_db_password=${{ secrets.TARGET_DB_PASSWORD }}" \
            -var "source_bucket_name=${{ inputs.source_bucket }}"
          echo "BUCKET=$(terraform output -raw bucket_name)" >> "$GITHUB_ENV"
          echo "TARGET_INSTANCE=$(terraform output -raw target_instance_name)" >> "$GITHUB_ENV"
          echo "TARGET_CONN_NAME=$(terraform output -raw target_connection_name)" >> "$GITHUB_ENV"

      # ------------------------------------------------------------
      # VERIFY THE FILES ACTUALLY EXIST BEFORE DOING ANYTHING ELSE
      # ------------------------------------------------------------
      - name: Verify Required Files Are Present
        run: |
          for TABLE in ${{ env.TABLES }}; do
            SRC="gs://${{ inputs.source_bucket }}/${{ inputs.source_prefix }}${TABLE}.csv"
            if ! gsutil -q stat "$SRC"; then
              echo "::error::Missing expected file: $SRC"
              exit 1
            fi
          done

      # ------------------------------------------------------------
      # COPY INTO YOUR OWN EPHEMERAL STAGING BUCKET (isolation + audit trail)
      # ------------------------------------------------------------
      - name: Copy Files into Migration Staging Bucket
        run: |
          gsutil -m cp \
            "gs://${{ inputs.source_bucket }}/${{ inputs.source_prefix }}*.csv" \
            "gs://${{ env.BUCKET }}/"

      - name: Sanity-Check Row Counts of Copied Files
        run: |
          for TABLE in ${{ env.TABLES }}; do
            LINES=$(gsutil cat "gs://${{ env.BUCKET }}/${TABLE}.csv" | wc -l)
            echo "$TABLE.csv: $((LINES - 1)) data rows"
            if [ "$LINES" -le 1 ]; then
              echo "::error::$TABLE.csv appears empty (header row only, or truly empty)"
              exit 1
            fi
          done

      # ------------------------------------------------------------
      # FROM HERE ON: IDENTICAL TO THE MAIN GUIDE
      # (install proxy → apply target_schema.sql → disable triggers →
      #  parallel gcloud sql import → re-enable triggers → fix_sequences.sql →
      #  verify counts → terraform destroy in always())
      # ------------------------------------------------------------
      - name: Install Cloud SQL Auth Proxy + psql
        run: |
          curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.13.0/cloud-sql-proxy.linux.amd64
          chmod +x cloud-sql-proxy
          sudo apt-get update && sudo apt-get install -y postgresql-client

      - name: Launch Proxy + Apply Schema + Import + Re-enable + Verify
        run: |
          ./cloud-sql-proxy --port 5432 "${{ env.TARGET_CONN_NAME }}" &
          PROXY_PID=$!
          for i in {1..30}; do (echo > /dev/tcp/127.0.0.1/5432) 2>/dev/null && break; sleep 1; done

          PGPASSWORD="${{ secrets.TARGET_DB_PASSWORD }}" psql -h 127.0.0.1 -p 5432 -U db_admin -d target_db -f sql/target_schema.sql

          PGPASSWORD="${{ secrets.TARGET_DB_PASSWORD }}" psql -h 127.0.0.1 -p 5432 -U db_admin -d target_db -c "
            ALTER TABLE users DISABLE TRIGGER ALL;
            ALTER TABLE orders DISABLE TRIGGER ALL;
            ALTER TABLE order_items DISABLE TRIGGER ALL;
          "

          for TABLE in ${{ env.TABLES }}; do
            gcloud sql import csv "${{ env.TARGET_INSTANCE }}" "gs://${{ env.BUCKET }}/${TABLE}.csv" \
              --database=target_db --table="${TABLE}" --quiet &
          done
          wait

          PGPASSWORD="${{ secrets.TARGET_DB_PASSWORD }}" psql -h 127.0.0.1 -p 5432 -U db_admin -d target_db -c "
            ALTER TABLE users ENABLE TRIGGER ALL;
            ALTER TABLE orders ENABLE TRIGGER ALL;
            ALTER TABLE order_items ENABLE TRIGGER ALL;
          "
          PGPASSWORD="${{ secrets.TARGET_DB_PASSWORD }}" psql -h 127.0.0.1 -p 5432 -U db_admin -d target_db -f sql/fix_sequences.sql

          kill $PROXY_PID

      - name: Destroy Ephemeral Infrastructure
        if: always()
        working-directory: terraform
        run: |
          terraform destroy -auto-approve \
            -var "project_id=${{ env.PROJECT_ID }}" \
            -var "target_db_password=${{ secrets.TARGET_DB_PASSWORD }}" \
            -var "source_bucket_name=${{ inputs.source_bucket }}"
```

### 1.3 Step-by-step
1. Get the **exact bucket name and object prefix** from the source team, and confirm the CSV column order matches
   `sql/target_schema.sql` exactly (this is the #1 failure mode — see troubleshooting).
2. Ask the source team (or your platform team) to grant your CI service account `roles/storage.objectViewer` on
   their bucket — this is usually a one-line IAM addition on their side, not something your Terraform can create
   unilaterally since you don't own that bucket.
3. Trigger the workflow with `source_bucket` (and `source_prefix` if their files live under a dated folder).
4. The "verify files present" and "sanity-check row counts" steps fail fast and loudly if the source team's export
   job hasn't run yet or produced empty files — check these logs first if the run fails early.
5. Everything downstream (schema, triggers, import, sequences, teardown) is identical to the main guide.

### 1.4 Troubleshooting specific to this scenario
| Symptom | Cause | Fix |
|---|---|---|
| `AccessDeniedException: 403` on `gsutil stat` | CI service account not granted read on source bucket | Confirm the IAM grant was applied on the source team's project, not yours |
| Import succeeds but columns are shifted/garbled | Source team changed column order or added a column without telling you | Pin down a contract (e.g. a shared schema doc or a header-row check) rather than assuming order |
| File exists but is from yesterday | Source export job hasn't run yet for today | Add a step that checks the GCS object's `updated` timestamp against `date -u` before proceeding |

---

## Scenario 2: Synthetic Data Generated by an AI Agent

**When this applies:** you want a realistic-looking, referentially-intact dataset (for load testing, demos, or
a staging environment) without touching any real production data at all. An AI agent generates the rows.

### 2.1 What changes vs. the main guide
- The Cloud Run job becomes a **generator**, not a scrubber: it has no source database connection at all. It
  calls the Claude API to produce rows, in **dependency order** (parents before children), so foreign keys are
  valid by construction rather than by disabling triggers as a workaround.
- Because generation respects FK order already, you technically don't need the disable/re-enable trigger dance —
  but the guide keeps it as a safety net, since `gcloud sql import` still loads tables independently and a
  transient ordering issue (e.g. parallel imports racing) would otherwise cause spurious failures.
- You need an Anthropic API key stored in Secret Manager, and a defined **row-count target per table**.

### 2.2 Terraform additions

```hcl
# terraform/variables.tf (add)
variable "rows_per_table" {
  type = map(number)
  default = {
    organizations = 50
    users         = 500
    orders        = 2000
    order_items   = 6000
  }
}
```

```hcl
# terraform/main.tf (replace the scrubber job's service account + job with this)
resource "google_service_account" "synth_generator" {
  account_id   = "synth-generator-${var.environment}"
  display_name = "Synthetic data generator Cloud Run Job SA"
}

resource "google_storage_bucket_iam_member" "synth_writes_stage" {
  bucket = google_storage_bucket.stage.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.synth_generator.email}"
}

resource "google_secret_manager_secret_iam_member" "synth_reads_api_key" {
  secret_id = "anthropic-api-key" # pre-created once via `gcloud secrets create anthropic-api-key --data-file=-`
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.synth_generator.email}"
}

resource "google_cloud_run_v2_job" "synth_generator" {
  name     = "ephemeral-synth-generator-${var.environment}"
  location = var.region

  template {
    template {
      service_account = google_service_account.synth_generator.email
      max_retries      = 0
      timeout          = "3600s"

      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/migration/synth-generator:latest"

        resources {
          limits = { cpu = "2", memory = "2Gi" } # no DuckDB/large in-memory scans needed here
        }

        env {
          name = "ANTHROPIC_API_KEY"
          value_source {
            secret_key_ref {
              secret  = "anthropic-api-key"
              version = "latest"
            }
          }
        }
        env {
          name  = "DEST_BUCKET"
          value = google_storage_bucket.stage.name
        }
        env {
          name  = "ROWS_PER_TABLE_JSON"
          value = jsonencode(var.rows_per_table)
        }
      }
    }
  }
}
```

### 2.3 The Generator Engine

`synth-generator/requirements.txt`
```
anthropic==0.40.0
google-cloud-storage==2.14.1
```

`synth-generator/Dockerfile`
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY generate_synthetic.py .
ENTRYPOINT ["python", "generate_synthetic.py"]
```

`synth-generator/generate_synthetic.py`
```python
import csv
import json
import os
import random

from anthropic import Anthropic
from google.cloud import storage

MODEL = "claude-haiku-4-5"  # fast + cheap, plenty capable for structured synthetic rows
BATCH_SIZE = 50             # rows requested per API call, keeps each response small and parseable

# Table generation order matters: parents before children, so we always have
# valid foreign key values to sample from when generating child rows.
TABLE_SPECS = [
    {
        "table": "organizations",
        "columns": ["id", "name", "created_at"],
        "prompt": (
            "Generate {n} realistic but fictional company names for a B2B SaaS customer base. "
            "Return ONLY a JSON array of objects with keys: name (string), created_at "
            "(ISO 8601 timestamp within the last 3 years). Do not include an id field."
        ),
    },
    {
        "table": "users",
        "columns": ["id", "organization_id", "email", "status", "created_at"],
        "prompt": (
            "Generate {n} realistic but fictional user records for a B2B SaaS product. "
            "Return ONLY a JSON array of objects with keys: email (string, lowercase), "
            "status (one of: active, inactive, suspended), created_at (ISO 8601 timestamp). "
            "Do not include id or organization_id fields — those are assigned separately."
        ),
    },
    {
        "table": "orders",
        "columns": ["id", "user_id", "total_cents", "status", "created_at"],
        "prompt": (
            "Generate {n} realistic e-commerce order records. Return ONLY a JSON array of "
            "objects with keys: total_cents (integer, 500-500000), status (one of: pending, "
            "paid, shipped, cancelled), created_at (ISO 8601 timestamp). Do not include id "
            "or user_id fields."
        ),
    },
    {
        "table": "order_items",
        "columns": ["id", "order_id", "sku", "quantity", "unit_cents"],
        "prompt": (
            "Generate {n} realistic order line items. Return ONLY a JSON array of objects "
            "with keys: sku (string like 'SKU-XXXXX'), quantity (integer 1-10), unit_cents "
            "(integer 100-50000). Do not include id or order_id fields."
        ),
    },
]


def call_claude_for_rows(client: Anthropic, prompt_template: str, n: int) -> list[dict]:
    """Requests a batch of synthetic rows as strict JSON and parses the response."""
    prompt = prompt_template.format(n=n) + " Respond with JSON only, no prose, no markdown fences."
    response = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(block.text for block in response.content if block.type == "text")
    text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(text)


def generate_table(client: Anthropic, spec: dict, total_rows: int, fk_pool: dict) -> tuple[str, list[dict]]:
    """Generates `total_rows` rows for one table, assigning real sequential IDs and,
    where applicable, sampling a valid foreign key from an already-generated parent table."""
    rows = []
    next_id = 1

    while len(rows) < total_rows:
        batch_n = min(BATCH_SIZE, total_rows - len(rows))
        generated = call_claude_for_rows(client, spec["prompt"], batch_n)

        for item in generated:
            row = {"id": next_id}
            next_id += 1

            if spec["table"] == "users":
                row["organization_id"] = random.choice(fk_pool["organizations"])
            elif spec["table"] == "orders":
                row["user_id"] = random.choice(fk_pool["users"])
            elif spec["table"] == "order_items":
                row["order_id"] = random.choice(fk_pool["orders"])

            row.update(item)
            rows.append(row)

    return spec["table"], rows


def write_and_upload_csv(bucket_name: str, table: str, columns: list[str], rows: list[dict]) -> None:
    local_path = f"/tmp/{table}.csv"
    with open(local_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in columns})

    client = storage.Client()
    client.bucket(bucket_name).blob(f"{table}.csv").upload_from_filename(local_path)
    print(f"Uploaded {table}.csv ({len(rows)} rows) -> gs://{bucket_name}/{table}.csv")


def main() -> None:
    bucket_name = os.environ["DEST_BUCKET"]
    rows_per_table = json.loads(os.environ["ROWS_PER_TABLE_JSON"])

    client = Anthropic()  # reads ANTHROPIC_API_KEY from env automatically
    fk_pool: dict[str, list[int]] = {}

    for spec in TABLE_SPECS:
        table = spec["table"]
        total = rows_per_table[table]
        print(f"--- Generating {total} rows for {table} ---")

        _, rows = generate_table(client, spec, total, fk_pool)
        fk_pool[table] = [row["id"] for row in rows]

        write_and_upload_csv(bucket_name, table, spec["columns"], rows)

    print("Synthetic dataset generation complete.")


if __name__ == "__main__":
    main()
```

> **Why IDs and foreign keys are assigned in Python, not by the model:** LLMs are good at generating realistic
> *content* (names, emails, statuses) but unreliable at maintaining exact referential arithmetic across separate
> API calls. The script asks Claude only for the content columns, then assigns sequential IDs and samples real
> parent IDs itself — this is what guarantees referential integrity by construction rather than by hoping the
> model got it right.

### 2.4 GitHub Actions workflow

Identical structure to the main guide, with the scrubber-job step replaced:

```yaml
      - name: Execute Synthetic Data Generator Job
        run: |
          gcloud run jobs execute "${{ env.SYNTH_JOB }}" \
            --region "${{ env.REGION }}" \
            --wait
```

(`SYNTH_JOB` comes from a new Terraform output `scrubber_job_name` → rename to `synth_job_name` pointing at
`google_cloud_run_v2_job.synth_generator.name`.) Everything after that — schema DDL, disable triggers, parallel
`gcloud sql import`, re-enable triggers, fix sequences, verify counts, teardown — is unchanged from the main guide.

### 2.5 Step-by-step
1. Create the Anthropic API key secret once: `gcloud secrets create anthropic-api-key --data-file=-` (paste the
   key, then Ctrl-D).
2. Set `rows_per_table` in `terraform/variables.tf` to whatever volume you need — keep child-table counts
   proportionate (e.g. ~10x users per organization, ~4x orders per user) so the data looks realistic rather than
   uniformly random.
3. Build and push the `synth-generator` image the same way as the scrubber image in the main guide's workflow.
4. Trigger the workflow. Watch the Cloud Run Job logs (`gcloud run jobs executions logs`) — each table's
   generation prints its own progress since it runs in `BATCH_SIZE` chunks.
5. Everything downstream is identical to the main guide's import/verify/teardown steps.

### 2.6 Troubleshooting specific to this scenario
| Symptom | Cause | Fix |
|---|---|---|
| `json.decoder.JSONDecodeError` parsing the model's response | Model wrapped the array in prose or markdown fences despite instructions | The script already strips ```` ```json ```` fences; if it still fails, lower `BATCH_SIZE` — smaller responses are more reliably clean JSON |
| Generated emails/names look repetitive across batches | Each API call has no memory of prior batches | Acceptable for most synthetic-data purposes; if you need stronger diversity, pass a short sample of already-generated values into the next batch's prompt as "don't repeat these" context |
| Cost adds up on very large row counts | One API call per `BATCH_SIZE` rows | Raise `BATCH_SIZE` (fewer calls, larger responses) or drop to a cheaper/faster model — `claude-haiku-4-5` is already the cost-optimized choice here |
| Skewed FK distribution (a few parents get most children) | `random.choice` is uniform but small `fk_pool` sizes amplify variance | Increase parent-table row counts, or weight sampling (e.g. `random.choices` with weights) if you need a specific distribution shape |

---

## Choosing Between All Four Scenarios

| Scenario | Use when | Source of truth for data |
|---|---|---|
| Live source DB (main guide) | Real migration/replatforming, need exact production data | Source Cloud SQL instance |
| Pre-staged files (this doc, §1) | Another team already owns extraction; you only load | Source team's GCS bucket |
| Synthetic data (this doc, §2) | Load testing, demos, staging environments — no real data allowed/needed | Claude API, generated fresh each run |
