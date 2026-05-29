## 2025-05-25 - Context-Aware Empty States
**Learning:** Context-aware empty states (distinguishing between "no content" and "no search results") significantly reduce user confusion by providing clear, relevant CTAs. A generic "No items found" message is often ambiguous for new users versus power users with active filters.
**Action:** Always verify if an empty view is absolute (empty database) or relative (active filters) and provide specific guidance/buttons for each scenario. Additionally, ensure decorative emojis/icons are hidden from screen readers using `aria-hidden="true"` to prevent verbal clutter.

## 2025-05-26 - Synchronized Accessible Loading States
**Learning:** When providing visual loading feedback (e.g., changing button text to "Loading..."), the `aria-label` must stay synchronized with the visible `textContent` to avoid confusing screen reader users. Additionally, using `aria-busy="true"` on the submitting element provides a semantic signal that the action is in progress.
**Action:** When implementing async UI feedback, ensure that any text changes are reflected in the element's ARIA attributes and use `aria-busy` to communicate state transition. If the design system lacks a spinner component, prioritize clear text feedback over custom CSS to maintain visual consistency.
