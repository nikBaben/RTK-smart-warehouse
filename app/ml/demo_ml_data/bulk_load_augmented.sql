
-- Bulk load augmented datasets (psql):
-- psql "$DATABASE_URL" -f bulk_load_augmented.sql

BEGIN;
SET session_replication_role = replica;

\copy product FROM '/home/baben/swrtk/RTK-smart-warehouse/app/ml/demo_ml_data/products_aug.csv' WITH (FORMAT csv, HEADER true);

\copy shipment FROM '/home/baben/swrtk/RTK-smart-warehouse/app/ml/demo_ml_data/shipments_aug.csv' WITH (FORMAT csv, HEADER true);
\copy shipments FROM '/home/baben/swrtk/RTK-smart-warehouse/app/ml/demo_ml_data/shipments_aug.csv' WITH (FORMAT csv, HEADER true); -- if your table is named 'shipments'

\copy shipment_items FROM '/home/baben/swrtk/RTK-smart-warehouse/app/ml/demo_ml_data/shipment_items_aug.csv' WITH (FORMAT csv, HEADER true);

\copy delivery FROM '/home/baben/swrtk/RTK-smart-warehouse/app/ml/demo_ml_data/deliveries_aug.csv' WITH (FORMAT csv, HEADER true);
\copy deliveries FROM '/home/baben/swrtk/RTK-smart-warehouse/app/ml/demo_ml_data/deliveries_aug.csv' WITH (FORMAT csv, HEADER true); -- if your table is 'deliveries'

\copy delivery_items FROM '/home/baben/swrtk/RTK-smart-warehouse/app/ml/demo_ml_data/delivery_items_aug.csv' WITH (FORMAT csv, HEADER true);

\copy inventory_history FROM '/home/baben/swrtk/RTK-smart-warehouse/app/ml/demo_ml_data/inventory_history_aug.csv' WITH (FORMAT csv, HEADER true);

SET session_replication_role = DEFAULT;
COMMIT;
