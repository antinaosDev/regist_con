import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

button_code = '''st.markdown(
    """
<style>
.titulo{font-size:28px;font-weight:bold;color:#1e3a5f;text-align:center;padding:20px;border-bottom:4px solid #2563eb}
.seccion{font-size:16px;font-weight:bold;color:#2563be;background:linear-gradient(135deg,#e0e7ff,#c7d2fe);padding:12px;border-radius:8px;margin:15px 0}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown('<p class="titulo">FORMULARIO RESCATE PACIENTE</p>', unsafe_allow_html=True)
st.markdown("---")

if st.button("🧪 Generar Datos de Prueba"):
    import datetime
    st.session_state.id_reg = "TEST-12345"
    st.session_state.fecha_registro = datetime.date.today()
    st.session_state.motivo_contacto = "Motivo de prueba generado automáticamente"
    st.session_state.fecha_llamado1 = datetime.date.today()
    st.session_state.hora_llamada1 = datetime.datetime.now().time()
    st.session_state.fecha_llamado2 = datetime.date.today()
    st.session_state.hora_llamado2 = datetime.datetime.now().time()
    st.session_state.telefono_paciente = "+56912345678"
    st.session_state.telefono_alternativo = "+56987654321"
    st.session_state.paciente_inubicable = False
    st.session_state.responsable_llamado = "Juan Pérez"
    st.session_state.centro_salud = "CESFAM Centro"
    st.session_state.nombre_paciente = "María González"
    st.session_state.rut_paciente = "12.345.678-9"
    st.session_state.sabe_ubicar = True
    st.session_state.direccion = "Av. Principal 123, Depto 4B, Santiago"
    st.session_state.nombre_contacto = "Pedro González"
    st.session_state.nombre_receptor = "Laura Smith"
    st.session_state.relacion_paciente = "Hijo"
    st.session_state.tipo_espera = "Ambulatoria"
    st.session_state.policlinico = "Cardiología"
    st.session_state.diagnostico = "Hipertensión Arterial en tratamiento"
    st.session_state.problema_resuelto = True
    st.session_state.ya_atendido = False
    st.session_state.paciente_en_espera = False
    st.session_state.causal_egreso = 1
    st.session_state.descripcion_causal = "Atención realizada de forma exitosa"
    st.session_state.prestador = "Hospital Regional"
    st.session_state.fecha_atencion = datetime.date.today()
    st.session_state.cambio_asegurador = False
    st.session_state.recuperacion_espontanea = False
    st.session_state.renuncia_rechazo = False
    st.session_state.inasistencias = False
    st.session_state.posterga_cirugia = False
    st.session_state.fallecimiento = False
    st.session_state.observaciones = "Sin observaciones adicionales. (Datos de prueba)"
    st.session_state.firma_resp_contacto = "Juan Pérez"
    st.session_state.firma_resp_gestion = "Dr. Silva"
    st.session_state.estado_gestion = "Resuelto"
'''

content = content.replace('''st.markdown(
    """
<style>
.titulo{font-size:28px;font-weight:bold;color:#1e3a5f;text-align:center;padding:20px;border-bottom:4px solid #2563eb}
.seccion{font-size:16px;font-weight:bold;color:#2563be;background:linear-gradient(135deg,#e0e7ff,#c7d2fe);padding:12px;border-radius:8px;margin:15px 0}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown('<p class="titulo">FORMULARIO RESCATE PACIENTE</p>', unsafe_allow_html=True)
st.markdown("---")''', button_code)

inputs = [
    'id_reg', 'fecha_registro', 'motivo_contacto', 'fecha_llamado1', 'hora_llamada1',
    'fecha_llamado2', 'hora_llamado2', 'telefono_paciente', 'telefono_alternativo',
    'paciente_inubicable', 'responsable_llamado', 'centro_salud', 'nombre_paciente',
    'rut_paciente', 'sabe_ubicar', 'direccion', 'nombre_contacto', 'nombre_receptor',
    'relacion_paciente', 'tipo_espera', 'policlinico', 'diagnostico', 'problema_resuelto',
    'ya_atendido', 'paciente_en_espera', 'causal_egreso', 'descripcion_causal',
    'prestador', 'fecha_atencion', 'cambio_asegurador', 'recuperacion_espontanea',
    'renuncia_rechazo', 'inasistencias', 'posterga_cirugia', 'fallecimiento',
    'observaciones', 'firma_resp_contacto', 'firma_resp_gestion', 'estado_gestion'
]

for inp in inputs:
    pattern = r'^(\s*' + inp + r'\s*=\s*st\.(?:text_input|date_input|text_area|time_input|checkbox|selectbox|number_input)\()'
    replacement = r'\g<1>key="' + inp + '", '
    content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Updated app.py')
