from docx import Document
import sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

doc = Document('PROTOCOLO_TEMPLATE.docx')

# Track if we already fixed the "nombre responsable" line above
prev_was_responsable = False

for p in doc.paragraphs:
    full = ''.join(r.text for r in p.runs)
    
    # If this paragraph is ONLY the tag (duplicated from previous fix), remove it
    if full.strip() == '{{ responsable_llamado }}' and prev_was_responsable:
        for r in p.runs:
            r.text = ''
        prev_was_responsable = False
        continue

    if '{{ responsable_llamado }}' in full:
        prev_was_responsable = True
    else:
        prev_was_responsable = False

    # Remove trailing underscores from OBSERVACIONES line
    if '{{ observaciones }}' in full and '_' in full:
        cleaned = re.sub(r'_+\s*$', '', full).rstrip()
        if p.runs:
            p.runs[0].text = cleaned
            for r in p.runs[1:]:
                r.text = ''

doc.save('PROTOCOLO_TEMPLATE.docx')
print('Limpieza final OK. Template completamente listo.')
