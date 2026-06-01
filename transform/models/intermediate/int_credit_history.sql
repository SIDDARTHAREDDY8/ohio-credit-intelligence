with loans as (
    select * from {{ ref('stg_loans') }}
)

select
    id,
    case when delinq_2yrs > 0 then 1 else 0 end       as has_delinquency,
    case when pub_rec > 0 then 1 else 0 end           as has_public_record,
    cast(open_acc as float) / nullif(total_acc, 0)    as account_diversity
from loans
