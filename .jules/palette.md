## 2025-01-24 - [Dashboard Actionability Enhancement]
**Learning:** In informational summaries (like the dashboard "Insights"), static text that references specific entities (e.g., game titles) creates a "dead end" for users. Converting these references into actionable links significantly reduces navigation friction and improves the "perceived performance" of the task flow.
**Action:** Always identify static entity names in summary views and evaluate if they should be links to their respective detail/edit pages. Use a distinct interactive style (like `.info-link`) to ensure they are discoverable and accessible.

## 2026-06-13 - [Exploratory Navigation via Metadata]
**Learning:** Metadata badges (like categories or platforms) in a dashboard are often perceived as actionable by users. Converting these static labels into filter links reduces cognitive load and allows for natural, exploratory navigation without requiring users to manually interact with complex filter forms.
**Action:** When displaying categorical metadata in list views, implement them as interactive links that apply the corresponding filter.

## 2026-06-13 - [Shortcut Discoverability via Inline Hints]
**Learning:** Powerful keyboard shortcuts (like '/' for search) remain underutilized if they aren't visible in the UI. A subtle, non-intrusive visual hint (e.g., "(Presiona /)") next to the corresponding label or placeholder significantly increases adoption and improves power-user efficiency.
**Action:** Always provide a visual hint for keyboard shortcuts near the UI element they affect, using a distinct but secondary style to avoid clutter.

## 2026-06-13 - [Visual Cues and Actionability in Logs]
**Learning:** Activity feeds and logs are often dry and hard to scan. Adding representative visual cues (like emojis) for different actions helps users quickly identify types of activity. Furthermore, making entity references (like game titles) actionable within these logs allows users to "teleport" to the relevant task (e.g., editing the game) without manual navigation.
**Action:** Use icons or emojis to categorize activity types in logs and always wrap entity names in actionable links to their respective detail or edit views.

## 2026-06-16 - [Search Input Native and Interactive Power-up]
**Learning:** For high-frequency interaction elements like search bars, combining native browser capabilities (`type="search"`) with interactive JS helpers (focus + `.select()`) significantly reduces task friction. Power users benefit from immediately replacing stale queries, while all users gain semantic clarity and a standard 'clear' button provided by the OS/Browser.
**Action:** Always prefer `type="search"` for search fields and evaluate if keyboard shortcuts to focus these fields should also automatically select existing content to facilitate rapid re-searching.

## 2025-05-15 - [Enhanced Interactive Card Feedback]
**Learning:** When wrapping inputs (like checkboxes) inside larger "card" containers, the visual connection between the user's action and the feedback can be weakened. Using modern CSS like `:has(input:checked)` and `:focus-within` allows the entire container to act as a responsive interactive element, significantly improving clarity and keyboard accessibility.
**Action:** For all card-wrapped inputs, always implement container-level styles for checked and focused states to provide a cohesive and accessible experience.

## 2026-06-19 - [Semantic Shortcut Hints with Tactile Styling]
**Learning:** Keyboard shortcut hints (like "Press /") are more effective when they use semantic `<kbd>` tags styled to look like physical keys. This creates a strong visual metaphor for "keyboard interaction," improving discoverability and making the interface feel more professional and accessible.
**Action:** Always wrap keyboard shortcut hints in `<kbd>` tags and ensure they have a tactile, "raised" style that adapts to the current theme.

## 2026-06-19 - [Contextual Focus after Internal Navigation]
**Learning:** When using internal links (anchors) to navigate to a form (e.g., "Add your first game"), the user's focus is often lost on the scroll. Automatically focusing the first relevant input field after the scroll significantly reduces task friction and provides a clear "start here" signal.
**Action:** For all CTA buttons that lead to internal forms, implement a JavaScript listener to programmatically `.focus()` the first input field after a small delay to allow for the scroll animation.

## 2026-06-20 - [Dashboard Filter Resiliency and Feedback]
**Learning:** When users apply filters from a deep page of results, they often land on an empty page if the filter reduces the set significantly. Automatically resetting pagination (e.g., `page=None`) in all filter-triggering links (badges, tiles) is crucial for a "glitch-free" experience. Additionally, using `role="status"` on result counts provides essential live feedback for screen reader users during these dynamic updates.
**Action:** Always ensure filter-applying links reset the current page parameter and use ARIA status roles for dynamic result summaries.

## 2026-06-20 - [Placeholder Aesthetic and Semantic Search]
**Learning:** Generic "Missing" text placeholders (like "No cover") feel like broken features. Adding a subtle icon (e.g., 🖼️) and a light background tint transforms these into professional-looking "empty states." For search, linking shortcut hints to the input via `aria-describedby` and `aria-keyshortcuts` ensures both visual discoverability and programmatic accessibility.
**Action:** Enhance text-only placeholders with iconography and background depth. Use standard ARIA attributes to connect keyboard shortcut hints with their target inputs.

## 2026-06-23 - [Auto-expanding Textareas for Seamless Content Entry]
**Learning:** For description or note fields in forms, a fixed-height textarea with internal scrollbars creates a cramped editing experience and hides content. Implementing auto-expansion based on `scrollHeight` allows the form to grow naturally with the content, improving readability and making the interface feel more responsive to user input. Disabling manual `resize: vertical` prevents users from accidentally breaking layouts while ensuring the field always fits its content.
**Action:** For all multi-line text inputs, implement an auto-expansion helper that adjusts height on `input` and initialization, and pair it with `resize: none` and `overflow-y: hidden` for a polished look.

## 2025-06-24 - [Focus Indicators and Star Rating Accessibility]
**Learning:** Overriding browser default focus indicators with `outline: none` without providing a high-contrast alternative is a common accessibility trap. Interactive elements like cards and badges need visible focus states to be usable by keyboard-only users.
**Action:** Always ensure `:focus-visible` provides a clear visual indicator. For complex interactive components like star ratings, mouse-specific feedback (hover) should be mirrored with keyboard-specific feedback (focus).

## 2026-06-25 - [Actionable Data via Copy-to-Clipboard]
**Learning:** Administrators and power users frequently need to extract data (like emails or IDs) from lists for external use. Forcing manual selection and copying creates high friction. A "one-click" copy utility with instant visual feedback (like a CSS tooltip) significantly improves the perceived efficiency of the administrative workflow while maintaining a clean UI.
**Action:** Identify high-frequency extraction targets in administrative or list views and evaluate if they should be enhanced with a "click-to-copy" utility.

## 2025-02-05 - [Visual Context for Active Dashboard Filters]
**Learning:** Dashboard metrics and overview cards often double as filter triggers. However, without visual feedback indicating which filter is currently active, users can lose context, especially when multiple overlapping filters are available. Adding an `.is-active` state to these cards/tiles provides immediate "You are here" orientation and visual confirmation of the applied filter, improving the exploratory UX.
**Action:** When dashboard summary elements act as links to filtered views, always implement an active state that visually highlights the element (e.g., using borders or background shifts) and include `aria-current="true"` when its corresponding filter parameters match the current state.

## 2024-05-15 - [Semantic Color-coding for Scannability]
**Learning:** Using semantic color-coding (mapped to existing theme variables like `--danger-color`) for priority-based metadata significantly improves visual scannability of dashboards and lists. Combining color with bold text (`font-weight: 700`) ensures the emphasis is clear even for users with moderate vision impairment.
**Action:** Identify text-based metadata with inherent severity or importance (e.g., priority, status, urgency) and apply semantic coloring that aligns with the application's established theme.

## 2025-02-13 - [Real-time Visual Feedback for Password Complexity]
**Learning:** For security-sensitive inputs like passwords, providing real-time visual feedback (a strength meter) transforms a "blind" requirement into a helpful guide. Using a multi-point scoring system (length, variety) helps users set stronger passwords without frustration. Initializing the meter on page load is crucial for pre-filled or recovered forms to avoid a "stale" UI state.
**Action:** Always implement a visual complexity meter for password creation/reset fields. Ensure the logic initializes on load to handle pre-filled values and uses `aria-live="polite"` for accessible textual feedback.

## 2026-06-30 - [Parity for Keyboard Focus in Interactive Containers]
**Learning:** Interactive "cards" or containers that provide visual feedback on hover (like lifts or shadows) should mirror this behavior when internal elements receive focus. Using `:focus-within` ensures that keyboard users navigating via Tab receive the same "lift" and orientation signals as mouse users, creating a more cohesive and accessible experience.
**Action:** For all interactive container components, always pair `:hover` styles with `:focus-within` to provide consistent visual feedback for keyboard navigation.

## 2025-02-14 - [Robust Positioning for Password Visibility Toggles]
**Learning:** Positioning a password visibility toggle with absolute coordinates (e.g., `bottom: 12px`) relative to a generic container like `.form-group` is fragile and prone to misalignment when the group contains variable-height elements like strength meters or help text. Wrapping the input and its toggle in a dedicated `.pw-field-wrapper` with `display: flex; align-items: center; position: relative;` provides a robust, vertically centered alignment that is independent of other elements in the form group.
**Action:** Always wrap password inputs and their respective visibility toggles in a scoped wrapper to ensure consistent, stable positioning.

## 2025-05-20 - [Constraint Alignment in Micro-UX]
**Learning:** Micro-UX improvements must strictly adhere to the "no custom CSS" and "line count" constraints. Even a standard feature like "Back to Top" can be rejected if it introduces a large block of custom styles or breaks language consistency within the UI.
**Action:** Prioritize enhancements that leverage existing Design System classes (like `.badge-log-*`) over creating new components that require significant custom CSS.

## 2025-05-20 - [Route-Template Logic Synchronization]
**Learning:** In projects with complex data enrichment (like audit logs), simply updating the template is often insufficient. Ensuring the route logic utilizes the same enrichment helpers as other pages (e.g., `enrich_log_metadata`) is critical for maintaining visual and functional parity across the application.
**Action:** When improving a component that exists in multiple views, verify that the backend data preparation is synchronized to support the enhanced UI features (badges, formatting, etc.) consistently.

## 2025-05-23 - [Threshold-based Form Feedback and Accessible Progress Meters]
**Learning:** Providing multi-state visual feedback for character counters (e.g., warning at 85%, danger at 100%) gives users better "peripheral" awareness of constraints without forcing them to read the exact number. Additionally, custom visual components like strength meters must explicitly use `role="progressbar"` and link to their labels via `aria-labelledby` to be perceivable by assistive technologies.
**Action:** Always implement tiered visual states for input constraints and ensure custom meters are fully annotated with ARIA progressbar attributes.

## 2026-07-09 - [Bidirectional Dashboard Filtering via Toggles]
**Learning:** Dashboard summary elements (cards, tiles) and metadata badges that act as filter triggers should support bidirectional interaction. When a filter is already active, clicking the same element should toggle it off (remove the filter). This reduces navigation friction by allowing users to undo a filter selection without searching for a "Clear" button or navigating back, making the exploratory experience more fluid and intuitive.
**Action:** Implement toggle logic for all filter-triggering elements. When the current state matches the element's filter value, the link should lead to a state where that filter is removed (e.g., passing None to the query builder). Update aria-label dynamically to reflect the "Remove filter" action for accessibility.

## 2026-07-10 - [Efficiency via Automatic Selection on Focus]
**Learning:** For fields that users frequently edit or replace (like titles or search queries), requiring a manual "Select All" or multiple backspaces adds unnecessary friction. Implementing an automatic selection behavior on focus allows for immediate replacement, significantly speeding up data entry and search workflows while remaining accessible.
**Action:** Identify pre-filled inputs that are targets for rapid modification and apply the `.select-on-focus` utility paired with a global JavaScript listener that triggers `this.select()`.

## 2026-07-10 - [Visual Parity for ARIA-Labels via Tooltips]
**Learning:** Functional elements that use `aria-label` for screen reader accessibility often leave mouse users without visual context for "what this does" if the label isn't reflected in the UI. Mirroring `aria-label` logic into the `title` attribute provides consistent visual tooltips that bridge the gap between accessibility and standard visual feedback.
**Action:** For all interactive elements where the purpose is communicated via `aria-label` (like filter badges or icon-only buttons), always include a matching `title` attribute to provide visual tooltips.

## 2026-07-13 - [Identity Field Utility and Accessibility]
**Learning:** Using `disabled` for immutable user data (like an email address) creates an accessibility "dead end" where users cannot select, copy, or easily hear the data with screen readers. Switching to `readonly` maintains data integrity while allowing focus and selection. Enhancing this with an explicit "Copy" button and `.select-on-focus` utility transforms a static label into a high-utility identity tool.
**Action:** Always prefer `readonly` over `disabled` for fields that users might need to copy (IDs, emails, keys), and pair them with a dedicated copy button and selection-on-focus for maximum efficiency.
