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
