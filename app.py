import streamlit as st
import requests
import re
import pandas as pd
import time
import os

# 1. Configuración de la interfaz (Estilo limpio)
st.set_page_config(page_title="Censo OSECAC MDP", page_icon="🕵️")

st.title("🚀 Censo de Beneficiarios - Mar del Plata")
st.write("Estado: **Conexión establecida con sesión Miramar**")

# 2. El botón de INICIO
if st.button("▶️ INICIAR BARRIDO AHORA"):
    resultados = []
    letras = "ABCDEFGHIJLMNOPRSTVZ"
    
    # Barra de progreso y texto de estado
    barra = st.progress(0)
    estado = st.empty()
    
    # DATOS DE ACCESO (Actualizados con tu captura)
    URL = "http://200.51.42.43/empadronamiento/beneficiarios/emp_benef.asp"
    HEADERS = {
        'User-Agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 10.0; WOW64; Trident/7.0)',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Cookie': 'ASPSESSIONIDSAABAAQD=JLLLNINCNCKMKPODPKJKNJMO; Usuario%280%29=rballano; Password=654321'
    }

    for i, letra in enumerate(letras):
        # Actualizamos la interfaz
        progreso_actual = (i + 1) / len(letras)
        barra.progress(progreso_actual)
        estado.write(f"🔎 Buscando letra: **{letra}**...")
        
        payload = {'Tableta': '3', 'Nombre': letra, 'localidad': '390', 'TipoObra': 'O'}
        
        try:
            res = requests.post(URL, headers=HEADERS, data=payload, timeout=20)
            # Buscamos DNI y Nombre en el código de la página
            matches = re.findall(r"Benef\(1,(\d+),'(.*?)'\);", res.text)
            for dni, nombre in matches:
                resultados.append({'DNI': dni, 'Nombre': nombre})
            
            # Espera de 1.2 segundos para que no nos bloqueen
            time.sleep(1.2) 
        except Exception as e:
            st.error(f"Error en letra {letra}: {e}")

    if resultados:
        # Guardamos el Excel en el servidor
        df = pd.DataFrame(resultados)
        df.to_excel("CENSO_FINAL_MDP.xlsx", index=False)
        st.success(f"✅ ¡TERMINADO! Se encontraron {len(resultados)} beneficiarios.")
        st.balloons()
    else:
        st.error("No se capturaron datos. Es posible que la sesión haya expirado de nuevo.")

# 3. SECCIÓN DE DESCARGA (Siempre visible si el archivo está listo)
st.divider()
if os.path.exists("CENSO_FINAL_MDP.xlsx"):
    with open("CENSO_FINAL_MDP.xlsx", "rb") as f:
        st.download_button(
            label="⬇️ DESCARGAR EXCEL COMPLETO",
            data=f,
            file_name="Censo_OSECAC_MDP.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
else:
    st.info("El botón de descarga aparecerá aquí abajo cuando el proceso termine.")
