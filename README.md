# Ohio Credit Intelligence Platform

**Production-style AI credit-risk scoring for regional banks — automated loan
decisions, SHAP explainability, and ECOA-compliant adverse action notices,
built on the exact data + MLOps stack Ohio banks are hiring to build.**

[![CI](https://github.com/SIDDARTHAREDDY8/ohio-credit-intelligence/actions/workflows/ci.yml/badge.svg)](https://github.com/SIDDARTHAREDDY8/ohio-credit-intelligence/actions)

---

## What it does

An applicant's loan request goes in; a calibrated risk decision comes out — with
a full audit trail. The platform:

1. **Scores** the application with a LightGBM model trained on 2.26M real loans (0–100 risk score, 5 tiers).
2. **Explains** the decision with SHAP — the exact factors that pushed the score up or down.
3. **Writes a compliant decline letter** with the Claude API when a loan is declined — plain-English, citing the applicant's own numbers, satisfying ECOA/FCRA adverse-action requirements.
4. **Audits fairness** against Ohio HMDA mortgage data using the CFPB 4/5ths rule.
5. **Monitors drift** with weekly PSI and alerting.
6. **Logs every decision** to PostgreSQL and surfaces it on a React dashboard.

> **No real customer data is used anywhere.** All inputs are public government
> records or open datasets; synthetic applicants are generated with Faker.

---

## Architecture

```
LendingClub CSV (2.26M rows)            Ohio HMDA 2023 (CFPB public data)
          │                                        │
   Python ingestion                         Python ingestion
          │                                        │
   raw.lending_club                         raw.hmda_ohio
          │                                        │
   dbt staging → intermediate               dbt staging
          │                                        │
   mart_training_set ──► ml/train.py        mart_bias_audit
          │              (LightGBM)                │
          │                  │                     │
          │            MLflow Registry      ml/fairness_audit.py
          │            (champion alias)     (4/5ths rule → MLflow)
          │                  │                     │
          └────────►  FastAPI scoring API  ◄───────┘
                      ├─ POST /score     → score + SHAP + Claude notice
                      ├─ POST /explain   → stored explanation by id
                      ├─ GET  /decisions → decision log
                      ├─ GET  /fairness  → HMDA demographic approval rates
                      ├─ GET  /drift     → weekly PSI readings
                      └─ GET  /health    → model version + uptime
                                 │
                      React + TypeScript UI (3 pages)
                      ├─ Dashboard  — today's volume + recent decisions
                      ├─ Score      — applicant intake form + live result
                      └─ Monitoring — fairness audit + PSI drift
```

---

## Risk tiers

The 0–100 score (higher = higher default probability) maps to five tiers. The
Claude API is called **only** on a DECLINE.

| Tier | Score | Decision | Adverse action notice |
|------|-------|----------|------------------------|
| 1 | 0–20  | APPROVE | — |
| 2 | 21–40 | APPROVE | — |
| 3 | 41–60 | REVIEW (human) | — |
| 4 | 61–80 | DECLINE | ✅ generated |
| 5 | 81–100 | DECLINE | ✅ generated |

---

## Tech stack

| Layer | Tools |
|-------|-------|
| **Data** | Python 3.11 · PostgreSQL 15 · dbt · Great Expectations · Prefect |
| **ML** | LightGBM · SHAP · scikit-learn · MLflow (tracking + model registry) |
| **API** | FastAPI · Pydantic v2 · Anthropic Claude API · SQLAlchemy |
| **Frontend** | React 18 · TypeScript · Vite · plain CSS (no UI framework) |
| **Infra** | Docker Compose · GitHub Actions CI/CD · AWS EC2 + RDS (deploy) |

---

## Data sources

All public. No customer PII is used or stored.

- **LendingClub** — 2.26M real loan records (Kaggle, public) → model training
- **Ohio HMDA 2023** — mortgage applications by demographic (CFPB, public) → fairness audit
- **Synthetic applicants** — Faker-generated → tests and demo

---

## Quick start

> **Port note:** PostgreSQL is published on host **5433** and MLflow on **5001**
> (5432/5000 are commonly taken on macOS). Inside Docker they remain 5432/5000.

```bash
git clone https://github.com/SIDDARTHAREDDY8/ohio-credit-intelligence
cd ohio-credit-intelligence
cp .env.example .env          # add your ANTHROPIC_API_KEY
docker compose up -d          # postgres + mlflow
```

Build the data → model → API:

```bash
# 1. ingest (after placing the LendingClub + HMDA CSVs under data/)
python ingestion/flows/ingest_lending_club.py
python ingestion/flows/ingest_hmda.py

# 2. transform
cd transform && dbt deps && dbt run && dbt test && cd ..

# 3. train + register the champion model
python ml/train.py
python ml/fairness_audit.py

# 4. serve
uvicorn api.main:app --reload --port 8000
cd frontend && npm install && npm run dev
```

| Service | URL |
|---------|-----|
| API | http://localhost:8000 |
| API docs | http://localhost:8000/docs |
| Frontend | http://localhost:3000 |
| MLflow UI | http://localhost:5001 |

Score a sample applicant:

```bash
curl -X POST http://localhost:8000/score \
  -H "Content-Type: application/json" \
  -d @tests/fixtures/sample_applicant.json
```

---

## Project layout

```
ingestion/        # raw CSV → PostgreSQL loaders + Great Expectations checks
transform/        # dbt project: staging → intermediate → marts (+ data tests)
ml/               # train, evaluate, SHAP explain, fairness audit, promote
                  # config/ holds features.yaml + model_config.yaml
api/              # FastAPI app: routers, schemas, services (model_loader,
                  # feature_builder, claude_service), db connection
monitoring/       # PSI drift detector + alert rules
frontend/         # React + TypeScript + Vite (Dashboard, Score, Monitoring)
tests/            # 50 unit + 11 integration (pytest)
infra/            # EC2 setup script + RDS init SQL
.github/workflows # ci.yml (pytest + ruff) · deploy.yml (ECR + EC2)
```

---

## Testing & CI

```bash
pytest tests/unit/ -v          # 50 fast unit tests (no DB/MLflow/Claude needed)
pytest tests/ -v               # full suite: 61 tests incl. live integration
ruff check api/ ml/ ingestion/ monitoring/
cd transform && dbt test       # 27 dbt data-quality tests
```

- **Unit tests** cover tier/decision boundaries, feature engineering (FICO mid,
  loan-to-income, utilization rescaling, term formatting), label-encoder
  unseen-value handling, Pydantic validation, and `/health`.
- **Integration tests** (marked `@pytest.mark.integration`) exercise the full
  stack end-to-end — scoring, SHAP, Postgres writes, the markdown-free Claude
  notice, and every endpoint.
- **GitHub Actions** runs the unit suite + ruff on every push.

---

## Key engineering details

- **MLflow model registry** with a `champion` alias and proxied artifact serving;
  the API loads `models:/ohio_credit_risk@champion` at startup.
- **Promotion gate** (`ml/promote.py`) only advances a new model if test AUC
  improves by more than 0.005 over the current champion.
- **Feature parity** — `feature_builder.py` reproduces training-time encoding
  exactly (e.g. utilization is rescaled 0–1 → 0–100, `term` formatted as
  "36 months") so inference matches the trained marts.
- **Compliance-first prompting** — the adverse-action system prompt forbids all
  markdown, requires second person, numbered reasons citing the applicant's own
  figures, and a concrete next step, kept under 200 words.
- **Fairness** — disparate-impact ratio vs the White + Male majority group;
  ratios below 0.80 are flagged as potential CFPB 4/5ths-rule violations.

---

## Why this matters for Ohio banks

Regional banks (Fifth Third, Huntington, KeyBank) are actively hiring to close
the gap with national fintech lenders on three fronts this project delivers:
**automated, model-driven underwriting**; **explainable, regulator-ready
decisions**; and a **modern data + MLOps pipeline** (PostgreSQL + dbt + MLflow +
Docker + CI/CD). The fairness and adverse-action layers map directly to the
compliance scrutiny these banks apply before deploying any ML model.

---

## Author

**Siddartha Reddy Chinthala** — Cincinnati, Ohio (Post-graduation OPT)
[github.com/SIDDARTHAREDDY8](https://github.com/SIDDARTHAREDDY8) · [linkedin.com/in/siddarthareddy9](https://linkedin.com/in/siddarthareddy9) · [siddarthareddy.com](https://siddarthareddy.com/)
