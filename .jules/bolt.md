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

## 2025-08-01 - Consolidating Global Counts with Status Grouping
**Learning:** Calculating a total table count separately from a `GROUP BY` query on a categorical column (like `status`) creates a redundant database roundtrip. Since the sum of individual group counts (including `NULL` if handled or known to be non-null) equals the total count, the scalar query can be eliminated.
**Action:** Always derive total counts from existing categorical grouping results in Python to reduce roundtrips in dashboard and statistics routes.
## 2026-06-12 - Consolidating Aggregation Queries
**Learning:** Performing a standalone `COUNT` query followed by a `GROUP BY` query on the same table is often redundant if the grouped results cover all possible values. Summing the grouped counts in Python saves a database round-trip without compromising data accuracy.
**Action:** Always check if a total count can be derived from existing grouped aggregations in the same transaction to reduce database latency.

## 2025-05-23 - Short-circuiting Unfiltered Collections
**Learning:** Even an optimized O(N) loop adds measurable overhead for large collections when no filtering is required. Short-circuiting to `list(items)` for a shallow copy before sorting is significantly faster than an iterative `append` loop. Additionally, deferring property extraction (like `juego['plataforma']`) to inside conditional blocks avoids thousands of redundant assignments in hot paths.
**Action:** Implement explicit short-circuits for "all" views and use native constructors for shallow copies when only sorting is needed.

## 2026-06-15 - Missing Indexes on Frequently Queried Fields
**Learning:** Tables like `users` and `games` that grow significantly over time cause query latency to increase linearly (O(N)) if fields used in `WHERE` or `ORDER BY` lack indexes.
**Action:** Add `index=True` to core model fields (e.g., `visibility`, `created_at`, `updated_at`) and ensure `ensure_schema_compatibility` includes idempotent SQL (`CREATE INDEX IF NOT EXISTS`) to optimize existing production environments.

## 2026-06-11 - Redundant Database Lookups in Decorated Routes
**Learning:** Routes protected by decorators like `@require_login` often have the user object already fetched and cached in Flask's `g` object. Performing an explicit `obtener_usuario_por_id` within the route body creates a redundant O(1) database round-trip.
**Action:** Always check `g.current_user` before performing a manual user lookup in authenticated routes.

## 2026-06-11 - Redundant Branching in Insight Loops
**Learning:** Performing multiple independent `if` checks on the same property (like game priority) within an O(N) loop adds unnecessary branching overhead.
**Action:** Nest dependent logic (like "next focus" selection) inside the primary property check to minimize CPU cycles per iteration.

## 2026-06-14 - Selective SQL Aggregation vs In-Memory Loops
**Learning:** Offloading metrics to SQL aggregations is a massive win when you don't need the underlying raw data (e.g., the Profile page). However, in views where the full collection is already fetched for in-memory filtering/sorting (e.g., the Dashboard), adding redundant SQL aggregation queries actually increases database round-trips and latency.
**Action:** Use SQL aggregations for "stats-only" views. Use a single-pass in-memory loop for views that already fetch the full dataset to maintain O(1) database round-trip complexity for metrics.

## 2026-06-15 - Deferring ISO Serialization in Large Collections
**Learning:** Pre-formatting `datetime` objects to ISO strings in the data layer (`obtener_juegos_por_usuario`) for every item in a collection introduces significant overhead in memory allocation and string processing. This is especially wasteful if the data is subsequently filtered or paginated. Native `datetime` comparisons are also faster than ISO string comparisons.
**Action:** Defer date serialization to the last possible moment (template enrichment layer). Ensure consistent use of UTC-aware datetimes when comparing against `now()` to avoid `TypeError` in heterogeneous environments (e.g., SQLite vs Postgres).

## 2026-06-16 - Breaking Contracts for Performance
**Learning:** Attempting to optimize  by removing unused metrics and changing the function signature led to a breaking change. In a monolithic Flask app where functions are shared between routes and templates, performance gains must be balanced against maintaining backward compatibility (both in parameters and return dictionary keys).
**Action:** When optimizing shared utility functions, preserve the original signature (parameters) and return keys even if they are currently "unused" to prevent runtime errors and regressions in consumers you might have missed. Optimize the *calculation* of those values instead of deleting them.
## 2025-08-05 - Breaking Contracts for Performance
**Learning:** Attempting to optimize `build_dashboard_insights` by removing unused metrics and changing the function signature led to a breaking change. In a monolithic Flask app where functions are shared between routes and templates, performance gains must be balanced against maintaining backward compatibility (both in parameters and return dictionary keys).
**Action:** When optimizing shared utility functions, preserve the original signature (parameters) and return keys even if they are currently "unused" to prevent runtime errors and regressions in consumers you might have missed. Optimize the *calculation* of those values instead of deleting them.

## 2025-08-10 - Short-circuiting String Search in Hot Loops
**Learning:** In O(N) loops that perform substring searches across multiple fields, reordering the search criteria to check shorter, categorical fields (like platform or state) before large text blocks (like titles or descriptions) allows for faster short-circuiting. This avoids expensive case-folding and searching on long strings in many cases.
**Action:** Always prioritize shorter or more likely-to-match fields in multi-criteria string search filters to maximize the benefits of short-circuit evaluation.

## 2025-08-10 - Streamlining Fallback Date Logic
**Learning:** Calculating an "effective date" (e.g., latest of updated or created) using nested if/else or redundant checks in a loop adds unnecessary branching. Using `max()` with `ensure_dt` wrappers provides a concise and efficient way to handle fallbacks and ensure comparisons remain safe between naive and aware objects.
**Action:** Use `max()` for consolidating multiple timestamp fallbacks in loops to reduce branching and improve code scannability.

## 2025-08-12 - Deferred Metadata Enrichment for Log Collections
**Learning:** Eagerly serializing dates to ISO strings and assigning UI-specific metadata (like badge classes) for large audit log collections (N=500) creates significant $O(N)$ overhead in CPU and memory allocations. This is especially wasteful in views that subsequently group or paginate the data, as most enriched records are never rendered.
**Action:** Implement a lazy enrichment pattern where the data layer returns raw objects (using native `datetime` for fast comparisons) and a separate enrichment helper is called only on the specific subset of records destined for the final view.

## 2026-06-18 - Function Call Overhead (max vs if/else) in Hot Loops
**Learning:** In a hot loop (N=1000), using the built-in `max(a, b)` function is significantly slower than an inline `a if a > b else b` comparison due to function call overhead. Benchmarks showed a ~35% improvement when inlining the logic.
**Action:** Prefer inline comparisons over built-in aggregation functions like `max()` or `min()` inside large loops where performance is critical.

## 2026-06-18 - Duplicate Keys in Dictionary Literals
**Learning:** Duplicate keys in a dictionary literal (e.g., `{'k': v1, 'k': v2}`) cause the last value to silently overwrite previous ones. In `audit_log_to_dict`, this meant an intended optimization (lazy date formatting) was being bypassed because a redundant, non-lazy assignment appeared first in the literal.
**Action:** Audit dictionary literals in hot paths for redundant keys that might defeat performance optimizations or cause subtle logic bugs.

## 2026-06-20 - Consolidating Aggregations for Filtered Collections
**Learning:** Using an unfiltered subquery to aggregate metrics (like game counts) across an entire table before joining with a filtered user list is a major bottleneck as the dataset grows. Consolidating the aggregation directly into the main query with a `group_by` allows the database to push filters down, significantly reducing the number of rows processed.
**Action:** Always prefer direct joins with `group_by` over unfiltered aggregation subqueries when the parent table has highly selective filters (e.g., visibility, opt-in status). Use inner joins for "must-have-content" views and outer joins for general administrative lists.

## 2026-06-25 - Overhead of collections.Counter and .get() in Hot Loops
**Learning:** In hot loops (N=5000), `collections.Counter` and dictionary `.get()` method calls introduce measurable overhead compared to plain dictionaries and bracket access `[]`. Additionally, `Counter.most_common(1)` is slower than `max(dict, key=dict.get)` for finding a single dominant element.
**Action:** Use plain dictionaries for counting in performance-critical loops and prefer bracket access for keys guaranteed by the data layer. Use `max()` with a key function for $O(N)$ dominant element lookups instead of sorting-based methods.

## 2025-05-23 - Micro-optimizations in Dashboard Insights Loop
**Learning:** In hot loops (N=1000+), extracting helper functions to the module level and removing redundant normalization calls (like ) significantly reduces CPU overhead. Replacing  with  and using  over  checks further streamlines execution.
**Action:** Always verify that the data layer provides normalized types to avoid redundant checks in view-layer loops. Move inner helper functions to module level to avoid re-definition overhead.

## 2025-05-23 - Micro-optimizations in Dashboard Insights Loop
**Learning:** In hot loops (N=1000+), extracting helper functions to the module level and removing redundant normalization calls (like ensure_dt) significantly reduces CPU overhead. Replacing .get() with if key in dict and using isinstance() over __class__ checks further streamlines execution.
**Action:** Always verify that the data layer provides normalized types to avoid redundant checks in view-layer loops. Move inner helper functions to module level to avoid re-definition overhead.

## 2026-07-29 - Attribute Lookup Overhead in SQLAlchemy Row
**Learning:** Accessing database columns dynamically using `getattr(row, field)` on a SQLAlchemy `Row` object from selective projections triggers standard attribute lookup and raises costly `AttributeError` exceptions for missing/omitted fields. Utilizing the dict-like `_mapping` view of SQLAlchemy `Row` (via `row._mapping.get(field)`) completely avoids this exception-handling overhead and is over 2.5x faster.
**Action:** Use `hasattr(row, '_mapping')` to detect SQLAlchemy `Row` objects in hot row-to-dictionary mappers, and prefer `_mapping.get(field)` over `getattr()` or direct attribute access.

## 2026-07-31 - Overhead of Python Lambda Key Extractors in Hot Sorting Loops
**Learning:** Using standard Python lambda functions (e.g., `lambda j: j['key']`) inside hot list sorting loops is relatively slow because the Python interpreter must allocate new stack frames and evaluate Python bytecodes for every element comparison. Replacing lambdas with standard C-optimized operators like `operator.itemgetter` completely bypasses Python bytecode evaluation, speeding up hot-loop dictionary list sorting by ~30% to ~50%.
**Action:** Prefer C-implemented operator functions such as `operator.itemgetter` or `operator.attrgetter` over lambda functions for list sorting keys on objects or dictionaries.

## 2026-06-21 - Bypassing ORM Hydration in Large Collections
**Learning:** For read-only hot paths that return large collections (like a user's entire game library), fetching specific columns directly via `session.execute(select(...))` is significantly faster than fetching full ORM entities. This avoids the overhead of SQLAlchemy's Identity Map and the instantiation of full model objects (hydration).
**Action:** Use Core-style selects and manual dictionary mapping for frequently accessed list views where full ORM functionality (like relationship lazy-loading or dirty tracking) is not required.

## 2026-07-04 - Schema-Resilient ORM Hydration Bypass
**Learning:** Bypassing ORM hydration by selecting specific columns improves performance but can lead to code duplication and fragility if columns are hardcoded in multiple fetchers. Using `select(Model.__table__)` via `session.execute()` provides the same performance benefit (returning raw Row objects) while remaining resilient to schema changes.
**Action:** Pair `select(Model.__table__)` with a centralized private mapping helper to achieve hydration-free performance without sacrificing DRY principles or schema robustness.

## 2026-07-15 - Deferred User Enrichment in Grouped Collections
**Learning:** Eagerly fetching user metadata (names, emails) for all unique accounts in a large collection (e.g., 500 audit logs) before pagination introduces significant database and hydration overhead. Since most accounts won't be visible on the first page, this work is mostly wasted.
**Action:** Defer metadata lookups until after pagination. Calculate the set of unique identifiers present only on the current page and fetch their metadata in a single batch query.

## 2026-07-20 - Explicitness vs. Micro-optimization in Transactions
**Learning:** Removing a manual duplicate check (SELECT before INSERT) to rely solely on database `IntegrityError` might seem like a performance win by reducing one query. However, in low-contention paths, this can be rejected if it makes business logic (like anti-spam) implicit or harder to trace. Functional correctness and explicitness often outweigh the gain of a single O(1) query in a non-hot path.
**Action:** Preserve explicit validation logic in models unless the path is confirmed to be a high-contention bottleneck where every millisecond in the transaction critical.

## 2026-07-12 - Singleton S3 Client and Storage Context Resilience
**Learning:** Initializing a `boto3.client` on every request in a loop (e.g., for signed URLs in a dashboard) is a significant CPU bottleneck. Moving this to a singleton pattern solves the speed issue, but in a Flask app, storage utilities are often called both from request contexts and standalone scripts. Relying solely on `current_app.config` causes `RuntimeError` in non-request contexts.
**Action:** Implement storage clients as singletons. Use a tiered configuration lookup: try `current_app.config` first for request-time overrides, and fall back to module-level constants (from `os.environ`) within a `try...except RuntimeError` block to maintain script compatibility.

## 2026-07-22 - SQL Projection for Partial User Lookups
**Learning:** Fetching full records or using `select(Model.__table__)` in batch lookups (like `obtener_usuarios_por_ids`) introduces unnecessary database I/O and network overhead when only a few identity fields (ID, name, email) are needed for UI enrichment. Bypassing ORM hydration while still returning normalized dictionaries requires mapping helpers that can handle partial results.
**Action:** Add a `fields` parameter to batch fetchers to enable SQL projection. Update mapping helpers (like `_user_row_to_dict`) to safely handle both dictionary and object inputs, ensuring date normalization is applied only when relevant fields are present.

## 2026-07-15 - Hardening Row-to-Dict Helpers for Selective Projection
**Learning:** Implementing selective SQL projection improves performance but can cause regressions in helper functions (like `_user_row_to_dict` or `_audit_log_row_to_dict`) that rely on direct attribute access (`row.field`). If a field is excluded from the projection, it raises an `AttributeError`.
**Action:** Always use `getattr(row, field, default)` in mapping helpers. This ensures robustness when handling partial results from SQL projection without requiring brittle type checks or breaking existing call-sites that expect a full dictionary structure.

## 2026-07-25 - Regex-based Redaction for Performance
**Learning:** Using an iterative `any(p in key for p in patterns)` loop in a hot path (like audit log redaction) has (N \times M)$ complexity. Replacing it with a pre-compiled regular expression (`re.compile('|'.join(patterns))`) moves the heavy lifting to the optimized C-based regex engine, achieving (M)$ complexity and a measurable speedup.
**Action:** Always prefer pre-compiled regex for multi-pattern string matching in performance-critical loops.

## 2026-07-28 - Pre-lowercased Fields for Hot-Path Searching and Sorting
**Learning:** Performing multiple `.lower()` string conversions and allocations inside an $O(N)$ filtering or sorting loop (like user-triggered text search) introduces measurable CPU and memory garbage collection overhead. Pre-calculating these lowercase values once during database-to-dictionary serialization (`_game_row_to_dict`) reduces search-time latency by avoiding dynamic string allocation entirely.
**Action:** Pre-calculate lowercase properties for fields frequently subjected to user-initiated search, filtering, or string-based sorting, while using safe fallback getters to maintain robustness.

## 2026-07-31 - Fast String Lookup & Single-pass Dictionary Grouping
**Learning:** Performing repeated `.upper()` case-folding on standard uppercase string constants inside rendering loops (like log tables) introduces unnecessary string allocations and CPU interpreter overhead. Additionally, performing double dictionary lookups (`if key not in d` followed by `d[key]`) during high-frequency collection grouping adds up to ~30% lookup overhead.
**Action:** Always attempt a direct fast-path lookup first before applying string modifications. For collection grouping, use `.get(key)` to retrieve the bucket in a single lookup and conditionally assign it.
