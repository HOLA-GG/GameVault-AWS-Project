## 2025-05-25 - Context-Aware Empty States
**Learning:** Context-aware empty states (distinguishing between "no content" and "no search results") significantly reduce user confusion by providing clear, relevant CTAs. A generic "No items found" message is often ambiguous for new users versus power users with active filters.
**Action:** Always verify if an empty view is absolute (empty database) or relative (active filters) and provide specific guidance/buttons for each scenario. Additionally, ensure decorative emojis/icons are hidden from screen readers using `aria-hidden="true"` to prevent verbal clutter.

## 2025-05-26 - Synchronized Accessible Loading States
**Learning:** When providing visual loading feedback (e.g., changing button text to "Loading..."), the `aria-label` must stay synchronized with the visible `textContent` to avoid confusing screen reader users. Additionally, using `aria-busy="true"` on the submitting element provides a semantic signal that the action is in progress.
**Action:** When implementing async UI feedback, ensure that any text changes are reflected in the element's ARIA attributes and use `aria-busy` to communicate state transition. If the design system lacks a spinner component, prioritize clear text feedback over custom CSS to maintain visual consistency.

## 2025-05-27 - Real-Time Validation Feedback
**Learning:** Using `setCustomValidity` within an `input` event listener provides immediate, native-feeling feedback for cross-field validation (like password confirmation). This reduces friction by preventing submission of invalid data rather than showing errors only after a failed POST request.
**Action:** Prefer real-time `input` or `change` listeners for validation that depends on multiple fields, ensuring `setCustomValidity('')` is called when the state becomes valid to allow submission.

## 2025-05-31 - Unified Auth Feedback & Metric Clarity
**Learning:** Standardizing asynchronous feedback across all authentication and recovery flows (using `aria-busy`, `disabled`, and synchronized text updates) ensures a predictable and accessible experience. Additionally, hiding decorative emojis in data-heavy dashboard metrics prevents verbal clutter, allowing screen reader users to focus on the actual numbers and labels.
**Action:** Apply the standardized form ID naming pattern (`Form`/`SubmitButton`) and the JavaScript loading state logic to all new submission flows. Audit all landing and dashboard metrics to ensure decorative icons are explicitly hidden with `aria-hidden="true"`.

## 2025-06-02 - Defensive Destructive Interactions
**Learning:** Destructive actions like clearing system logs require a double-layer of UX protection: a confirmation dialog to prevent accidental clicks and an immediate loading state to prevent double-submissions. Using the native `confirm()` is highly accessible and familiar, while synchronized ARIA attributes (`aria-busy`, `aria-label`) provide necessary feedback for screen readers during the execution.
**Action:** Always pair `confirm()` with a synchronized loading state (disabled button + text/ARIA updates) for all destructive operations in the admin panel.

## 2025-06-03 - Centralized Non-Destructive Loading States
**Learning:** Implementing app-wide loading feedback via a global `submit` listener on `document` is highly efficient but requires defensive programming. It must respect `defaultPrevented` (to avoid interfering with custom handlers) and check for child elements to avoid destroying nested icons (SVGs/span) when updating button text.
**Action:** Use centralized event delegation for app-wide UX consistency. When updating button content, prefer ARIA attributes (`aria-busy`, `aria-label`) for accessibility and only modify `textContent` if the element has no complex inner HTML.

## 2025-06-04 - Global Password Visibility Toggle
**Learning:** Automatically injecting password visibility toggles via JavaScript ensures a consistent security-friendly UX across all forms (Login, Registration, Profile, Recovery) without manual template repetition. Using inline SVGs and synchronized ARIA labels ensures accessibility and compatibility across themes without external dependencies.
**Action:** Use a "detect-and-inject" pattern for universal UI enhancements like password toggles or character counters to maintain a DRY (Don't Repeat Yourself) architecture. Always ensure the injected elements are keyboard accessible (`button type="button"`) and provide clear visual and audible feedback for the state change.
