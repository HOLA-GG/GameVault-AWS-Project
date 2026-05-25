## 2025-05-15 - Redundant Schema Inspections
**Learning:** Calling `ensure_schema_compatibility()` (which uses SQLAlchemy `inspect(engine)`) outside of a "run-once" guard in `init_database()` caused expensive database introspection to occur on every call to `ensure_tables()` or `database_healthcheck()`. Since these are often called per-request or per-operation, it introduced significant overhead.
**Action:** Always guard schema migration/compatibility checks with a initialization flag (like `_database_initialized`) to ensure they only run once per application lifecycle.
