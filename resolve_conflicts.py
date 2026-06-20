import os

filepath = 'app/routes.py'
with open(filepath, 'r') as f:
    lines = f.readlines()

new_lines = []
skip = False
for line in lines:
    if line.startswith('<<<<<<< HEAD'):
        skip = True
        continue
    if line.startswith('======='):
        skip = False
        continue
    if line.startswith('>>>>>>> origin/main'):
        continue
    if not skip:
        new_lines.append(line)

with open(filepath, 'w') as f:
    f.writelines(new_lines)
