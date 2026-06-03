import re

path = r'z:\12_Hochschulinformationen bereitstellen\Studiengang-Steckbrief\Studiengang_Steckbriefe_Version_10\index.html'

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Match the entire hint text on the Uebergangsverhalten page
pattern = r'(<strong>\* Hinweis:</strong>) Es werden Bachelor-Absolventen \(Ausstiegsstatus.+?/ 180\)\.'
replacement = r'\1 Es werden Bachelor-Absolventen der letzten 5 Kohortenjahre ber' + '\u00fc' + r'cksichtigt, deren Regelstudienzeit bereits abgeschlossen ist.'

new_content, count = re.subn(pattern, replacement, content)
if count > 0:
    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f'OK - {count} Ersetzung(en) vorgenommen')
else:
    print('NICHT GEFUNDEN')
