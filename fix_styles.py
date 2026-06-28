import sys

with open('app/static/css/styles.css', 'r') as f:
    content = f.read()

# 1. Improve light theme contrast
old_light = """[data-theme="light"] {
    --primary-color: #6c5ce7;
    --primary-color-rgb: 108, 92, 231;
    --primary-dark: #5649b8;
    --secondary-color: #dfe6e9;
    --background-dark: #f5f6fa;
    --background-darker: #dfe6e9;
    --text-primary: #2d3436;
    --text-secondary: #636e72;
    --border-color: #b2bec3;
    --card-bg: #ffffff;
    --input-bg: #f5f6fa;
    --electric-color: #6c5ce7;
    --electric-glow: rgba(108, 92, 231, 0.5);
    --star-active: #f4b400;
    --star-inactive: rgba(45, 52, 54, 0.14);
}"""

new_light = """[data-theme="light"] {
    --primary-color: #5c4cd1;
    --primary-color-rgb: 92, 76, 209;
    --primary-dark: #4a3ba3;
    --secondary-color: #f1f2f6;
    --background-dark: #f8f9fa;
    --background-darker: #f1f2f6;
    --text-primary: #1a1a1a;
    --text-secondary: #4a4a4a;
    --border-color: #d1d8e0;
    --card-bg: #ffffff;
    --input-bg: #f8f9fa;
    --electric-color: #5c4cd1;
    --electric-glow: rgba(92, 76, 209, 0.3);
    --star-active: #f39c12;
    --star-inactive: rgba(0, 0, 0, 0.1);
}

[data-theme="light"] .badge-log-action {
    background: rgba(92, 76, 209, 0.1);
    color: #4a3ba3;
    border-color: rgba(92, 76, 209, 0.25);
}

[data-theme="light"] .badge-log-resource {
    background: #f1f2f6;
    color: #2d3436;
    border-color: #d1d8e0;
}

[data-theme="light"] .badge-log-success {
    background: rgba(39, 174, 96, 0.12);
    color: #1e8449;
    border-color: rgba(39, 174, 96, 0.25);
}

[data-theme="light"] .badge-log-error {
    background: rgba(192, 57, 43, 0.12);
    color: #922b21;
    border-color: rgba(192, 57, 43, 0.25);
}

[data-theme="light"] .badge-log-neutral {
    background: rgba(211, 84, 0, 0.12);
    color: #a04000;
    border-color: rgba(211, 84, 0, 0.25);
}"""

content = content.replace(old_light, new_light)

# 2. Fix responsiveness and table squashing
# Remove the restrictive width
content = content.replace('.log-activity-panel .admin-table td:first-child {\n    width: 18%;\n}', '.log-activity-panel .admin-table td:first-child {\n    min-width: 120px;\n}')

# Fix the vertical wrapping in badges
content = content.replace('.badge {\n    display: inline-flex;', '.badge {\n    display: inline-flex;\n    white-space: nowrap;')

# Add specific min-widths for key columns in admin logs
extra_styles = """
.admin-table th:nth-child(2),
.admin-table td:nth-child(2) {
    min-width: 160px;
}

.admin-table th:nth-child(5),
.admin-table td:nth-child(5) {
    min-width: 100px;
}

@media (max-width: 1100px) {
    .log-explorer {
        grid-template-columns: 1fr;
    }
}
"""

# Append or insert extra styles
if '/* ================================\n   RESPONSIVE DESIGN\n   ================================ */' in content:
    content = content.replace('/* ================================\n   RESPONSIVE DESIGN\n   ================================ */', extra_styles + '\n/* ================================\n   RESPONSIVE DESIGN\n   ================================ */')
else:
    content += extra_styles

with open('app/static/css/styles.css', 'w') as f:
    f.write(content)
