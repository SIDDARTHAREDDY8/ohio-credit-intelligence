with hmda as (
    select * from {{ ref('stg_hmda') }}
)

select
    race_label,
    sex_label,
    count(*)                                                          as total_applications,
    sum(case when action_taken_label = 'Originated' then 1 else 0 end) as approvals,
    round(
        100.0 * sum(case when action_taken_label = 'Originated' then 1 else 0 end)
        / count(*),
        2
    )                                                                 as approval_rate_pct
from hmda
group by race_label, sex_label
having count(*) > 100
order by approval_rate_pct desc
