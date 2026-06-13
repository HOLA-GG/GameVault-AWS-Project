## 2025-01-24 - [Dashboard Actionability Enhancement]
**Learning:** In informational summaries (like the dashboard "Insights"), static text that references specific entities (e.g., game titles) creates a "dead end" for users. Converting these references into actionable links significantly reduces navigation friction and improves the "perceived performance" of the task flow.
**Action:** Always identify static entity names in summary views and evaluate if they should be links to their respective detail/edit pages. Use a distinct interactive style (like `.info-link`) to ensure they are discoverable and accessible.

## 2026-06-13 - [Exploratory Navigation via Metadata]
**Learning:** Metadata badges (like categories or platforms) in a dashboard are often perceived as actionable by users. Converting these static labels into filter links reduces cognitive load and allows for natural, exploratory navigation without requiring users to manually interact with complex filter forms.
**Action:** When displaying categorical metadata in list views, implement them as interactive links that apply the corresponding filter.

## 2026-06-13 - [Shortcut Discoverability via Inline Hints]
**Learning:** Powerful keyboard shortcuts (like '/' for search) remain underutilized if they aren't visible in the UI. A subtle, non-intrusive visual hint (e.g., "(Presiona /)") next to the corresponding label or placeholder significantly increases adoption and improves power-user efficiency.
**Action:** Always provide a visual hint for keyboard shortcuts near the UI element they affect, using a distinct but secondary style to avoid clutter.
