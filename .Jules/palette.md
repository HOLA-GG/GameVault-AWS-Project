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

## 2026-07-06 - Interactive Access Keyboard Shortcuts & Progressive Hints
**Learning:** Keyboard shortcuts (`Alt + Key` or single keys like `N`) significantly improve navigation speed and accessibility for power and assistive technology users. However, they must be announced to screen readers via an active live region (`announceToScreenReader`) and paired with visible hints (like the `<kbd>` tag) for discoverability. Crucially, shortcut event listeners must ignore input elements (e.g., `INPUT`, `TEXTAREA`) to prevent hijacking normal user typing.
**Action:** Implement `aria-keyshortcuts` on interactive triggers and bind key listeners on `keydown`, ignoring typing in text fields. Pair with screen reader announcements and elegant visual keyboard hints to achieve perfect discoverability.

## 2026-07-07 - Lightweight and Generic Unsaved Changes Tracker
**Learning:** Tracking dirty forms to prevent data loss on accidental navigation or tab closure is a critical micro-UX feature. To avoid heavy dependencies or complex state machines, checking the browser's native `defaultValue` and `defaultChecked` values provides a remarkably lightweight, reliable, and accessible solution. To prevent false positives, we must dynamically map and track select inputs on load, ignore search or hidden fields, and safely hook both standard submit events and programmatic `form.submit()` calls.
**Action:** Build lightweight, ID-independent form trackers utilizing native DOM properties (`defaultValue`, `defaultChecked`). Always proxy programmatic form submissions to avoid warning prompts on valid automated/background submissions.

## 2026-07-08 - Keyboard Shortcut Discoverability & Guided Focus
**Learning:** Supporting power-user keyboard shortcuts (like Alt+A, /, N) is fantastic for efficiency, but they remain completely invisible unless there is a centralized, discoverable cheat sheet. Integrating an "Atajos de teclado" list directly inside an existing accessibility drawer makes it highly accessible. Mapping the standard `?` key to dynamically open this drawer and programmatically shift focus to the shortcuts header (with real-time ARIA live region announcements) provides immediate keyboard context without visual clutter on the page.
**Action:** Always provide a visual summary of available keyboard shortcuts. Bind the standard `?` key as a universal help trigger that safely avoids text input fields, opens the accessibility tools, and places focus directly on the shortcuts guide.

## 2026-07-30 - Interactive Drag & Drop Visual Affordance
**Learning:** Dashed borders on file input components are standard signifiers for drag-and-drop support, but without active state transitions during the drag interaction, users cannot be certain the drop action is recognized. Toggling a stateful class (e.g., `is-dragover`) via global event listeners and styling it with high-contrast glowing shadows or distinct colors provides immediate, high-fidelity visual affirmation.
**Action:** Always register stateful drag/drop event listeners on file inputs to provide immediate state feedback, styling the active hover zone using theme-consistent CSS variables (such as glowing shadows or color shifts) to boost delight and clarity.

## 2026-08-03 - Unified Dismissible Active Filters Row
**Learning:** Having active filters scattered across dynamic elements (such as game cards) creates an accessibility and interaction dead-end: if a search returns 0 results, those dynamic elements are not rendered, preventing users from seeing or dismissing individual filters. Implementing a centralized, static active-filters row above the results area solves this dead-end, provides clear visual status, and empowers keyboard and screen-reader users to refine their state step-by-step.
**Action:** Always provide a centralized summary of active search/filter states near the results count, ensuring individual dismiss controls remain keyboard-accessible even when results are empty. Style dismiss links using standard badge system classes with clear `aria-label` instructions.

## 2026-08-05 - CSP Compatibility for Client-Side Image Previews
**Learning:** Implementing progressive client-side image previews using `URL.createObjectURL` is a fantastic UX improvement, but will fail with a broken image icon if the server's Content Security Policy (CSP) `img-src` directive does not explicitly permit the `blob:` schema. Security-hardened CSP definitions must balance defense-in-depth with legitimate client-side progressive enhancement requirements.
**Action:** When utilizing `URL.createObjectURL` for immediate client-side UI feedback or image thumbnails, always ensure that `blob:` is explicitly whitelisted in the CSP `img-src` header to prevent silent visual regressions.

## 2026-08-07 - Contextual Form Constraints & Loading Feedback
**Learning:** Blank input and textarea fields across critical user/game forms can feel cold or confusing without guidance. Consistently providing contextual Spanish examples as placeholders (e.g., 'Ej: Juan') eases cognitive load, while pairing actions with 'data-loading-text' attributes on form submissions guarantees immediate visual feedback that reduces perceived latency.
**Action:** Always define helpful, culturally aligned placeholder attributes for standard form inputs, and include descriptive 'data-loading-text' values on submit buttons to communicate ongoing backend processing.

## 2026-08-09 - Accessible Interactive Rating Star Components
**Learning:** Rating star components are often implemented with generic labels (e.g., "1 estrella") which fail to describe the underlying action to screen-reader users, and lack toggle-state representation. Wrapping star buttons with an active "Valorar con..." action-oriented label and syncing the `aria-pressed` attribute dynamically on hover, focus, and submission provides screen-reader and keyboard users with real-time status clarity.
**Action:** Always enhance rating components with action-oriented aria-labels and sync `aria-pressed` both on initial server-side rendering and during client-side state adjustments.

## 2026-08-10 - Real-Time Visual Status Tags in Accessibility Panels
**Learning:** Drawer panels containing multiple settings (such as accessibility control groups) require significant visual search effort to understand which settings are currently active. Adding clean, dynamic, right-aligned status tags directly next to the section headers (e.g., "Tema: Gamer") provides an elegant and immediate overview of current active configurations, reducing cognitive load and improving accessibility.
**Action:** In settings drawers or panel interfaces, pair action triggers with dynamic visual status labels next to group headers, and keep them synchronized in real-time.

## 2026-08-12 - Tactile Range Slider Flanking Controls
**Learning:** HTML5 range input sliders are standard but introduce accessibility bottlenecks for screen-readers, motor-impaired individuals, or users on small screens who lack high-precision pointer control. Flanking range sliders with tactile increment/decrement buttons (`-` and `+`) offers alternative precise click/touch targets, dramatically lowering friction while ensuring screen reader users can trigger direct, real-time live region updates.
**Action:** For all system settings using range sliders, flank the input control with discrete, accessible tactile step buttons (`-` and `+`) and tie them to programmatic slider state changes and ARIA live region announcements.

## 2026-08-14 - Logical Dependency Controls & Dynamic State Explanation
**Learning:** Forms containing conditional logical rules (e.g., a setting that only makes sense if another option is set to public) create a cognitive and interaction burden if left unchecked. Letting users toggle invalid options leads to silent backend drops or invalid data. Dynamically disabling the dependent input, fading its container, replacing helper text with a precise reason, and broadcasting the change to screen readers via a live region provides an incredibly guided, self-documenting form experience.
**Action:** When options have logical dependencies, proactively bind event listeners to disable inputs and update adjacent instructional feedback, utilizing proper ARIA live region announcements to communicate the change instantly.

## 2026-08-20 - Semantic Pagination Landmarks and State Attributes
**Learning:** Bare pagination containers (such as `<div>` wrappers) fail to establish a navigation landmark for screen-reader users, making it difficult to locate or skip directly to page controls. Wrapping pagination blocks in a `<nav>` element with an explicit `aria-label` (e.g. `aria-label="Paginación de juegos"`), pairing "Anterior" and "Siguiente" links with target page numbers in `aria-label`s, and annotating the current page indicator with `aria-current="page"` provides complete structural clarity and state context across assistive technologies.
**Action:** Always wrap pagination controls in a `<nav>` tag with a descriptive `aria-label`, specify target page numbers in directional button labels, and mark the active page text with `aria-current="page"`.

## 2026-08-22 - Contextual Empty States with Actionable Filter Resets
**Learning:** Bare paragraph text in empty table states leaves users feeling stranded when filters yield zero records. Structuring empty states with decorative icons (`aria-hidden="true"`), clear headings, and dynamic, conditional reset links ("Limpiar filtros") provides visual feedback and immediate navigation recoverability across modalities.
**Action:** Always pair empty state components with explicit headings and actionable recovery shortcuts (such as conditional reset buttons when filters are active) across administrative and list views.

## 2026-08-25 - Progressive Client-Side Live Filtering with Debounced ARIA Announcements
**Learning:** Adding real-time client-side filtering to search inputs provides instant visual feedback by hiding/showing list items before form submission. To maintain complete accessibility parity, filtering events must trigger debounced screen reader announcements (`announceToScreenReader`) indicating the number of matching items, ensuring non-visual users are updated without being overwhelmed by announcements on every keystroke.
**Action:** Implement client-side live list filtering on search inputs, pairing DOM visibility updates with debounced ARIA live region announcements to communicate match counts to screen reader users.

## 2026-08-28 - Dynamic Date Range Boundaries & ARIA Live Constraint Announcements
**Learning:** Date range filter inputs (like "start_date" and "end_date") can allow logically invalid selections (e.g. start date after end date) if left unconstrained, resulting in empty or confusing server queries. Dynamically synchronizing `min` and `max` DOM attributes on change and automatically adjusting invalid dates while broadcasting clear live region announcements (`announceToScreenReader`) prevents invalid query states and keeps non-visual users informed.
**Action:** Always link start/end date input pairs by dynamically setting `min`/`max` constraints on `change` events, auto-correcting conflicting selections with immediate screen-reader feedback.

## 2026-08-30 - Semantic FAQ Disclosure Accordions & ARIA Live Announcements
**Learning:** Static FAQ sections add unnecessary visual length to landing pages and fail to provide keyboard or screen reader users with interactive state feedback. Converting static FAQ blocks into semantic HTML5 `<details>` and `<summary>` disclosure controls delivers native keyboard navigation (Tab focus, Space/Enter toggle) and zero-dependency collapsibility, while listening for client-side `toggle` events to trigger real-time screen reader announcements (`announceToScreenReader`) ensures assistive technology users receive immediate context upon item expansion.
**Action:** Use native `<details>` and `<summary>` elements for FAQ sections or collapsibles, styling `<summary>` markers with CSS variable transitions and pairing item expansion with real-time ARIA live region announcements.

## 2026-09-02 - Image Clear Focus Restoration & Table Focus-Within Visuals
**Learning:** When interactive elements (such as image preview removal triggers) hide or remove their container on click, browser focus resets to `<body>`, disorienting keyboard and assistive technology users. Explicitly calling `fileInput.focus()` before hiding the preview container seamlessly preserves keyboard focus on the file upload control. Additionally, extending table row hover states with `:focus-within` (`.admin-table tbody tr:focus-within`) provides keyboard users with a clear visual row highlight as they tab through controls inside table cells.
**Action:** Always restore focus to the originating input control when hiding dynamic preview elements, and pair `:hover` with `:focus-within` on container components (such as table rows or cards) to maintain high visual focus feedback during keyboard navigation.

## 2026-09-05 - Smooth CTA Auto-Scroll & Guided Input Focus Announcements
**Learning:** Empty state call-to-action (CTA) links targeting forms on the same page can cause abrupt visual jumps and leave screen-reader/keyboard users without clear context if they only trigger default hash navigation. Intercepting the click event to perform smooth scrolling (`scrollIntoView({ behavior: 'smooth', block: 'center' })`), auto-selecting the primary input (`firstInput.focus(); firstInput.select();`), and dispatching an ARIA live region announcement (`announceToScreenReader`) creates a seamless, context-rich transition for all users.
**Action:** For empty-state or page-internal CTA triggers that link to input forms, prevent default jump navigation and use smooth scrolling paired with delayed focus selection and an explicit ARIA live region announcement.
