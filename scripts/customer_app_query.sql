-- Customer App: one row per PROJECT (not per login event), with each
-- project's first verified Customer App login (if any) and its lifecycle
-- milestone dates + city.
--
-- Anchored on `project`, with logins LEFT JOINed in -- this is deliberate:
-- projects with zero logins must still appear (first_login_at = NULL) so the
-- dashboard can compute "% of commissioned/installed/HOTO base that has
-- logged in" against the FULL base, not just the subset that ever logged in.
-- An earlier version of this query started from `otps` instead, which
-- silently excluded every project with zero logins -- confirmed wrong by
-- Yash, 2026-08.
--
-- Only the FIRST login per project is tracked (MIN), not every login -- per
-- Yash, 2026-08: multiple logins by the same customer should not be counted
-- separately.
--
-- date_anomaly = TRUE flags projects where commissioning_date is before
-- installation_date - this should not normally happen (rare data anomaly per
-- Yash, 2026-08). These rows are still returned (not dropped) so the
-- dashboard can display them as flagged anomalies rather than silently
-- bucketing them into a nonsensical negative-duration milestone window.
--
-- Only project_state IN ('active','completed') is included -- excludes
-- 'cancelled', 'on-hold', 'seeking-cancellation', and null-state projects.
-- Confirmed exact lowercase values against the actual data, per Yash, 2026-08.

WITH login_data AS (
    SELECT
        p.sseid,
        MIN(o."createdAt") AS first_login_at
    FROM otps o
    LEFT JOIN customer c
        ON o.mobile = c.phone
    LEFT JOIN customer_projects cp
        ON c.projects = cp.projects__rid_
        AND cp.projects__index_ = 0
    JOIN project p
        ON p.sseid = cp.projects_sseid
    WHERE o."isVerified" = 'True'
        AND o.source IN ('CONSUMER', 'CUSTOMER_JOURNEY_TRACKER')
    GROUP BY p.sseid
)

SELECT
    p.sseid,
    p.lead_id,
    p.site_address_cluster            AS city,
    p.order_closure_datetime          AS order_booked_at,
    p.cx_approval_timestamp           AS hoto_at,
    p.installation_date               AS installation_at,
    p.commissioning_date              AS commissioning_at,
    ld.first_login_at                 AS first_login_at,
    CASE
        WHEN p.commissioning_date IS NOT NULL
         AND p.installation_date IS NOT NULL
         AND p.commissioning_date::timestamptz < p.installation_date::timestamptz
        THEN TRUE
        ELSE FALSE
    END                                AS date_anomaly
FROM project p
LEFT JOIN login_data ld
    ON ld.sseid = p.sseid
WHERE p.project_state IN ('active', 'completed')
ORDER BY p.sseid;
