# =============================================================================
# SolarSquare Dashboard — BigQuery Data Fetcher
# Runs daily via GitHub Actions at 10:30 AM IST
# Outputs 3 JSON files → read by index.html dashboard
# =============================================================================

from google.cloud import bigquery
import json, os
from datetime import datetime, timedelta, timezone

client = bigquery.Client(project="presales-442917")

# Yesterday's date (same logic as your App Script)
yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime('%Y-%m-%d')

print(f"{'='*60}")
print(f"SolarSquare Data Fetch — {datetime.now().strftime('%d %b %Y %H:%M UTC')}")
print(f"Fetching data up to: {yesterday}")
print(f"{'='*60}\n")

os.makedirs('data', exist_ok=True)


# =============================================================================
# QUERY 1 — REFERRAL EFFORT DATA
# Source: Your Effort App Script (exact same SQL, output renamed for clarity)
# HTML uses: action_date, month, year, city, sub_channel, BQL, MS, MD, Order, HOTO
# =============================================================================

referral_effort_query = f"""
DECLARE d1 DATE DEFAULT DATE('2025-10-01');
DECLARE d2 DATE DEFAULT DATE('{yesterday}');

WITH
date_list AS (
  SELECT date_ AS Action_Date
  FROM UNNEST(GENERATE_DATE_ARRAY(d1, d2, INTERVAL 1 DAY)) AS date_
),

LEAD_BASE AS (
  SELECT DISTINCT Phone_Number
  FROM `presales-442917.leadcsv.Samagam`
  WHERE DATE(created_on) BETWEEN d1 AND d2
  AND Phone_Number IS NOT NULL
),

BQL_BASE AS (
  SELECT DISTINCT Phone_Number
  FROM `presales-442917.leadcsv.Samagam`
  WHERE DATE(created_on) BETWEEN d1 AND d2
  AND PincodeStatus = 'Active'
  AND Monthly_Bill_Amount NOT IN ('<1500', '< 1500')
  AND Exception IS NULL
  AND Phone_Number IS NOT NULL
),

DEV_CONFIRMATION AS (
  SELECT DISTINCT Phone_Number
  FROM `presales-442917.leadcsv.Samagam`
  WHERE COALESCE(DATE(Latest_Dev_Confirmed_At), DATE(SIQ_DEV_Confirmed_At)) BETWEEN d1 AND d2
),

DEV_DONE AS (
  SELECT DISTINCT Phone_Number
  FROM `presales-442917.leadcsv.Samagam`
  WHERE COALESCE(DATE(dev_details_dev_done_on), DATE(Latest_Dev_Done_At)) BETWEEN d1 AND d2
),

DESIGN_DONE AS (
  SELECT DISTINCT Phone_Number
  FROM `presales-442917.leadcsv.Samagam`
  WHERE COALESCE(DATE(dev_details_design_done_on), DATE(DES_Done_At)) BETWEEN d1 AND d2
),

MEETING_SCHEDULED AS (
  SELECT DISTINCT Phone_Number
  FROM `presales-442917.leadcsv.Samagam`
  WHERE DATE(Meeting_Scheduled_Date) BETWEEN d1 AND d2
),

MEETING_DONE AS (
  SELECT DISTINCT Phone_Number
  FROM `presales-442917.leadcsv.Samagam`
  WHERE DATE(Meeting_Done_Date) BETWEEN d1 AND d2
),

ORDER_BASE AS (
  SELECT DISTINCT Phone_Number
  FROM `presales-442917.leadcsv.Samagam`
  WHERE DATE(Order_closure_Date) BETWEEN d1 AND d2
),

HOTO_BASE AS (
  SELECT DISTINCT Phone_Number
  FROM `presales-442917.leadcsv.Samagam`
  WHERE DATE(Approved_by_customer_Date) BETWEEN d1 AND d2
),

MASTER_BASE AS (
  SELECT DISTINCT Phone_Number FROM (
    SELECT * FROM LEAD_BASE
    UNION ALL SELECT * FROM BQL_BASE
    UNION ALL SELECT * FROM DEV_CONFIRMATION
    UNION ALL SELECT * FROM DEV_DONE
    UNION ALL SELECT * FROM DESIGN_DONE
    UNION ALL SELECT * FROM MEETING_SCHEDULED
    UNION ALL SELECT * FROM MEETING_DONE
    UNION ALL SELECT * FROM ORDER_BASE
    UNION ALL SELECT * FROM HOTO_BASE
  )
),

SAMAGAM_MAPPING AS (
  SELECT *
  FROM `presales-442917.leadcsv.Samagam`
  QUALIFY ROW_NUMBER() OVER (PARTITION BY Phone_Number, Lead_ID ORDER BY Last_Action_Date DESC) = 1
),

MASTER_DATA AS (
  SELECT
    A.Phone_Number,
    COALESCE(B.Lead_ID, B.opportunity_id)          AS Lead_ID,
    COALESCE(B.LSQ_City, B.Cluster)                AS CITY,
    B.Source_Class,
    B.Source_Sub_Class,
    B.SalesChannel,
    B.LRM_Email_Id,
    B.Exception,
    B.PincodeStatus,
    COALESCE(B.Monthly_Bill_Amount, B.Monthly_Bill) AS Monthly_Bill_Amount,
    B.Created_On,
    COALESCE(B.Latest_Dev_Confirmed_At, B.SIQ_DEV_Confirmed_At) AS DEV_Confirmed_At,
    COALESCE(B.dev_details_dev_done_on, B.Latest_Dev_Done_At)   AS Dev_Done_At,
    COALESCE(B.dev_details_design_done_on, B.DES_Done_At)       AS DES_Date,
    B.Meeting_Scheduled_Date,
    B.Meeting_Done_Date,
    B.Order_closure_Date,
    B.Approved_by_customer_Date
  FROM MASTER_BASE A
  LEFT JOIN SAMAGAM_MAPPING B ON A.Phone_Number = B.Phone_Number
),

LEAD_DATA AS (
  SELECT *,
    CASE
      WHEN Source_Class LIKE '%Referral%' OR Source_Class LIKE '%Customer App%' THEN 'Referral'
      ELSE 'Others'
    END AS Source_Class_final,
    CASE
      WHEN Source_Class LIKE '%Referral%'   THEN COALESCE(Source_Sub_Class, 'WhatsApp')
      WHEN Source_Class LIKE '%Customer App%' THEN 'Customer_App'
      ELSE Source_Sub_Class
    END AS Source_Sub_Class_final,
    CASE
      WHEN Meeting_Done_Date IS NOT NULL THEN
        CASE
          WHEN Dev_Done_At < Meeting_Done_Date AND DES_Date < Meeting_Done_Date THEN 'SO'
          ELSE 'BAU'
        END
      WHEN Meeting_Scheduled_Date IS NOT NULL THEN 'SO'
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
    l.DELIVERY_TYPE,
    l.SalesChannel,
    l.LRM_Email_Id,
    COUNT(DISTINCT CASE WHEN DATE(l.Created_On) = d.Action_Date THEN l.Lead_ID END)                                                                  AS total_leads,
    COUNT(DISTINCT CASE WHEN DATE(l.Created_On) = d.Action_Date AND l.PincodeStatus = 'Active'
                         AND l.Monthly_Bill_Amount NOT IN ('<1500','< 1500') AND l.Exception IS NULL
                        THEN l.Lead_ID END)                                                                                                           AS bill_qualified,
    COUNT(DISTINCT CASE WHEN DATE(l.DEV_Confirmed_At)             = d.Action_Date THEN l.Lead_ID END) AS dev_confirmed,
    COUNT(DISTINCT CASE WHEN DATE(l.Dev_Done_At)                  = d.Action_Date THEN l.Lead_ID END) AS dev_done,
    COUNT(DISTINCT CASE WHEN DATE(l.DES_Date)                     = d.Action_Date THEN l.Lead_ID END) AS des_done,
    COUNT(DISTINCT CASE WHEN DATE(l.Meeting_Scheduled_Date)       = d.Action_Date THEN l.Lead_ID END) AS meeting_scheduled,
    COUNT(DISTINCT CASE WHEN DATE(l.Meeting_Done_Date)            = d.Action_Date THEN l.Lead_ID END) AS meeting_done,
    COUNT(DISTINCT CASE WHEN DATE(l.Order_closure_Date)           = d.Action_Date THEN l.Lead_ID END) AS order_closure,
    COUNT(DISTINCT CASE WHEN DATE(l.Approved_by_customer_Date)    = d.Action_Date THEN l.Lead_ID END) AS approved_by_customer
  FROM date_list d
  LEFT JOIN LEAD_DATA l
  ON d.Action_Date IN (
    DATE(l.Created_On),
    DATE(l.DEV_Confirmed_At),
    DATE(l.Dev_Done_At),
    DATE(l.DES_Date),
    DATE(l.Meeting_Scheduled_Date),
    DATE(l.Meeting_Done_Date),
    DATE(l.Order_closure_Date),
    DATE(l.Approved_by_customer_Date)
  )
  GROUP BY
    d.Action_Date,
    l.CITY,
    l.Source_Class_final,
    l.Source_Sub_Class_final,
    l.DELIVERY_TYPE,
    l.SalesChannel,
    l.LRM_Email_Id
)

-- Final SELECT — only columns the dashboard needs (keeps JSON small)
SELECT
  FORMAT_DATE('%d-%m-%Y', Action_Date)  AS action_date,   -- matches pd() in HTML
  EXTRACT(MONTH FROM Action_Date)        AS month,
  EXTRACT(YEAR  FROM Action_Date)        AS year,
  CITY                                   AS city,
  Source_Sub_Class_final                 AS sub_channel,
  SUM(bill_qualified)                    AS BQL,
  SUM(meeting_scheduled)                 AS MS,
  SUM(meeting_done)                      AS MD,
  SUM(order_closure)                     AS `Order`,
  SUM(approved_by_customer)              AS HOTO
FROM EFFORT_DATA
WHERE Source_Class_final = 'Referral'
GROUP BY action_date, month, year, city, sub_channel
ORDER BY PARSE_DATE('%d-%m-%Y', FORMAT_DATE('%d-%m-%Y', Action_Date)) DESC
"""


# =============================================================================
# QUERY 2 — REFERRAL LEAD LEVEL DATA
# Source: Your Lead App Script (exact same SQL)
# HTML uses: city, sub_channel, created, msD, mdD, ordD, hotoD
# =============================================================================

referral_leads_query = f"""
WITH
BQL_BASE AS (
  SELECT DISTINCT Opportunity_Id, Lead_ID
  FROM `presales-442917.leadcsv.Samagam`
  WHERE DATE(created_on) BETWEEN DATE('2025-09-01') AND DATE('{yesterday}')
  AND PincodeStatus = 'Active'
  AND Monthly_Bill_Amount NOT IN ('<1500','< 1500')
  AND Exception IS NULL
  QUALIFY ROW_NUMBER() OVER (PARTITION BY Opportunity_Id ORDER BY Last_Action_Date DESC) = 1
),

SAMAGAM_MAPPING AS (
  SELECT *
  FROM `presales-442917.leadcsv.Samagam`
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
    A.Opportunity_Id,
    A.Lead_ID,
    COALESCE(B.LSQ_City, B.Cluster)                                      AS CITY,
    B.Source_Class,
    B.Source_Sub_Class                                                    AS Source_Sub_Class_final,
    B.Created_On,
    B.Meeting_Scheduled_Date,
    B.Meeting_Done_Date,
    B.Order_closure_Date,
    B.Approved_by_customer_Date,
    CASE
      WHEN B.Meeting_Done_Date IS NOT NULL THEN
        CASE WHEN B.DES_Done_At < B.Meeting_Done_Date THEN 'SO' ELSE 'BAU' END
      WHEN B.DES_Done_At IS NOT NULL    THEN 'SO'
      WHEN B.Latest_Dev_Done_At IS NOT NULL THEN 'SO'
      ELSE 'NA'
    END AS delivery_type
  FROM BQL_BASE A
  LEFT JOIN SAMAGAM_MAPPING B ON A.Opportunity_Id = B.Opportunity_Id
)

-- Final SELECT — only 7 columns the dashboard actually needs
SELECT
  CITY                                      AS city,
  Source_Sub_Class_final                    AS sub_channel,
  CAST(Created_On AS STRING)                AS created,
  CAST(Meeting_Scheduled_Date AS STRING)    AS msD,
  CAST(Meeting_Done_Date AS STRING)         AS mdD,
  CAST(Order_closure_Date AS STRING)        AS ordD,
  CAST(Approved_by_customer_Date AS STRING) AS hotoD
FROM MASTER_DATA
WHERE Source_Class IN ('Referral', 'Customer App')
"""


# =============================================================================
# HELPER — Run query and save as JSON
# =============================================================================
def run_and_save(query, filename, description):
    print(f"▶ Running: {description}")
    try:
        df = client.query(query).to_dataframe()

        # Replace NaT / None / 'None' strings with null in JSON
        df = df.where(df.notna(), other=None)
        for col in df.select_dtypes(include='object').columns:
            df[col] = df[col].replace({'None': None, 'NaT': None, 'nan': None})

        records = df.to_dict(orient='records')
        filepath = f'data/{filename}'

        with open(filepath, 'w') as f:
            json.dump(records, f, default=str)

        size_kb = os.path.getsize(filepath) / 1024
        print(f"  ✅ Saved {filename} — {len(records):,} rows — {size_kb:.1f} KB\n")

    except Exception as e:
        print(f"  ❌ FAILED: {filename} — {str(e)}\n")
        raise


# =============================================================================
# RUN ALL QUERIES
# =============================================================================
run_and_save(referral_effort_query, 'referral_effort.json', 'Referral Effort Data')
run_and_save(referral_leads_query,  'referral_leads.json',  'Referral Lead Level Data')

print("="*60)
print("All queries complete ✅")
print(f"Finished at: {datetime.now().strftime('%d %b %Y %H:%M UTC')}")
print("="*60)
