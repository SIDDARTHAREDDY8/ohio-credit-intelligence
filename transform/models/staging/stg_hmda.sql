with source as (
    select *
    from raw.hmda_ohio
    where action_taken in (1, 3)
)

select
    activity_year::integer       as activity_year,
    county_code::text            as county_code,
    loan_type::integer           as loan_type,
    loan_purpose::integer        as loan_purpose,
    action_taken::integer        as action_taken,
    loan_amount::numeric         as loan_amount,
    applicant_income::numeric    as applicant_income,
    applicant_race_1::integer    as applicant_race_1,
    applicant_sex::integer       as applicant_sex,
    denial_reason_1::integer     as denial_reason_1,

    case applicant_race_1::integer
        when 1 then 'American Indian or Alaska Native'
        when 2 then 'Asian'
        when 3 then 'Black or African American'
        when 5 then 'White'
        when 6 then 'Information not provided'
        when 7 then 'Not applicable'
        else 'Unknown'
    end as race_label,

    case applicant_sex::integer
        when 1 then 'Male'
        when 2 then 'Female'
        when 3 then 'Information not provided'
        else 'Unknown'
    end as sex_label,

    case action_taken::integer
        when 1 then 'Originated'
        when 3 then 'Denied'
    end as action_taken_label

from source
