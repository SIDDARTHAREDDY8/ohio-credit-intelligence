-- Fails if any feature snapshot is timestamped in the future.
-- The feature store is the only mart with a date column, so this is the
-- only table the check applies to.
select id, feature_snapshot_at
from {{ ref('mart_feature_store') }}
where feature_snapshot_at > now()
