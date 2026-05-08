import streamlit as st
import datetime
import os
import json
import gspread
from google.oauth2.service_account import Credentials

SHEET_URL = "https://docs.google.com/spreadsheets/d/1dDzr41dkiZHZPtESipMmke2Zqg9bD5aFGeReDG9U4rg/edit"
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

st.set_page_config(page_title="Rescate Paciente", layout="wide")

st.markdown(
    """
<style>
.titulo{font-size:32px;font-weight:bold;color:#0C2D53;text-align:center;padding:10px 20px;border-bottom:5px solid #F5BE25;margin-bottom:20px}
.seccion{font-size:18px;font-weight:bold;color:#FFFFFF;background:linear-gradient(135deg,#0C2D53,#1D9C96);padding:12px 20px;border-radius:10px;margin:20px 0;box-shadow:0 4px 6px rgba(0,0,0,0.1)}
.registro-box{background:#FFFFFF;border:2px solid #1D9C96;border-radius:10px;padding:15px;margin:10px 0;box-shadow:0 2px 4px rgba(0,0,0,0.05)}
/* Estilo para botones principales */
.stButton>button {
    background-color: #0C2D53 !important;
    color: white !important;
    border-radius: 8px !important;
    border: 2px solid #1D9C96 !important;
}
.stButton>button:hover {
    background-color: #1D9C96 !important;
    border-color: #F5BE25 !important;
}
</style>
""",
    unsafe_allow_html=True,
)

# ── Funciones compartidas ──────────────────────────────────────────────────────

import re

def get_creds():
    """Obtiene credenciales desde archivo local o desde Streamlit Secrets (para la nube)."""
    if os.path.exists("google_credentials.json"):
        try:
            return Credentials.from_service_account_file("google_credentials.json", scopes=SCOPES)
        except Exception as e:
            st.error(f"❌ Error con google_credentials.json local: {e}")
            # Si falla el local, intentamos con secrets
    
    # Intenta cargar desde Streamlit Secrets
    creds_info = None
    
    def clean_pem(pk):
        """Limpia una clave PEM de forma ultra-robusta."""
        pk = str(pk).strip()
        if "-----BEGIN PRIVATE KEY-----" in pk:
            header = "-----BEGIN PRIVATE KEY-----"
            footer = "-----END PRIVATE KEY-----"
            try:
                # Extraer cuerpo
                parts = pk.split(header)
                if len(parts) < 2: return pk
                body_parts = parts[1].split(footer)
                if len(body_parts) < 1: return pk
                body = body_parts[0]
                
                # 2. Eliminar todo lo que no sea caracteres base64 válidos
                body = body.replace('\\\\n', '').replace('\\n', '')
                body = re.sub(r'[^A-Za-z0-9+/]', '', body)
                
                # 3. Corregir padding (añadir = si falta) sin alterar los bits internos
                missing_padding = len(body) % 4
                if missing_padding:
                    body += '=' * (4 - missing_padding)

                # 4. Reconstruir envolviendo en 64 caracteres (estándar estricto PEM)
                wrapped_body = "\n".join(body[i:i+64] for i in range(0, len(body), 64))
                return f"{header}\n{wrapped_body}\n{footer}"
            except Exception:
                return pk.replace('\\\\n', '\n').replace('\\n', '\n')
        return pk.replace('\\\\n', '\n').replace('\\n', '\n')

    if "gcp_service_account" in st.secrets:
        creds_raw = st.secrets["gcp_service_account"]
        if isinstance(creds_raw, str):
            try:
                processed_raw = creds_raw.replace('\\\\n', '\\n').replace('\\n', '\n')
                creds_info = json.loads(processed_raw, strict=False)
            except Exception as e:
                st.error(f"❌ Error al parsear JSON de 'gcp_service_account': {e}")
                st.stop()
        else:
            creds_info = dict(creds_raw)
            
        if creds_info and "private_key" in creds_info:
            creds_info["private_key"] = clean_pem(creds_info["private_key"])
    
    elif "GCP_TYPE" in st.secrets:
        pk = clean_pem(st.secrets.get("GCP_PRIVATE_KEY", ""))
        creds_info = {
            "type": st.secrets.get("GCP_TYPE"),
            "project_id": st.secrets.get("GCP_PROJECT_ID"),
            "private_key_id": st.secrets.get("GCP_PRIVATE_KEY_ID"),
            "private_key": pk,
            "client_email": st.secrets.get("GCP_CLIENT_EMAIL"),
            "client_id": st.secrets.get("GCP_CLIENT_ID"),
            "auth_uri": st.secrets.get("GCP_AUTH_URI"),
            "token_uri": st.secrets.get("GCP_TOKEN_URI"),
            "auth_provider_x509_cert_url": st.secrets.get("GCP_AUTH_PROVIDER_X509_CERT_URL"),
            "client_x509_cert_url": st.secrets.get("GCP_CLIENT_X509_CERT_URL")
        }

    if creds_info:
        try:
            return Credentials.from_service_account_info(creds_info, scopes=SCOPES)
        except Exception as e:
            st.error(f"❌ Error de autenticación: {e}")
            st.stop()
    else:
        st.error("❌ No se encontraron credenciales en Streamlit Secrets.")
        st.stop()

def fmt(val):
    if val is None:
        return ""
    if isinstance(val, datetime.time):
        return val.strftime("%H:%M")
    if isinstance(val, datetime.date):
        return val.strftime("%d/%m/%Y")
    if isinstance(val, bool):
        return "Sí" if val else "No"
    return str(val)

def chk(val):
    if isinstance(val, str):
        return "☑" if val.lower() in ("sí", "si", "true", "1", "verdadero") else "☐"
    return "☑" if val else "☐"

def build_context_from_row(row):
    """Construye el contexto Jinja a partir de una fila de Google Sheets (lista de strings)."""
    def g(i): return row[i] if i < len(row) else ""
    causal = g(25)
    tipo_espera = g(19)
    motivo_tipo = g(38) if len(row) > 38 else ""  # columna extra si existe
    return {
        "id_reg": g(0), "fecha_registro": g(1), "motivo_contacto": g(2),
        "fecha_llamado1": g(3), "hora_llamada1": g(4),
        "fecha_llamado2": g(5), "hora_llamado2": g(6),
        "telefono_paciente": g(7), "telefono_alternativo": g(8),
        "chk_inubicable": chk(g(9)),
        "responsable_llamado": g(10), "centro_salud": g(11),
        "nombre_paciente": g(12), "rut_paciente": g(13),
        "chk_sabe_ubicar": chk(g(14)), "direccion": g(15),
        "nombre_contacto": g(16), "nombre_receptor": g(17),
        "relacion_paciente": g(18),
        "tipo_espera": tipo_espera,
        "chk_ambulatoria": chk(g(38) == "Confirmación de Cita"),
        "chk_hospitalaria": chk(g(38) == "Gestión de LE"),
        "chk_especialidades": chk(tipo_espera == "Consultas Especialidades"),
        "chk_quirurgica": chk(tipo_espera == "Intervención Quirúrgica"),
        "chk_procedimientos": chk(tipo_espera == "Procedimientos"),
        "chk_aps": chk(tipo_espera == "Consulta APS"),
        "policlinico": g(20), "diagnostico": g(21),
        "chk_problema_resuelto": chk(g(22)), "chk_ya_atendido": chk(g(23)),
        "chk_paciente_en_espera": chk(g(24)),
        "causal_egreso": causal,
        "chk_ges": chk(causal in ("0", "Causal 0", 0)),
        "chk_ssasur": chk(causal in ("1", "Causal 1", 1)),
        "chk_extrasistema": chk(causal in ("4", "Causal 4", 4)),
        "descripcion_causal": g(26), "prestador": g(27), "fecha_atencion": g(28),
        "chk_cambio_asegurador": chk(g(29)), "chk_recuperacion_espontanea": chk(g(30)),
        "chk_renuncia_rechazo": chk(g(31)), "chk_inasistencias": chk(g(32)),
        "chk_posterga_cirugia": chk(g(33)), "chk_fallecimiento": chk(g(34)),
        "observaciones": g(35), "firma_resp_contacto": g(36),
        "firma_resp_gestion": g(37), "estado_gestion": g(38) if len(row) > 38 else "",
    }

def generate_pdf(context, safe_rut, safe_id):
    """Genera el PDF desde la plantilla y devuelve (pdf_bytes, error)."""
    import base64
    from docxtpl import DocxTemplate
    from docx2pdf import convert

    template_name = "PROTOCOLO_TEMPLATE.docx"

    # Si el archivo no existe localmente, intenta recuperarlo de los secretos
    if not os.path.exists(template_name):
        if "word_template" in st.secrets:
            try:
                template_data = base64.b64decode(st.secrets["word_template"])
                with open(template_name, "wb") as f:
                    f.write(template_data)
            except Exception as e:
                return None, f"Error al decodificar la plantilla desde secretos: {e}"
        else:
            return None, "No se encontró la plantilla (archivo o secreto)."

    if not os.path.exists("pdfs_generados"):
        os.makedirs("pdfs_generados")

    docx_path = f"pdfs_generados/Protocolo_{safe_rut}_{safe_id}.docx"
    pdf_path  = f"pdfs_generados/Protocolo_{safe_rut}_{safe_id}.pdf"

    try:
        doc = DocxTemplate(template_name)
        doc.render(context)
        doc.save(docx_path)
        convert(docx_path, pdf_path)
    except Exception as e:
        return None, f"Error en generación/conversión: {e}"

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    return pdf_bytes, None


# ── Logo y Título ─────────────────────────────────────────────────────────────
col_logo1, col_logo2, col_logo3 = st.columns([1, 1.5, 1])
with col_logo2:
    st.image("servicio de orientacion.png", width='stretch')

st.markdown('<p class="titulo">FORMULARIO RESCATE PACIENTE</p>', unsafe_allow_html=True)
st.markdown("---")

# ── Sección: Registros Guardados ─────────────────────────────────────────────
with st.expander("📂 Registros Guardados — Generar PDF desde un registro existente", expanded=False):
    if st.button("🔄 Cargar Registros de Google Sheets"):
        try:
            creds = get_creds()
            client = gspread.authorize(creds)
            sheet = client.open_by_url(SHEET_URL).sheet1
            data = sheet.get_all_values()
            if data:
                st.session_state["sheet_data"] = data
                st.success(f"✅ {len(data)} filas cargadas (incluye encabezado si existe).")
            else:
                st.warning("La hoja está vacía.")
        except Exception as e:
            st.error(f"Error al cargar: {e}")

    if "sheet_data" in st.session_state and st.session_state["sheet_data"]:
        data = st.session_state["sheet_data"]
        # Detectar si primera fila es encabezado
        first = data[0]
        has_header = any(c.isalpha() and not c.replace('.','').replace('-','').replace(' ','').isdigit() for c in first[:3])
        rows = data[1:] if has_header else data

        if rows:
            import pandas as pd
            def safe(r, i): return r[i] if i < len(r) else ""
            preview = pd.DataFrame([
                {"#": i+1, "ID": safe(r,0), "Fecha": safe(r,1),
                 "Paciente": safe(r,12), "RUT": safe(r,13), "Estado": safe(r,38) if len(r)>38 else ""}
                for i, r in enumerate(rows)
            ])
            st.dataframe(preview, width='stretch', hide_index=True)

            opciones = [f"{i+1} — {safe(r,12)} ({safe(r,13)}) [{safe(r,0)}]" for i, r in enumerate(rows)]
            seleccion = st.selectbox("Selecciona un registro para generar su PDF:", opciones)
            idx = opciones.index(seleccion)
            row_sel = rows[idx]

            if st.button("📄 Generar PDF del registro seleccionado"):
                safe_rut = safe(row_sel, 13).replace(".","").replace("-","") or "s_rut"
                safe_id  = safe(row_sel, 0) or "s_id"
                context  = build_context_from_row(row_sel)

                with st.spinner("Generando PDF..."):
                    pdf_bytes, err = generate_pdf(context, safe_rut, safe_id)

                if err:
                    st.error(f"❌ {err}")
                else:
                    st.success("📄 PDF generado exitosamente.")
                    st.download_button(
                        label="⬇️ Descargar PDF",
                        data=pdf_bytes,
                        file_name=f"Protocolo_{safe_rut}_{safe_id}.pdf",
                        mime="application/pdf"
                    )
        else:
            st.info("No hay registros en la hoja.")

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
    st.session_state.tipo_espera = "Consultas Especialidades"
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
    st.session_state.motivo_contacto_tipo = "Confirmación de Cita"
    st.session_state.estado_gestion = "Resuelto"


with st.form("rescate_form"):
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<p class="seccion">IDENTIFICACIÓN</p>', unsafe_allow_html=True)
        id_reg = st.text_input("ID del Registro", key="id_reg", placeholder="Ej: RUT-RUP-001 (identificador único del caso)",
            help="Identificador interno del registro. Puede ser el RUT del paciente, número de RUP u otro código institucional."
        )
        fecha_registro = st.date_input("Fecha del Registro", key="fecha_registro", 
            help="Fecha en que se crea este registro de llamado telefónico."
        )

    with col2:
        st.markdown('<p class="seccion">MOTIVO CONTACTO</p>', unsafe_allow_html=True)
        motivo_contacto_tipo = st.selectbox("Motivo del Contacto", key="motivo_contacto_tipo",
            options=["", "Confirmación de Cita", "Gestión de LE"],
            help="CONFIRMACIÓN DE CITA: complete la 1ª hoja del protocolo. GESTIÓN DE LE: diríjase a la 2ª hoja (Lista de Espera).",
        )
        motivo_contacto = st.text_area("Descripción del Motivo", key="motivo_contacto",
            height=80,
            placeholder="Describa brevemente el motivo específico del llamado (Ej: confirmar hora de control, gestionar pendiente en lista de espera quirúrgica, etc.)",
        )

    st.markdown("---")
    st.markdown(
        '<p class="seccion">FECHA Y HORA DE LLAMADOS</p>', unsafe_allow_html=True
    )
    col3, col4, col5, col6 = st.columns(4)
    with col3:
        fecha_llamado1 = st.date_input("Fecha Llamado 1", key="fecha_llamado1",
            help="Fecha en que se realizó el primer intento de llamado al paciente."
        )
    with col4:
        hora_llamada1 = st.time_input("Hora Llamado 1", key="hora_llamada1",
            help="Hora exacta del primer llamado realizado.")
    with col5:
        fecha_llamado2 = st.date_input("Fecha Llamado 2", key="fecha_llamado2",
            help="Fecha del segundo intento de llamado (completar solo si hubo un segundo llamado)."
        )
    with col6:
        hora_llamado2 = st.time_input("Hora Llamado 2", key="hora_llamado2",
            help="Hora exacta del segundo llamado (completar solo si hubo un segundo llamado).")

    st.markdown("---")
    st.markdown('<p class="seccion">TELEFONÍA</p>', unsafe_allow_html=True)
    col7, col8, col9 = st.columns(3)
    with col7:
        telefono_paciente = st.text_input("Teléfono Principal del Paciente", key="telefono_paciente",
            placeholder="Ej: +56912345678 (primer número registrado en la ficha)",
            help="Número de teléfono principal del paciente según ficha clínica."
        )
    with col8:
        telefono_alternativo = st.text_input("Teléfono Alternativo", key="telefono_alternativo",
            placeholder="Ej: +56221234567 (teléfono de familiar, apoderado o contacto de emergencia)",
            help="Segundo número de contacto: puede ser de familiar, vecino u otro referente del paciente."
        )
    with col9:
        paciente_inubicable = st.checkbox("☐ PACIENTE INUBICABLE", key="paciente_inubicable",
            help="Marcar si NO se logró contactar al paciente en ninguno de los números disponibles. ACCIÓN REQUERIDA: activar visita domiciliaria o envío de carta certificada.",
        )

    col10, col11 = st.columns(2)
    with col10:
        responsable_llamado = st.text_input("Nombre del Responsable del Llamado", key="responsable_llamado",
            placeholder="Ej: María Soto (funcionario/a que realizó el llamado)",
            help="Nombre completo del funcionario o funcionaria que realiza este llamado telefónico. Este nombre quedará registrado en el protocolo."
        )
    with col11:
        pass

    st.markdown("---")
    st.markdown('<p class="seccion">CENTRO DE SALUD</p>', unsafe_allow_html=True)
    centro_salud = st.text_input("Centro de Salud / Hospital", key="centro_salud",
        placeholder="Ej: CESFAM Dr. Juan Noe, Hospital Base Osorno",
        help="Nombre del establecimiento de salud desde el cual se realiza el llamado (el que aparecerá en el protocolo: 'Le llamo del Hospital...')."
    )

    st.markdown("---")
    st.markdown('<p class="seccion">DATOS PACIENTE</p>', unsafe_allow_html=True)
    col12, col13 = st.columns(2)
    with col12:
        nombre_paciente = st.text_input("Nombre Completo del Paciente", key="nombre_paciente",
            placeholder="Ej: Juan Antonio González Pérez",
            help="Nombre y apellidos del paciente tal como aparece en su cédula de identidad y ficha clínica."
        )
    with col13:
        rut_paciente = st.text_input("RUT del Paciente", key="rut_paciente",
            placeholder="Ej: 12.345.678-9",
            help="RUT del paciente en formato con puntos y guión."
        )

    col14, col15 = st.columns(2)
    with col14:
        sabe_ubicar = st.checkbox("¿Quien respondió SABE cómo ubicar al paciente?", key="sabe_ubicar",
            help="Marcar si la persona que contestó el teléfono indicó que sabe cómo localizar al paciente. En ese caso, registrar teléfono y dirección donde puede ubicársele."
        )
    with col15:
        pass

    st.markdown("---")
    st.markdown('<p class="seccion">DIRECCIÓN</p>', unsafe_allow_html=True)
    direccion = st.text_area("Dirección del Paciente", key="direccion",
        height=80,
        placeholder="Ej: Calle Los Aromos 234, Villa El Sol, Osorno (calle, número, villa/población, ciudad)",
        help="Dirección donde puede ubicarse al paciente, entregada por quien respondió el llamado."
    )

    st.markdown("---")
    st.markdown('<p class="seccion">CONTACTO</p>', unsafe_allow_html=True)
    col16, col17 = st.columns(2)
    with col16:
        nombre_contacto = st.text_input("Nombre de la Persona de Contacto", key="nombre_contacto",
            placeholder="Ej: Rosa Pérez (persona que entregó información sobre el paciente)",
            help="Nombre de quien entregó la información al momento del llamado, en caso de que el paciente no haya respondido directamente."
        )
    with col17:
        pass

    st.markdown("---")
    st.markdown('<p class="seccion">RECEPTOR</p>', unsafe_allow_html=True)
    col18, col19 = st.columns(2)
    with col18:
        nombre_receptor = st.text_input("Nombre Completo del Receptor", key="nombre_receptor",
            placeholder="Ej: Carlos González (nombre de quien contestó el teléfono)",
            help="Nombre de la persona que atendió la llamada. Completar la sección '¿CON QUIÉN HABLO YO?'."
        )
    with col19:
        relacion_paciente = st.text_input("Relación del Receptor con el Paciente", key="relacion_paciente",
            placeholder="Ej: Hijo, Cónyuge, Madre, Vecino, Cuidador",
            help="Vínculo que tiene la persona que contestó con el paciente que se está buscando."
        )

    st.markdown("---")
    st.markdown('<p class="seccion">ATENCIÓN</p>', unsafe_allow_html=True)
    col20, col21, col22 = st.columns(3)
    with col20:
        tipo_espera = st.selectbox("Tipo de Lista de Espera", key="tipo_espera",
            options=["", "Consultas Especialidades", "Intervención Quirúrgica", "Procedimientos", "Consulta APS"],
            help="Seleccione según el tipo de prestación por la que el paciente está en lista de espera (LE). Solo completar si el motivo de contacto es 'Gestión de LE'.",
        )
    with col21:
        policlinico = st.text_input("Policlínico o Especialidad", key="policlinico",
            placeholder="Ej: Cardiología, Traumatología, Oftalmología, Cirugía General",
            help="Nombre del policlínico o especialidad médica a la que el paciente está esperando acceder."
        )
    with col22:
        pass

    diagnostico = st.text_area("Diagnóstico del Paciente", key="diagnostico",
        height=80,
        placeholder="Ej: Hipertensión Arterial Esencial, Artrosis de rodilla derecha, Catarata bilateral",
        help="Diagnóstico principal registrado en la lista de espera o en la ficha clínica del paciente."
    )

    st.markdown("---")
    st.markdown('<p class="seccion">ESTADO</p>', unsafe_allow_html=True)
    col23, col24, col25 = st.columns(3)
    with col23:
        problema_resuelto = st.checkbox("¿El problema de salud ya está resuelto?", key="problema_resuelto",
            help="Marcar si el paciente o su contacto informan que el problema de salud que motivó la LE ya fue resuelto."
        )
    with col24:
        ya_atendido = st.checkbox("¿El paciente ya fue atendido?", key="ya_atendido",
            help="Marcar si el paciente ya recibió la atención (cirugía, consulta, procedimiento) por la que estaba en lista de espera, ya sea en este u otro establecimiento."
        )
    with col25:
        paciente_en_espera = st.checkbox("☐ PACIENTE EFECTIVAMENTE EN ESPERA", key="paciente_en_espera",
            help="Marcar si el paciente confirma que AÚN está esperando la atención. ACCIÓN REQUERIDA: activar gestión de NODO."
        )

    st.markdown("---")
    st.markdown('<p class="seccion">CAUSAL EGRESO</p>', unsafe_allow_html=True)
    col26, col27 = st.columns(2)
    with col26:
        causal_egreso = st.selectbox("Causal de Egreso de Lista de Espera", key="causal_egreso",
            options=[0, 1, 4, 5, 6, 7, 8, 9],
            format_func=lambda x: {
                0: "Causal 0 – Paciente GES (activar egreso LE NO GES / SIGGES)",
                1: "Causal 1 – Atención realizada por SSASUR",
                4: "Causal 4 – Atención realizada en el Extrasistema",
                5: "Causal 5 – Cambio de Asegurador (imprimir cert. FONASA)",
                6: "Causal 6 – Renuncia o Rechazo Voluntario del Usuario",
                7: "Causal 7 – Recuperación Espontánea (solo LE consulta, no quirúrgica)",
                8: "Causal 8 – Inasistencias (2 NO GES / 3 GES)",
                9: "Causal 9 – Fallecimiento"
            }.get(x, str(x)),
            help="Seleccione la causal de egreso que corresponde según el protocolo institucional."
        )
    with col27:
        pass

    descripcion_causal = st.text_area("Descripción de la Causal", key="descripcion_causal",
        height=80,
        placeholder="Detalle adicional de la causal: nombre del establecimiento prestador, fecha, contexto relevante, etc.",
        help="Información complementaria que justifica la causal de egreso seleccionada."
    )

    col28, col29 = st.columns(2)
    with col28:
        prestador = st.text_input("Establecimiento Prestador", key="prestador",
            placeholder="Ej: Hospital Base Osorno, Clínica Bío-Bío",
            help="Nombre del establecimiento donde se realizó o realizará la atención (aplica para Causales 1 y 4)."
        )
    with col29:
        fecha_atencion = st.date_input("Fecha de Otorgamiento de la Atención", key="fecha_atencion",
            help="Fecha en que se otorgó la atención en el establecimiento prestador (aplica para Causales 1 y 4)."
        )

    st.markdown("---")
    st.markdown('<p class="seccion">SEGUIMIENTO</p>', unsafe_allow_html=True)
    col30, col31, col32, col33, col34, col35 = st.columns(6)
    with col30:
        cambio_asegurador = st.checkbox("Cambio de Asegurador (C5)", key="cambio_asegurador",
            help="Causal 5: El paciente cambió de sistema previsional (FONASA/ISAPRE). ACCIÓN: imprimir certificado FONASA."
        )
    with col31:
        recuperacion_espontanea = st.checkbox("Recuperación Espontánea (C7)", key="recuperacion_espontanea",
            help="Causal 7: El paciente se recuperó sin necesitar la intervención. Solo aplica para LE de consulta, NO para LE quirúrgica."
        )
    with col32:
        renuncia_rechazo = st.checkbox("Renuncia/Rechazo Voluntario (C6)", key="renuncia_rechazo",
            help="Causal 6: El usuario rechaza o renuncia voluntariamente a la prestación de salud pendiente."
        )
    with col33:
        inasistencias = st.checkbox("Inasistencias (C8)", key="inasistencias",
            help="Causal 8 NO GES: 2 inasistencias injustificadas. En casos GES: 3 inasistencias."
        )
    with col34:
        posterga_cirugia = st.checkbox("Posterga Cirugía", key="posterga_cirugia",
            help="El paciente solicita postergar la fecha de cirugía asignada."
        )
    with col35:
        fallecimiento = st.checkbox("Fallecimiento (C9)", key="fallecimiento",
            help="Causal 9: El paciente falleció. Verificar previamente en Registro Civil antes de realizar el llamado.")

    st.markdown("---")
    st.markdown('<p class="seccion">OBSERVACIONES</p>', unsafe_allow_html=True)
    observaciones = st.text_area("Observaciones", key="observaciones",
        height=100,
        placeholder="Registre aquí cualquier información relevante: actitud del paciente/contacto, acciones tomadas, derivaciones realizadas, próximos pasos, etc.",
        help="Campo libre para sistematizar la respuesta del contacto y registrar las acciones de seguimiento tomadas."
    )

    st.markdown("---")
    st.markdown('<p class="seccion">FIRMAS</p>', unsafe_allow_html=True)
    col36, col37 = st.columns(2)
    with col36:
        firma_resp_contacto = st.text_input("Nombre: Responsable del Contacto", key="firma_resp_contacto",
            placeholder="Ej: Ana Torres (funcionario/a que realizó el llamado)",
            help="Nombre del funcionario o funcionaria responsable de realizar el contacto telefónico con el paciente."
        )
    with col37:
        firma_resp_gestion = st.text_input("Nombre: Responsable de Gestión", key="firma_resp_gestion",
            placeholder="Ej: Dr. Pedro Silva (profesional a cargo de la gestión clínica)",
            help="Nombre del profesional responsable de la gestión o supervisión del caso."
        )

    st.markdown("---")
    st.markdown('<p class="seccion">ESTADO GESTIÓN</p>', unsafe_allow_html=True)
    estado_gestion = st.selectbox("Estado de la Gestión", key="estado_gestion",
        options=["", "Pendiente", "En Proceso", "Resuelto", "Cerrado"],
        help="Pendiente: requiere acciones adicionales. | En Proceso: gestión iniciada, aún sin resolver. | Resuelto: el problema de salud fue solucionado. | Cerrado: caso cerrado definitivamente (alta, egreso, fallecimiento).",
    )

    st.markdown("---")
    col38, col39 = st.columns([1, 1])
    with col38:
        submitted = st.form_submit_button(
            "💾 GUARDAR", type="primary", width='stretch'
        )
    with col39:
        pass

if submitted:
    # Si el ID está vacío, usar el RUT como código único
    final_id = id_reg if id_reg.strip() else rut_paciente
    
    row_data = [
        fmt(final_id), fmt(fecha_registro), fmt(motivo_contacto),
        fmt(fecha_llamado1), fmt(hora_llamada1),
        fmt(fecha_llamado2), fmt(hora_llamado2),
        fmt(telefono_paciente), fmt(telefono_alternativo),
        fmt(paciente_inubicable), fmt(responsable_llamado), fmt(centro_salud),
        fmt(nombre_paciente), fmt(rut_paciente), fmt(sabe_ubicar),
        fmt(direccion), fmt(nombre_contacto), fmt(nombre_receptor),
        fmt(relacion_paciente), fmt(tipo_espera), fmt(policlinico),
        fmt(diagnostico), fmt(problema_resuelto), fmt(ya_atendido),
        fmt(paciente_en_espera), fmt(causal_egreso), fmt(descripcion_causal),
        fmt(prestador), fmt(fecha_atencion), fmt(cambio_asegurador),
        fmt(recuperacion_espontanea), fmt(renuncia_rechazo), fmt(inasistencias),
        fmt(posterga_cirugia), fmt(fallecimiento), fmt(observaciones),
        fmt(firma_resp_contacto), fmt(firma_resp_gestion), fmt(motivo_contacto_tipo),
        fmt(estado_gestion)
    ]

    try:
        creds = get_creds()
        client = gspread.authorize(creds)
        sheet = client.open_by_url(SHEET_URL).sheet1
        sheet.append_row(row_data)
        st.success("✅ Registro guardado exitosamente en Google Sheets!")
        st.balloons()

        # Construir contexto PDF desde variables del formulario
        context = {
            "id_reg": fmt(final_id), "fecha_registro": fmt(fecha_registro),
            "motivo_contacto": fmt(motivo_contacto),
            "fecha_llamado1": fmt(fecha_llamado1), "hora_llamada1": fmt(hora_llamada1),
            "fecha_llamado2": fmt(fecha_llamado2), "hora_llamado2": fmt(hora_llamado2),
            "telefono_paciente": fmt(telefono_paciente),
            "telefono_alternativo": fmt(telefono_alternativo),
            "chk_inubicable": chk(paciente_inubicable),
            "responsable_llamado": fmt(responsable_llamado),
            "centro_salud": fmt(centro_salud),
            "nombre_paciente": fmt(nombre_paciente), "rut_paciente": fmt(rut_paciente),
            "chk_sabe_ubicar": chk(sabe_ubicar), "direccion": fmt(direccion),
            "nombre_contacto": fmt(nombre_contacto), "nombre_receptor": fmt(nombre_receptor),
            "relacion_paciente": fmt(relacion_paciente),
            "tipo_espera": fmt(tipo_espera),
            "chk_ambulatoria": chk(motivo_contacto_tipo == "Confirmación de Cita"),
            "chk_hospitalaria": chk(motivo_contacto_tipo == "Gestión de LE"),
            "chk_especialidades": chk(tipo_espera == "Consultas Especialidades"),
            "chk_quirurgica": chk(tipo_espera == "Intervención Quirúrgica"),
            "chk_procedimientos": chk(tipo_espera == "Procedimientos"),
            "chk_aps": chk(tipo_espera == "Consulta APS"),
            "policlinico": fmt(policlinico), "diagnostico": fmt(diagnostico),
            "chk_problema_resuelto": chk(problema_resuelto),
            "chk_ya_atendido": chk(ya_atendido),
            "chk_paciente_en_espera": chk(paciente_en_espera),
            "causal_egreso": fmt(causal_egreso),
            "chk_ges": chk(causal_egreso == 0),
            "chk_ssasur": chk(causal_egreso == 1),
            "chk_extrasistema": chk(causal_egreso == 4),
            "descripcion_causal": fmt(descripcion_causal),
            "prestador": fmt(prestador), "fecha_atencion": fmt(fecha_atencion),
            "chk_cambio_asegurador": chk(cambio_asegurador),
            "chk_recuperacion_espontanea": chk(recuperacion_espontanea),
            "chk_renuncia_rechazo": chk(renuncia_rechazo),
            "chk_inasistencias": chk(inasistencias),
            "chk_posterga_cirugia": chk(posterga_cirugia),
            "chk_fallecimiento": chk(fallecimiento),
            "observaciones": fmt(observaciones),
            "firma_resp_contacto": fmt(firma_resp_contacto),
            "firma_resp_gestion": fmt(firma_resp_gestion),
            "estado_gestion": fmt(estado_gestion),
        }

        safe_rut = fmt(rut_paciente).replace(".", "").replace("-", "") or "s_rut"
        safe_id  = fmt(final_id).replace(".", "").replace("-", "") or "s_id"

        with st.spinner("Generando PDF..."):
            pdf_bytes, err = generate_pdf(context, safe_rut, safe_id)

        if err:
            st.warning(f"⚠️ {err}")
        else:
            st.success("📄 PDF generado exitosamente.")
            st.download_button(
                label="⬇️ Descargar PDF",
                data=pdf_bytes,
                file_name=f"Protocolo_{safe_rut}_{safe_id}.pdf",
                mime="application/pdf"
            )

    except Exception as e:
        st.error(f"Error al guardar: {e}")

st.caption("v1.2")


