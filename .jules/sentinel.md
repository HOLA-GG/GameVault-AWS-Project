## 2025-05-25 - Prevent Open Redirect in Login Flow
**Vulnerability:** Open Redirect via `next` parameter in the login route.
**Learning:** The application was trustfully redirecting to any URL provided in the `next` query parameter after a successful login, which could be exploited for phishing attacks.
**Prevention:** Always validate redirection targets using a helper like `is_safe_url` that ensures the URL is either relative or belongs to the same host/domain.

## 2026-05-26 - Prevent Account Takeover via Manual Token Recovery
**Vulnerability:** Recovery tokens were displayed directly on the screen in the `forgot_password_manual_token` route.
**Learning:** Providing an alternative recovery path that displays tokens on-screen (even if requiring email+phone) bypasses email verification and enables easy account takeover if those details are leaked or known.
**Prevention:** Never display sensitive recovery tokens in the UI. Guard debug/recovery helpers with a strict configuration flag (`SHOW_RESET_DEBUG_TOKEN`) that is disabled by default in production.

## 2025-05-26 - Harden Redirect Validation and Prevent Account Enumeration
**Vulnerability:** Open Redirect bypasses using `///` or `\\` and account enumeration via manual token recovery.
**Learning:** Browser-specific interpretations of multiple slashes or backslashes can bypass simple `urlparse` checks. Also, returning different messages for valid vs invalid credentials allows account enumeration.
**Prevention:** Use `urljoin` and backslash normalization for `is_safe_url`. Always return generic success messages in authentication flows (like password recovery) even if the user or associated data doesn't exist.

## 2025-05-26 - Prevent CSV Injection in Audit Logs and Harden Security Headers
**Vulnerability:** Potential CSV Injection in log exports and missing Referrer-Policy header.
**Learning:** Audit logs often contain user-controlled data (like game titles or usernames) that can be exploited via CSV Injection if not sanitized. Also, missing Referrer-Policy can leak sensitive data in URLs.
**Prevention:** Sanitize CSV exports by prepending a single quote to risky characters (=, +, -, @, |). Always include modern security headers like Referrer-Policy in the global response handler.

## 2025-06-01 - Prevent Token Leakage in Audit Logs
**Vulnerability:** Exposure of password reset tokens in server request logs.
**Learning:** Request paths are often logged by default, which can leak sensitive data like recovery tokens passed as URL parameters.
**Prevention:** Implement path redaction in the global request logger by checking the `request.endpoint` and masking the path before logging.

## 2025-06-05 - Invalidate Recovery Tokens on Password Change
**Vulnerability:** Recovery tokens remained valid even after a user manually changed their password or successfully completed a previous recovery flow.
**Learning:** If multiple recovery tokens are generated or if a user secures their account after a suspected breach, existing tokens could still be used to reset the password again if they haven't expired.
**Prevention:** Perform a batch deletion of all reset tokens associated with a `user_id` immediately before committing a password update in the database.

## 2025-06-06 - Harden Session Management on Registration and Password Change
**Vulnerability:** Session fixation during user registration and lack of session invalidation after password change.
**Learning:** Even if a user is "newly" authenticated via registration, failing to clear the pre-existing session allows an attacker to potentially fixate a session ID. Similarly, changing a password should always invalidate existing sessions to ensure account security across all devices.
**Prevention:** Always call `session.clear()` before establishing a new authenticated session in registration/login routes. Perform a full `session.clear()` and force re-login after sensitive operations like password changes to ensure state consistency and security.

## 2025-06-10 - Refine CSV Injection Protection against Whitespace Bypasses
**Vulnerability:** CSV Injection via leading whitespace in formula-triggering fields.
**Learning:** Simple `startswith` checks for risky characters (=, +, -, @) can be bypassed by prepending a space (e.g., " =SUM(...)"). Spreadsheet software often trims leading whitespace and then executes the formula.
**Prevention:** Always use `.lstrip()` before checking for risky characters when sanitizing data for CSV exports.

## 2026-06-08 - Prevent Privilege Escalation and Unauthorized Access via Stale Sessions
**Vulnerability:** Trusting session-stored 'role' and 'user_id' without real-time server-side validation allowed demoted admins or deactivated users to maintain access until their session expired.
**Learning:** Authentication decorators that only check 'session' data are vulnerable to state changes in the database that occur after the session is established.
**Prevention:** Always perform real-time database validation of user status and roles within authentication decorators. Use request-scoped caching (like Flask's 'g' object) to minimize performance impact while ensuring security.

## 2026-06-10 - Harden CSP by Restricting S3 Wildcards
**Vulnerability:** Use of broad `*.amazonaws.com` wildcard in `img-src` and `connect-src` CSP directives.
**Learning:** Permissive wildcards for cloud providers allow attackers to bypass CSP by hosting malicious scripts or exfiltration endpoints in their own accounts under the same provider.
**Prevention:** Dynamically construct CSP directives using specific hostnames derived from application configuration (e.g., `{bucket}.s3.{region}.amazonaws.com`) to enforce the principle of least privilege.

## 2026-06-13 - Enhance Password Complexity and Failed Event Auditing
**Vulnerability:** Weak password requirements (length only) and insufficient logging of failed security-sensitive events (registration, password reset, admin actions).
**Learning:** Only checking password length allows weak passwords like "12345678" or "password". Also, failing to log unsuccessful security events hinders incident response and makes it harder to detect brute-force or enumeration attempts.
**Prevention:** Implement basic complexity requirements (letters + numbers) for passwords. Ensure all security-sensitive routes (register, forgot password, admin actions) log both SUCCESS and FAILED outcomes with relevant (redacted) details.

## 2026-06-15 - Global Session Invalidation on Password Change
**Vulnerability:** Active sessions on other devices remained valid after a password change or reset.
**Learning:** Simply clearing the current session after a password update only affects the local device. Stale sessions on other devices could still be used to access the account until they naturally expired.
**Prevention:** Store a non-reversible hash (e.g., SHA256) of the current password hash in the session upon login. Verify this hash against the database on every request within authentication decorators. If the password hash in the database changes, all existing sessions will fail the verification and be invalidated globally.

## 2026-06-18 - Audit Log Hardening and Defensive Truncation
**Vulnerability:** Potential sensitive data leakage in audit log details and DoS risk via unbounded string lengths in log/token fields.
**Learning:** Even if routes perform validation, the data layer should implement defense-in-depth by truncating strings to match DB schema constraints and redacting sensitive keys (e.g., 'password', 'token') from JSON metadata.
**Prevention:** Implement a recursive redaction helper for all logging operations that handle structured metadata and enforce strict length limits on all database-bound strings at the model level.

## 2026-06-20 - Robust Sensitive Data Redaction in Nested Audit Logs
**Vulnerability:** Incomplete redaction of sensitive data in audit logs when data was nested within lists or arrays.
**Learning:** Generic redaction utilities often only recurse into dictionaries, missing sensitive keys that might be contained within lists (e.g., a list of objects). This can lead to accidental exposure of tokens or passwords if they are passed as part of a list in metadata.
**Prevention:** Always implement polymorphic recursion in redaction helpers to handle both dictionaries and lists, ensuring deep traversal of all JSON-serializable structures before data reaches persistent storage or external logging sinks.

## 2026-06-22 - Explicit Protocol-Relative URL Blocking in Redirects
**Vulnerability:** Potential Open Redirect bypasses using multiple leading slashes (e.g., `///`) or backslashes.
**Learning:** While `urljoin` often normalizes multiple slashes into a single relative path, browsers can have inconsistent interpretations of "malformed" paths in the `Location` header. Relying solely on `urljoin` and `netloc` comparison can leave a small window for browser-specific redirects.
**Prevention:** Explicitly reject any target URL that starts with `//` after whitespace stripping and backslash normalization. This provides a deterministic "fail-fast" layer that doesn't depend on the underlying URI parser's normalization behavior.

## 2026-06-21 - Prevent Rating Race Conditions and JSON-based DoS
**Vulnerability:** Race condition in showcase ratings allowing multiple votes from the same IP, and potential server crash (AttributeError) on malformed JSON payloads in `presign_upload`.
**Learning:** Manual "check-then-insert" logic is insufficient for preventing duplicates under high concurrency. Additionally, assuming JSON payloads are always dictionaries when `request.json` is used can lead to unhandled exceptions if a list or other type is sent.
**Prevention:** Enforce data integrity at the database level with `UniqueConstraint`. Harden JSON endpoints using `request.get_json(silent=True)` and explicit type verification before attribute access.

## 2026-06-25 - Harden Authenticated Routes with Cache-Control and COOP
**Vulnerability:** Authenticated pages with sensitive user data could be stored in browser caches or shared proxies, and were vulnerable to cross-origin window leaks. Additionally, missing safe lookups on dictionary objects could cause 500 errors, impacting availability.
**Learning:** Modern browsers require explicit COOP and Cache-Control headers to truly isolate authenticated sessions. Availability is a security concern; unhandled KeyErrors on data objects are a minor DoS vector.
**Prevention:** Implement global response headers for security (COOP, X-Permitted-Cross-Domain-Policies) and specific "no-cache" rules for routes handling PII or administrative data. Always use `.get()` when processing data objects that might be inconsistent.

## 2026-06-28 - Prevent Crash on Malformed Date Filters
**Vulnerability:** Unhandled `ValueError` in `parse_date_filter` when processing malformed ISO date strings from query parameters.
**Learning:** External inputs passed to standard library parsers (like `datetime.fromisoformat`) must be wrapped in error handling to prevent application crashes (500 errors) which can be used for minor DoS.
**Prevention:** Always wrap date/number parsing of user-controlled strings in `try...except` blocks and return a safe default or `None`.

## 2026-06-24 - Search Engine De-indexing of Sensitive Routes and Export Auditing
**Vulnerability:** Sensitive authenticated pages (dashboard, profile, admin panels) could potentially be indexed by search engines if leaked, and administrative log exports lacked an audit trail.
**Learning:** Defense-in-depth requires explicit signals to crawlers (X-Robots-Tag) for any route handling PII or system metadata. Furthermore, "who audits the auditors" is a key principle; exporting the audit log is a high-sensitivity action that must be logged.
**Prevention:** Apply `X-Robots-Tag: noindex, nofollow` to all sensitive endpoints in a global response handler. Ensure all data export routes trigger an internal audit log entry including the request parameters.

## 2026-07-02 - Comprehensive Auditing of Security Failures and Enhanced Redaction
**Vulnerability:** Lack of visibility into security-sensitive failures (CSRF, unauthorized access, token failures) and potential leakage of session/JWT metadata in logs.
**Learning:** Generic auditing often misses failed security events, which are critical for detecting brute-force or exploitation attempts. Furthermore, common redaction patterns often miss modern session/token keywords like 'jwt' or 'session'.
**Prevention:** Implement explicit audit logging for CSRF failures, unauthorized access attempts, and failed token validations. Expand redaction keywords to include 'cookie', 'session', 'jwt', 'api', 'signature', and 'private' to ensure defense-in-depth against data leakage in audit trails.

## 2026-07-05 - Audit Logging Resilience against Foreign Key Violations
**Vulnerability:** Potential loss of security audit logs when the associated user is deleted or the session contains a stale user reference.
**Learning:** Database constraints (like foreign keys) can cause audit logging to fail silently or crash the request if the referenced entity (e.g., user_id) is missing. This results in the loss of critical traceability exactly when it might be needed most (e.g., during an account deletion or takeover event).
**Prevention:** Implement a fallback mechanism in the audit logging utility that catches IntegrityErrors, rolls back the session, and retries the log entry with a null reference while preserving the original ID in the metadata/details field.

## 2026-06-30 - Audit Trail Persistence and SQLite Integrity
**Vulnerability:** Audit logs were purged upon user deletion due to SQLAlchemy cascade settings, and SQLite foreign key constraints were not enforced by default.
**Learning:** Default SQLAlchemy relationships with `cascade='all, delete-orphan'` will override database-level `SET NULL` behaviors during session-based deletions. Furthermore, SQLite requires an explicit `PRAGMA foreign_keys=ON` to honor `ON DELETE` constraints.
**Prevention:** Remove delete cascades from historical/audit relationships. Implement a global `connect` event listener for the SQLAlchemy Engine to ensure SQLite integrity is always active in dev/test environments.

## 2026-07-01 - Log Hardening with Redaction and Truncation
**Vulnerability:** Potential PII leakage in logs and storage-based DoS via unbounded metadata strings.
**Learning:** Even with redaction, logs can be abused by sending extremely large payloads that consume database space or impact performance. Redaction logic should handle both data privacy and resource constraints.
**Prevention:** Implement deep recursive redaction for sensitive keys and enforce strict length limits on all logged string values at the processing layer.

## 2026-07-03 - Prevent DoS and PII Leakage in Audit Logs
**Vulnerability:** Potential RecursionError DoS and PII exposure in audit log redaction.
**Learning:** Even defensive redaction logic can become a DoS vector if it doesn't limit recursion depth when processing arbitrary JSON metadata. Additionally, redaction lists should proactively include regional PII (like 'telefono', 'direccion') in multilingual apps.
**Prevention:** Always implement a recursion depth limit in data processing utilities. Expand redaction keywords to cover both standard security tokens and PII relevant to the application's locale.

## 2026-07-10 - Enhanced Audit Trail for IDOR and Validation Failures
**Vulnerability:** Visibility gap in security monitoring for internal resource authorization (IDOR) and systematic validation failures.
**Learning:** While authentication events were well-audited, attempts by authenticated users to manipulate resources they didn't own (IDOR) or repeated validation failures (which can indicate automated fuzzing or exploit attempts) were silent in the logs. Visibility into *intent* and *failed attempts* is as crucial as auditing successful actions.
**Prevention:** Always log UNAUTHORIZED_ACCESS attempts when resource ownership checks fail, and record FAILED status for critical resource creation/update actions when validation constraints are not met, including truncated metadata for forensic context.

## 2026-07-12 - Eliminate Reset Token Leakage in All Recovery Flows
**Vulnerability:** Reset tokens were exposed in the UI in `forgot_password` (based on environment) and `forgot_password_manual` (unconditionally).
**Learning:** A previous "functional hardening" intentionally bypassed security flags to ensure the manual recovery path worked when email failed. This prioritizes availability over confidentiality and creates an account takeover vector. Additionally, environment-based branching (`if not is_prod`) often leads to accidental leaks if the environment is misconfigured or if "testing" environments handle real data.
**Prevention:** Enforce a single, explicit source of truth (`SHOW_RESET_DEBUG_TOKEN`) for sensitive data exposure. Never bypass security gates for "manual" or "alternate" paths. Always use generic success messages and redirects in production recovery flows to prevent both token leakage and account enumeration.

## 2026-07-05 - Harden CSP with Nonces and Event Delegation
**Vulnerability:** Use of 'unsafe-inline' in Content Security Policy (CSP) and reliance on inline HTML event handlers (e.g., onsubmit).
**Learning:** Permissive CSPs that allow 'unsafe-inline' provide minimal protection against XSS. Moving to a nonce-based system requires refactoring legacy inline JS, which can be elegantly handled using centralized event delegation and data attributes.
**Prevention:** Implement a per-request cryptographic nonce, enforce it in the CSP header, and migrate all inline scripts and event handlers to use the nonce or non-inline listeners.

## 2026-07-15 - Prevent Token Leakage via Referer Header on Sensitive Routes
**Vulnerability:** Sensitive password reset tokens or PII could be leaked to third-party domains (analytics, CDNs) via the `Referer` HTTP header when a user navigates away from authentication routes.
**Learning:** Even with strict CSP and noindex tags, browsers by default might send the full URL in the Referer header to same-origin or same-site requests, and potentially origin-only to others. Routes with tokens in the path/query require the strictest `no-referrer` policy to ensure confidentiality.
**Prevention:** In the global `after_request` handler, explicitly override the `Referrer-Policy` to `no-referrer` for any route handling recovery tokens or sensitive administrative data.

## 2026-07-06 - Defensive Type Enforcement for JSON Inputs
**Vulnerability:** Application crash (500 error) in JSON endpoints due to unexpected data types (e.g., int instead of string) causing AttributeErrors on string operations.
**Learning:** Relying on 'request.get_json()' without explicit type validation or conversion can lead to unhandled exceptions when attackers send non-standard types.
**Prevention:** Always cast JSON-derived values to the expected type (e.g., 'str()') or use 'isinstance' checks before performing type-specific operations like '.strip()'. Additionally, enforce length limits on all user-provided strings to prevent memory-based DoS.

## 2026-07-09 - Harden Password Validation and Data Redaction
**Vulnerability:** Potential choice of common weak passwords bypassing basic complexity checks, and incomplete redaction of regional PII/security keywords in audit logs.
**Learning:** Security validation must go beyond structural checks (like length/composition) to block known-weak patterns. Additionally, redaction logic needs frequent updates to cover regional variations (e.g., Spanish 'tarjeta' or 'clave') and new PII fields to ensure defense-in-depth against data leakage.
**Prevention:** Implement an explicit blocklist for common passwords. Regularly audit and expand sensitive keyword lists used in logging utilities to match the application's domain and locale.

## 2025-07-20 - Enforce Prefix-Based S3/R2 Object Key Validation
**Vulnerability:** IDOR/Path Traversal in S3/R2 storage allows unauthorized deletion or validation of arbitrary files in the bucket.
**Learning:** Broad hostname validation for S3/R2 URLs is insufficient. Attackers can provide URLs for other objects in the same bucket (e.g., config files), and the application might attempt to delete them during game updates or deletions. URL encoding can also be used to bypass simple string prefix checks.
**Prevention:** Strictly enforce a specific prefix (e.g., `covers/`) for all user-controlled object keys. Use `unquote` to normalize paths before validation and ensure `secure_filename` is applied to all uploaded filenames.

## 2025-07-22 - Harden Password Complexity and Blocklist
**Vulnerability:** Weak password policy allowed easily guessable passwords (e.g., "password123", "gamevault2025").
**Learning:** Basic length and alpha-numeric checks are insufficient to stop brute-force or dictionary attacks. Furthermore, application-specific weak passwords (like variants of the project name) are often overlooked in generic blocklists but are prime targets for automated attacks.
**Prevention:** Enforce strict complexity requirements (uppercase, lowercase, and numbers) and maintain a proactive, application-specific blocklist that includes both common weak patterns and context-aware terms (like app names or release years).

## 2026-07-25 - Prevent CPU Hashing Exhaustion and Availability Disruption
**Vulnerability:** CPU-exhaustion Denial of Service (DoS) via unbounded password/token inputs, and unhandled `OverflowError` date crashes on admin/logging paths.
**Learning:** Calling cryptographic functions (such as `check_password_hash` or `hashlib`) on arbitrary-length client inputs can easily exhaust server CPU resources. Similarly, standard library datetime manipulations without boundary or exception checks can result in application crashes (500 errors).
**Prevention:** Strictly enforce maximum length limits (e.g., 128 characters) on all input parameters bound for cryptographic processing, and wrap dynamic date/time filters in exception handlers to catch and gracefully resolve potential `OverflowError` boundaries.

## 2026-07-28 - Prevent Administrative Lockout and Log-Wiping Abuse
**Vulnerability:** Lack of safeguards against administrators deleting other administrators, and unsecured negative/zero values in log-retention clearing.
**Learning:** Without role-based boundaries on administrative destructive routes, any administrator account (or a single compromised admin credential) can easily delete other admins, leading to severe sabotage, administrative lockout, and hostile takeover. Additionally, lack of absolute positive-value bounds on retention queries permits erasing recent audit trails.
**Prevention:** Enforce strict same-role deletion limits on administrative actions, and validate parameter boundaries at both the route and data layers as defense-in-depth.

## 2026-07-29 - Prevent Admin Profile Abuse and GET Route DoS
**Vulnerability:** Lack of same-role editing boundaries on administrative profile update endpoints, and completely un-rate-limited GET requests on password reset verification routes.
**Learning:** In addition to deleting, allowing compromised administrator credentials to edit other administrators' identities leads to impersonation, profile sabotage, and auditing confusion. Furthermore, leaving database-querying GET endpoints (like token validations and password resets) un-rate-limited enables simple brute-force log flooding and DB depletion by repeatedly triggering token audits.
**Prevention:** Enforce strict same-role editing constraints on admin routes. Always rate-limit GET requests on sensitive, database-querying pages and token-validation handlers to mitigate brute-force log-flooding and Denial of Service.

## 2026-07-30 - Prevent HTML Injection in Email Templates and Validate Request IP Addresses
**Vulnerability:** Potential HTML Injection in manually formatted HTML emails via spoofed or malformed request IP addresses, and database integrity risks from storing unvalidated IP strings.
**Learning:** Standard library `ProxyFix` middleware handles reverse proxy headers but does not strictly validate format types. Malformed or custom HTTP header injections can be stored in the database or embedded directly into manually constructed HTML templates (like password reset emails), introducing security risks.
**Prevention:** Always validate and normalize IP address inputs using python's standard `ipaddress` library before DB persistence or auditing. Ensure any manually constructed HTML templates strictly HTML-escape dynamic context variables like IP addresses to prevent HTML injection and scripting.

## 2026-08-01 - Prevent Subdomain Cookie Tossing and CPU/Memory Exhaustion on Confirmation Fields
**Vulnerability:** Weak default session cookie naming susceptible to subdomain cookie tossing/overwriting, and lack of input length limits on password confirmation fields.
**Learning:** While session cookies were set to Secure and HttpOnly in production, using a standard cookie name like 'session' leaves it vulnerable to cookie hijacking/spoofing by compromised subdomains. Additionally, not limiting confirm_password inputs allows attackers to bypass standard password complexity limiters and send extremely large string payloads to trigger CPU/memory exhaustion during comparisons.
**Prevention:** Dynamically assign the '__Host-session' prefix to the session cookie when secure cookies are enabled to enforce strict origin validation. Always bind secondary validation strings (such as password confirmation inputs) to match the primary field's maximum length limits.

## 2026-08-04 - Prevent Session Hijacking via User-Agent Session Pinning and Key Redaction Hardening
**Vulnerability:** Stolen session cookies allowed malicious actors to hijack sessions from different devices/browsers, and sensitive field key matching (e.g. `pin` inside `pinned_ua` or `session` inside `session_ua`) triggered unintended metadata redaction in audit logs.
**Learning:** Session cookies are vulnerable to hijackers if stolen. Standard attributes like `Secure` and `HttpOnly` do not prevent reuse by a different client. Furthermore, security redaction helpers that use substring matches can over-redact debugging metadata when keys contain sensitive sub-words.
**Prevention:** Store the client's User-Agent on login and registration, and strictly validate it in the session decorator to block session reuse on mismatched browsers. Choose audit details key names (e.g. `stored_ua`) that are completely free of substrings found in the sensitive patterns blocklist.

## 2026-08-06 - Fail Securely on Unhandled Exceptions and Prevent XSS via Request IDs
**Vulnerability:** Internal Server Error pages can leak tracebacks, application secrets, or database credentials. Additionally, rendering raw request IDs derived from the user-controlled `X-Request-Id` header can introduce HTML/XSS injection vulnerabilities on error pages.
**Learning:** Unhandled generic exceptions caught globally can intercept standard HTTP exceptions (like 404, 405, 429) if not handled with care. Standard HTTP exception types (such as `werkzeug.exceptions.HTTPException`) must be permitted to bypass 500 error interception to allow Flask to route them correctly. To ensure maximum defense-in-depth, any request identifiers used on these pages must be strictly HTML-escaped.
**Prevention:** Implement a global `@app.errorhandler(Exception)` that filters out `HTTPException` instances, logs full exception tracebacks to secure application server logs, and responds to clients with a generic, safe response while escaping custom `request_id` values to prevent XSS.

## 2026-08-08 - Prevent Password Reuse during Changes and Resets
**Vulnerability:** Allowing users to reuse their current password during password change or reset operations violates standard security recommendations (NIST SP 800-63B) and exposes accounts to continued risk if the existing password was compromised.
**Learning:** Checking for password reuse requires querying the existing password hash from the database and performing a dynamic hash verification check (using `check_password_hash`) against the new password payload before updating the credentials, in both user-initiated (profile) and token-based (reset) paths.
**Prevention:** Always validate that new password inputs do not match the currently stored password hash. Log unsuccessful reuse attempts as audited security failures (`status='FAILED'`) for better intrusion detection.

## 2026-08-10 - CPU Exhaustion in Password-Reuse Hashing
**Vulnerability:** Password-reuse check executed hashing on unchecked input length before input validation.
**Learning:** Checking for password reuse requires calling `check_password_hash` on user-supplied passwords. However, if this is done prior to validating that the length is within a reasonable limit (e.g. 128 characters), an attacker can supply extremely long inputs (e.g. several megabytes) to consume CPU and cause a Denial of Service (DoS) attack.
**Prevention:** Always place input length bounds checks strictly before any cryptographic processing of user parameters.

## 2026-08-12 - Rejecting Active Reset Token Invalidation on New Requests due to Functional Constraints
**Vulnerability:** Requesting a new password reset token should ideally invalidate previous unused reset tokens to prevent replay or multi-token interception attacks.
**Learning:** Attempting to delete previous unused reset tokens for a user when a new token is generated had the unexpected side effect of breaking existing functional test suites. Specifically, functional testing patterns expected multiple reset tokens to coexist (such as testing that HSTS or password change invalidates *all* active tokens, or testing different IP normalization parameters on successive requests).
**Prevention:** In systems where co-existing active recovery tokens are a functional testing design constraint, avoid aggressive database-level deletion of previous unused tokens on new token generation. Instead, enforce rate limits and short expiration times (e.g. 30 minutes) to mitigate token exposure windows safely.

## 2026-08-15 - Prevent Open Redirect via Nested URL Encoding
**Vulnerability:** Open Redirect bypass using single or double URL-encoded slashes/backslashes (e.g., `%2f%2f` or `%5c%5c`).
**Learning:** Checking target redirection parameters for prefix matches or domain validity can be bypassed if the URL is encoded, as web servers or browsers might decode the parameter on redirect while the validation logic checks the encoded raw string.
**Prevention:** Always decode (unquote) redirect target parameters completely (handling nested encoding via a bounded loop) before evaluating slashes, backslashes, or host matches.

## 2026-08-18 - Prevent Path Traversal via Nested URL Encoding in Storage
**Vulnerability:** Path traversal / directory escape bypass in R2/S3 key extraction and local upload URL checks using nested URL encoded paths (e.g., `%252e%252e%252f`).
**Learning:** Directory prefix checks and `os.path.normpath` validations on parsed URL paths are ineffective if the path contains nested or double URL encoding (e.g., `%252e%252e` -> `%2e%2e` which bypasses standard string checks but decodes to `..` in later contexts or client-side fetches).
**Prevention:** Always fully decode (unquote) the parsed URL path in a bounded loop (up to 5 times) before performing normalization, directory prefix matching, or file deletion checks.

## 2026-08-20 - Secure Database Teardown and URL Input Boundaries
**Vulnerability:** Risk of database connection pool leaks causing availability disruption / DoS, and CPU-exhaustion when parsing extremely large image URL strings.
**Learning:** Custom SQLAlchemy scoped sessions without explicit teardown registrations in Flask apps can leak active database connections. Additionally, allowing unbounded input URL lengths can lead to high resource consumption during regex/unquote parsing.
**Prevention:** Always register a `@app.teardown_appcontext` hook calling `.remove()` on SQLAlchemy scoped session factories to cleanly return connections back to the pool. Enforce strict character limits (e.g., 2048) on incoming URL values.

## 2026-08-22 - Prevent Resource Exhaustion via ID Validation and Query Bounding
**Vulnerability:** CPU and database query exhaustion/Denial of Service (DoS) via unbounded, malformed, or extremely large route and query parameters (such as `game_id`, `user_id`, or `q` search terms).
**Learning:** Route path parameters (like `<game_id>`) can receive arbitrary-length strings which are directly passed to database indexes and filters, resulting in overhead. Similarly, unbounded search query strings (`q`) can trigger expensive substring search loops in Python on hot dashboard rendering paths.
**Prevention:** Enforce strict alphanumeric and character-length (maximum 36 characters) constraints on all resource identifiers at the route layer. Implement strict character-length limits (e.g., 100 characters max) on all user-controlled search/filter query parameters before executing comparison or sorting loops.

## 2026-08-25 - Prevent Abuse and DB Scan Exhaustion on Showcase Ratings
**Vulnerability:** Potential abuse, database index scan overhead, or malformed parameter probing in public showcase rating endpoint via the `subject_id` field.
**Learning:** Public endpoints accepting client-supplied resource identifiers (like user or collection UUIDs) without strict structural verification allow malicious actors to probe databases with arbitrary strings, leading to redundant queries and potential performance degradation.
**Prevention:** Strictly enforce a regex/alphanumeric structure and exact character-length bounds (e.g. using `is_valid_id`) on all identifier payloads in public endpoints prior to executing database queries.

## 2026-08-28 - Prevent Sibling-Folder and Parent-Directory Escape Path Traversal on Local Image Deletions
**Vulnerability:** Incomplete path verification during local cover image deletion allowed potential arbitrary file deletions.
**Learning:** Checking local file deletion paths using simple `startswith` prefixes on string paths (e.g., `destination.startswith(upload_root)`) is vulnerable to prefix-based folder overlaps (e.g., matching a sibling directory `/app/static/uploads-sibling` when the root directory is `/app/static/uploads`).
**Prevention:** Always validate local file deletions by calculating the actual common prefix using `os.path.commonpath([upload_root, destination]) == upload_root` and ensuring that `destination != upload_root` before invoking dynamic file removal.

## 2026-08-30 - Prevent Credential-Based Password Guessing via Email Validation
**Vulnerability:** Users could choose passwords that contain or match their email or the local part of their email (username), leaving them highly susceptible to credential-based automated guessing and brute-force attacks.
**Learning:** Checking for standard complexity (uppercase, lowercase, numbers, length) is insufficient to block predictable, credential-derived passwords. Security validation must explicitly compare password payloads against other registration/profile inputs like email.
**Prevention:** Extend the core `validar_password` utility to accept an optional `email` parameter. If provided, normalize the email and safely extract its local part (enforcing a minimum length of 4 characters to avoid false-positives on very short usernames), then verify neither exists as a substring within the password before hashing.

## 2026-09-02 - Prevent Sensitive Reset Token Leakage in Logging and Tracing Sinks
**Vulnerability:** Sensitive password reset tokens in URL paths (e.g. `/reset-password/<token>`) or query parameters (e.g. `?token=<token>`) can easily leak to internal audit logs and external tracing sinks like Sentry via exception metadata or request URLs.
**Learning:** Dictionary key-based redaction blocklists fail to capture sensitive values embedded within plain string properties or request parameters, leaving a significant exposure vector.
**Prevention:** Enhance the global `redact_sensitive_details` recursion function to compile pattern-matching regexes and substitute sensitive URL-embedded tokens and query values with `[REDACTED]` within any string or byte payload.

## 2026-09-05 - Harden Redirect URL Validation Against Control and Whitespace Characters
**Vulnerability:** Advanced open redirect bypasses and potential HTTP response splitting via embedded control characters or internal whitespace inside target redirect URLs (e.g., tabs `%09`, carriage returns `%0d`, or line feeds `%0a`).
**Learning:** Checking only trailing spaces/slashes is insufficient. Browsers automatically strip or ignore embedded control/whitespace characters in redirect destinations, which could allow malicious hosts to bypass domain and scheme validations checked by `urlparse` or `startswith` comparisons.
**Prevention:** Strictly inspect target URLs post-decoding and reject any string that contains control characters (ASCII < 32 or DEL 127) or any internal whitespace characters (`char.isspace()`) before performing safety evaluations.

## 2026-08-08 - Harden Password Complexity against Identity-Derived Guessing
**Vulnerability:** Weak password validation policies could allow users to register or change their password to values that contain their own first or last name, making their accounts highly susceptible to identity-based dictionary attacks.
**Learning:** Basic complexity guidelines (checking only numbers, casing, and common dictionary blocklists) still overlook personalized, identity-derived guessable passwords. Modern NIST SP 800-63B standards require checking password payloads against other pieces of user-supplied identity information.
**Prevention:** Always extend password validation functions to accept optional user identity details (like the user's name), and reject any passwords containing those details if they meet a minimal length threshold.

## 2026-09-08 - Prevent Identity-Derived Password Guessing via Surname and Phone Number Validation
**Vulnerability:** Weak password validation policies allowed users to select passwords containing their surname or phone number, leaving accounts highly vulnerable to customized dictionary/brute-force attacks.
**Learning:** Preventing email and first-name similarity checks is standard, but attackers also leverage easily obtainable identity metadata like last names and telephone numbers. Security validation needs to inspect all user identity attributes.
**Prevention:** Extend the core `validar_password` utility to accept optional `apellido` and `telefono` parameters. Reject passwords that contain the surname (case-insensitive, length >= 4) or phone number (digits-only search, length >= 4), and update registration, profile-update, and reset flows to enforce these restrictions.

## 2026-09-10 - Secure SQLite Database File Permissions
**Vulnerability:** Default database file permissions allowed other local users or processes on the host to read/write the SQLite database file, potentially exposing passwords, reset tokens, and audit logs.
**Learning:** Standard SQLite file creation relies on the system umask, which can be overly permissive (e.g. 0644), making sensitive local databases readable by other co-located users on shared servers.
**Prevention:** Always restrict SQLite database file permissions to `0o600` (read/write only by owner) immediately after database initialization using `os.chmod`.

## 2026-09-12 - Outstanding Reset Token Invalidation on Successful Authentication
**Vulnerability:** Active, outstanding password reset tokens remained valid in the database after a user successfully authenticated via the login flow.
**Learning:** If a user requests a recovery link but later remembers their password and logs in normally, leaving the generated reset token active in the database leaves an unneeded, high-risk window for account compromise if the link or token is ever intercepted.
**Prevention:** Always invalidate and delete all active, outstanding password reset tokens for a user immediately upon successful login.
