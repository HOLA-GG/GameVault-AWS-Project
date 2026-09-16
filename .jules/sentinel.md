## 2026-09-15 - Strict Input Truncation for Admin Query Parameters
**Vulnerability:** Unbounded query parameter lengths in administrative routes (`/admin/collections`, `/admin/logs`, `/admin/logs/export`) could lead to excessive memory allocation during request processing and audit log details inflation.
**Learning:** Even if data queries or model layers handle filters safely, accepting arbitrarily long query string values on administrative endpoints can degrade application performance and cause log bloat when these parameters are audited.
**Prevention:** Enforce strict length bounds (e.g. `[:36]`, `[:80]`, `[:20]`, `[:50]`) on all query parameter string extractions at the route controller layer.

## 2026-09-16 - Dynamic Storage Backend Resolution and Filename Sanitization for Presigned POST Keys
**Vulnerability:** In `crear_presigned_upload`, relying on module-level `STORAGE_BACKEND` instead of dynamic `current_app.config` caused config mismatches, while unsanitized filename parameters in presigned POST key generation posed object path manipulation risks.
**Learning:** Storage helper functions must dynamically resolve application configuration via `current_app.config.get('STORAGE_BACKEND', STORAGE_BACKEND)` inside `try...except RuntimeError` and sanitize user-provided filename strings with `secure_filename` before interpolating them into storage object keys.
**Prevention:** Always sanitize object key components and read storage configuration dynamically from Flask application context.
