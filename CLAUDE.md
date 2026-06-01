# Ohio Credit Intelligence Platform

## Project purpose
Portfolio project by Siddartha Reddy Chinthala targeting Ohio bank
employers (Fifth Third, Huntington, KeyBank). Demonstrates the AI +
data engineering stack these banks are actively hiring to build.

## Key commands

### Start all Docker services
docker compose up -d

### Stop all services
docker compose down

### Run dbt (from transform/ directory)
cd transform && dbt deps && dbt run && dbt test

### Apply database migrations (Alembic)
alembic upgrade head            # fresh DB
alembic stamp head              # existing DB that already has the tables

### Train ML model (also fits the isotonic probability calibrator)
python ml/train.py

### (Re)fit the probability calibrator against the current champion
python ml/calibrate.py

### Run fairness audit
python ml/fairness_audit.py

### Start API in dev mode
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

### Start frontend in dev mode
cd frontend && npm run dev

### Run all tests
pytest tests/ -v

### Run unit tests only
pytest tests/unit/ -v

### Run the adverse-action notice eval harness (calls Claude)
pytest tests/eval -m eval -v

### Check service health
curl http://localhost:8000/health

### Score a test applicant
curl -X POST http://localhost:8000/score \
  -H "Content-Type: application/json" \
  -d @tests/fixtures/sample_applicant.json

### Open MLflow UI
open http://localhost:5001

### Open frontend
open http://localhost:3000

## Database
- Engine: PostgreSQL 15
- Host: localhost:5432 (local), RDS endpoint (production)
- Database name: ohio_credit
- Schemas:
  - raw: written by ingestion scripts
  - public: written by dbt models and API

## Tables

### Written by ingestion (raw schema)
- raw.lending_club: 2.26M LendingClub loan records
- raw.hmda_ohio: Ohio HMDA 2023 mortgage application records
- raw.synthetic_applicants: 1000 Faker-generated test applicants

### Written by dbt (public schema)
- stg_loans: cleaned LendingClub staging view
- stg_hmda: cleaned HMDA staging view with readable labels
- int_loan_features: engineered features (DTI bucket, FICO mid, etc.)
- int_credit_history: delinquency flags, account diversity metrics
- mart_training_set: final labeled dataset for model training (70/30 split)
- mart_feature_store: live feature snapshot for API inference
- mart_bias_audit: approval rates by demographic group from HMDA

### Written by API (public schema)
- public.decisions: every scoring decision logged with full detail
- public.drift_log: weekly PSI scores from drift detector

## Data flow
LendingClub CSV
  → raw.lending_club
  → stg_loans → int_loan_features + int_credit_history
  → mart_training_set
  → ml/train.py → MLflow Model Registry (champion model)
  → api/services/model_loader.py
  → POST /score endpoint
  → public.decisions table
  → React Dashboard

Ohio HMDA CSV
  → raw.hmda_ohio
  → stg_hmda
  → mart_bias_audit
  → ml/fairness_audit.py → MLflow metrics
  → GET /fairness endpoint
  → React Monitoring page

Faker generator
  → raw.synthetic_applicants + data/synthetic/applicants.csv
  → used by tests and API demo

## Model
- Algorithm: LightGBM (binary classifier)
- Registered in MLflow as: ohio_credit_risk, alias: champion
- Features: defined in ml/config/features.yaml
- Encoders: saved as joblib in ml/encoders/ (gitignored, MLflow artifact)
- Score range: 0 to 100 (higher = higher default probability)
- Risk tiers:
  - Tier 1: score 0-20   → decision: APPROVE
  - Tier 2: score 21-40  → decision: APPROVE
  - Tier 3: score 41-60  → decision: REVIEW (human review required)
  - Tier 4: score 61-80  → decision: DECLINE
  - Tier 5: score 81-100 → decision: DECLINE
- Claude API called only on DECLINE decisions

## API endpoints
- POST /score         Score an applicant, returns full DecisionResponse
- POST /explain       Get explanation for existing decision by applicant_id
- GET  /decisions     List recent decisions (query param: limit, default 50)
- GET  /fairness      Return mart_bias_audit data for Monitoring page
- GET  /drift         Return public.drift_log data for Monitoring page
- GET  /health        Service health, model version, uptime

## Environment
- Python 3.11
- All secrets in .env (never committed)
- Use .env.example as template

## No real customer data
- LendingClub: public Kaggle dataset
- HMDA: public CFPB government data
- Synthetic: Faker library
