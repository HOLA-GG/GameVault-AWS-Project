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
