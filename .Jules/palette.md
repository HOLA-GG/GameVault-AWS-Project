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

## 2026-07-01 - Global Accessibility Parity for Transient and Static Feedback
**Learning:** Transient visual feedback (like copy-to-clipboard notifications) and static constraints (like character counters or required fields) create a "hidden" experience for assistive technology users if not programmatically announced or linked. A centralized `aria-live` announcer and the consistent use of `aria-describedby` ensure that non-visual users receive the same real-time context as visual users.
**Action:** Implement a global announcer for all non-standard UI feedback. Link character counters and required indicators to their inputs using ARIA attributes to maintain a single source of truth for form constraints across all modalities.

## 2026-07-02 - Actionable Real-Time Password Complexity Guidance
**Learning:** Generic "Weak" or "Medium" password strength indicators fail to help users satisfy complex backend validation rules, leading to frustrating trial-and-error form submissions. Supplementing strength visualizers with real-time, localized descriptions of missing criteria (e.g., lowercase, uppercase, number, minimum characters) directly addresses user cognitive load and reduces form submission failures.
**Action:** Always pair abstract metrics (like password strength percentages or color bars) with direct, human-readable instructions detailing what requirements are currently unmet, ensuring smooth progressive feedback before submission.

## 2026-07-03 - Real-Time Screen Reader Feedback for Accessibility Settings
**Learning:** When users modify accessibility settings (such as theme selection, font scale, reduced motion, or panel positioning), these changes are invisible to screen-reader users unless dynamically announced. Centralizing the `announceToScreenReader` function to the global scope allows both system utilities and custom elements to leverage `aria-live` polite announcements. Furthermore, inputs like range sliders must dynamically update `aria-valuetext` with formatted strings (e.g. "115%") to prevent screen readers from reading meaningless raw numbers.
**Action:** Expose a global `announceToScreenReader` helper and always tie accessibility panel interactions to real-time `aria-live` announcements. For range sliders, dynamically sync `aria-valuetext` with formatted units.

## 2026-07-04 - Proactive Client-Side Validation & Accessible Interactive Controls
**Learning:** Checking password strength in real-time against a backend-synced blocklist of common weak passwords provides instant, low-friction feedback before form submission, reducing server errors and reloads. Furthermore, interactive controls such as password visibility toggles must be paired with real-time ARIA announcements to prevent assistive technologies from missing hidden-to-visible context changes.
**Action:** Always sync known security blocklists with client-side real-time checks to enhance feedback immediacy. Pair standard visual state toggles (like eye/eye-off icons) with explicit screen reader announcements (`announceToScreenReader`) on user interaction to provide immediate structural feedback.

## 2026-07-05 - Capturing-Phase Event Delegation & Progressive Title Tooltips
**Learning:** Attaching standard event delegation click handlers on `document` is too late to stop the event from triggering handlers on parent components (such as anchor tags wrapping log cards) because the bubble phase has already executed through those parents. Registering the delegation handler in the capturing phase (`true`) successfully intercepts and halts propagation BEFORE parent bubble-phase handlers or default browser actions are fired. Furthermore, delegating `mouseover` on `document` to progressively enhance elements with `title` tooltips matching their `aria-label` is highly efficient, robust, and supports dynamically loaded nodes automatically without manual rebinding.
**Action:** Use capturing-phase global event delegation (`document.addEventListener('click', handler, true)`) to completely isolate click actions on inner utility buttons (like copies or toggles) placed inside interactive parents. Combine with mouse/focus delegation to dynamically populate accessibility attributes on the fly.
