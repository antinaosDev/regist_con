import streamlit as st
import datetime
import os
import json
import gspread
import base64
from google.oauth2.service_account import Credentials
try:
    from word import word_template as WORD_TEMPLATE_B64
except ImportError:
    WORD_TEMPLATE_B64 = None

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

# --- CONFIGURACIÓN DE SEGURIDAD ---

def fix_pem_key(key_str):
    """
    Reconstruye una clave privada PEM con exactamente 64 caracteres por línea.
    Extrae solo el contenido Base64 puro para evitar errores de formato.
    """
    if not key_str:
        return key_str
    
    # 1. Normalizar saltos de línea literales
    key_str = key_str.replace("\\r\\n", "\n").replace("\\n", "\n")
    
    # 2. Extraer solo el contenido entre cabeceras o ignorar metadatos
    # Buscamos líneas que no sean cabeceras, comentarios ni estén vacías
    lines = key_str.split("\n")
    raw_content = ""
    for line in lines:
        l = line.strip()
        if not l or "BEGIN" in l or "END" in l or l.startswith("#") or "=" in l[:5]:
            continue
        raw_content += l

    # 3. Limpiar cualquier carácter que no sea Base64 (por si acaso)
    # Base64: A-Z, a-z, 0-9, +, /, y el padding =
    b64_only = "".join(re.findall(r'[A-Za-z0-9+/]+', raw_content))
    
    # 4. Añadir el padding '=' necesario al final si falta
    # (Aunque en PEM suele venir incluido, lo aseguramos)
    padding = len(b64_only) % 4
    if padding > 0:
        b64_only += "=" * (4 - padding)

    # 5. Reenvolver en líneas de 64 caracteres
    HEADER = "-----BEGIN PRIVATE KEY-----"
    FOOTER = "-----END PRIVATE KEY-----"
    chunks = [b64_only[i:i+64] for i in range(0, len(b64_only), 64)]
    
    return HEADER + "\n" + "\n".join(chunks) + "\n" + FOOTER + "\n"

def get_creds():

    """Obtiene credenciales GCP desde varias fuentes en orden de prioridad."""
    # 1. Archivo local (Desarrollo)
    if os.path.exists("google_credentials.json"):
        try:
            return Credentials.from_service_account_file("google_credentials.json", scopes=SCOPES)
        except Exception as e:
            st.error(f"❌ Error con google_credentials.json local: {e}")

    creds_info = None

    # 2. Campos individuales en Secrets (GCP_TYPE, GCP_PROJECT_ID, etc.)
    if "GCP_TYPE" in st.secrets:
        try:
            private_key = fix_pem_key(st.secrets["GCP_PRIVATE_KEY"])
            creds_info = {
                "type": st.secrets["GCP_TYPE"],
                "project_id": st.secrets["GCP_PROJECT_ID"],
                "private_key_id": st.secrets["GCP_PRIVATE_KEY_ID"],
                "private_key": private_key,
                "client_email": st.secrets["GCP_CLIENT_EMAIL"],
                "client_id": st.secrets["GCP_CLIENT_ID"],
                "auth_uri": st.secrets["GCP_AUTH_URI"],
                "token_uri": st.secrets["GCP_TOKEN_URI"],
                "auth_provider_x509_cert_url": st.secrets["GCP_AUTH_PROVIDER_X509_CERT_URL"],
                "client_x509_cert_url": st.secrets["GCP_CLIENT_X509_CERT_URL"],
            }
        except Exception as e:
            st.error(f"❌ Error leyendo campos GCP de Secrets: {e}")
            st.stop()

    # 3. Base64 completo en Secrets
    elif "GCP_JSON_B64" in st.secrets:
        try:
            decoded_json = base64.b64decode(st.secrets["GCP_JSON_B64"]).decode('utf-8')
            creds_info = json.loads(decoded_json)
        except Exception as e:
            st.error(f"❌ Error decodificando GCP_JSON_B64 de Secrets: {e}")
            st.stop()

    # 4. JSON como sección TOML en Secrets
    elif "gcp_service_account" in st.secrets:
        creds_raw = st.secrets["gcp_service_account"]
        if isinstance(creds_raw, str):
            try:
                creds_info = json.loads(creds_raw.replace('\\\\n', '\\n').replace('\\n', '\n'))
            except Exception as e:
                st.error(f"❌ Error en JSON gcp_service_account: {e}")
                st.stop()
        else:
            creds_info = dict(creds_raw)

    if creds_info:
        try:
            # Asegurar que la clave privada tenga el formato PEM correcto
            pk = creds_info.get("private_key", "")
            creds_info["private_key"] = fix_pem_key(pk)
            return Credentials.from_service_account_info(creds_info, scopes=SCOPES)
        except Exception as e:
            st.error(f"❌ Error de autenticación: {e}")
            st.stop()
    else:
        st.error("❌ No se encontraron credenciales. Configura los campos GCP_* en los Secrets de Streamlit.")
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

# --- VARIABLE PARA PLANTILLA INTEGRADA ---
# Pegar aquí el Base64 de la plantilla si no se encuentra el archivo local.
WORD_TEMPLATE_B64 = "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" 

def generate_pdf(context, safe_rut, safe_id):
    """Genera el PDF desde la plantilla integrada o local y devuelve (pdf_bytes, error)."""
    from docxtpl import DocxTemplate
    from docx2pdf import convert

    template_name = "PROTOCOLO_TEMPLATE.docx"

    # 1. Recuperar plantilla (prioridad archivo local, luego integrada)
    if not os.path.exists(template_name):
        template_source = ""
        if WORD_TEMPLATE_B64:
            template_source = WORD_TEMPLATE_B64
        elif "word_template" in st.secrets:
            template_source = st.secrets["word_template"]
        
        if template_source:
            try:
                template_data = base64.b64decode(template_source)
                with open(template_name, "wb") as f:
                    f.write(template_data)
            except Exception as e:
                return None, f"Error al decodificar la plantilla integrada: {e}"
        else:
            return None, "No se encontró la plantilla (falta archivo o WORD_TEMPLATE_B64 en el código)."

    if not os.path.exists("pdfs_generados"):
        os.makedirs("pdfs_generados")

    docx_path = f"pdfs_generados/Protocolo_{safe_rut}_{safe_id}.docx"
    pdf_path  = f"pdfs_generados/Protocolo_{safe_rut}_{safe_id}.pdf"

    try:
        doc = DocxTemplate(template_name)
        doc.render(context)
        doc.save(docx_path)
        # Nota: En Streamlit Cloud Linux, docx2pdf puede fallar si no hay Word instalado.
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


