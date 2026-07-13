# Ephemeral DataStore Subsystem — Implementation & Test Guide

**Scope:** Database provisioning and data seeding for PR-based ephemeral environments.
**Engines (pilot):** PostgreSQL (in-cluster), MySQL (in-cluster), Oracle (on-prem, PDB clone).
**Consumers:** Java (Spring Boot) and Python (Django/FastAPI) web applications.
**Boundary:** The environment platform (owned by the other team) creates PR namespaces, deploys apps via Argo CD ApplicationSets, runs tests, and tears environments down. This subsystem owns everything between "give me a seeded database for PR 123" and "it's gone."

---

## 1. Architecture summary

The subsystem has four components:

1. **`EphemeralDataStore` CRD** — the contract. The environment platform includes one CR per required database in each PR's manifests. It is the only interface the other team needs to know.
2. **DataStore operator** — a Kubernetes operator (Python / Kopf) that reconciles the CRs: clones from a golden source, creates scoped credentials, writes a uniform connection Secret, reports readiness through status conditions, and cleans up via finalizers.
3. **Golden data pipeline** — scheduled jobs that produce immutable, versioned, sanitized data sets ("golden sources") per application per engine.
4. **Reaper** — a nightly CronJob that cross-checks every backend (Postgres golden host, MySQL resources, Oracle CDB) against open PRs and destroys orphans past TTL.

Data flow per PR:

```
PR opened
  └─ env platform creates namespace pr-123 + EphemeralDataStore CR(s)
       └─ operator: clone from golden source (engine-specific)
            └─ create scoped user + password
                 └─ write Secret (uniform keys) into pr-123
                      └─ status.conditions Ready=True
                           └─ env platform runs migrations, deploys app, runs tests
PR closed
  └─ env platform deletes namespace/CR
       └─ operator finalizer drops database / PDB / pod, deletes Secret
            └─ (nightly) reaper verifies nothing leaked
```

### Engine strategy

| Engine | Location | Per-PR mechanism | Expected provision time | Teardown |
|---|---|---|---|---|
| PostgreSQL | Shared "golden host" in cluster (CloudNativePG) | `CREATE DATABASE ... TEMPLATE golden_x` | < 5 s (small sets), < 30 s (few GB) | `DROP DATABASE`, drop role |
| PostgreSQL (dedicated profile) | Per-PR CloudNativePG cluster | Bootstrap from golden base backup | 45–90 s | Delete CNPG Cluster CR |
| MySQL v1 | Per-PR single mysqld pod | Logical restore (`mydumper`/`myloader`) from object storage | 1–5 min per GB | Delete pod + PVC |
| MySQL v2 (optimization) | Per-PR pod from VolumeSnapshot | CSI snapshot of golden PVC | 10–30 s | Delete pod + PVC |
| Oracle | Shared on-prem CDB (19c+) | `CREATE PLUGGABLE DATABASE pr_x FROM golden_x SNAPSHOT COPY` | Seconds (snapshot-capable storage) / minutes-per-GB (full copy) | `DROP PLUGGABLE DATABASE ... INCLUDING DATAFILES` |

---

## 2. Prerequisites

### 2.1 Cluster prerequisites

The preview Kubernetes cluster (provided by the environment team) must have: CloudNativePG operator installed (`cnpg-system` namespace); a default StorageClass with `VolumeSnapshot` support if pursuing MySQL v2; External Secrets Operator or direct Secret creation RBAC for this operator; network reachability to the on-prem Oracle CDB listener (validate with a `telnet <cdb-host> 1521` from a debug pod before writing any Oracle code); and a platform namespace `datastore-system` where the operator, golden Postgres host, and reaper run.

### 2.2 Oracle / DBA prerequisites (start this conversation first — longest lead time)

Obtain from the DBA team, in writing:

1. A CDB (19c or later) designated for preview use, with confirmation of whether datafiles reside on snapshot-capable storage (ACFS, ZFS, or supporting ASM/array). This determines whether `SNAPSHOT COPY` is available; the operator supports both paths but timings differ by an order of magnitude.
2. A provisioning account with exactly these privileges (not SYSDBA): `CREATE PLUGGABLE DATABASE`, `DROP PLUGGABLE DATABASE`, `ALTER PLUGGABLE DATABASE`, `SELECT` on `v$pdbs` and `cdb_pdbs`, and the ability to connect to newly created PDBs to run user-creation DDL (common pattern: a common user `C##PREVIEW_PROV` with `CONTAINER=ALL` grants).
3. Agreement on a concurrent-PDB quota (recommendation: 20) and on the naming convention `PR_<number>_<app>` so DBAs can identify preview PDBs at a glance.
4. `FILE_NAME_CONVERT` / `CREATE_FILE_DEST` target paths for clone datafiles.
5. Sign-off that the golden PDB refresh window (nightly, see §5) is acceptable on that CDB.

### 2.3 Compliance prerequisite

Written approval of the masking rule set (§5.2) from security/compliance before any production-derived data lands in a golden source. This is a hard gate; schedule the review in week 1.

### 2.4 Tooling

Operator development: Python 3.11+, `kopf`, `kubernetes` client, `psycopg[binary]`, `PyMySQL`, `oracledb` (thin mode — no Oracle client install needed). Golden pipeline: Greenmask (Postgres), `mydumper`/`myloader` (MySQL), Oracle Data Pump (`expdp`/`impdp`) executed on the DB host by DBA-approved jobs. Testing: `kind`, `pytest`, `pytest-kubernetes` or plain client fixtures, Testcontainers (Java side reference tests).

---

## 3. Component 1 — the `EphemeralDataStore` CRD

This is the contract with the environment team. Treat it as an API: version it, never break v1.

```yaml
# crd/ephemeraldatastore.yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: ephemeraldatastores.data.yourco.com
spec:
  group: data.yourco.com
  scope: Namespaced
  names:
    kind: EphemeralDataStore
    plural: ephemeraldatastores
    singular: ephemeraldatastore
    shortNames: [eds]
  versions:
    - name: v1
      served: true
      storage: true
      subresources:
        status: {}
      additionalPrinterColumns:
        - name: Engine
          type: string
          jsonPath: .spec.engine
        - name: Ready
          type: string
          jsonPath: .status.conditions[?(@.type=="Ready")].status
        - name: Golden
          type: string
          jsonPath: .spec.goldenSource
      schema:
        openAPIV3Schema:
          type: object
          required: [spec]
          properties:
            spec:
              type: object
              required: [engine, goldenSource]
              properties:
                engine:
                  type: string
                  enum: [postgres, mysql, oracle]
                goldenSource:
                  type: string
                  description: "<app>/<version>, e.g. orders/v42. 'latest' resolves at creation and is pinned."
                sizeProfile:
                  type: string
                  enum: [shared, small, medium]
                  default: shared
                ttl:
                  type: string
                  default: "72h"
                secretName:
                  type: string
                  description: "Name of the connection Secret to create. Defaults to <cr-name>-conn."
            status:
              type: object
              properties:
                phase:
                  type: string
                observedGoldenVersion:
                  type: string
                backendRef:
                  type: string
                  description: "Engine-native identifier: database name, PDB name, or pod name. Used by the reaper."
                secretRef:
                  type: string
                conditions:
                  type: array
                  items:
                    type: object
                    properties:
                      type: { type: string }
                      status: { type: string }
                      reason: { type: string }
                      message: { type: string }
                      lastTransitionTime: { type: string }
```

### 3.1 The connection Secret contract

For every Ready CR, the operator writes a Secret in the CR's namespace with exactly these keys — never engine-specific variations. App Helm charts template env vars only from these:

```
host, port, database, username, password,
jdbcUrl   # jdbc:postgresql://..., jdbc:mysql://..., jdbc:oracle:thin:@//host:port/service
uri       # postgresql://..., mysql://..., oracle://...  (SQLAlchemy-compatible where applicable)
```

For Oracle, `database` carries the PDB service name. Document for Java teams that `jdbcUrl` is authoritative; for Python teams, `uri`.

### 3.2 Semantics agreed with the environment platform

Readiness gating: the platform must not start migrations or tests until the `Ready` condition is `True`. Provide them an Argo CD custom health check (see §7.1). Failure surfacing: on any terminal failure the operator sets `Ready=False` with `reason` and a human-readable `message`; the platform pipes `message` into the PR comment verbatim. Deletion: deleting the CR (directly or via namespace deletion) always cleans the backend — guaranteed by the finalizer `data.yourco.com/cleanup`. Version resolution: `goldenSource: orders/latest` is resolved to a concrete version at first reconcile and written to `status.observedGoldenVersion`; it never re-resolves, so a PR's data does not change under it when a new golden publishes.

---

## 4. Component 2 — the DataStore operator

Python + Kopf keeps the code approachable for your Python app teams and avoids a Go toolchain. One deployment in `datastore-system`, leader-elected, watching `EphemeralDataStore` cluster-wide.

### 4.1 Project layout

```
datastore-operator/
├── operator/
│   ├── main.py              # kopf handlers, finalizer wiring
│   ├── engines/
│   │   ├── base.py          # Engine interface: provision() / verify() / destroy()
│   │   ├── postgres.py
│   │   ├── mysql.py
│   │   └── oracle.py
│   ├── golden.py            # golden-source registry lookup (ConfigMap-backed)
│   ├── secrets.py           # uniform Secret builder
│   └── conditions.py        # status condition helpers
├── tests/
│   ├── unit/
│   └── integration/
├── deploy/                  # RBAC, Deployment, CRD
└── Dockerfile
```

### 4.2 Core handler (main.py)

```python
import kopf, logging
from operator.engines import get_engine
from operator import secrets, conditions, golden

FINALIZER = "data.yourco.com/cleanup"

@kopf.on.create("data.yourco.com", "v1", "ephemeraldatastores")
@kopf.on.resume("data.yourco.com", "v1", "ephemeraldatastores")
def provision(spec, meta, status, patch, namespace, name, **_):
    pr_id = namespace.removeprefix("pr-")          # naming convention from env platform
    engine = get_engine(spec["engine"])

    # 1. Resolve and pin the golden version (idempotent).
    version = status.get("observedGoldenVersion") or golden.resolve(spec["goldenSource"])
    patch.status["observedGoldenVersion"] = version
    patch.status["phase"] = "Provisioning"

    # 2. Engine-specific clone. Must be idempotent: re-running after a crash
    #    detects an existing backend and continues.
    backend = engine.provision(pr_id=pr_id, app=name, golden=version,
                               profile=spec.get("sizeProfile", "shared"))
    patch.status["backendRef"] = backend.ref

    # 3. Scoped credentials + uniform Secret.
    creds = engine.create_scoped_user(backend, pr_id)
    secret_name = spec.get("secretName", f"{name}-conn")
    secrets.write(namespace, secret_name, engine.connection_info(backend, creds))
    patch.status["secretRef"] = secret_name

    # 4. Verify: connect with the new creds, run engine smoke query,
    #    check sentinel row from the golden set (see §5.4).
    engine.verify(backend, creds)

    patch.status["phase"] = "Ready"
    conditions.set_ready(patch, True, reason="Provisioned",
                         message=f"{spec['engine']} ready from {version}")

@kopf.on.delete("data.yourco.com", "v1", "ephemeraldatastores")
def destroy(spec, status, namespace, name, **_):
    """Finalizer-backed. Kopf blocks CR deletion until this returns."""
    backend_ref = status.get("backendRef")
    if not backend_ref:
        return                                     # never provisioned; nothing to do
    engine = get_engine(spec["engine"])
    engine.destroy(backend_ref)                    # idempotent: absent backend is success

@kopf.on.timer("data.yourco.com", "v1", "ephemeraldatastores", interval=300)
def ttl_check(spec, meta, namespace, name, **_):
    """Belt-and-braces: delete the CR ourselves if past TTL."""
    from datetime import datetime, timedelta, timezone
    import re
    created = meta["creationTimestamp"]
    hours = int(re.match(r"(\d+)h", spec.get("ttl", "72h")).group(1))
    age = datetime.now(timezone.utc) - datetime.fromisoformat(created.replace("Z", "+00:00"))
    if age > timedelta(hours=hours):
        kopf.info(meta, reason="TTLExpired", message="Deleting datastore past TTL")
        _delete_cr(namespace, name)
```

Error handling policy: raise `kopf.TemporaryError(msg, delay=30)` for retryable faults (backend unreachable, quota momentarily exceeded) and `kopf.PermanentError` for terminal ones (unknown golden version, Oracle quota hard-exceeded, masking-version mismatch); on permanent errors also set `Ready=False` with the message before raising, so the PR comment shows the real cause.

### 4.3 Postgres engine (engines/postgres.py)

Backed by a shared CloudNativePG "golden host" cluster in `datastore-system` holding every golden version as a database (`golden_orders_v42`), plus PgBouncer in front for PR traffic.

```python
import psycopg
from .base import Engine, Backend

class PostgresEngine(Engine):
    def provision(self, pr_id, app, golden, profile):
        db = f"app_pr_{pr_id}_{app}".replace("-", "_")[:63]
        tmpl = f"golden_{golden.replace('/', '_v')}"      # orders/v42 -> golden_orders_v42
        with self._admin_conn() as conn:                  # autocommit=True
            if not self._db_exists(conn, db):
                # Template copy requires zero connections on the template DB.
                # Golden DBs carry: ALTER DATABASE ... ALLOW_CONNECTIONS false is NOT
                # used (template copy needs it connectable-by-superuser); instead we
                # enforce "no app connections" via pg_hba + a datallowconn check here.
                conn.execute(
                    psycopg.sql.SQL("CREATE DATABASE {} TEMPLATE {}").format(
                        psycopg.sql.Identifier(db), psycopg.sql.Identifier(tmpl)))
        return Backend(ref=db, host=self.pgbouncer_host, port=6432)

    def create_scoped_user(self, backend, pr_id):
        user, pwd = f"pr_{pr_id}_app", self._genpass()
        with self._admin_conn() as conn:
            conn.execute(f"CREATE ROLE {user} LOGIN PASSWORD %s CONNECTION LIMIT 20", (pwd,))
            conn.execute(f"GRANT ALL ON DATABASE {backend.ref} TO {user}")
            # Inside the new DB: grant on schema public + default privileges,
            # and GRANT the migration role if the app uses a separate one.
        return {"username": user, "password": pwd}

    def destroy(self, backend_ref):
        with self._admin_conn() as conn:
            conn.execute(f"""SELECT pg_terminate_backend(pid) FROM pg_stat_activity
                             WHERE datname = %s""", (backend_ref,))
            conn.execute(psycopg.sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)")
                         .format(psycopg.sql.Identifier(backend_ref)))
            conn.execute(f"DROP ROLE IF EXISTS pr_{self._pr_from_ref(backend_ref)}_app")
```

Sizing the golden host: start with 4 vCPU / 16 GiB / fast storage; each template copy is I/O-bound. Set `max_connections` high enough for (open PRs × per-role limit) plus pipeline headroom, and let PgBouncer (transaction mode) absorb app-side pool exuberance from Spring/HikariCP defaults.

The `sizeProfile: small|medium` path creates a dedicated CNPG `Cluster` CR in the PR namespace bootstrapped from the golden's base backup (`bootstrap.recovery.source`), then proceeds identically from step 3. Implement it after the shared path works.

### 4.4 MySQL engine (engines/mysql.py) — v1 logical restore

v1 keeps moving parts minimal: a per-PR StatefulSet-less single pod (mysqld 8.0, `emptyDir` or small PVC) plus an init Job that runs `myloader` against the golden dump in object storage.

```python
class MySQLEngine(Engine):
    def provision(self, pr_id, app, golden, profile):
        pod = f"mysql-pr-{pr_id}-{app}"
        self._apply_manifest("mysql-pod.yaml.j2", pr_id=pr_id, app=app)   # pod + svc + secret(root)
        self._apply_manifest("mysql-seed-job.yaml.j2",                     # myloader from s3://golden/mysql/<app>/<ver>/
                             pr_id=pr_id, app=app, golden=golden)
        self._wait_for_job(f"{pod}-seed", timeout=600)
        return Backend(ref=pod, host=f"{pod}.pr-{pr_id}.svc", port=3306)

    def destroy(self, backend_ref):
        # Namespace deletion normally handles this; explicit path covers reaper use.
        self._delete_pod_svc_pvc(backend_ref)
```

v2 optimization (after pilot proves demand): nightly restore into a "golden PVC" per app, `VolumeSnapshot` it, and provision PR pods with `dataSource: {kind: VolumeSnapshot}` — drops seed time from minutes to ~15 s. The engine interface doesn't change; only `provision()` does.

### 4.5 Oracle engine (engines/oracle.py)

```python
import oracledb

class OracleEngine(Engine):
    MAX_PDBS = 20   # agreed quota; also enforced by reaper alerting

    def provision(self, pr_id, app, golden, profile):
        pdb = f"PR_{pr_id}_{app}".upper().replace("-", "_")[:30]
        gold_pdb = f"GOLDEN_{golden.split('/')[0]}_{golden.split('/')[1]}".upper()
        with self._cdb_conn() as conn:                    # C##PREVIEW_PROV, thin mode
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM v$pdbs WHERE name LIKE 'PR_%'")
            if cur.fetchone()[0] >= self.MAX_PDBS:
                raise kopf.PermanentError(
                    f"Oracle preview quota reached ({self.MAX_PDBS} PDBs). "
                    f"Close stale PRs or contact #platform-data.")
            if not self._pdb_exists(cur, pdb):
                clause = "SNAPSHOT COPY" if self.snapshot_capable else ""
                cur.execute(f"""CREATE PLUGGABLE DATABASE {pdb} FROM {gold_pdb}
                                {clause} CREATE_FILE_DEST = '{self.file_dest}'""")
            cur.execute(f"ALTER PLUGGABLE DATABASE {pdb} OPEN READ WRITE")
            cur.execute(f"ALTER PLUGGABLE DATABASE {pdb} SAVE STATE")
        return Backend(ref=pdb, host=self.cdb_host, port=1521, service=pdb.lower())

    def create_scoped_user(self, backend, pr_id):
        user, pwd = f"PR_{pr_id}_APP", self._genpass()
        with self._pdb_conn(backend.ref) as conn:         # provisioning user, container=pdb
            cur = conn.cursor()
            cur.execute(f'CREATE USER {user} IDENTIFIED BY "{pwd}"')
            cur.execute(f"GRANT CONNECT, RESOURCE TO {user}")
            cur.execute(f"ALTER USER {user} QUOTA UNLIMITED ON USERS")
            # Grant object privileges on the golden schema, or make the app
            # schema itself the login (decide with app team; document choice).
        return {"username": user, "password": pwd}

    def destroy(self, backend_ref):
        with self._cdb_conn() as conn:
            cur = conn.cursor()
            if self._pdb_exists(cur, backend_ref):
                cur.execute(f"ALTER PLUGGABLE DATABASE {backend_ref} CLOSE IMMEDIATE")
                cur.execute(f"DROP PLUGGABLE DATABASE {backend_ref} INCLUDING DATAFILES")
```

Two Oracle gotchas to encode as tests, not tribal knowledge: snapshot-copy child PDBs pin their golden source — the golden refresh job must check `v$pdbs` for children of the outgoing version and keep N-2 versions until childless; and `DROP ... INCLUDING DATAFILES` is mandatory (a plain drop leaks datafiles on the on-prem array, invisible to any cloud bill).

### 4.6 RBAC (deploy/rbac.yaml — minimum grants)

ClusterRole for the operator: full verbs on `ephemeraldatastores` and `ephemeraldatastores/status`; create/get/delete on `secrets`, `pods`, `services`, `jobs`, `persistentvolumeclaims` in PR namespaces; get/list on `namespaces`; create on `events`. Database admin credentials (Postgres superuser-lite, MySQL root template, Oracle provisioning user) live in `datastore-system` Secrets sourced from Vault via External Secrets — never in PR namespaces.

---

## 5. Component 3 — the golden data pipeline

One pipeline per application per engine, running nightly (or weekly where data churn is low), producing immutable versioned artifacts. Structure every pipeline as: extract → subset → mask → validate → publish.

### 5.1 Source rules

Extract only from a production replica or the latest verified backup — never the primary. For the pilot, a nightly restore of the prod backup into a scratch instance inside the pipeline's isolated namespace is the safest pattern and doubles as backup-restore verification.

### 5.2 Masking (the compliance gate)

Masking must be deterministic (same input → same fake output, so FK joins and test assertions remain stable across versions) and rule-complete (every column classified: pass-through, mask, or drop — new unclassified columns fail the pipeline rather than pass through silently).

Postgres — Greenmask config skeleton (`golden/orders/greenmask.yaml`):

```yaml
common:
  pg_dump_options: { dbname: "postgres://pipeline@scratch:5432/orders" }
transformers:
  - schema: public
    name: customers
    transformers:
      - name: Hash            # deterministic
        params: { column: email, salt: "{{ .Env.MASK_SALT }}", function: sha256 }
      - name: RandomPerson
        params: { columns: [{name: first_name}, {name: last_name}], engine: deterministic }
      - name: Replace
        params: { column: ssn, value: "000-00-0000" }
  - schema: public
    name: payments
    transformers:
      - name: Hash
        params: { column: card_token, salt: "{{ .Env.MASK_SALT }}" }
validate:
  resolved_warnings_only: true   # unclassified sensitive columns fail the run
```

MySQL: run masking as SQL UPDATE pass on the scratch restore before dumping with `mydumper` (deterministic UDF-style expressions: `email = CONCAT(SHA2(email, 256), '@example.test')`), or standardize on Greenmask's MySQL support if your version covers it. Oracle: masking runs on the scratch PDB before it becomes golden, via DBA-approved PL/SQL masking scripts or Oracle Data Masking Pack templates; keep the scripts in this repo under `golden/<app>/oracle/mask.sql` so rules are reviewable in Git.

### 5.3 Subsetting

Target hundreds of MB to low GB. Approach: select an anchor set (e.g. 5,000 recent customers spanning key segments), then walk the FK graph outward (orders → order_items → payments) with a tool (Jailer) or maintained SQL. Always include the edge-case rows QA depends on (unicode names, zero-amount orders, boundary dates) via a pinned inclusion list so functional tests are deterministic.

### 5.4 Validation and publishing

Before publishing a version, the pipeline must pass: row-count bands per table (±30% of previous version — catches broken subset queries); PII scan (regex + dictionary sweep for emails, SSNs, card patterns over a sample of every text column — any hit fails); migration check (apply the app's current migration head on a clone of the candidate — catches golden/schema drift); and sentinel insert — write a row `_golden_meta(version, captured_at, migration_baseline, mask_ruleset_sha)` that the operator's `verify()` step reads to confirm a PR clone really came from the pinned version.

Publishing: Postgres — `CREATE DATABASE golden_orders_v43` on the golden host from the pipeline output, then update the registry; MySQL — upload `mydumper` output to `s3://golden/mysql/orders/v43/`; Oracle — Data Pump import into `GOLDEN_ORDERS_V43` PDB, open read-only. Registry: a ConfigMap `golden-registry` in `datastore-system` mapping `orders/latest -> v43` plus per-version metadata (migration baseline, size, publish date). The operator reads only this registry; pipelines only append to it. Keep versions N, N-1, N-2; the retirement job refuses to drop a version with live children (Postgres template has no children issue; Oracle check per §4.5).

---

## 6. Component 4 — the reaper

A nightly CronJob in `datastore-system`, engine-aware, whose job is to make leaks impossible rather than unlikely:

```
for each backend:
  postgres: SELECT datname FROM pg_database WHERE datname LIKE 'app_pr_%'
  mysql:    list pods/PVCs/VolumeSnapshots labeled app.kubernetes.io/part-of=ephemeral-datastore
  oracle:   SELECT name FROM v$pdbs WHERE name LIKE 'PR_%'
cross-reference:
  extract PR number from each name
  query Git provider API: is the PR still open?
  does a live EphemeralDataStore CR reference this backendRef?
act:
  orphaned (PR closed, or no CR, or age > TTL + 24h grace) -> destroy via engine.destroy()
  emit metrics: datastore_reaper_orphans_found_total{engine}, ..._destroyed_total{engine}
  page (not just log) if orphans_found > 0 two nights running — that means finalizers are broken
```

Run the reaper with `--dry-run` for its first two weeks in any environment and review its would-destroy list manually before arming it.

---

## 7. Integration with the environment platform

### 7.1 Argo CD health check for the CRD

Hand this Lua snippet to the environment team for their Argo CD ConfigMap so their sync waits on your readiness:

```lua
-- resource.customizations.health.data.yourco.com_EphemeralDataStore
hs = {}
if obj.status ~= nil and obj.status.conditions ~= nil then
  for _, c in ipairs(obj.status.conditions) do
    if c.type == "Ready" and c.status == "True" then
      hs.status = "Healthy"; hs.message = c.message; return hs
    end
    if c.type == "Ready" and c.status == "False" and c.reason ~= "Provisioning" then
      hs.status = "Degraded"; hs.message = c.message; return hs
    end
  end
end
hs.status = "Progressing"; hs.message = "Waiting for datastore"
return hs
```

### 7.2 Ordering with app deployment

Recommended sync-wave layout inside each PR's Argo Application: wave 0 — `EphemeralDataStore` CRs; wave 1 — migration Job (Flyway/Liquibase/Alembic) reading the connection Secret; wave 2 — the app Deployment. With the health check above, Argo won't advance to wave 1 until your Secret exists and `Ready=True`, which eliminates the classic "app booted before DB" flake.

### 7.3 What app teams add to their Helm values

```yaml
dataStores:
  - name: orders-db
    engine: postgres
    goldenSource: orders/latest
  - name: legacy-billing
    engine: oracle
    goldenSource: billing/latest
```

Their chart templates one `EphemeralDataStore` per entry and wires `envFrom.secretRef: <name>-conn` (or explicit env mappings to `jdbcUrl` / `uri`) into containers. Java note for the onboarding doc: Spring Boot reads `SPRING_DATASOURCE_URL` from `jdbcUrl`; set HikariCP `maximum-pool-size: 5` in the preview profile so twenty PR environments don't exhaust shared-host connections. Python note: SQLAlchemy/Django read `uri` (Django needs a small `dj-database-url` mapping).

---

## 8. Test plan

### 8.1 Unit tests (repo: `tests/unit/`, run on every commit)

Pure-Python, no cluster, engines mocked at the connection layer. Cover: golden version resolution and pinning (latest resolves once, never re-resolves); name generation (PR 123 + app `orders-api` → valid Postgres identifier ≤63 chars, valid Oracle PDB name ≤30 chars, hyphen handling); Secret builder emits exactly the seven contract keys for each engine with correct `jdbcUrl`/`uri` shapes; condition transitions (Provisioning → Ready, Provisioning → Failed with message); TTL parser; quota logic (Oracle provision raises PermanentError at MAX_PDBS with the agreed message text); idempotency guards (provision called twice returns same backendRef without a second CREATE).

### 8.2 Integration tests (repo: `tests/integration/`, run on PRs to this repo, ~10 min)

Environment: `kind` cluster in CI with CloudNativePG installed; a golden host CNPG cluster seeded with a tiny fixture golden (`golden_testapp_v1`, ~50 rows + sentinel row); a mysqld container as the "object storage restore" target with a fixture dump; Oracle covered separately (§8.4).

| # | Scenario | Assert |
|---|---|---|
| I1 | Create Postgres CR | Ready≤60s; Secret has 7 keys; can `psql` with creds; sentinel row shows v1 |
| I2 | Create MySQL CR | Ready≤5min; seed Job succeeded; sentinel row present |
| I3 | Delete CR | Database dropped, role dropped, Secret gone, finalizer removed, CR gone |
| I4 | Delete namespace (not CR) | Same as I3 — cascade path works |
| I5 | Duplicate reconcile (kill operator pod mid-provision, restart) | Single database exists; CR reaches Ready; no orphan role |
| I6 | Unknown goldenSource | Ready=False, reason=GoldenNotFound, message names the bad version; no backend created |
| I7 | `latest` pinning | Publish testapp/v2 to registry after CR created; CR still reports v1; new CR gets v2 |
| I8 | TTL expiry (ttl: 1m fixture) | CR self-deletes; backend cleaned |
| I9 | Reaper dry-run | Manually create `app_pr_999_x` database; reaper reports it as orphan, destroys nothing in dry-run, destroys it when armed |
| I10 | Scoped-credential isolation | PR A's user cannot connect to PR B's database (pg_hba/GRANT check) |
| I11 | Secret contract regression | Golden-file test: rendered Secret matches checked-in expected YAML per engine |

### 8.3 End-to-end tests (staging preview cluster, with the environment team, weekly + before each rollout stage)

E2E-1 happy path: open a real PR on the pilot Python app → environment Ready → migrations applied on top of golden → functional suite green → close PR → within 2 min: namespace gone, `app_pr_*` database gone, role gone. E2E-2 Java app: same with the Spring Boot pilot app; additionally assert Hikari pool connects via `jdbcUrl` and app `/actuator/health` reports DB UP. E2E-3 update path: push a new commit with a new migration to an open PR → env resyncs → migration applies → data from golden still present (no re-seed wipe). E2E-4 concurrency: script opens 10 PRs within one minute → all Ready within SLO → golden host connection count within limits → close all → zero residue (run the reaper check as the assertion). E2E-5 failure surfacing: PR referencing a bogus goldenSource → PR comment contains the operator's failure message verbatim.

### 8.4 Oracle test approach

CI cannot host your on-prem CDB, so split coverage: logic-level — unit tests against a mocked `oracledb` cursor assert exact SQL emitted for snapshot vs full-copy paths, quota, open/save-state, and drop-including-datafiles; container-level — a nightly CI job against `gvenzl/oracle-free` (23ai Free supports PDB create/drop) runs the I-series scenarios for the Oracle engine, accepting that SNAPSHOT COPY behavior differs; real-CDB certification — a checklist executed manually with a DBA on the actual preview CDB before Oracle goes live, covering: clone timing measured (snapshot vs full), quota rejection at MAX_PDBS, drop leaves no datafiles (DBA verifies on storage), golden refresh blocked while children exist, provisioning user cannot escalate (negative test: attempt SYSDBA op, expect ORA-01031). Record measured timings in this document's appendix; they set the Ready-time SLO for Oracle-backed apps.

### 8.5 Golden pipeline tests

Run on every pipeline change and nightly with production runs: masking completeness — introduce a new column in a fixture schema without a rule → pipeline must fail; determinism — run masking twice on the same input → byte-identical output for masked columns; PII scan self-test — inject a known fake SSN into fixture input → scan must catch it (tests the scanner, not just the data); migration-baseline check — golden candidate + current app migration head applies cleanly; publish atomicity — registry only updates after all validations pass (kill pipeline mid-publish, registry must still point at previous version).

### 8.6 Chaos / failure drills (once before GA, then quarterly)

Kill the operator pod during each engine's provision and during a destroy — assert convergence and zero orphans. Make the Oracle listener unreachable mid-provision — assert TemporaryError retry loop, eventual Ready when restored, and a sane condition message meanwhile. Fill the Oracle quota with 20 synthetic PDBs — assert PR #21 fails fast with the quota message and existing environments are unaffected. Delete the golden registry ConfigMap — operator must fail safe (no provisioning) and page.

### 8.7 Acceptance criteria (pilot exit)

Postgres p95 time-to-Ready < 60 s (shared profile); MySQL v1 p95 < 6 min; Oracle p95 < 3 min on snapshot storage (or documented full-copy figure); orphaned backends after 30 days of pilot = 0 (reaper metric); zero PII findings across all published golden versions (scan reports archived); both pilot apps (Java + Python) pass their functional suites in PR environments for 2 consecutive weeks; environment team sign-off that the CRD contract required no changes on their side after week 2.

---

## 9. Observability

Export from the operator: `datastore_provision_duration_seconds{engine, profile}` (histogram — your headline SLO), `datastore_provision_failures_total{engine, reason}`, `datastore_active_total{engine}` (gauge — watch against Oracle quota), `datastore_teardown_duration_seconds{engine}`, `datastore_reaper_orphans_found_total{engine}` (alert at >0 twice consecutively), `golden_version_age_hours{app, engine}` (alert if a golden goes stale past its refresh cadence — masked data drifts from prod schema). Dashboards: one panel row per engine (provisioning latency, active count, failures), one row for the pipeline (last publish per app, validation failures), one for the reaper. Structured-log every backend-mutating statement (CREATE/DROP DATABASE, CREATE/DROP PLUGGABLE DATABASE, CREATE/DROP USER) with pr_id and CR UID — this is your audit trail when a DBA asks "what created PR_87_BILLING at 3 a.m."

## 10. Rollout plan

Week 1–2: CRD + operator skeleton + Postgres shared-template path; integration suite I1–I11 green on kind; start DBA (§2.2) and compliance (§2.3) conversations in parallel. Week 3: golden pipeline v1 for the Python pilot app (Greenmask, subset, validation, registry); E2E-1 with the environment team on staging; reaper in dry-run. Week 4: Java pilot app + MySQL v1 (logical restore); E2E-2/3; arm the reaper. Week 5–6: Oracle engine against `gvenzl/oracle-free` in CI, then real-CDB certification checklist with DBAs; golden PDB refresh job; E2E for the Oracle-backed app. Week 7: concurrency (E2E-4), chaos drills, acceptance metrics review; write the app-team onboarding one-pager (§7.3 plus Secret contract). Week 8: pilot GA — pilot teams switch on the `preview` label by default; begin measuring the §8.7 exit criteria over two weeks.

## 11. Runbook (seed with these; grow from incidents)

**PR environment stuck Progressing:** `kubectl -n pr-<n> get eds -o yaml` → read Ready condition message. GoldenNotFound → check registry ConfigMap; connection failures to Oracle → check VPN/DirectConnect path (`nc -vz <cdb> 1521` from debug pod). **Oracle quota exhausted:** `SELECT name, open_time FROM v$pdbs WHERE name LIKE 'PR_%' ORDER BY open_time` → cross-check PR states → run reaper ad hoc with `--engine oracle`. **Golden host connection saturation:** check PgBouncer stats; usual culprit is a Java app without the preview Hikari profile — cap via `ALTER ROLE ... CONNECTION LIMIT` as immediate mitigation. **Golden publish failed validation:** previous version still serves (registry untouched by design); inspect pipeline job logs; PII-scan hits page security per the agreed process — do not re-run with the rule relaxed. **Finalizer stuck, namespace Terminating:** almost always the backend is unreachable; fix connectivity, or as last resort verify backend manually destroyed, then remove the finalizer by patch — and file the bug, because the reaper existing is not a license for manual finalizer removal to become routine.

## 12. Appendix A — decisions to confirm before coding

Confirm with the environment team: namespace naming (`pr-<number>` assumed throughout), who templates the `EphemeralDataStore` CRs (their platform chart vs each app chart — recommend app chart per §7.3), and PR-comment plumbing for failure messages. Confirm with DBAs: everything in §2.2, plus the golden refresh window and Data Pump directory grants. Confirm with security: masking rule sets per app, `MASK_SALT` custody (Vault, rotated only with a full golden republish), and whether preview environments may hold masked-prod-derived data at all or must use synthetic data for specific apps (some regulated data classes force synthetic — decide per app now, not after go-live).

## 13. Appendix B — measured figures (fill during pilot)

| Metric | Postgres shared | MySQL v1 | Oracle snapshot | Oracle full-copy |
|---|---|---|---|---|
| Golden size (pilot app) | | | | |
| p50 provision time | | | | |
| p95 provision time | | | | |
| Teardown time | | | | |
| Cost / environment-day | | | | |
