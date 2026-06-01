"""Ingest the LendingClub accepted-loans CSV into raw.lending_club.

Reads data/raw/lending_club.csv in chunks, maps loan_status to a binary
`defaulted` label, drops rows we can't use, and loads the result into
PostgreSQL. No real customer data — LendingClub is a public Kaggle dataset.
"""

import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

CSV_PATH = "data/raw/lending_club.csv"
CHUNK_SIZE = 10000

KEEP_COLUMNS = [
    "id",
    "loan_amnt",
    "term",
    "int_rate",
    "installment",
    "grade",
    "sub_grade",
    "emp_length",
    "home_ownership",
    "annual_inc",
    "verification_status",
    "loan_status",
    "dti",
    "delinq_2yrs",
    "fico_range_low",
    "fico_range_high",
    "open_acc",
    "pub_rec",
    "revol_bal",
    "revol_util",
    "total_acc",
    "purpose",
]

# loan_status -> defaulted
DEFAULT_MAP = {
    "Charged Off": 1,
    "Default": 1,
    "Fully Paid": 0,
}

NOT_NULL_COLUMNS = ["dti", "annual_inc", "fico_range_low", "revol_util"]


def ingest() -> int:
    database_url = os.getenv("DATABASE_URL")
    engine = create_engine(database_url)

    total_rows = 0
    first_chunk = True

    reader = pd.read_csv(
        CSV_PATH,
        usecols=lambda c: c in KEEP_COLUMNS,
        chunksize=CHUNK_SIZE,
        low_memory=False,
    )

    for chunk in reader:
        # Keep only rows with a target value we understand
        chunk = chunk[chunk["loan_status"].isin(DEFAULT_MAP.keys())].copy()
        chunk["defaulted"] = chunk["loan_status"].map(DEFAULT_MAP).astype(int)

        # Drop rows missing required numeric fields
        chunk = chunk.dropna(subset=NOT_NULL_COLUMNS)

        # Drop dti sentinels / out-of-range values (LendingClub uses -1 and 999)
        chunk = chunk[(chunk["dti"] >= 0) & (chunk["dti"] <= 100)]

        if chunk.empty:
            continue

        chunk.to_sql(
            "lending_club",
            engine,
            schema="raw",
            if_exists="replace" if first_chunk else "append",
            index=False,
        )
        first_chunk = False
        total_rows += len(chunk)

    print(f"raw.lending_club loaded: {total_rows} rows")
    return total_rows


if __name__ == "__main__":
    ingest()
