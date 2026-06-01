-- Fails if any staged loan has a dti outside the valid 0–100 range.
select id, dti
from {{ ref('stg_loans') }}
where dti < 0 or dti > 100
