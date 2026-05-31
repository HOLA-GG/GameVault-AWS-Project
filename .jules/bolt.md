## 2025-05-15 - Redundant Schema Inspections
**Learning:** Calling `ensure_schema_compatibility()` (which uses SQLAlchemy `inspect(engine)`) outside of a "run-once" guard in `init_database()` caused expensive database introspection to occur on every call to `ensure_tables()` or `database_healthcheck()`. Since these are often called per-request or per-operation, it introduced significant overhead.
**Action:** Always guard schema migration/compatibility checks with a initialization flag (like `_database_initialized`) to ensure they only run once per application lifecycle.

## 2025-05-22 - N+1 Query in Rating Enrichment
**Learning:** Enrichment loops (like `aplicar_ratings_showcase`) that call a database fetcher per item create an N+1 query problem. This becomes a significant bottleneck as the number of public collections grows. Offloading aggregation (AVG, COUNT) to the database using SQLAlchemy `func` and grouping by ID in a single query reduces complexity from O(N) to O(1) roundtrips.
**Action:** Implement batch-fetching methods with `GROUP BY` and `IN` for any logic that enriches lists of items with aggregated or related data.

## 2025-06-10 - O(N) Iterative Deletions in Cleanup
**Learning:** Functions like `limpiar_logs_antiguos` and `eliminar_tokens_expirados` fetched all matching records into memory and deleted them one-by-one. This causes O(N) database round-trips and high memory pressure. Batch deletions using SQLAlchemy's `delete()` construct perform the operation in O(1) round-trips and avoid loading objects.
**Action:** Use `sqlalchemy.delete` for any maintenance or cleanup tasks involving multiple records to ensure efficient execution and low memory overhead.

## 2025-06-15 - In-memory List Aggregation and Sorting
**Learning:** Functions like `obtener_resumenes_colecciones` that fetch all items (via `selectinload`) to calculate averages, counts, and perform complex multi-criteria sorting in Python create a massive O(N) memory and CPU bottleneck. SQL is significantly faster at grouping, aggregating, and sorting.
**Action:** Always offload summary metrics (avg, count, sum) and multi-column sorting to SQL subqueries. Use batch fetching for attributes that require mode calculation (like dominant platform) to maintain O(1) query complexity for the returned page.

## 2025-06-20 - Redundant Iterations and Python Sorting
**Learning:** Functions like `build_dashboard_insights` were performing 5+ passes over the same collection to calculate different metrics (using Counter, multiple loops, and filters). Additionally, admin routes were re-sorting data that already had SQL `ORDER BY` applied. Python sorts are O(N log N) and redundant if the DB already did the work.
**Action:** Consolidate multi-pass metrics into a single-pass loop. Reuse parsed objects (like datetimes) within that loop. Trust database-level ordering to avoid redundant CPU-intensive sorting in the application layer.
