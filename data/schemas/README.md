# Data schemas

The Pydantic schemas used by the ingestion layer are the source of truth. They live in
[`backend/app/data/load.py`](../../backend/app/data/load.py). Column lists per CSV:

| Dataset | Columns |
|---|---|
| `products.csv` | `product_id, name, category, unit_cost, unit_price, shelf_life_days` |
| `stores.csv` | `store_id, name, region, city, size_sqft` |
| `suppliers.csv` | `supplier_id, name, region, nominal_lead_time_days, capacity_units_per_day, min_order_qty, reliability_hint` |
| `supplier_products.csv` | `supplier_id, product_id, unit_cost, eligible` |
| `inventory.csv` | `snapshot_date, product_id, store_id, on_hand_units, in_transit_units` |
| `sales.csv` | `sale_date, product_id, store_id, units_sold, revenue, promotion` |
| `purchase_orders.csv` | `po_id, supplier_id, product_id, store_id, units, order_date, expected_delivery_date, actual_delivery_date, status` |
| `store_transfers.csv` | `transfer_id, product_id, from_store_id, to_store_id, units, created_date, status` |
| `promotions.csv` | `product_id, store_id, start_date, end_date, uplift_factor` |
| `labels_ground_truth.csv` | `event_type, payload` — synthetic labels for evaluation |

---
*Author: **Pradeep Sahoo**.*
