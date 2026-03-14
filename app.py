import streamlit as st
import pandas as pd
import requests
import re
import time

# --- SECCIÓN DEL CENSO ---
st.divider()
st.subheader("📊 Auditoría de Padrón - Mar del Plata")

if st.button('🚀 Iniciar Barrido Masivo'):
    # Tus credenciales que ya verificamos
    URL = "http://200.51.42.43/empadronamiento/beneficiarios/emp_benef.asp"
    HEADERS = {
        'User-Agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 10.0; WOW64; Trident/7.0)',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Cookie': 'ASPSESSIONIDSAADDDQA=EEJPNPNCAMHCFHKELMGFLDAO; Usuario%280%29=rballano; Password=654321'
    }

    resultados = []
    letras = "ABCDEFGHIJLMNOPRSTVZ" # Podés acortarla para probar primero
    
    progreso = st.progress(0)
    status_text = st.empty()
    
    for i, letra in enumerate(letras):
        status_text.text(f"Buscando letra: {letra}...")
        payload = {'Tableta': '3', 'Nombre': letra, 'localidad': '390', 'TipoObra': 'O'}
        
        try:
            res = requests.post(URL, headers=HEADERS, data=payload, timeout=15)
            # Buscamos DNI y Nombre con el patrón que descubrimos
            matches = re.findall(r"Benef\(1,(\d+),'(.*?)'\);", res.text)
            
            for dni, nombre in matches:
                resultados.append({'DNI': dni, 'Nombre': nombre})
            
            # Actualizamos la barra de progreso
            progreso.progress((i + 1) / len(letras))
            time.sleep(1.5) # Pausa para que el servidor no sospeche
            
        except Exception as e:
            st.error(f"Error en letra {letra}: {e}")

    # Cuando termina, creamos el Excel
    if resultados:
        df = pd.DataFrame(resultados)
        nombre_archivo = "CENSO_MDP_OSECAC.xlsx"
        df.to_excel(nombre_archivo, index=False)
        
        st.success(f"✅ ¡Censo completado! Se encontraron {len(resultados)} beneficiarios.")
        
        # Botón para descargar el Excel generado en la nube a tu PC
        with open(nombre_archivo, "rb") as f:
            st.download_button(
                label="⬇️ Descargar Excel para Auditoría",
                data=f,
                file_name=nombre_archivo,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.warning("No se encontraron datos. Revisá si la sesión rballano sigue activa.")
