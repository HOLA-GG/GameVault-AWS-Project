## 2026-09-15 - Strict Input Truncation for Admin Query Parameters
**Vulnerability:** Unbounded query parameter lengths in administrative routes (`/admin/collections`, `/admin/logs`, `/admin/logs/export`) could lead to excessive memory allocation during request processing and audit log details inflation.
**Learning:** Even if data queries or model layers handle filters safely, accepting arbitrarily long query string values on administrative endpoints can degrade application performance and cause log bloat when these parameters are audited.
**Prevention:** Enforce strict length bounds (e.g. `[:36]`, `[:80]`, `[:20]`, `[:50]`) on all query parameter string extractions at the route controller layer.

## 2026-09-16 - Dynamic Storage Backend Resolution and Filename Sanitization for Presigned POST Keys
**Vulnerability:** In `crear_presigned_upload`, relying on module-level `STORAGE_BACKEND` instead of dynamic `current_app.config` caused config mismatches, while unsanitized filename parameters in presigned POST key generation posed object path manipulation risks.
**Learning:** Storage helper functions must dynamically resolve application configuration via `current_app.config.get('STORAGE_BACKEND', STORAGE_BACKEND)` inside `try...except RuntimeError` and sanitize user-provided filename strings with `secure_filename` before interpolating them into storage object keys.
**Prevention:** Always sanitize object key components and read storage configuration dynamically from Flask application context.

## 2026-09-22 - Audit Trail Hardening on Early-Return Token Validation Paths
**Vulnerability:** In `/verify-token` and `/reset-password/<token>`, early length-checking and empty-token guard clauses returned responses without recording `TOKEN_VALIDATION_FAILED` audit log entries.
**Learning:** Early validation returns prior to model function execution can create auditing blind spots where malformed or oversized authentication attempt inputs bypass audit trail recording.
**Prevention:** Always record `crear_log_audit` with `status='FAILED'` before returning on early validation failure branches in security-sensitive route handlers.

## 2026-09-28 - Bounded Stream Reading for In-Memory Image Processing
**Vulnerability:** In `procesar_imagen_base64`, calling `archivo.read()` without size bounds on unauthenticated uploads could cause memory exhaustion DoS when processing large files on the public demo endpoint.
**Learning:** File stream reads in memory processing functions must pass explicit byte limits (`archivo.read(max_bytes + 1)`) matching application configuration (`MAX_IMAGE_UPLOAD_BYTES`), rejecting streams that exceed the limit before base64 encoding or buffering.
**Prevention:** Always bound file stream reads with `read(max_bytes + 1)` when processing uploaded file objects in memory.

## 2026-10-05 - Audit Trail Coverage on ID Format Validation Failure Branches
**Vulnerability:** In `eliminar_juego_ruta` and `editar_juego_ruta`, early-return guard clauses checking `is_valid_id(game_id)` returned early without recording `crear_log_audit` entries when malformed or oversized `game_id` values were supplied.
**Learning:** Early validation returns on route handlers prior to database model lookups can create auditing blind spots where invalid or malformed resource manipulation attempts evade audit trail tracking.
**Prevention:** Always invoke `crear_log_audit` with `status='FAILED'` and an explicit reason before returning early on ID format validation failures.

## 2026-10-12 - Audit Trail Coverage on Early Validation Password Reset Requests
**Vulnerability:** In `forgot_password` and `forgot_password_manual`, early validation returns on empty or oversized inputs returned without recording `PASSWORD_RESET_REQUEST` failed audit log entries.
**Learning:** Early validation guard clauses returning before user resolution create auditing blind spots where malformed password recovery requests evade audit trail tracking and security monitoring.
**Prevention:** Always invoke `crear_log_audit` with `status='FAILED'` and an explicit reason before returning early on validation failures in password reset request handlers.

## 2026-10-18 - Exception Handling and Failure Audit Trail Logging on Administrative Data Exports
**Vulnerability:** Unhandled exceptions during administrative CSV audit log exports (`/admin/logs/export`) could trigger 500 server crashes and bypass audit log recording for failed administrative data exports.
**Learning:** Administrative data export controllers that lack try-except error handling can crash on database or stream generation errors and create auditing blind spots when failure events go unrecorded.
**Prevention:** Always wrap administrative data export routines in `try...except` blocks, recording `crear_log_audit` with `status='FAILED'` before redirecting with a sanitized error flash message.

## 2026-10-25 - Defensive Type Coercion for Audit Logging Parameters
**Vulnerability:** In `crear_log_audit`, slicing parameters (`action[:80]`, `resource[:80]`, `status[:20]`, `user_agent[:500]`) without string coercion caused `TypeError` crashes when non-string values (such as integer HTTP status codes) were passed.
**Learning:** Slicing non-string types in logging helpers crashes audit record creation and can trigger cascading 500 errors in route error handlers.
**Prevention:** Always perform explicit `str(...)` type coercion before applying length bounds to string parameters in audit logging functions.

## 2026-11-02 - Defensive Exception Handling and Audit Trail Logging for Admin Collection Views
**Vulnerability:** Unhandled database exceptions in administrative collection management (`/admin/collections`) could trigger 500 server crashes and bypass audit trail logging for failed administrative collection operations.
**Learning:** Administrative collection listing endpoints that lack try-except error handling can crash on database or query execution errors, exposing 500 internal server errors and creating auditing blind spots when failure events go unrecorded.
**Prevention:** Wrap administrative data querying routines in `try...except` blocks, logging the error, recording `crear_log_audit` with `status='FAILED'`, and redirecting safely with a user-friendly flash message.

## 2026-11-09 - Exception Handling and Audit Trail Logging for Administrative User Panel
**Vulnerability:** Unhandled database exceptions in administrative user management (`/admin`) could trigger 500 server crashes and bypass audit trail logging for failed administrative user panel loads.
**Learning:** Administrative user management endpoints that lack try-except error handling can crash on database or query execution errors, exposing 500 internal server errors and creating auditing blind spots when failure events go unrecorded.
**Prevention:** Wrap administrative user panel data querying routines in `try...except` blocks, logging the error, recording `crear_log_audit` with `status='FAILED'`, and redirecting safely with a user-friendly flash message.
