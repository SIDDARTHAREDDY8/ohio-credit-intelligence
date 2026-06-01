with features as (
    select * from {{ ref('int_loan_features') }}
),

credit as (
    select * from {{ ref('int_credit_history') }}
)

select
    f.id,

    -- numeric features (features.yaml order)
    f.loan_amount,
    f.int_rate,
    f.installment,
    f.annual_inc,
    f.dti,
    f.delinq_2yrs,
    f.fico_mid,
    f.open_acc,
    f.pub_rec,
    f.revol_bal,
    f.revol_util,
    f.total_acc,
    f.loan_to_income_ratio,
    f.emp_length_years,

    -- categorical features
    f.term,
    f.grade,
    f.sub_grade,
    f.home_ownership,
    f.verification_status,
    f.purpose,

    -- credit-history engineered columns
    c.has_delinquency,
    c.has_public_record,
    c.account_diversity,

    now() as feature_snapshot_at
from features f
join credit c on f.id = c.id
