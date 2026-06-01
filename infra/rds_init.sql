-- Schemas
CREATE SCHEMA IF NOT EXISTS raw;

-- =============================================
-- RAW TABLES (written by ingestion scripts)
-- =============================================

CREATE TABLE IF NOT EXISTS raw.lending_club (
    id                  TEXT,
    loan_amnt           NUMERIC,
    term                TEXT,
    int_rate            NUMERIC,
    installment         NUMERIC,
    grade               TEXT,
    sub_grade           TEXT,
    emp_length          TEXT,
    home_ownership      TEXT,
    annual_inc          NUMERIC,
    verification_status TEXT,
    loan_status         TEXT,
    dti                 NUMERIC,
    delinq_2yrs         INTEGER,
    fico_range_low      INTEGER,
    fico_range_high     INTEGER,
    open_acc            INTEGER,
    pub_rec             INTEGER,
    revol_bal           NUMERIC,
    revol_util          NUMERIC,
    total_acc           INTEGER,
    purpose             TEXT,
    defaulted           INTEGER,
    loaded_at           TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS raw.hmda_ohio (
    activity_year       INTEGER,
    county_code         TEXT,
    loan_type           INTEGER,
    loan_purpose        INTEGER,
    action_taken        INTEGER,
    loan_amount         NUMERIC,
    applicant_income    NUMERIC,
    applicant_race_1    INTEGER,
    applicant_sex       INTEGER,
    denial_reason_1     INTEGER,
    loaded_at           TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS raw.synthetic_applicants (
    applicant_id              TEXT PRIMARY KEY,
    loan_amount               NUMERIC,
    term_months               INTEGER,
    annual_income             NUMERIC,
    dti                       NUMERIC,
    fico_score                INTEGER,
    emp_length_years          INTEGER,
    home_ownership            TEXT,
    loan_purpose              TEXT,
    delinq_2yrs               INTEGER,
    open_accounts             INTEGER,
    revolving_utilization     NUMERIC,
    grade                     TEXT,
    sub_grade                 TEXT,
    verification_status       TEXT,
    int_rate                  NUMERIC,
    installment               NUMERIC,
    revol_bal                 NUMERIC,
    pub_rec                   INTEGER,
    total_acc                 INTEGER,
    generated_at              TIMESTAMP DEFAULT NOW()
);

-- =============================================
-- APP TABLES (written by API and monitoring)
-- =============================================

CREATE TABLE IF NOT EXISTS public.decisions (
    id                      SERIAL PRIMARY KEY,
    applicant_id            TEXT NOT NULL,
    loan_amount             NUMERIC,
    annual_income           NUMERIC,
    dti                     NUMERIC,
    fico_score              INTEGER,
    risk_score              NUMERIC,
    risk_tier               INTEGER,
    decision                TEXT CHECK (decision IN ('APPROVE','REVIEW','DECLINE')),
    top_shap_factors        JSONB,
    adverse_action_notice   TEXT,
    fairness_flags          JSONB DEFAULT '[]',
    model_version           TEXT,
    created_at              TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.drift_log (
    id          SERIAL PRIMARY KEY,
    psi_score   NUMERIC NOT NULL,
    status      TEXT NOT NULL,
    week_start  DATE NOT NULL,
    logged_at   TIMESTAMP DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_decisions_created_at
    ON public.decisions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_decisions_decision
    ON public.decisions(decision);
CREATE INDEX IF NOT EXISTS idx_decisions_risk_tier
    ON public.decisions(risk_tier);
CREATE INDEX IF NOT EXISTS idx_decisions_applicant_id
    ON public.decisions(applicant_id);
CREATE INDEX IF NOT EXISTS idx_drift_log_week_start
    ON public.drift_log(week_start DESC);
