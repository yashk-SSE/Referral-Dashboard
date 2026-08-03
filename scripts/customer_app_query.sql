-- Customer App: raw login events joined to project milestone dates + city.
-- One row per verified Customer App login event (not aggregated - the
-- milestone-window bucketing and P50/P90/P95/Avg stats are computed downstream,
-- in the dashboard, so every individual login timestamp is needed here).
--
-- date_anomaly = TRUE flags projects where commissioning_date is before
-- installation_date - this should not normally happen (rare data anomaly per
-- Yash, 2026-08). These rows are still returned (not dropped) so the
-- dashboard can display them as flagged anomalies rather than silently
-- bucketing them into a nonsensical negative-duration milestone window.

SELECT
    p.sseid,
    p.lead_id,
    p.site_address_cluster            AS city,
    p.order_closure_datetime          AS order_booked_at,
    p.cx_approval_timestamp           AS hoto_at,
    p.installation_date               AS installation_at,
    p.commissioning_date              AS commissioning_at,
    o."createdAt"                     AS login_at,
    CASE
        WHEN p.commissioning_date IS NOT NULL
         AND p.installation_date IS NOT NULL
         AND p.commissioning_date::timestamptz < p.installation_date::timestamptz
        THEN TRUE
        ELSE FALSE
    END                                AS date_anomaly
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
ORDER BY p.sseid, o."createdAt";
