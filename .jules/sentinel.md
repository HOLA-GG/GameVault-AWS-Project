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
