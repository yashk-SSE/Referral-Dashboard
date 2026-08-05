// ============================================================
// SOLARSQUARE DASHBOARD — App Script v5
// Referral + Digital channels
// Queries BigQuery → Pushes JSON to GitHub
// ============================================================
// IMPORTANT: Run via TIME-BASED TRIGGER only (not manually)
// Manual runs have 6-min limit → triggers get 30-min limit
// Total runtime ~8-9 min → safe with trigger
// ============================================================
// v5 CHANGE LOG:
// - runLeadData('Referral'): BQL_BASE widened to BQL_New definition
//   (Active OR NULL pincode, Exception IS NULL — bill filter removed)
//   so New-definition-only leads (null pincode / null / <1500 bill)
//   are no longer silently dropped from referral_leads.json.
// - Added Opportunity_Id, Lead_ID, sc_email_id, lrm_email_id, pincode,
//   monthly_bill_value, exception, pincode_status, BQL_New, BQL_Old
//   to the Referral lead-level output. Kept ordD/hotoD field names
//   (not order_date/hoto_date) to match index.html's existing LD
//   parsing convention — no dashboard-side changes needed for this file.
// - Because BQL_BASE re-runs its full 2025-04-01 -> yesterday window on
//   every scheduled run (not incremental) and pushToGitHub overwrites
//   the file wholesale, the very next run backfills all history under
//   the new definition — no separate backfill job needed.
// ============================================================

var GITHUB_OWNER = 'yashk-SSE';
var GITHUB_REPO  = 'Referral-Dashboard';
var BQ_PROJECT   = 'presales-442917';

// ============================================================
// MASTER FUNCTION — Schedule THIS via trigger at 10:30 AM
// Runs all 4 queries sequentially
// ============================================================
function runDashboardUpdate() {
  Logger.log('========================================');
  Logger.log('Dashboard Update Started: ' + new Date());
  Logger.log('========================================');
  var start = new Date();

  try { runReferralEffort(); } catch(e) { Logger.log('❌ Referral Effort FAILED: ' + e.message + '\n' + e.stack); }
  try { runReferralLeads();  } catch(e) { Logger.log('❌ Referral Leads FAILED: '  + e.message + '\n' + e.stack); }
  try { runDigitalEffort();  } catch(e) { Logger.log('❌ Digital Effort FAILED: '  + e.message + '\n' + e.stack); }
  try { runDigitalLeads();   } catch(e) { Logger.log('❌ Digital Leads FAILED: '   + e.message + '\n' + e.stack); }

  var mins = ((new Date() - start) / 60000).toFixed(1);
  Logger.log('========================================');
  Logger.log('All done in ' + mins + ' minutes');
  Logger.log('========================================');
}

// ============================================================
// 4 INDIVIDUAL FUNCTIONS
// Can also be run/tested separately anytime
// ============================================================
function runReferralEffort() { runEffortData('Referral'); }
function runReferralLeads()  { runLeadData('Referral');   }
function runDigitalEffort()  { runEffortData('Digital');  }
function runDigitalLeads()   { runLeadData('Digital');    }


// ============================================================
// REFERRAL EFFORT QUERY — outputs BQL_Old, BQL_New,
// First_MS, Total_MS, First_MD, Total_MD, Order, HOTO
//
// DIGITAL EFFORT QUERY — unchanged (single BQL, MS, MD)
// ============================================================
function runEffortData(channel) {
  Logger.log('▶ Starting Effort Data: ' + channel);
  var start = new Date();

  if (channel === 'Referral') {
    // ── REFERRAL: new query with Old/New BQL + First/Total MS/MD ──
    var query = `
DECLARE d1 DATE DEFAULT DATE('2025-04-01');
DECLARE d2 DATE DEFAULT DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY);

WITH
date_list AS (
  SELECT date_ AS Action_Date
  FROM UNNEST(GENERATE_DATE_ARRAY(d1, d2, INTERVAL 1 DAY)) AS date_
),
LEAD_BASE AS (
  SELECT DISTINCT Phone_Number FROM \`presales-442917.leadcsv.Samagam\`
  WHERE DATE(created_on) BETWEEN d1 AND d2 AND Phone_Number IS NOT NULL
),

-- BQL New: Active OR NULL pincode, Exception IS NULL
BQL_BASE_NEW AS (
  SELECT DISTINCT Phone_Number
  FROM \`presales-442917.leadcsv.Samagam\`
  WHERE DATE(created_on) BETWEEN d1 AND d2
    AND (PincodeStatus = 'Active' OR PincodeStatus IS NULL)
    AND Exception IS NULL
    AND Phone_Number IS NOT NULL
),

-- BQL Old: Active pincode only, bill filter added
BQL_BASE_OLD AS (
  SELECT DISTINCT Phone_Number
  FROM \`presales-442917.leadcsv.Samagam\`
  WHERE DATE(created_on) BETWEEN d1 AND d2
    AND PincodeStatus = 'Active'
    AND Monthly_Bill_Amount NOT IN ('<1500', '< 1500')
    AND Exception IS NULL
    AND Phone_Number IS NOT NULL
),

DEV_CONFIRMATION AS (
  SELECT DISTINCT Phone_Number FROM \`presales-442917.leadcsv.Samagam\`
  WHERE COALESCE(DATE(Latest_Dev_Confirmed_At), DATE(SIQ_DEV_Confirmed_At)) BETWEEN d1 AND d2
),
DEV_DONE AS (
  SELECT DISTINCT Phone_Number FROM \`presales-442917.leadcsv.Samagam\`
  WHERE COALESCE(DATE(dev_details_dev_done_on), DATE(Latest_Dev_Done_At)) BETWEEN d1 AND d2
),
DESIGN_DONE AS (
  SELECT DISTINCT Phone_Number FROM \`presales-442917.leadcsv.Samagam\`
  WHERE COALESCE(DATE(dev_details_design_done_on), DATE(DES_Done_At)) BETWEEN d1 AND d2
),

-- First MS / First MD (first-time columns)
MEETING_SCHEDULED AS (
  SELECT DISTINCT Phone_Number FROM \`presales-442917.leadcsv.Samagam\`
  WHERE DATE(meeting_schedule_first_time) BETWEEN d1 AND d2
),
MEETING_DONE AS (
  SELECT DISTINCT Phone_Number FROM \`presales-442917.leadcsv.Samagam\`
  WHERE DATE(first_meeting_done_date) BETWEEN d1 AND d2
),

-- Total MS / Total MD (latest/repeat columns)
MEETING_SCHEDULED_TOTAL AS (
  SELECT DISTINCT Phone_Number FROM \`presales-442917.leadcsv.Samagam\`
  WHERE DATE(meeting_scheduled_date) BETWEEN d1 AND d2
),
MEETING_DONE_TOTAL AS (
  SELECT DISTINCT Phone_Number FROM \`presales-442917.leadcsv.Samagam\`
  WHERE DATE(meeting_done_date) BETWEEN d1 AND d2
),

ORDER_BASE AS (
  SELECT DISTINCT Phone_Number FROM \`presales-442917.leadcsv.Samagam\`
  WHERE DATE(Order_closure_Date) BETWEEN d1 AND d2
),
HOTO_BASE AS (
  SELECT DISTINCT Phone_Number FROM \`presales-442917.leadcsv.Samagam\`
  WHERE DATE(Approved_by_customer_Date) BETWEEN d1 AND d2
),
MASTER_BASE AS (
  SELECT DISTINCT Phone_Number FROM (
    SELECT * FROM LEAD_BASE
    UNION ALL SELECT * FROM BQL_BASE_OLD
    UNION ALL SELECT * FROM BQL_BASE_NEW
    UNION ALL SELECT * FROM DEV_CONFIRMATION UNION ALL SELECT * FROM DEV_DONE
    UNION ALL SELECT * FROM DESIGN_DONE
    UNION ALL SELECT * FROM MEETING_SCHEDULED UNION ALL SELECT * FROM MEETING_DONE
    UNION ALL SELECT * FROM MEETING_SCHEDULED_TOTAL UNION ALL SELECT * FROM MEETING_DONE_TOTAL
    UNION ALL SELECT * FROM ORDER_BASE
    UNION ALL SELECT * FROM HOTO_BASE
  )
),
SAMAGAM_MAPPING AS (
  SELECT * FROM \`presales-442917.leadcsv.Samagam\`
  QUALIFY ROW_NUMBER() OVER (PARTITION BY Phone_Number, Lead_ID ORDER BY Last_Action_Date DESC) = 1
),
MASTER_DATA AS (
  SELECT
    A.Phone_Number,
    COALESCE(B.Lead_ID, B.opportunity_id)           AS Lead_ID,
    COALESCE(B.LSQ_City, B.Cluster)                 AS CITY,
    B.Source_Class, B.Source_Sub_Class, B.LRM_Email_Id,
    B.Exception, B.PincodeStatus,
    COALESCE(B.Monthly_Bill_Amount, B.Monthly_Bill) AS Monthly_Bill_Amount,
    B.Created_On,
    COALESCE(B.Latest_Dev_Confirmed_At, B.SIQ_DEV_Confirmed_At) AS DEV_Confirmed_At,
    COALESCE(B.dev_details_dev_done_on, B.Latest_Dev_Done_At)   AS Dev_Done_At,
    COALESCE(B.dev_details_design_done_on, B.DES_Done_At)       AS DES_Date,
    -- First MS / First MD
    B.meeting_schedule_first_time,
    B.first_meeting_done_date,
    -- Total MS / Total MD
    B.meeting_scheduled_date,
    B.meeting_done_date,
    B.Order_closure_Date,
    B.Approved_by_customer_Date
  FROM MASTER_BASE A
  LEFT JOIN SAMAGAM_MAPPING B ON A.Phone_Number = B.Phone_Number
),
LEAD_DATA AS (
  SELECT *,
    -- Customer_App sub-channel removed from BigQuery pickup 2026-08-05, per
    -- Yash's explicit instruction -- Source_Class LIKE '%Customer App%' rows no
    -- longer count as Referral channel at all (previously reclassified to
    -- 'Customer_App' sub-channel; that whole branch is gone, not replaced).
    -- See CLAUDE.md Section 4 for history -- this supersedes the earlier
    -- "reclassification, not removal" plan documented there.
    CASE
      WHEN Source_Class LIKE '%Referral%' THEN 'Referral'
      WHEN Source_Class LIKE '%Digital%' THEN 'Digital'
      ELSE 'Others'
    END AS Source_Class_final,
    CASE
      WHEN Source_Class LIKE '%Referral%' THEN COALESCE(Source_Sub_Class, 'WhatsApp')
      ELSE Source_Sub_Class
    END AS Source_Sub_Class_final,
    CASE
      WHEN first_meeting_done_date IS NOT NULL THEN
        CASE WHEN Dev_Done_At < first_meeting_done_date AND DES_Date < first_meeting_done_date THEN 'SO' ELSE 'BAU' END
      WHEN meeting_schedule_first_time IS NOT NULL THEN 'SO'
      WHEN Dev_Done_At IS NOT NULL THEN 'SO'
      ELSE 'NA'
    END AS DELIVERY_TYPE
  FROM MASTER_DATA
),
EFFORT_DATA AS (
  SELECT
    d.Action_Date,
    l.CITY,
    l.Source_Class_final,
    l.Source_Sub_Class_final,

    -- BQL New: Active OR NULL pincode, Exception IS NULL
    COUNT(DISTINCT CASE
      WHEN DATE(l.Created_On) = d.Action_Date
       AND (l.PincodeStatus = 'Active' OR l.PincodeStatus IS NULL)
       AND l.Exception IS NULL
      THEN l.Lead_ID
    END) AS bql_new,

    -- BQL Old: Active only, bill filter
    COUNT(DISTINCT CASE
      WHEN DATE(l.Created_On) = d.Action_Date
       AND l.PincodeStatus = 'Active'
       AND l.Monthly_Bill_Amount NOT IN ('<1500', '< 1500')
       AND l.Exception IS NULL
      THEN l.Lead_ID
    END) AS bql_old,

    -- First MS
    COUNT(DISTINCT CASE
      WHEN DATE(l.meeting_schedule_first_time) = d.Action_Date
      THEN l.Lead_ID
    END) AS first_meeting_scheduled,

    -- First MD
    COUNT(DISTINCT CASE
      WHEN DATE(l.first_meeting_done_date) = d.Action_Date
      THEN l.Lead_ID
    END) AS first_meeting_done,

    -- Total MS
    COUNT(DISTINCT CASE
      WHEN DATE(l.meeting_scheduled_date) = d.Action_Date
      THEN l.Lead_ID
    END) AS total_meeting_scheduled,

    -- Total MD
    COUNT(DISTINCT CASE
      WHEN DATE(l.meeting_done_date) = d.Action_Date
      THEN l.Lead_ID
    END) AS total_meeting_done,

    COUNT(DISTINCT CASE
      WHEN DATE(l.Order_closure_Date) = d.Action_Date
      THEN l.Lead_ID
    END) AS order_closure,

    COUNT(DISTINCT CASE
      WHEN DATE(l.Approved_by_customer_Date) = d.Action_Date
      THEN l.Lead_ID
    END) AS approved_by_customer

  FROM date_list d
  LEFT JOIN LEAD_DATA l
    ON d.Action_Date IN (
      DATE(l.Created_On),
      DATE(l.meeting_schedule_first_time),
      DATE(l.first_meeting_done_date),
      DATE(l.meeting_scheduled_date),
      DATE(l.meeting_done_date),
      DATE(l.Order_closure_Date),
      DATE(l.Approved_by_customer_Date)
    )
   AND l.Source_Class_final = 'Referral'

  GROUP BY
    d.Action_Date,
    l.CITY,
    l.Source_Class_final,
    l.Source_Sub_Class_final
)
SELECT
  FORMAT_DATE('%d/%m/%Y', Action_Date) AS action_date,
  EXTRACT(MONTH FROM Action_Date)      AS month,
  EXTRACT(YEAR  FROM Action_Date)      AS year,
  CITY                                 AS city,
  Source_Sub_Class_final               AS sub_channel,
  SUM(bql_old)                         AS BQL_Old,
  SUM(bql_new)                         AS BQL_New,
  SUM(first_meeting_scheduled)         AS First_MS,
  SUM(first_meeting_done)              AS First_MD,
  SUM(total_meeting_scheduled)         AS Total_MS,
  SUM(total_meeting_done)              AS Total_MD,
  SUM(order_closure)                   AS \`Order\`,
  SUM(approved_by_customer)            AS HOTO
FROM EFFORT_DATA
GROUP BY action_date, month, year, city, sub_channel
ORDER BY PARSE_DATE('%d/%m/%Y', action_date) DESC
    `;

    var rows = runBigQuery(query);
    if (!rows) { Logger.log('No data returned for Referral effort'); return; }

    var jsonData = rows.map(function(row) {
      return {
        action_date:  row[0],
        month:        parseInt(row[1])||0,
        year:         parseInt(row[2])||0,
        city:         (row[3]||'').trim(),
        sub_channel:  (row[4]||'').trim(),
        BQL_Old:      parseFloat(row[5])||0,
        BQL_New:      parseFloat(row[6])||0,
        First_MS:     parseFloat(row[7])||0,
        First_MD:     parseFloat(row[8])||0,
        Total_MS:     parseFloat(row[9])||0,
        Total_MD:     parseFloat(row[10])||0,
        Order:        parseFloat(row[11])||0,
        HOTO:         parseFloat(row[12])||0
      };
    });

    pushToGitHub(JSON.stringify(jsonData), 'data/referral_effort.json', '📊 Referral effort: ' + formatDate(new Date()));
    Logger.log('✅ data/referral_effort.json — ' + jsonData.length + ' rows in ' + ((new Date()-start)/60000).toFixed(1) + ' min');

  } else {
    // ── DIGITAL: unchanged query (single BQL, MS, MD) ──
    var sourceFilter = "Source_Class_final = 'Digital'";

    var query = `
DECLARE d1 DATE DEFAULT DATE('2025-10-01');
DECLARE d2 DATE DEFAULT DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY);

WITH
date_list AS (
  SELECT date_ AS Action_Date
  FROM UNNEST(GENERATE_DATE_ARRAY(d1, d2, INTERVAL 1 DAY)) AS date_
),
LEAD_BASE AS (
  SELECT DISTINCT Phone_Number FROM \`presales-442917.leadcsv.Samagam\`
  WHERE DATE(created_on) BETWEEN d1 AND d2 AND Phone_Number IS NOT NULL
),
BQL_BASE AS (
  SELECT DISTINCT Phone_Number FROM \`presales-442917.leadcsv.Samagam\`
  WHERE DATE(created_on) BETWEEN d1 AND d2
  AND PincodeStatus = 'Active'
  AND Monthly_Bill_Amount NOT IN ('<1500', '< 1500')
  AND Exception IS NULL AND Phone_Number IS NOT NULL
),
DEV_CONFIRMATION AS (
  SELECT DISTINCT Phone_Number FROM \`presales-442917.leadcsv.Samagam\`
  WHERE COALESCE(DATE(Latest_Dev_Confirmed_At), DATE(SIQ_DEV_Confirmed_At)) BETWEEN d1 AND d2
),
DEV_DONE AS (
  SELECT DISTINCT Phone_Number FROM \`presales-442917.leadcsv.Samagam\`
  WHERE COALESCE(DATE(dev_details_dev_done_on), DATE(Latest_Dev_Done_At)) BETWEEN d1 AND d2
),
DESIGN_DONE AS (
  SELECT DISTINCT Phone_Number FROM \`presales-442917.leadcsv.Samagam\`
  WHERE COALESCE(DATE(dev_details_design_done_on), DATE(DES_Done_At)) BETWEEN d1 AND d2
),
MEETING_SCHEDULED AS (
  SELECT DISTINCT Phone_Number FROM \`presales-442917.leadcsv.Samagam\`
  WHERE DATE(Meeting_Scheduled_Date) BETWEEN d1 AND d2
),
MEETING_DONE AS (
  SELECT DISTINCT Phone_Number FROM \`presales-442917.leadcsv.Samagam\`
  WHERE DATE(Meeting_Done_Date) BETWEEN d1 AND d2
),
ORDER_BASE AS (
  SELECT DISTINCT Phone_Number FROM \`presales-442917.leadcsv.Samagam\`
  WHERE DATE(Order_closure_Date) BETWEEN d1 AND d2
),
HOTO_BASE AS (
  SELECT DISTINCT Phone_Number FROM \`presales-442917.leadcsv.Samagam\`
  WHERE DATE(Approved_by_customer_Date) BETWEEN d1 AND d2
),
MASTER_BASE AS (
  SELECT DISTINCT Phone_Number FROM (
    SELECT * FROM LEAD_BASE UNION ALL SELECT * FROM BQL_BASE
    UNION ALL SELECT * FROM DEV_CONFIRMATION UNION ALL SELECT * FROM DEV_DONE
    UNION ALL SELECT * FROM DESIGN_DONE UNION ALL SELECT * FROM MEETING_SCHEDULED
    UNION ALL SELECT * FROM MEETING_DONE UNION ALL SELECT * FROM ORDER_BASE
    UNION ALL SELECT * FROM HOTO_BASE
  )
),
SAMAGAM_MAPPING AS (
  SELECT * FROM \`presales-442917.leadcsv.Samagam\`
  QUALIFY ROW_NUMBER() OVER (PARTITION BY Phone_Number, Lead_ID ORDER BY Last_Action_Date DESC) = 1
),
MASTER_DATA AS (
  SELECT
    A.Phone_Number,
    COALESCE(B.Lead_ID, B.opportunity_id) AS Lead_ID,
    COALESCE(B.LSQ_City, B.Cluster) AS CITY,
    B.Source_Class, B.Source_Sub_Class, B.LRM_Email_Id,
    B.Exception, B.PincodeStatus,
    COALESCE(B.Monthly_Bill_Amount, B.Monthly_Bill) AS Monthly_Bill_Amount,
    B.Created_On,
    COALESCE(B.Latest_Dev_Confirmed_At, B.SIQ_DEV_Confirmed_At) AS DEV_Confirmed_At,
    COALESCE(B.dev_details_dev_done_on, B.Latest_Dev_Done_At) AS Dev_Done_At,
    COALESCE(B.dev_details_design_done_on, B.DES_Done_At) AS DES_Date,
    B.Meeting_Scheduled_Date, B.Meeting_Done_Date,
    B.Order_closure_Date, B.Approved_by_customer_Date
  FROM MASTER_BASE A
  LEFT JOIN SAMAGAM_MAPPING B ON A.Phone_Number = B.Phone_Number
),
LEAD_DATA AS (
  SELECT *,
    -- Customer_App sub-channel removed from BigQuery pickup 2026-08-05 -- see
    -- the matching comment in runEffortData() above for full context.
    CASE
      WHEN Source_Class LIKE '%Referral%' THEN 'Referral'
      WHEN Source_Class LIKE '%Digital%' THEN 'Digital'
      ELSE 'Others'
    END AS Source_Class_final,
    CASE
      WHEN Source_Class LIKE '%Referral%' THEN COALESCE(Source_Sub_Class,'WhatsApp')
      ELSE Source_Sub_Class
    END AS Source_Sub_Class_final,
    CASE
      WHEN Meeting_Done_Date IS NOT NULL THEN
        CASE WHEN Dev_Done_At < Meeting_Done_Date AND DES_Date < Meeting_Done_Date THEN 'SO' ELSE 'BAU' END
      WHEN Meeting_Scheduled_Date IS NOT NULL THEN 'SO'
      WHEN Dev_Done_At IS NOT NULL THEN 'SO'
      ELSE 'NA'
    END AS DELIVERY_TYPE
  FROM MASTER_DATA
),
EFFORT_DATA AS (
  SELECT
    d.Action_Date, l.CITY, l.Source_Class_final, l.Source_Sub_Class_final,
    COUNT(DISTINCT CASE WHEN DATE(l.Created_On) = d.Action_Date
      AND l.PincodeStatus = 'Active'
      AND l.Monthly_Bill_Amount NOT IN ('<1500','< 1500')
      AND l.Exception IS NULL THEN l.Lead_ID END) AS bill_qualified,
    COUNT(DISTINCT CASE WHEN DATE(l.Meeting_Scheduled_Date) = d.Action_Date THEN l.Lead_ID END) AS meeting_scheduled,
    COUNT(DISTINCT CASE WHEN DATE(l.Meeting_Done_Date)      = d.Action_Date THEN l.Lead_ID END) AS meeting_done,
    COUNT(DISTINCT CASE WHEN DATE(l.Order_closure_Date)     = d.Action_Date THEN l.Lead_ID END) AS order_closure,
    COUNT(DISTINCT CASE WHEN DATE(l.Approved_by_customer_Date) = d.Action_Date THEN l.Lead_ID END) AS approved_by_customer
  FROM date_list d
  LEFT JOIN LEAD_DATA l ON d.Action_Date IN (
    DATE(l.Created_On), DATE(l.Meeting_Scheduled_Date), DATE(l.Meeting_Done_Date),
    DATE(l.Order_closure_Date), DATE(l.Approved_by_customer_Date)
  )
  GROUP BY d.Action_Date, l.CITY, l.Source_Class_final, l.Source_Sub_Class_final
)

SELECT
  FORMAT_DATE('%d/%m/%Y', Action_Date) AS action_date,
  EXTRACT(MONTH FROM Action_Date)       AS month,
  EXTRACT(YEAR  FROM Action_Date)       AS year,
  CITY                                  AS city,
  Source_Sub_Class_final                AS sub_channel,
  SUM(bill_qualified)                   AS BQL,
  SUM(meeting_scheduled)                AS MS,
  SUM(meeting_done)                     AS MD,
  SUM(order_closure)                    AS \`Order\`,
  SUM(approved_by_customer)             AS HOTO
FROM EFFORT_DATA
WHERE ${sourceFilter}
GROUP BY action_date, month, year, city, sub_channel
ORDER BY PARSE_DATE('%d/%m/%Y', action_date) DESC
    `;

    var rows = runBigQuery(query);
    if (!rows) { Logger.log('No data returned for Digital effort'); return; }

    var jsonData = rows.map(function(row) {
      return {
        action_date: row[0], month: parseInt(row[1])||0, year: parseInt(row[2])||0,
        city: (row[3]||'').trim(), sub_channel: (row[4]||'').trim(),
        BQL: parseFloat(row[5])||0, MS: parseFloat(row[6])||0, MD: parseFloat(row[7])||0,
        Order: parseFloat(row[8])||0, HOTO: parseFloat(row[9])||0
      };
    });

    pushToGitHub(JSON.stringify(jsonData), 'data/digital_effort.json', '📊 Digital effort: ' + formatDate(new Date()));
    Logger.log('✅ data/digital_effort.json — ' + jsonData.length + ' rows in ' + ((new Date()-start)/60000).toFixed(1) + ' min');
  }
}


// ============================================================
// LEAD LEVEL DATA QUERY — Referral OR Digital
// Referral: v5 — widened to BQL_New definition + pincode/bill/
//           exception/BQL_Old/BQL_New fields for segmentation
// Digital: unchanged
// ============================================================
function runLeadData(channel) {
  Logger.log('▶ Starting Lead Data: ' + channel);
  var start = new Date();

  var today = new Date();
  today.setDate(today.getDate() - 1);
  var d2 = Utilities.formatDate(today, 'GMT', 'yyyy-MM-dd');

  if (channel === 'Referral') {
    // ── REFERRAL: v5 query — BQL_New-scoped base + segmentation fields ──
    var query = `
WITH
BQL_BASE AS (
  SELECT DISTINCT Opportunity_Id, Lead_ID
  FROM \`presales-442917.leadcsv.Samagam\`
  WHERE DATE(created_on) BETWEEN DATE('2025-04-01') AND DATE('${d2}')
    AND (PincodeStatus = 'Active' OR PincodeStatus IS NULL)
    AND Exception IS NULL
    -- Customer App-sourced leads no longer picked up here at all, 2026-08-05
    -- (previously included via "OR Source_Class LIKE '%Customer App%'").
    AND Source_Class LIKE '%Referral%'
  QUALIFY ROW_NUMBER() OVER (PARTITION BY Opportunity_Id ORDER BY Last_Action_Date DESC) = 1
),
SAMAGAM_MAPPING AS (
  SELECT *
  FROM \`presales-442917.leadcsv.Samagam\`
  WHERE (
    DATE(Created_On)                   BETWEEN '2024-01-01' AND CURRENT_DATE()
    OR DATE(Lead_Creation_Date)        BETWEEN '2024-01-01' AND CURRENT_DATE()
    OR DATE(lead_sent_to_siq)          BETWEEN '2024-01-01' AND CURRENT_DATE()
    OR DATE(lead_delivered_to_lrm)     BETWEEN '2024-01-01' AND CURRENT_DATE()
    OR DATE(Initial_Dev_Confirmed_At)  BETWEEN '2024-01-01' AND CURRENT_DATE()
    OR DATE(Latest_Dev_Scheduled_At)   BETWEEN '2024-01-01' AND CURRENT_DATE()
    OR DATE(SIQ_DEV_Scheduled_At)      BETWEEN '2024-01-01' AND CURRENT_DATE()
    OR DATE(Initial_Dev_Done_At)       BETWEEN '2024-01-01' AND CURRENT_DATE()
    OR DATE(Meeting_Scheduled_Date)    BETWEEN '2024-01-01' AND CURRENT_DATE()
    OR DATE(Meeting_Done_Date)         BETWEEN '2024-01-01' AND CURRENT_DATE()
    OR DATE(Order_closure_Date)        BETWEEN '2024-01-01' AND CURRENT_DATE()
    OR DATE(Approved_by_customer_Date) BETWEEN '2024-01-01' AND CURRENT_DATE()
  )
  QUALIFY ROW_NUMBER() OVER (PARTITION BY Opportunity_Id ORDER BY Last_Action_Date DESC) = 1
),
MASTER_DATA AS (
  SELECT
    A.Opportunity_Id,
    A.Lead_ID,
    COALESCE(B.LSQ_City, B.Cluster)                 AS CITY,
    B.Source_Class,
    B.Source_Sub_Class                               AS Source_Sub_Class_final,
    B.SC_Email_Id,
    B.LRM_Email_Id,
    B.Pincode,
    COALESCE(B.Monthly_Bill_Amount, B.Monthly_Bill)  AS Monthly_Bill_Value,
    B.Exception,
    B.PincodeStatus,
    B.Created_On,
    B.meeting_schedule_first_time,
    B.first_meeting_done_date,
    B.Meeting_Scheduled_Date,
    B.Meeting_Done_Date,
    B.Order_closure_Date,
    B.Approved_by_customer_Date,

    -- BQL_New: Active OR NULL pincode + Exception IS NULL
    CASE
      WHEN (B.PincodeStatus = 'Active' OR B.PincodeStatus IS NULL)
       AND B.Exception IS NULL
      THEN 'Yes' ELSE 'No'
    END AS BQL_New,

    -- BQL_Old: Active only + bill filter + Exception IS NULL
    CASE
      WHEN B.PincodeStatus = 'Active'
       AND COALESCE(B.Monthly_Bill_Amount, B.Monthly_Bill) NOT IN ('<1500', '< 1500')
       AND B.Exception IS NULL
      THEN 'Yes' ELSE 'No'
    END AS BQL_Old

  FROM BQL_BASE A
  LEFT JOIN SAMAGAM_MAPPING B ON A.Opportunity_Id = B.Opportunity_Id
)

SELECT
  Opportunity_Id,
  Lead_ID,
  CITY                                                          AS city,
  Source_Sub_Class_final                                        AS sub_channel,
  SC_Email_Id                                                   AS sc_email_id,
  LRM_Email_Id                                                  AS lrm_email_id,
  Pincode                                                       AS pincode,
  Monthly_Bill_Value                                            AS monthly_bill_value,
  Exception                                                     AS exception,
  PincodeStatus                                                 AS pincode_status,
  BQL_New,
  BQL_Old,
  FORMAT_DATE('%d/%m/%Y', DATE(Created_On))                     AS created,
  FORMAT_DATE('%d/%m/%Y', DATE(meeting_schedule_first_time))    AS first_ms_date,
  FORMAT_DATE('%d/%m/%Y', DATE(first_meeting_done_date))        AS first_md_date,
  FORMAT_DATE('%d/%m/%Y', DATE(Meeting_Scheduled_Date))         AS total_ms_date,
  FORMAT_DATE('%d/%m/%Y', DATE(Meeting_Done_Date))              AS total_md_date,
  FORMAT_DATE('%d/%m/%Y', DATE(Order_closure_Date))             AS ordD,
  FORMAT_DATE('%d/%m/%Y', DATE(Approved_by_customer_Date))      AS hotoD
FROM MASTER_DATA
    `;

    var rows = runBigQuery(query);
    if (!rows) { Logger.log('No lead data returned for Referral'); return; }

    var jsonData = rows.map(function(row) {
      return {
        opportunity_id:     row[0]||null,
        lead_id:            row[1]||null,
        city:               (row[2]||'').trim(),
        sub_channel:        (row[3]||'').trim(),
        sc_email_id:        row[4]||null,
        lrm_email_id:       row[5]||null,
        pincode:            row[6]||null,
        monthly_bill_value: row[7]||null,
        exception:          row[8]||null,
        pincode_status:     row[9]||null,
        BQL_New:            row[10]||'No',
        BQL_Old:            row[11]||'No',
        created:            row[12]||null,
        first_ms_date:      row[13]||null,
        first_md_date:      row[14]||null,
        total_ms_date:      row[15]||null,
        total_md_date:      row[16]||null,
        ordD:               row[17]||null,
        hotoD:              row[18]||null
      };
    });

    pushToGitHub(JSON.stringify(jsonData), 'data/referral_leads.json', '📊 Referral leads: ' + formatDate(new Date()));
    Logger.log('✅ data/referral_leads.json — ' + jsonData.length + ' rows in ' + ((new Date()-start)/60000).toFixed(1) + ' min');

  } else {
    // ── DIGITAL: unchanged query ──
    var sourceFilter = "Source_Class LIKE '%Digital%'";

    var query = `
WITH
BQL_BASE AS (
  SELECT DISTINCT Opportunity_Id, Lead_ID
  FROM \`presales-442917.leadcsv.Samagam\`
  WHERE DATE(created_on) BETWEEN DATE('2025-04-01') AND DATE('${d2}')
  AND PincodeStatus = 'Active'
  AND Monthly_Bill_Amount NOT IN ('<1500','< 1500')
  AND Exception IS NULL
  QUALIFY ROW_NUMBER() OVER (PARTITION BY Opportunity_Id ORDER BY Last_Action_Date DESC) = 1
),
SAMAGAM_MAPPING AS (
  SELECT *
  FROM \`presales-442917.leadcsv.Samagam\`
  WHERE (
    DATE(Created_On)                BETWEEN '2024-01-01' AND CURRENT_DATE()
    OR DATE(Lead_Creation_Date)     BETWEEN '2024-01-01' AND CURRENT_DATE()
    OR DATE(lead_sent_to_siq)       BETWEEN '2024-01-01' AND CURRENT_DATE()
    OR DATE(lead_delivered_to_lrm)  BETWEEN '2024-01-01' AND CURRENT_DATE()
    OR DATE(Initial_Dev_Confirmed_At)  BETWEEN '2024-01-01' AND CURRENT_DATE()
    OR DATE(Latest_Dev_Scheduled_At)   BETWEEN '2024-01-01' AND CURRENT_DATE()
    OR DATE(SIQ_DEV_Scheduled_At)      BETWEEN '2024-01-01' AND CURRENT_DATE()
    OR DATE(Initial_Dev_Done_At)       BETWEEN '2024-01-01' AND CURRENT_DATE()
    OR DATE(Meeting_Scheduled_Date)    BETWEEN '2024-01-01' AND CURRENT_DATE()
    OR DATE(Meeting_Done_Date)         BETWEEN '2024-01-01' AND CURRENT_DATE()
    OR DATE(Order_closure_Date)        BETWEEN '2024-01-01' AND CURRENT_DATE()
    OR DATE(Approved_by_customer_Date) BETWEEN '2024-01-01' AND CURRENT_DATE()
  )
  QUALIFY ROW_NUMBER() OVER (PARTITION BY Opportunity_Id ORDER BY Last_Action_Date DESC) = 1
),
MASTER_DATA AS (
  SELECT
    A.Opportunity_Id, A.Lead_ID,
    COALESCE(B.LSQ_City, B.Cluster)   AS CITY,
    B.Source_Class,
    B.Source_Sub_Class                AS Source_Sub_Class_final,
    B.Created_On,
    B.Meeting_Scheduled_Date,
    B.Meeting_Done_Date,
    B.Order_closure_Date,
    B.Approved_by_customer_Date
  FROM BQL_BASE A
  LEFT JOIN SAMAGAM_MAPPING B ON A.Opportunity_Id = B.Opportunity_Id
)

SELECT
  CITY                                                       AS city,
  Source_Sub_Class_final                                     AS sub_channel,
  FORMAT_DATE('%d/%m/%Y', DATE(Created_On))                  AS created,
  FORMAT_DATE('%d/%m/%Y', DATE(Meeting_Scheduled_Date))      AS msD,
  FORMAT_DATE('%d/%m/%Y', DATE(Meeting_Done_Date))           AS mdD,
  FORMAT_DATE('%d/%m/%Y', DATE(Order_closure_Date))          AS ordD,
  FORMAT_DATE('%d/%m/%Y', DATE(Approved_by_customer_Date))   AS hotoD
FROM MASTER_DATA
WHERE ${sourceFilter}
    `;

    var rows = runBigQuery(query);
    if (!rows) { Logger.log('No lead data returned for Digital'); return; }

    var jsonData = rows.map(function(row) {
      return {
        city: (row[0]||'').trim(), sub_channel: (row[1]||'').trim(),
        created: row[2]||null, msD: row[3]||null,
        mdD: row[4]||null, ordD: row[5]||null, hotoD: row[6]||null
      };
    });

    pushToGitHub(JSON.stringify(jsonData), 'data/digital_leads.json', '📊 Digital leads: ' + formatDate(new Date()));
    Logger.log('✅ data/digital_leads.json — ' + jsonData.length + ' rows in ' + ((new Date()-start)/60000).toFixed(1) + ' min');
  }
}


// ============================================================
// HELPER — Run BigQuery query with pagination
// ============================================================
function runBigQuery(query) {
  var request = { query: query, useLegacySql: false };
  var queryResults = BigQuery.Jobs.query(request, BQ_PROJECT);
  var jobId = queryResults.jobReference.jobId;
  while (!queryResults.jobComplete) {
    Utilities.sleep(2000);
    queryResults = BigQuery.Jobs.getQueryResults(BQ_PROJECT, jobId);
  }
  var allRows = [], pageToken = null;
  do {
    var results = BigQuery.Jobs.getQueryResults(BQ_PROJECT, jobId, {
      pageToken: pageToken, maxResults: 5000
    });
    if (results.rows) allRows = allRows.concat(results.rows.map(function(r){
      return r.f.map(function(c){ return c.v; });
    }));
    pageToken = results.pageToken;
  } while (pageToken);
  return allRows.length > 0 ? allRows : null;
}


// ============================================================
// HELPER — Push file to GitHub using Git Data API
// ============================================================
function pushToGitHub(content, filePath, commitMessage) {
  var token = PropertiesService.getScriptProperties().getProperty('GITHUB_TOKEN');
  if (!token) throw new Error('GITHUB_TOKEN not set in Script Properties');
  var base = 'https://api.github.com/repos/' + GITHUB_OWNER + '/' + GITHUB_REPO;
  var headers = {
    'Authorization': 'Bearer ' + token,
    'Accept': 'application/vnd.github+json',
    'Content-Type': 'application/json',
    'X-GitHub-Api-Version': '2022-11-28'
  };
  function ghGet(url){ var r=UrlFetchApp.fetch(url,{headers:headers,muteHttpExceptions:true}); if(r.getResponseCode()>=400)throw new Error('GET '+r.getResponseCode()); return JSON.parse(r.getContentText()); }
  function ghPost(url,body){ var r=UrlFetchApp.fetch(url,{method:'POST',headers:headers,payload:JSON.stringify(body),muteHttpExceptions:true}); if(r.getResponseCode()>=400)throw new Error('POST '+r.getResponseCode()+': '+r.getContentText().substring(0,200)); return JSON.parse(r.getContentText()); }
  var ref=ghGet(base+'/git/refs/heads/main'),commitSha=ref.object.sha;
  var commit=ghGet(base+'/git/commits/'+commitSha),treeSha=commit.tree.sha;
  var blob=ghPost(base+'/git/blobs',{content:Utilities.base64Encode(content,Utilities.Charset.UTF_8),encoding:'base64'});
  var tree=ghPost(base+'/git/trees',{base_tree:treeSha,tree:[{path:filePath,mode:'100644',type:'blob',sha:blob.sha}]});
  var newCommit=ghPost(base+'/git/commits',{message:commitMessage,tree:tree.sha,parents:[commitSha]});
  UrlFetchApp.fetch(base+'/git/refs/heads/main',{method:'PATCH',headers:headers,payload:JSON.stringify({sha:newCommit.sha}),muteHttpExceptions:true});
  Logger.log('  GitHub push OK: ' + filePath + ' (' + (content.length/1024).toFixed(0) + ' KB)');
}


// ============================================================
// HELPER — Format date as IST
// ============================================================
function formatDate(d) {
  return Utilities.formatDate(d, 'Asia/Kolkata', 'dd MMM yyyy hh:mm a') + ' IST';
}


// ============================================================
// ONE-TIME SETUP — Run once to store your GitHub token
// Delete token value from code immediately after running
// ============================================================
function setupGitHubToken() {
  var token = 'PASTE_YOUR_GITHUB_TOKEN_HERE';
  PropertiesService.getScriptProperties().setProperty('GITHUB_TOKEN', token);
  Logger.log('✅ Token saved. DELETE the token value from this function now!');
}