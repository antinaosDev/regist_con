from docx import Document
import sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

doc = Document('PROTOCOLO_TEMPLATE.docx')

def replace_in_paragraph(para, find, replace):
    full_text = ''.join(r.text for r in para.runs)
    if find not in full_text:
        return False
    new_text = full_text.replace(find, replace)
    if para.runs:
        para.runs[0].text = new_text
        for r in para.runs[1:]:
            r.text = ''
    return True

for p in doc.paragraphs:
    full = ''.join(r.text for r in p.runs)
    
    # Línea de guiones sola (línea para firma del responsable de llamado)
    if full.strip() == '__________________________________________________________________________________________':
        if p.runs:
            p.runs[0].text = '{{ responsable_llamado }}'
            for r in p.runs[1:]:
                r.text = ''
        continue

    # OBSERVACIONES con guiones extra al final
    if '{{ observaciones }}' in full and '_' in full:
        cleaned = re.sub(r'_+$', '', full).rstrip()
        if p.runs:
            p.runs[0].text = cleaned
            for r in p.runs[1:]:
                r.text = ''

doc.save('PROTOCOLO_TEMPLATE.docx')
print('Correcciones finales OK.')
