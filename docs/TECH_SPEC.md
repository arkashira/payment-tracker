# TECH_SPEC.md  

## Project Overview  
**Name:** payment‑tracker  
**Domain:** FinTech – Payment processing & transaction monitoring  
**Purpose:** Provide financial service companies and payment processors with real‑time visibility into payment lifecycles, automated anomaly detection, and issue resolution workflows. The platform ingests transaction events from multiple sources, normalises them, stores a unified view, and exposes APIs & dashboards for status tracking, alerts, and remediation actions.  

---

## 1. Architecture Overview  

```
+-------------------+        +-------------------+        +-------------------+
|   Ingestion Layer | --->   |   Processing Core | --->   |   Persistence Layer|
| (Kafka / HTTP)    |        | (vLLM, SGLang)    |        | (PostgreSQL, Click|
+-------------------+        +-------------------+        | house)            |
        |                         |                         |
        |                         v                         v
        |                +-------------------+   +-------------------+
        |                |   Real‑time API   |   |   Batch Analytics |
        |                |   (FastAPI)      |   |   (Spark)         |
        |                +-------------------+   +-------------------+
        |                         |                         |
        v                         v                         v
+-------------------+   +-------------------+   +-------------------+
|   Dashboard UI   |   |   Alert Service   |   |   Admin Console   |
|   (React + MUI)   |   |   (Celery +      |   |   (NestJS)        |
+-------------------+   |    Redis)        |   +-------------------+
```

* **Ingestion Layer** – High‑throughput event capture via Kafka topics and optional HTTP webhook endpoints.  
* **Processing Core** – Stateless micro‑services written in Python, leveraging **vLLM** for fast inference on transaction‑status classification and **SGLang** for structured generation of remediation steps.  
* **Persistence Layer** –  
  * **PostgreSQL** (transaction master data, audit logs).  
  * **ClickHouse** (time‑series storage for high‑velocity event queries).  
* **Real‑time API** – FastAPI service exposing REST & WebSocket endpoints for status queries and streaming updates.  
* **Batch Analytics** – Spark jobs (PySpark) for daily/weekly KPI reports, fraud pattern mining.  
* **Alert Service** – Celery workers with Redis broker, dispatching email/SMS/push alerts based on rule engine outcomes.  
* **Dashboard UI** – React + Material‑UI single‑page app, authenticates via OAuth2 (Keycloak).  
* **Admin Console** – NestJS backend for managing routing rules, user permissions, and integration configs.  

All services are containerised (Docker) and orchestrated via **Kubernetes** (Helm charts).  

---

## 2. Component Details  

### 2.1 Ingestion Layer  
| Sub‑component | Tech | Responsibilities |
|---------------|------|------------------|
| Kafka Cluster | Apache Kafka 3.3 | Scalable, ordered event streaming (topics: `payments.raw`, `payments.status`) |
| HTTP Webhook Receiver | FastAPI (uvicorn) | Accepts POSTs from partner gateways, validates signatures, pushes to Kafka |
| Schema Registry | Confluent Schema Registry | Enforces Avro schemas for payment events |

### 2.2 Processing Core  
| Service | Language | Key Libraries | Function |
|---------|----------|---------------|----------|
| Status Classifier | Python 3.11 | vLLM, scikit‑learn, pandas | Classifies raw events into `AUTHORIZED`, `SETTLED`, `FAILED`, `CHARGEBACK` |
| Remediation Generator | Python 3.11 | SGLang, Jinja2 | Generates step‑by‑step resolution scripts for failures |
| Enrichment Worker | Python 3.11 | requests, pycountry | Adds merchant, risk‑score, geo‑info |

All workers are stateless, consume from Kafka, and produce enriched events to `payments.enriched`.  

### 2.3 Persistence Layer  
* **PostgreSQL** (v15) – Primary relational store. Tables: `payments`, `merchants`, `alerts`, `audit_log`.  
* **ClickHouse** (v23) – Columnar store for time‑series queries. Materialised view syncs from PostgreSQL via Debezium connector.  

### 2.4 Real‑time API  
* **Framework:** FastAPI (async)  
* **Endpoints:**  
  * `GET /payments/{id}` – fetch latest status (cached in Redis).  
  * `GET /payments?merchant_id=&status=` – filtered list (ClickHouse).  
  * `WS /payments/stream` – server‑sent events for live updates.  
* **Auth:** OAuth2 Bearer tokens (Keycloak).  
* **Rate limiting:** 100 req/s per client (Redis‑based token bucket).  

### 2.5 Dashboard UI  
* **Stack:** React 18, TypeScript, Material‑UI, Recharts.  
* **Features:**  
  * Real‑time payment flow visualisation.  
  * Alert inbox with bulk actions.  
  * KPI widgets (TPS, success rate, avg settlement time).  

### 2.6 Alert Service  
* **Task Queue:** Celery 5 + Redis 7.  
* **Rules Engine:** JSON‑based rule definitions stored in PostgreSQL; evaluated on each enriched event.  
* **Channels:** SMTP, Twilio SMS, Firebase Cloud Messaging.  

### 2.7 Admin Console  
* **Backend:** NestJS (Node 20) with TypeORM.  
* **Functions:**  
  * Manage partner integrations (webhook URLs, secret keys).  
  * CRUD for merchants, risk profiles.  
  * View system health metrics (Prometheus + Grafana).  

---

## 3. Data Model  

### 3.1 Core Entities (PostgreSQL)

```sql
CREATE TABLE merchants (
    id            UUID PRIMARY KEY,
    name          TEXT NOT NULL,
    country_code  CHAR(2) NOT NULL,
    risk_score    SMALLINT DEFAULT 0,
    created_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE payments (
    id                UUID PRIMARY KEY,
    merchant_id       UUID REFERENCES merchants(id),
    amount_cents      BIGINT NOT NULL,
    currency          CHAR(3) NOT NULL,
    status            VARCHAR(20) NOT NULL,
    created_at        TIMESTAMPTZ NOT NULL,
    updated_at        TIMESTAMPTZ NOT NULL,
    raw_event         JSONB,
    enriched_event    JSONB,
    settlement_ts     TIMESTAMPTZ,
    failure_reason    TEXT
);

CREATE TABLE alerts (
    id                BIGSERIAL PRIMARY KEY,
    payment_id        UUID REFERENCES payments(id),
    rule_id           UUID,
    channel           VARCHAR(20),
    payload           JSONB,
    sent_at           TIMESTAMPTZ,
    status            VARCHAR(20) DEFAULT 'PENDING'
);
```

### 3.2 ClickHouse Table (Time‑Series)

```sql
CREATE TABLE payments_events (
    event_time   DateTime64(3, 'UTC'),
    payment_id   UUID,
    status       LowCardinality(String),
    amount_cents UInt64,
    merchant_id  UUID
) ENGINE = MergeTree()
ORDER BY (event_time, payment_id);
```

---

## 4. Key APIs & Interfaces  

| Interface | Protocol | Endpoint | Request | Response | Notes |
|-----------|----------|----------|---------|----------|-------|
| Ingest Webhook | HTTPS/JSON | `POST /webhook/payments` | `{event_id, payload, signature}` | `202 Accepted` | Validates HMAC‑SHA256 signature |
| Status Query | REST | `GET /payments/{id}` | – | `{id, status, amount, timestamps, remediation}` | Cached (5 s) |
| Stream Updates | WebSocket | `ws://api/payments/stream?token=` | – | `{payment_id, status, ts}` | Subscribes to merchant‑scoped topics |
| Alert Rule CRUD | REST | `POST /admin/rules` | `{rule_json}` | `201 Created` | Admin only |
| KPI Report | REST | `GET /reports/daily?date=` | – | CSV/JSON | Uses Spark job output stored in S3 |

---

## 5. Technology Stack  

| Layer | Technology | Version | Rationale |
|-------|------------|---------|-----------|
| Language | Python | 3.11 | Mature ML ecosystem, async support |
| Inference Engine | vLLM | latest | Low‑latency LLM inference for classification |
| Structured Generation | SGLang | latest | Guarantees JSON‑compatible remediation scripts |
| API Framework | FastAPI | 0.110 | High performance, OpenAPI auto‑gen |
| Message Bus | Apache Kafka | 3.3 | Horizontal scalability, durability |
| DB (OLTP) | PostgreSQL | 15 | Strong ACID guarantees |
| DB (OLAP) | ClickHouse | 23 | Fast analytical queries on high‑volume data |
| Task Queue | Celery + Redis | 5 / 7 | Simple, reliable background processing |
| Front‑end | React + TypeScript + MUI | 18 / 5.x / 5.x | Modern UI, component library |
| Admin Backend | NestJS | 10 | Structured, decorator‑driven API |
| Containerisation | Docker | 24.0 | Consistent dev/prod environments |
| Orchestration | Kubernetes + Helm | 1.28 / 3.12 | Declarative deployment, auto‑scaling |
| Monitoring | Prometheus + Grafana | 2.50 / 10 | Metrics & dashboards |
| Auth | Keycloak (OpenID Connect) | 23 | Centralised identity & RBAC |
| CI/CD | GitHub Actions + ArgoCD | – | Automated testing & progressive delivery |

---

## 6. Dependencies  

- **vLLM** – `vllm-project/vllm` (GitHub) – compiled with CUDA 12.2 for GPU inference.  
- **SGLang** – `sgl-project/sglang` – used for deterministic JSON output.  
- **Confluent Schema Registry** – enforces Avro schemas.  
- **Debezium** – CDC connector from PostgreSQL → ClickHouse.  
- **Twilio SDK**, **Firebase Admin SDK** – alert channels.  

All third‑party libraries are listed in `requirements.txt` (Python) and `package.json` (Node).  

---

## 7. Deployment & Operations  

### 7.1 Helm Chart Structure  

```
payment-tracker/
├─ charts/
│  ├─ kafka/
│  ├─ postgresql/
│  ├─ clickhouse/
│  ├─ redis/
│  ├─ ingestion/
│  ├─ processing/
│  ├─ api/
│  ├─ dashboard/
│  └─ admin/
└─ values.yaml
```

* Each sub‑chart defines `resources.limits/requests`, `autoscaling`, and `serviceAccount` with least‑privilege RBAC.  

### 7.2 CI/CD Pipeline  

1. **PR Validation** – Unit tests (pytest), lint (ruff, eslint), contract tests (pact).  
2. **Build** – Multi‑arch Docker images, pushed to `registry.axentx.io/payment-tracker`.  
3. **Staging Deploy** – ArgoCD sync to `staging` namespace, run integration tests against a synthetic event generator.  
4. **Canary Promotion** – 10 % traffic to new version, monitor latency & error rate via Prometheus alerts.  
5. **Production Rollout** – Gradual rollout to 100 % after health gates pass.  

### 7.3 Scaling Guidelines  

| Component | Scaling Trigger | Recommended Config |
|-----------|----------------|--------------------|
| Kafka Brokers | > 5 GB/s inbound | Add broker, rebalance partitions |
| vLLM Workers | > 200 ms inference latency | Add GPU node (A100 40 GB) |
| API Pods | > 80 % CPU avg (5 min) | HorizontalPodAutoscaler (min 2, max 12) |
| ClickHouse | > 1 TB daily inserts | Add shard, enable distributed tables |
| Celery Workers | Queue lag > 30 s | Increase replica count |

### 7.4 Observability  

- **Metrics:** Prometheus exporters for Kafka, PostgreSQL, ClickHouse, FastAPI, Celery.  
- **Logs:** Structured JSON logs shipped to Loki; correlation via `trace_id`.  
- **Tracing:** OpenTelemetry (Jaeger) across all services.  
- **Alerting:** SLA breach (> 99.5 % success rate) triggers PagerDuty incident.  

---

## 8. Security Considerations  

| Area | Controls |
|------|----------|
| Data in transit | TLS 1.3 everywhere (Ingress, Kafka, DB connections) |
| Data at rest | PostgreSQL & ClickHouse encrypted with AES‑256; S3 bucket with SSE‑KMS |
| AuthN/Z | OAuth2/OIDC via Keycloak; role‑based access (viewer, operator, admin) |
| Webhook verification | HMAC‑SHA256 signature with per‑partner secret |
| Secret management | HashiCorp Vault; injected as Kubernetes secrets |
| Auditing | Immutable audit_log table; write‑once S3 archive for 2 years |
| Compliance | PCI‑DSS v4.0 scope‑reduction via tokenisation of PAN (stored only as last‑4) |

---

## 9. Risks & Mitigations  

| Risk | Impact | Mitigation |
|------|--------|------------|
| Model drift in status classifier | Mis‑classification → false alerts | Continuous monitoring of classification confidence; weekly retraining using new labeled data from `auto` dataset |
| Kafka topic backlog | Event loss or latency | Enable tiered storage; autoscale consumer groups |
| Regulatory changes (e.g., PSD2) | Non‑compliance penalties | Modular rule engine; rapid rule updates via admin console |
| Dependency vulnerability (vLLM) | Service disruption | Dependabot alerts; CI step that runs `safety check` on Python deps |

---

## 10. Release Plan  

| Milestone | Scope | Acceptance Criteria |
|-----------|-------|----------------------|
| **MVP (v0.1)** | Ingestion → Classification → Real‑time API + Dashboard (basic view) | Process ≥ 100 k events/day, 99 % API uptime, UI shows live status |
| **Beta (v0.3)** | Add remediation generator, alert service, admin console | Automated remediation steps generated for ≥ 90 % failures, alerts delivered within 30 s |
| **GA (v1.0)** | Full analytics pipeline, SLA reporting, multi‑region deployment | 99.9 % availability, latency < 200 ms for status query, compliance audit passed |
| **Post‑GA (v1.1+)** | Plug‑in SDK for partners, AI‑enhanced fraud scoring | SDK available in Java, Go, Node; fraud model improves detection recall by 15 % |

---

*Prepared by:* Senior Product/Engineering Lead – Axentx  
*Date:* 2026‑06‑17
