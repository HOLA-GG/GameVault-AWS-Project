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

## 2025-06-25 - ISO 8601 String Comparison vs Datetime Parsing
**Learning:** Parsing ISO 8601 strings into `datetime` objects for every item in a large collection is expensive. Since ISO 8601 is lexicographically sortable, comparing strings directly for "greater than" or "less than" (e.g., for recent/stale checks) is significantly faster and logically equivalent.
**Action:** Use string comparisons for ISO 8601 dates in hot loops where only relative ordering or cutoff checks are needed.

## 2025-07-05 - In-memory Pagination of User List
**Learning:** Fetching all records from a table (like `users`) to perform in-memory pagination with `paginate_items` creates a massive (N)$ bottleneck in memory and CPU as the table grows.
**Action:** Always implement pagination at the database level using `LIMIT` and `OFFSET` (via SQLAlchemy `.limit()` and `.offset()`) paired with a separate `COUNT` query for metadata. Ensure the `page` input is sanitized with `max(1, page)` to prevent negative offset errors.

## 2025-07-10 - Dictionary Copying and Redundant Sorting
**Learning:** Creating shallow copies of dictionaries (`dict(item)`) in high-frequency loops and performing redundant sorts in Python on data already ordered by the database significantly impacts performance. Mutating transient dictionaries in-place and adding short-circuits for default views can yield immediate speed wins.
**Action:** Mutate transient processing dictionaries in-place to reduce allocations. Trust and utilize database-level ordering to skip O(N log N) Python sorts whenever possible.

## 2025-07-25 - In-place Mutation vs Metric Calculation
**Learning:** Mutating dictionaries in-place (e.g., adding signed URLs) saves memory allocations but can corrupt data for subsequent operations like summary metric calculations if not ordered correctly.
**Action:** Always perform summary calculations and dashboard insights on the original data before applying transient in-place mutations for template enrichment.

## 2025-07-25 - Case-sensitive Comparison with Constants
**Learning:** Using `.lower()` on every iteration in a hot loop (like checking game priority) adds redundant CPU cycles and string allocations. Since input is validated against a set of constants (e.g., `GAME_PRIORITY_OPTIONS`), direct case-sensitive comparison is significantly faster and safe.
**Action:** Prefer direct comparison against normalized constants in iteration loops to avoid unnecessary string processing overhead.

## 2026-06-07 - Redundant Data Fetching for Unused Metrics
**Learning:** Fetching data (like activity logs) and processing it for metrics that aren't displayed in the UI creates wasted database round-trips and CPU cycles. In this case, `recent_activity` was being calculated on every dashboard and profile load despite not being used in any template.
**Action:** Make metric calculation parameters optional and guard their processing logic. Regularly audit route data-fetching against template requirements to eliminate dead database queries.
