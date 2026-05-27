import openpyxl

path = r'Z:\12_Hochschulinformationen bereitstellen\Studiengang-Steckbrief-Versionen\Verision-1\Rahmengebendes\Asgard-HO\Allgemeines\Farbwelten Ressort, HSB, Institut für VSC.xlsx'
wb = openpyxl.load_workbook(path)
print('Sheets:', wb.sheetnames)
for name in wb.sheetnames:
    ws = wb[name]
    print(f'\n=== {name} (rows={ws.max_row}, cols={ws.max_column}) ===')
    for row in ws.iter_rows(min_row=1, max_row=min(25, ws.max_row), values_only=False):
        vals = []
        colors = []
        for cell in row:
            v = str(cell.value)[:30] if cell.value else ''
            vals.append(v)
            if cell.fill and cell.fill.fgColor and cell.fill.fgColor.rgb:
                rgb = cell.fill.fgColor.rgb
                if rgb != '00000000':
                    try:
                        hex_color = f'#{str(rgb)[-6:]}' if isinstance(rgb, str) else f'#{rgb.index:06X}' if hasattr(rgb, 'index') else str(rgb)
                    except:
                        hex_color = str(rgb)
                    colors.append(f'{cell.column_letter}{cell.row}={hex_color}')
        print(' | '.join(vals), '  ', colors if colors else '')
