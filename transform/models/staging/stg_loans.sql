with source as (
    select *
    from raw.lending_club
    where defaulted is not null
)

select
    id::text                                  as id,
    loan_amnt::numeric                        as loan_amount,
    trim(term)                                as term,
    int_rate::numeric                         as int_rate,
    installment::numeric                      as installment,
    grade::text                               as grade,
    sub_grade::text                           as sub_grade,
    emp_length::text                          as emp_length,
    home_ownership::text                      as home_ownership,
    annual_inc::numeric                       as annual_inc,
    verification_status::text                 as verification_status,
    dti::numeric                              as dti,
    delinq_2yrs::integer                      as delinq_2yrs,
    fico_range_low::integer                   as fico_range_low,
    fico_range_high::integer                  as fico_range_high,
    (fico_range_low + fico_range_high) / 2.0  as fico_mid,
    open_acc::integer                         as open_acc,
    pub_rec::integer                          as pub_rec,
    revol_bal::numeric                        as revol_bal,
    revol_util::numeric                       as revol_util,
    total_acc::integer                        as total_acc,
    purpose::text                             as purpose,
    defaulted::integer                        as defaulted
from source
