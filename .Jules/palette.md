## 2026-06-08 - Unified Form Feedback & Password UX
**Learning:** Centralizing form submission logic on a global `submit` listener reduces boilerplate but requires strict adherence to HTML5 validation (`checkValidity`) and defensive programming (disabling button via `setTimeout`) to prevent double-submissions and invalid state feedback. Additionally, a dynamic password visibility toggle with swapped icons (eye/eye-off) provides a superior and more accessible experience than a simple text-change toggle.
**Action:** Use a "detect-and-inject" pattern for password toggles and character counters (expanded to `input` fields). In the global submit listener, always check for `defaultPrevented` and `form.checkValidity()` before updating UI state to ensure feedback only triggers on valid submissions.

## 2026-06-09 - Interactive Flash Messages
**Learning:** Flash messages (notifications) can become UI clutter if they persist indefinitely, especially "success" messages that only confirm an expected action. Adding a manual dismissal (close button) and auto-dismissal for success messages improves the experience. Smooth transitions (fade and slide-up) are essential for a non-jarring dismissal experience.
**Action:** Implement a global `setupFlashMessages` function that handles both manual and auto-dismissal with CSS transitions. Ensure success messages auto-dismiss after a few seconds while keeping errors/warnings visible until manually closed.

## 2026-06-10 - Efficient Client-Side Relative Timestamps
**Learning:** Native `Intl.RelativeTimeFormat` combined with a simple client-side update script provides a lightweight, highly accessible, and localized way to handle relative timestamps without external dependencies. By annotating ISO strings with a `data-timestamp` attribute, the UI can be progressively enhanced from static dates to dynamic, human-readable labels.
**Action:** Use `data-timestamp` attributes on any datetime display and implement a global `setupRelativeTimes` helper that uses the `lang` attribute from `<html>` to ensure consistency with the app's localization.

## 2026-06-11 - Interactive Collection Metrics
**Learning:** Transforming static dashboard statistics into functional, filtered links significantly improves "explorability" and user engagement without adding visual complexity. Using `text-decoration: none` and `color: inherit` allows for seamless integration of `<a>` tags into existing card/tile components while maintaining the intended design.
**Action:** Always consider if a metric or summary statistic can serve as a shortcut to its underlying data. Ensure interactive elements use `:focus-visible` to provide clear feedback for keyboard users.

## 2026-06-12 - Hardcoded Transparency vs. Thematic Consistency
**Learning:** Hardcoded semi-transparent colors (e.g., `rgba(255, 255, 255, 0.08)`) are "invisible bugs" in light themes if they were designed primarily for dark backgrounds. They fail to provide necessary contrast for borders and surfaces. Additionally, contrast-sensitive elements like badges require theme-specific overrides to maintain readability (WCAG compliance) across different background luminosities.
**Action:** Avoid hardcoded transparency for structural elements. Use CSS variables for borders and background tints. When implementing a light theme override, explicitly verify contrast ratios for text-on-badge combinations and darken colors as needed.
