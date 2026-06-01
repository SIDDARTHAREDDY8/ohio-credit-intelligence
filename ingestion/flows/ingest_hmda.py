"""Ingest Ohio HMDA 2023 mortgage applications into raw.hmda_ohio.

Source is the public CFPB HMDA data browser export. We keep only Ohio
records (county FIPS prefix "39") and the columns used by the fairness
audit. No real customer data — HMDA is public government data.
"""

import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

CSV_PATH = "data/hmda/ohio_hmda_2023.csv"

# Map raw.hmda_ohio target columns -> actual CFPB export column names.
# The public CFPB data uses hyphenated/abbreviated headers, so we rename.
COLUMN_MAP = {
    "activity_year": "activity_year",
    "county_code": "county_code",
    "loan_type": "loan_type",
    "loan_purpose": "loan_purpose",
    "action_taken": "action_taken",
    "loan_amount": "loan_amount",
    "income": "applicant_income",
    "applicant_race-1": "applicant_race_1",
    "applicant_sex": "applicant_sex",
    "denial_reason-1": "denial_reason_1",
}


def ingest() -> int:
    database_url = os.getenv("DATABASE_URL")
    engine = create_engine(database_url)

    df = pd.read_csv(
        CSV_PATH,
        dtype={"county_code": str},
        usecols=list(COLUMN_MAP.keys()),
        low_memory=False,
    )

    # Ohio counties only (FIPS state prefix 39)
    df = df[df["county_code"].astype(str).str.startswith("39")].copy()

    df = df.rename(columns=COLUMN_MAP)

    df.to_sql(
        "hmda_ohio",
        engine,
        schema="raw",
        if_exists="replace",
        index=False,
    )

    print(f"raw.hmda_ohio loaded: {len(df)} rows")
    return len(df)


if __name__ == "__main__":
    ingest()
