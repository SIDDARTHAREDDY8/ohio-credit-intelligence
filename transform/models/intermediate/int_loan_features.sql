with loans as (
    select * from {{ ref('stg_loans') }}
)

select
    *,

    loan_amount / nullif(annual_inc, 0) as loan_to_income_ratio,

    case
        when emp_length = '10+ years' then 10
        when emp_length = '< 1 year' then 0
        when emp_length is null then 0
        else cast(regexp_replace(emp_length, '[^0-9]', '', 'g') as integer)
    end as emp_length_years,

    case
        when dti < 15 then 'low'
        when dti < 25 then 'medium'
        when dti < 35 then 'high'
        else 'very_high'
    end as dti_bucket,

    case when revol_util > 0.8 then 1 else 0 end as credit_utilization_flag

from loans
