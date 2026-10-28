
# Olist Raw Data Profile

## Purpose

This document records the initial profiling results for the nine raw Olist CSV datasets used by ShopSignal. The profile was generated with DuckDB using `shopsignal.transform.profiling`.

Duplicate keys are investigated as potential data-quality issues; they are not automatically removed.

## Dataset inventory

| Table | Rows | Columns |
|---|---:|---:|
| orders | 99,441 | 8 |
| order_items | 112,650 | 7 |
| order_payments | 103,886 | 5 |
| order_reviews | 99,224 | 7 |
| customers | 99,441 | 5 |
| sellers | 3,095 | 4 |
| products | 32,951 | 9 |
| geolocation | 1,000,163 | 5 |
| product_category_name_translation | 71 | 2 |

## Candidate key findings

| Table | Candidate key | Duplicate groups | Excess duplicate rows | Missing key rows |
|---|---|---:|---:|---:|
| orders | order_id | 0 | 0 | 0 |
| order_items | order_id + order_item_id | 0 | 0 | 0 |
| order_payments | order_id + payment_sequential | 0 | 0 | 0 |
| order_reviews | review_id | 789 | 814 | 0 |
| customers | customer_id | 0 | 0 | 0 |
| customers | customer_unique_id | 2,997 | 3,345 | 0 |
| sellers | seller_id | 0 | 0 | 0 |
| products | product_id | 0 | 0 | 0 |
| product_category_name_translation | product_category_name | 0 | 0 | 0 |

Geolocation ZIP prefixes are not treated as unique keys because multiple records can share a ZIP prefix.

## Initial observations

### Orders

- `order_id` is unique in the raw dataset.
- No missing or blank `order_id` values were reported.

### Order items

- The composite key `(order_id, order_item_id)` is unique.
- No missing or blank composite-key components were reported.

### Order payments

- The composite key `(order_id, payment_sequential)` is unique.
- No missing or blank composite-key components were reported.

### Order reviews

- `review_id` has 789 duplicate groups and 814 excess duplicate rows.
- No missing or blank `review_id` values were reported.
- Investigate repeated review IDs before deciding whether Silver should reject, quarantine, or retain those records.

### Customers

- `customer_id` is unique.
- `customer_unique_id` has repeated values. This field should not be assumed to uniquely identify a row in the customers table.

### Sellers and products

- The candidate keys `seller_id` and `product_id` are unique in the raw datasets.

### Product category translations

- `product_category_name` is unique in the raw dataset.

## Completed profiling and contract validation

The initial profiling is documented above. The following implementation is now available:

- A DuckDB profiling module at `src/shopsignal/transform/profiling.py`.
- Explicit Silver column type, nullability, and candidate-key contracts in `src/shopsignal/transform/schemas.py`.
- Tests covering source column order, required-field completeness, type convertibility, and declared primary-key integrity.

The source-contract tests validate convertibility to declared types; the numeric ranges above remain exploratory profiles and are not, by themselves, business-rule validation.

## Contract design principles

- Define expected types and required fields explicitly.
- Define primary and composite keys based on observed data and business meaning.
- Do not treat every repeated value as invalid.
- Make data-quality failures observable and testable.
- Document any intentional nullability and duplicate-handling decisions.



## Null and blank value findings

Only columns with observed null or blank values are listed below.

| Table | Column | Missing rows | Missing rate |
|---|---|---:|---:|
| orders | order_approved_at | 160 | 0.1609% |
| orders | order_delivered_carrier_date | 1,783 | 1.7930% |
| orders | order_delivered_customer_date | 2,965 | 2.9817% |
| order_reviews | review_comment_title | 87,658 | 88.3435% |
| order_reviews | review_comment_message | 58,256 | 58.7116% |
| products | product_category_name | 610 | 1.8512% |
| products | product_name_lenght | 610 | 1.8512% |
| products | product_description_lenght | 610 | 1.8512% |
| products | product_photos_qty | 610 | 1.8512% |
| products | product_weight_g | 2 | 0.0061% |
| products | product_length_cm | 2 | 0.0061% |
| products | product_height_cm | 2 | 0.0061% |
| products | product_width_cm | 2 | 0.0061% |

The profiler reported no null or blank values in the remaining columns.

### Nullability implications

- Order approval and delivery timestamps must not be assumed universally present.
- Review titles and messages are frequently absent and should be modeled as optional fields.
- Several product attributes are missing for 610 products, while four physical-dimension and weight fields are missing for two products.
- Missing values should not automatically be replaced with zero or empty strings.

## Date ranges and parsing

All profiled date columns had zero unparseable nonblank values.

| Table | Column | Minimum | Maximum |
|---|---|---|---|
| orders | order_purchase_timestamp | 2016-09-04 21:15:19 | 2018-10-17 17:30:18 |
| orders | order_approved_at | 2016-09-15 12:16:38 | 2018-09-03 17:40:06 |
| orders | order_delivered_carrier_date | 2016-10-08 10:34:01 | 2018-09-11 19:48:28 |
| orders | order_delivered_customer_date | 2016-10-11 13:46:32 | 2018-10-17 13:22:46 |
| orders | order_estimated_delivery_date | 2016-09-30 00:00:00 | 2018-11-12 00:00:00 |
| order_items | shipping_limit_date | 2016-09-19 00:15:34 | 2020-04-09 22:35:08 |
| order_reviews | review_creation_date | 2016-10-02 00:00:00 | 2018-08-31 00:00:00 |
| order_reviews | review_answer_timestamp | 2016-10-07 18:32:28 | 2018-10-29 12:27:35 |

The `shipping_limit_date` maximum extends beyond the observed order-purchase period. Investigate this during validation rather than assuming it is invalid.

## Numeric ranges and parsing

All profiled numeric columns had zero unparseable nonblank values.

| Table | Column | Minimum | Maximum |
|---|---|---:|---:|
| order_items | price | 0.85 | 6,735.00 |
| order_items | freight_value | 0.00 | 409.68 |
| order_payments | payment_sequential | 1 | 29 |
| order_payments | payment_installments | 0 | 24 |
| order_payments | payment_value | 0.00 | 13,664.08 |
| order_reviews | review_score | 1 | 5 |
| products | product_name_lenght | 5 | 76 |
| products | product_description_lenght | 4 | 3,992 |
| products | product_photos_qty | 1 | 20 |
| products | product_weight_g | 0 | 40,425 |
| products | product_length_cm | 7 | 105 |
| products | product_height_cm | 2 | 105 |
| products | product_width_cm | 6 | 118 |
| geolocation | geolocation_lat | -36.6054 | 45.0659 |
| geolocation | geolocation_lng | -101.4668 | 121.1054 |

### Numeric validation follow-ups

- `review_score` falls within the expected integer range of 1–5.
- `payment_installments` includes zero; investigate its meaning before deciding whether to reject it.
- Product weight includes zero; do not assume every zero is invalid without checking the source semantics.
- Geolocation coordinates extend beyond typical Brazilian bounds. Investigate these outliers before deciding on geographic validation rules.

## Remaining investigations

- Confirm the business meaning of repeated `review_id` values with source documentation or additional evidence.
- Profile foreign-key relationships between related tables.
- Validate timestamp sequencing and delivery-related business rules.
- Investigate numeric and geographic outliers before defining validation thresholds.
- Investigate the zero values in `payment_installments` and product weight.
- Decide whether additional business constraints should be enforced in Silver.

### Duplicate review ID investigation

The raw `order_reviews` dataset contains 789 duplicate `review_id` groups, covering 1,603 rows.

A cross-group analysis found:

- All 789 groups contain records associated with multiple orders.
- Zero groups contain conflicting values across review score, title, message, creation timestamp, or answer timestamp.
- A representative group contains three different orders with identical review details.

**Decision:** retain all source rows and do not enforce `review_id` as a unique Silver primary key. The observed data does not establish a unique row key for this table. The underlying business meaning of the repeated review ID remains unconfirmed.
