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
--
-- HOTO and Installation fields corrected 2026-08-04 to match Yash's own
-- Metabase question 1466 ("OMS Plants"), per his explicit instruction --
-- superseding the earlier cx_approval_timestamp / project.installation_date
-- choice (see CLAUDE.md Section 15 for the full reconciliation history):
--   - HOTO is now p.sales_handover_datetime (card 1466's "Sales Handover
--     Date"), not p.cx_approval_timestamp.
--   - Installation is now the usertasks task-039A completion timestamp
--     (card 1466's "Installation Completion Date"), not
--     p.installation_date. Sourced via the install_task CTE below, joined
--     on project._id (usertasks has no direct sseid column).
-- Commissioning is unchanged (p.commissioning_date matches card 1466 already).

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
),

-- Installation Completion date, per card 1466's pivot_tasks CTE: task KEY
-- '039A' completion, keyed on project._id (not sseid). timeCompleted is a
-- unix-ms string with '-1.0' meaning "not completed yet" (nullif'd to NULL).
-- Kept as a full timestamp (not cast to ::date like card 1466's display
-- column) so day-level velocity calcs downstream retain hour-of-day precision,
-- consistent with how the other 3 milestone dates are stored on `project`.
install_task AS (
    SELECT
        "parameters_projectId" AS project_id,
        MAX(to_timestamp(NULLIF("timeCompleted", '-1.0')::numeric / 1000)) AS installation_at
    FROM usertasks
    WHERE KEY = '039A'
    GROUP BY "parameters_projectId"
)

SELECT
    p.sseid,
    p.lead_id,
    p.site_address_cluster            AS city,
    p.order_closure_datetime          AS order_booked_at,
    p.sales_handover_datetime         AS hoto_at,
    it.installation_at                AS installation_at,
    p.commissioning_date              AS commissioning_at,
    ld.first_login_at                 AS first_login_at,
    CASE
        WHEN p.commissioning_date IS NOT NULL
         AND it.installation_at IS NOT NULL
         AND p.commissioning_date::timestamptz < it.installation_at
        THEN TRUE
        ELSE FALSE
    END                                AS date_anomaly
FROM project p
LEFT JOIN login_data ld
    ON ld.sseid = p.sseid
LEFT JOIN install_task it
    ON it.project_id = p._id
WHERE p.project_state IN ('active', 'completed')
ORDER BY p.sseid;
