import streamlit as st
import requests
import re
import pandas as pd
import time

# Configuración de la página para que se vea profesional (según tu estilo minimalista)
st.set_page_config(page_title="Auditoría OSECAC MDP", page_icon="🕵️")

st.title("🚀 Censo de Beneficiarios - Mar del Plata")
st.write("Presioná el botón y **no cierres la pestaña** hasta que aparezca el botón de descarga.")

# Datos de acceso configurados
URL = "http://200.51.42.43/empadronamiento/beneficiarios/emp_benef.asp"
HEADERS = {
    'User-Agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 10.0; WOW64; Trident/7.0)',
    'Content-Type': 'application/x-www-form-urlencoded',
    'Cookie': 'ASPSESSIONIDSAADDDQA=EEJPNPNCAMHCFHKELMGFLDAO; Usuario%280%29=rballano; Password=654321'
}

# 1. BOTÓN DE INICIO
if st.button("▶️ INICIAR BARRIDO MASIVO"):
    resultados = []
    letras = "ABCDEFGHIJLMNOPRSTVZ"
    
    progreso = st.progress(0)
    estado = st.empty()
    
    for i, letra in enumerate(letras):
        # Actualización de interfaz para evitar hibernación
        percent = (i + 1) / len(letras)
        progreso.progress(percent)
        estado.write(f"🔎 Buscando letra: **{letra}**...")
        
        payload = {'Tableta': '3', 'Nombre': letra, 'localidad': '390', 'TipoObra': 'O'}
        
        try:
            res = requests.post(URL, headers=HEADERS, data=payload, timeout=20)
            matches = re.findall(r"Benef\(1,(\d+),'(.*?)'\);", res.text)
            
            for dni, nombre in matches:
                resultados.append({'DNI': dni, 'Nombre': nombre})
            
            time.sleep(1.2) # Pausa estratégica
        except Exception as e:
            st.error(f"Error en letra {letra}: {e}")

    if resultados:
        df = pd.DataFrame(resultados)
        # Guardamos el archivo físicamente en el servidor
        df.to_excel("CENSO_MDP.xlsx", index=False)
        st.success(f"✅ ¡FINALIZADO! Se encontraron {len(resultados)} registros.")
    else:
        st.warning("No se obtuvieron datos. Verificá la sesión rballano.")

# 2. SECCIÓN DE DESCARGA (FUERA DEL IF PARA QUE NO DESAPAREZCA)
st.divider()
try:
    with open("CENSO_MDP.xlsx", "rb") as f:
        st.download_button(
            label="⬇️ DESCARGAR EXCEL DEL CENSO",
            data=f,
            file_name="Censo_OSECAC_MDP.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
except FileNotFoundError:
    st.info("El botón de descarga aparecerá aquí apenas termine el proceso.")
