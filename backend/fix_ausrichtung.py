with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

fixes = []
for i, line in enumerate(lines):
    if 'l_m.Institut' in line and 'FOM' in line:
        if i+1 < len(lines) and 'Ausrichtung' not in lines[i+1]:
            fixes.append(i)

print('Lines to fix:', [f+1 for f in fixes])
insert_line = "          AND l_m.Ausrichtung = 'national'\n"
for idx in reversed(fixes):
    lines.insert(idx+1, insert_line)

with open('app.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print('Done')
