import streamlit as st
import requests
import re
import pandas as pd
import time
import os

# Configuración profesional de la página
st.set_page_config(page_title="Censo OSECAC MDP", page_icon="🕵️", layout="centered")

st.title("🚀 Censo de Beneficiarios - Mar del Plata")
st.markdown("---")
st.info("Estado: **Sesión Chrome Miramar Detectada**. Presioná el botón para iniciar.")

# --- BOTÓN DE INICIO ---
if st.button("▶️ INICIAR BARRIDO MASIVO"):
    resultados = []
    letras = "ABCDEFGHIJLMNOPRSTVZ"
    
    # Barra de progreso y contenedor de estado
    barra = st.progress(0)
    estado = st.empty()
    
    # DATOS DE ACCESO (Limpiados de tu cadena de texto)
    URL = "http://200.51.42.43/empadronamiento/beneficiarios/emp_benef.asp"
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Cookie': 'ASPSESSIONIDSCBDBBSA=CFBDFNOCNMKLGGPBMGEAKJPM; Usuario%280%29=rballano; Password=654321; Delegacion%280%29=MIRAMAR%28BA%29'
    }

    # Iniciamos el recorrido letra por letra
    for i, letra in enumerate(letras):
        progreso_actual = (i + 1) / len(letras)
        barra.progress(progreso_actual)
        estado.write(f"🔎 Procesando letra: **{letra}**...")
        
        # Localidad 390 = Mar del Plata
        payload = {'Tableta': '3', 'Nombre': letra, 'localidad': '390', 'TipoObra': 'O'}
        
        try:
            res = requests.post(URL, headers=HEADERS, data=payload, timeout=25)
            # Extraer DNI y Nombre con Regex
            matches = re.findall(r"Benef\(1,(\d+),'(.*?)'\);", res.text)
            
            for dni, nombre in matches:
                resultados.append({'DNI': dni, 'Nombre': nombre})
            
            # Pausa de seguridad para no ser bloqueados
            time.sleep(1.5)
            
        except Exception as e:
            st.error(f"Error en letra {letra}: {e}")

    if resultados:
        # Generar el archivo Excel
        df = pd.DataFrame(resultados)
        df.to_excel("CENSO_MDP_COMPLETO.xlsx", index=False)
        st.success(f"✅ ¡PROCESO FINALIZADO! Se encontraron {len(resultados)} beneficiarios.")
        st.balloons()
    else:
        st.error("No se capturaron datos. Asegurate de que la pestaña de OSECAC en Chrome siga abierta.")

# --- SECCIÓN DE DESCARGA ---
st.divider()
if os.path.exists("CENSO_MDP_COMPLETO.xlsx"):
    with open("CENSO_MDP_COMPLETO.xlsx", "rb") as f:
        st.download_button(
            label="⬇️ DESCARGAR PADRÓN EN EXCEL",
            data=f,
            file_name="Censo_OSECAC_MDP.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
else:
    st.write("⏳ El botón de descarga aparecerá aquí apenas termine el proceso.")
