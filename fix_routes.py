import os

filepath = 'app/routes.py'
with open(filepath, 'r') as f:
    lines = f.readlines()

new_lines = []
skip = False
# Skip the first build_dashboard_insights definition (lines 107-196 approx)
in_duplicate = False
for i, line in enumerate(lines):
    if line.startswith('def build_dashboard_insights(juegos: list[dict], user_id: str) -> dict:'):
        in_duplicate = True
        continue
    if in_duplicate:
        if line.startswith('LANDING_SAMPLE_COLLECTIONS = ['):
            in_duplicate = False
        else:
            continue
    new_lines.append(line)

# Now replace the call to build_dashboard_insights(juegos, user_id) with build_dashboard_insights(juegos)
# And update the dashboard route to not pass user_id

final_lines = []
for line in new_lines:
    if 'dashboard_insights = build_dashboard_insights(juegos, user_id)' in line:
        final_lines.append(line.replace('(juegos, user_id)', '(juegos)'))
    else:
        final_lines.append(line)

with open(filepath, 'w') as f:
    f.writelines(final_lines)
