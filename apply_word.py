import win32com.client
import os

word = win32com.client.Dispatch("Word.Application")
word.Visible = False

doc_path = os.path.abspath("PROTOCOLO DE LLAMADO.docx")
new_path = os.path.abspath("PROTOCOLO_TEMPLATE.docx")

doc = word.Documents.Open(doc_path)

replacements = [
    ('FECHA Y HORA DEL LLAMADO 1 ___/____/_____ _______ hrs', 'FECHA Y HORA DEL LLAMADO 1: {{ fecha_llamado1 }} {{ hora_llamada1 }} hrs'),
    ('FECHA Y HORA DEL LLAMADO 2 ___/____/_____ _______ hrs', 'FECHA Y HORA DEL LLAMADO 2: {{ fecha_llamado2 }} {{ hora_llamado2 }} hrs'),
    ('NUMEROS DE TELEFONO _________________ _________________ _________________', 'NUMEROS DE TELEFONO: {{ telefono_paciente }} / {{ telefono_alternativo }}'),
    ('LE LLAMO DEL HOSPITAL (centro de salud) _______________________________________________________', 'LE LLAMO DEL HOSPITAL: {{ centro_salud }}'),
    ('COMPLETO _____________________________________________________ RUT _______________________', 'COMPLETO: {{ nombre_paciente }}    RUT: {{ rut_paciente }}'),
    ('TELEFONO_____________________________ DIRECCIÓN __________________________________________', 'TELEFONO: {{ telefono_paciente }}   DIRECCIÓN: {{ direccion }}'),
    ('NOMBRE DE PERSONA DE CONTACTO ___________________________________________________________', 'NOMBRE DE PERSONA DE CONTACTO: {{ nombre_contacto }}'),
    ('COMPLETO _________________________________________________________________________________', 'COMPLETO: {{ nombre_receptor }}'),
    ('CON EL PACIENTE_____________________________________________________________________________', 'CON EL PACIENTE: {{ relacion_paciente }}'),
    ('POLICLÍNICO O ESPECIALIDAD ________________________________________________________________', 'POLICLÍNICO O ESPECIALIDAD: {{ policlinico }}'),
    ('DIAGNÓSTICO _____________________________________________________________________________', 'DIAGNÓSTICO: {{ diagnostico }}'),
    ('Establecimiento prestador __________________________________________________________', 'Establecimiento prestador: {{ prestador }}'),
    ('Fecha otorgamiento __________________________________________________________', 'Fecha otorgamiento: {{ fecha_atencion }}'),
    ('FIRMA DEL RESPONSABLE DEL CONTACTO', 'FIRMA DEL RESPONSABLE DEL CONTACTO: {{ firma_resp_contacto }}'),
    ('FIRMA RESPONSABLE DE GESTION', 'FIRMA RESPONSABLE DE GESTION: {{ firma_resp_gestion }}'),
    ('▢ CONFIRMACIÓN DE CITA', '{{ chk_ambulatoria }} CONFIRMACIÓN DE CITA'),
    ('▢ GESTIÓN DE LE', '{{ chk_hospitalaria }} GESTIÓN DE LE'),
    ('▢ PACIENTE INUBICABLE', '{{ chk_inubicable }} PACIENTE INUBICABLE'),
    ('▢ CONSULTAS ESPECIALIDADES', '{{ chk_especialidades }} CONSULTAS ESPECIALIDADES'),
    ('▢ INTERVENCION QUIRÚRGICA', '{{ chk_quirurgica }} INTERVENCION QUIRÚRGICA'),
    ('▢ PROCEDIMIENTOS', '{{ chk_procedimientos }} PROCEDIMIENTOS'),
    ('▢ CONSULTA APS', '{{ chk_aps }} CONSULTA APS'),
    ('▢ PACIENTE EFECTIVAMENTE EN ESPERA', '{{ chk_paciente_en_espera }} PACIENTE EFECTIVAMENTE EN ESPERA'),
    ('▢ PACIENTE GES (CAUSAL Nº 0)', '{{ chk_ges }} PACIENTE GES (CAUSAL Nº 0)'),
    ('▢ ATENCION REALIZADA POR SSASUR', '{{ chk_ssasur }} ATENCION REALIZADA POR SSASUR'),
    ('▢ ATENCION REALIZADA EN EL EXTRASISTEMA', '{{ chk_extrasistema }} ATENCION REALIZADA EN EL EXTRASISTEMA'),
    ('▢ CAMBIO DE ASEGURADOR', '{{ chk_cambio_asegurador }} CAMBIO DE ASEGURADOR'),
    ('▢ RECUPERACIÓN ESPONTÁNEA', '{{ chk_recuperacion_espontanea }} RECUPERACIÓN ESPONTÁNEA'),
    ('▢ RENUNCIA O RECHAZO VOLUNTARIO', '{{ chk_renuncia_rechazo }} RENUNCIA O RECHAZO VOLUNTARIO'),
    ('▢ INASISTENCIAS', '{{ chk_inasistencias }} INASISTENCIAS'),
    ('▢ POSTERGA CIRUGIA', '{{ chk_posterga_cirugia }} POSTERGA CIRUGIA'),
    ('▢ FALLECIMIENTO', '{{ chk_fallecimiento }} FALLECIMIENTO')
]

for find_str, replace_str in replacements:
    word.Selection.HomeKey(Unit=6)
    word.Selection.Find.ClearFormatting()
    word.Selection.Find.Replacement.ClearFormatting()
    word.Selection.Find.Execute(
        FindText=find_str,
        MatchCase=False, MatchWholeWord=False, MatchWildcards=False,
        MatchSoundsLike=False, MatchAllWordForms=False, Forward=True,
        Wrap=1, Format=False, ReplaceWith=replace_str, Replace=2
    )

# OBSERVACIONES (using wildcards to avoid length limit)
word.Selection.HomeKey(Unit=6)
word.Selection.Find.Execute(
    FindText="OBSERVACIONES: _@",
    MatchWildcards=True,
    ReplaceWith="OBSERVACIONES: {{ observaciones }}",
    Replace=2
)

# MUY BUENOS DÍAS with newline
word.Selection.HomeKey(Unit=6)
word.Selection.Find.Execute(
    FindText="MUY BUENOS DÍAS (TARDES), MI NOMBRE ES (registrar responsable del Llamado)^p__________________________________________________________________________________________",
    ReplaceWith="MUY BUENOS DÍAS (TARDES), MI NOMBRE ES: {{ responsable_llamado }}",
    Replace=2
)

doc.SaveAs(new_path)
doc.Close()
word.Quit()
print("Applied formatting changes via MS Word.")
