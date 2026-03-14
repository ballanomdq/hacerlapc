import streamlit as st
import requests
import re
import pandas as pd
import time

st.set_page_config(page_title="Auditoría OSECAC MDP", page_icon="🕵️")

st.title("🚀 Censo de Beneficiarios - Mar del Plata")
st.write("Presioná el botón para iniciar el barrido. **No cierres la pestaña** hasta que termine.")

# Datos de acceso (Los que ya tenés funcionando)
URL = "http://200.51.42.43/empadronamiento/beneficiarios/emp_benef.asp"
HEADERS = {
    'User-Agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 10.0; WOW64; Trident/7.0)',
    'Content-Type': 'application/x-www-form-urlencoded',
    'Cookie': 'ASPSESSIONIDSAADDDQA=EEJPNPNCAMHCFHKELMGFLDAO; Usuario%280%29=rballano; Password=654321'
}

if st.button("▶️ INICIAR BARRIDO MASIVO"):
    resultados = []
    letras = "ABCDEFGHIJLMNOPRSTVZ"
    
    progreso = st.progress(0)
    estado = st.empty()
    
    for i, letra in enumerate(letras):
        # Actualizamos la interfaz para que sepas que NO está colgada
        percent = (i + 1) / len(letras)
        progreso.progress(percent)
        estado.write(f"🔎 Buscando letra: **{letra}**...")
        
        payload = {'Tableta': '3', 'Nombre': letra, 'localidad': '390', 'TipoObra': 'O'}
        
        try:
            res = requests.post(URL, headers=HEADERS, data=payload, timeout=20)
            matches = re.findall(r"Benef\(1,(\d+),'(.*?)'\);", res.text)
            
            for dni, nombre in matches:
                resultados.append({'DNI': dni, 'Nombre': nombre})
            
            time.sleep(1.5) # Pausa de seguridad
        except Exception as e:
            st.error(f"Error en letra {letra}: {e}")

    if resultados:
        df = pd.DataFrame(resultados)
        # Guardamos el Excel en memoria para la descarga
        excel_name = "CENSO_MDP.xlsx"
        df.to_excel(excel_name, index=False)
        
        st.success(f"✅ ¡Finalizado! Se encontraron {len(resultados)} beneficiarios.")
        
        # EL BOTÓN DE DESCARGA APARECE SOLO AL FINAL
        with open(excel_name, "rb") as f:
            st.download_button(
                label="⬇️ DESCARGAR EXCEL COMPLETO",
                data=f,
                file_name="Censo_OSECAC_MDP.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.warning("No se encontraron datos. Revisá si la sesión de rballano sigue activa.")
