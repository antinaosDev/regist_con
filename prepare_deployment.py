import base64
import os
import re

def get_base64_of_file(filename):
    if not os.path.exists(filename):
        return None
    with open(filename, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def update_app_py_template(b64_string):
    app_path = "app.py"
    if not os.path.exists(app_path):
        print("❌ No se encontró app.py")
        return
    
    with open(app_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Reemplazar la variable WORD_TEMPLATE_B64
    new_line = f'WORD_TEMPLATE_B64 = "{b64_string}"'
    updated_content = re.sub(r'WORD_TEMPLATE_B64 = ".*"', new_line, content)
    
    with open(app_path, "w", encoding="utf-8") as f:
        f.write(updated_content)
    print("SUCCESS: app.py actualizado con la plantilla integrada.")

def main():
    print("--- Preparando despliegue de Rescate Paciente ---\n")
    
    # 1. Credenciales GCP
    creds_file = "google_credentials.json"
    b64_creds = get_base64_of_file(creds_file)
    if b64_creds:
        print("--- COPIA ESTO EN LOS SECRETS DE STREAMLIT (GCP_JSON_B64) ---")
        print(b64_creds)
        print("------------------------------------------------------------\n")
    else:
        print(f"WARN: No se encontro {creds_file}. Asegurate de tenerlo localmente para generar el Secret.")
    
    # 2. Plantilla Word
    template_file = "PROTOCOLO_TEMPLATE.docx"
    b64_template = get_base64_of_file(template_file)
    if b64_template:
        update_app_py_template(b64_template)
    else:
        print(f"WARN: No se encontro {template_file}. No se pudo integrar en app.py.")

if __name__ == "__main__":
    main()
