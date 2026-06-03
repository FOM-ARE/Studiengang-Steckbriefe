import re

path = r'z:\12_Hochschulinformationen bereitstellen\Studiengang-Steckbrief\Studiengang_Steckbriefe_Version_10\index.html'

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old = 'Ausrichtung national und international. Gesamtstudierende mit UV.'
new = 'Ausrichtung national (internationale Standorte ausgeschlossen). Gesamtstudierende mit UV.'
content = content.replace(old, new)

old2 = 'Ausrichtung national und international. Studienbeginner mit UV.'
new2 = 'Ausrichtung national (internationale Standorte ausgeschlossen). Studienbeginner mit UV.'
content = content.replace(old2, new2)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print('OK - Kommentare angepasst')
