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

## 2026-11-16 - Exception Handling and Audit Trail Logging for Administrative User Actions
**Vulnerability:** Uncaught database or runtime exceptions during administrative user deletion (`/admin/delete/<user_id>`), user editing (`/admin/edit/<user_id>`), or log clearing (`/admin/logs/clear`) could trigger 500 internal server errors and bypass audit trail logging for failed administrative actions.
**Learning:** Administrative action controllers that modify state or clean audit records must catch unexpected runtime or database errors at the route handler layer to prevent unhandled 500 crashes and record `FAILED` audit trail entries.
**Prevention:** Always wrap administrative action handlers in `try...except` blocks, logging the error with `current_app.logger.error`, recording `crear_log_audit` with `status='FAILED'`, and redirecting safely with a user-friendly flash message.

## 2026-11-23 - Strict Input Parameter Validation and Audit Trail Coverage on Administrative Log Cleanup
**Vulnerability:** In `/admin/logs/clear`, missing, non-numeric, or out-of-bounds `dias` parameters fell back to default values, allowing malformed administrative log cleanup requests to execute and evade failure audit logging.
**Learning:** Destructive administrative operations that fall back to default input parameters when supplied with invalid form inputs can result in unintentional data deletion and create auditing blind spots.
**Prevention:** Strictly validate integer bounds on administrative parameters before executing state-altering tasks, recording `crear_log_audit` with `status='FAILED'` and an explicit reason on validation rejection.

## 2026-11-30 - Defensive Exception Handling and Failure Audit Logging for User Game Routes
**Vulnerability:** Unhandled runtime or database exceptions in user game management routes (`/agregar`, `/delete/<game_id>`, `/edit/<game_id>`) could trigger 500 internal server error crashes and bypass audit trail logging for failed game creation, deletion, or editing operations.
**Learning:** State-altering user route handlers that lack top-level try-except error handling can crash on unexpected backend or database exceptions, exposing 500 internal server errors and creating auditing blind spots when failure events go unrecorded.
**Prevention:** Always wrap state-altering route handlers in top-level `try...except` blocks, logging exceptions via `current_app.logger.error`, recording `crear_log_audit` with `status='FAILED'`, and redirecting safely with a user-friendly flash error message.

## 2026-12-07 - Defensive Exception Handling and Failure Audit Logging for Password Recovery Routes
**Vulnerability:** Unhandled runtime or database exceptions in password recovery routes (`/forgot-password` and `/forgot-password/manual`) could trigger 500 internal server error crashes and bypass audit trail logging for failed password reset requests.
**Learning:** Authentication and recovery handlers that lack top-level try-except error handling can crash on unexpected backend or database exceptions, exposing 500 internal server errors and creating auditing blind spots when failure events go unrecorded.
**Prevention:** Always wrap authentication and password recovery route handlers in top-level `try...except` blocks, logging exceptions via `current_app.logger.error`, recording `crear_log_audit` with `status='FAILED'`, and redirecting safely with a user-friendly flash error message.

## 2026-12-14 - Defensive Exception Handling and Failure Audit Logging for User Registration
**Vulnerability:** Unhandled runtime or database exceptions in user registration (`/registro`) could trigger 500 internal server error crashes and bypass audit trail logging for failed user registration requests.
**Learning:** Registration route handlers that lack top-level try-except error handling can crash on unexpected database connection loss or runtime errors during user existence lookups or password hashing, exposing internal 500 server errors and creating auditing blind spots when registration failure attempts go unrecorded.
**Prevention:** Always wrap user registration handlers in top-level `try...except` blocks, logging exceptions via `current_app.logger.error`, recording `crear_log_audit` with `status='FAILED'`, flashing a user-friendly error message, and redirecting safely.

## 2026-12-21 - Defensive Exception Handling and Failure Audit Logging for Token Verification and Password Reset Routes
**Vulnerability:** Unhandled runtime or database exceptions in token verification (`/verify-token`) and password reset (`/reset-password/<token>`) routes could trigger 500 internal server error crashes and bypass audit trail logging for failed token validation attempts.
**Learning:** Token validation and password reset handlers that lack top-level try-except error handling can crash on unexpected database connection loss or runtime exceptions during token resolution or user lookups, exposing internal 500 server errors and creating auditing blind spots when token validation failure attempts go unrecorded.
**Prevention:** Always wrap token verification and password reset route handlers in top-level `try...except` blocks, logging exceptions via `current_app.logger.error`, recording `crear_log_audit` with `status='FAILED'`, flashing a user-friendly error message, and redirecting safely.
