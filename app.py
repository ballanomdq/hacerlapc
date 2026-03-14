import streamlit as st
import requests
import re
import pandas as pd
import time
import os

# 1. Configuración básica de la interfaz
st.set_page_config(page_title="Censo OSECAC MDP", layout="centered")

st.title("🕵️ Auditoría Mar del Plata")
st.write("Estado actual: **Listo para iniciar**")

# 2. El botón de INICIO
if st.button("▶️ INICIAR CENSO"):
    resultados = []
    letras = "ABCDEFGHIJLMNOPRSTVZ"
    
    # 3. La BARRA DE PROGRESO que pediste
    barra = st.progress(0)
    estado = st.empty()
    
    # Datos de acceso (Cookie y Usuario)
    URL = "http://200.51.42.43/empadronamiento/beneficiarios/emp_benef.asp"
    HEADERS = {
        'User-Agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 10.0; WOW64; Trident/7.0)',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Cookie': 'ASPSESSIONIDSAADDDQA=EEJPNPNCAMHCFHKELMGFLDAO; Usuario%280%29=rballano; Password=654321'
    }

    for i, letra in enumerate(letras):
        # Actualizamos la barra y el texto
        progreso_actual = (i + 1) / len(letras)
        barra.progress(progreso_actual)
        estado.write(f"🔎 Procesando letra: **{letra}**...")
        
        payload = {'Tableta': '3', 'Nombre': letra, 'localidad': '390', 'TipoObra': 'O'}
        
        try:
            res = requests.post(URL, headers=HEADERS, data=payload, timeout=20)
            matches = re.findall(r"Benef\(1,(\d+),'(.*?)'\);", res.text)
            for dni, nombre in matches:
                resultados.append({'DNI': dni, 'Nombre': nombre})
            time.sleep(1.2) # Sigilo para no ser detectado
        except:
            st.error(f"Error en letra {letra}")

    if resultados:
        # 4. Generamos el archivo cuando dice "LISTO"
        df = pd.DataFrame(resultados)
        df.to_excel("CENSO_FINAL.xlsx", index=False)
        st.success(f"✅ ¡LISTO! Se encontraron {len(resultados)} personas.")
        st.balloons()
    else:
        st.error("No se capturaron datos. Revisá si la sesión rballano expiró.")

# 5. El botón de DESCARGAR (Aparece abajo cuando el archivo existe)
st.divider()
if os.path.exists("CENSO_FINAL.xlsx"):
    with open("CENSO_FINAL.xlsx", "rb") as f:
        st.download_button(
            label="⬇️ DESCARGAR EXCEL AHORA",
            data=f,
            file_name="Censo_OSECAC_MDP.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
else:
    st.info("El botón de descarga aparecerá aquí abajo cuando el censo termine.")
