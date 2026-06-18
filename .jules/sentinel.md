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
