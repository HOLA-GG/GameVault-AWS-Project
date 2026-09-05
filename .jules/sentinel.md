## 2026-09-15 - Strict Input Truncation for Admin Query Parameters
**Vulnerability:** Unbounded query parameter lengths in administrative routes (`/admin/collections`, `/admin/logs`, `/admin/logs/export`) could lead to excessive memory allocation during request processing and audit log details inflation.
**Learning:** Even if data queries or model layers handle filters safely, accepting arbitrarily long query string values on administrative endpoints can degrade application performance and cause log bloat when these parameters are audited.
**Prevention:** Enforce strict length bounds (e.g. `[:36]`, `[:80]`, `[:20]`, `[:50]`) on all query parameter string extractions at the route controller layer.
