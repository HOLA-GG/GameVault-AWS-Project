## 2025-05-25 - Prevent Open Redirect in Login Flow
**Vulnerability:** Open Redirect via `next` parameter in the login route.
**Learning:** The application was trustfully redirecting to any URL provided in the `next` query parameter after a successful login, which could be exploited for phishing attacks.
**Prevention:** Always validate redirection targets using a helper like `is_safe_url` that ensures the URL is either relative or belongs to the same host/domain.
