import sys

with open('app/static/css/styles.css', 'r') as f:
    content = f.read()

# Fix gamer theme badge wrapping which was causing vertical text
old_gamer_badge = """[data-theme="gamer"] .log-account-card .badge,
[data-theme="gamer"] .admin-table .badge {
    white-space: normal;
    text-align: left;
    justify-content: flex-start;
}"""

new_gamer_badge = """[data-theme="gamer"] .log-account-card .badge,
[data-theme="gamer"] .admin-table .badge {
    white-space: nowrap;
    text-align: left;
    justify-content: flex-start;
}"""

content = content.replace(old_gamer_badge, new_gamer_badge)

# Also ensure table container always allows scrolling if needed, not just on mobile
content = content.replace('.table-container {\n    overflow: hidden;', '.table-container {\n    overflow-x: auto;')

with open('app/static/css/styles.css', 'w') as f:
    f.write(content)
