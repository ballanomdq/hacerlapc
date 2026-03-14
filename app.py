import streamlit as st
import requests
import re
import pandas as pd
import time
import os

st.set_page_config(page_title="Censo MDP", layout="centered")

st.title("🚀 Censo Mar del Plata")
st.info("Presioná el botón de abajo para iniciar el barrido de beneficiarios.")

# --- CONFIGURACIÓN DE ACCESO ---
URL = "http://200.51.42.43/empadronamiento/beneficiarios/emp_benef.asp"
HEADERS = {
    'User-Agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 10.0; WOW64; Trident/7.0)',
    'Content-Type': 'application/x-www-form-urlencoded',
    'Cookie': 'ASPSESSIONIDSAADDDQA=EEJPNPNCAMHCFHKELMGFLDAO; Usuario%280%29=rballano; Password=654321'
}

# --- LÓGICA DEL BARRIDO ---
if st.button("▶️ EMPEZAR BARRIDO"):
    resultados = []
    letras = "ABCDEFGHIJLMNOPRSTVZ"
    barra = st.progress(0)
    texto_estado = st.empty()
    
    for i, letra in enumerate(letras):
        texto_estado.write(f"🔎 Buscando letra: **{letra}**...")
        barra.progress((i + 1) / len(letras))
        
        payload = {'Tableta': '3', 'Nombre': letra, 'localidad': '390', 'TipoObra': 'O'}
        try:
            res = requests.post(URL, headers=HEADERS, data=payload, timeout=20)
            matches = re.findall(r"Benef\(1,(\d+),'(.*?)'\);", res.text)
            for dni, nombre in matches:
                resultados.append({'DNI': dni, 'Nombre': nombre})
            time.sleep(1.2)
        except:
            st.error(f"Error en letra {letra}")

    if resultados:
        df = pd.DataFrame(resultados)
        df.to_excel("CENSO_COMPLETO.xlsx", index=False)
        st.success(f"✅ ¡TERMINADO! {len(resultados)} encontrados.")
        st.balloons()
    else:
        st.error("No se capturaron datos. Revisá la sesión.")

# --- SECCIÓN DE DESCARGA (SIEMPRE VISIBLE SI EL ARCHIVO EXISTE) ---
st.markdown("---")
if os.path.exists("CENSO_COMPLETO.xlsx"):
    with open("CENSO_COMPLETO.xlsx", "rb") as f:
        st.download_button(
            label="⬇️ DESCARGAR EXCEL",
            data=f,
            file_name="Censo_OSECAC_MDP.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
else:
    st.write("⏳ El botón de descarga aparecerá aquí cuando finalice el barrido.")
