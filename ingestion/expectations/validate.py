"""Validate raw.lending_club with plain pandas checks.

Loads the ingested LendingClub table and asserts the data-quality
expectations the downstream model depends on. Prints PASS/FAIL for each
check and exits non-zero if any check fails (so CI can gate on it).
"""

import os
import sys

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

MIN_ROWS = 100_000


def validate() -> bool:
    database_url = os.getenv("DATABASE_URL")
    engine = create_engine(database_url)
    df = pd.read_sql("SELECT * FROM raw.lending_club", engine)

    results = []

    def check(name: str, condition: bool) -> None:
        results.append((name, condition))
        print(f"[{'PASS' if condition else 'FAIL'}] {name}")

    check(
        "loan_amnt: no nulls, all > 0",
        df["loan_amnt"].notna().all() and (df["loan_amnt"] > 0).all(),
    )
    check(
        "dti: no nulls, all between 0 and 100",
        df["dti"].notna().all() and df["dti"].between(0, 100).all(),
    )
    check(
        "annual_inc: no nulls, all > 0",
        df["annual_inc"].notna().all() and (df["annual_inc"] > 0).all(),
    )
    check(
        "defaulted: no nulls, values only 0 or 1",
        df["defaulted"].notna().all() and df["defaulted"].isin([0, 1]).all(),
    )
    check(
        f"row count: at least {MIN_ROWS:,} rows",
        len(df) >= MIN_ROWS,
    )

    passed = all(ok for _, ok in results)
    print(f"\n{'ALL CHECKS PASSED' if passed else 'VALIDATION FAILED'} "
          f"({sum(ok for _, ok in results)}/{len(results)} passed, {len(df):,} rows)")
    return passed


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
