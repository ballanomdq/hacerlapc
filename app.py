import streamlit as st
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import time

# --- CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="PUCO - OSECAC MDP", layout="wide")
st.title("🛡️ Buscador PUCO (Modo Seguro)")

dni_input = st.text_area("Ingresá los DNIs (uno por línea):", height=150, placeholder="25131361")
buscar_btn = st.button("🚀 Iniciar Búsqueda", type="primary")

def consultar_sisa(dni):
    options = Options()
    options.add_argument("--headless=new") # Nueva forma de headless
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    # En la nueva versión de Streamlit, Chromium está aquí:
    options.binary_location = "/usr/bin/chromium" 

    try:
        # Usamos el Service para apuntar al driver instalado
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=options)
        
        driver.get("https://sisa.msal.gov.ar/sisa/#pms/pms_poblacion_padrones_consulta_publica")
        
        time.sleep(5) # Espera para carga de página
        
        # Buscamos el campo de texto (SISA suele usar inputs simples)
        campo_dni = driver.find_element(By.CSS_SELECTOR, "input[type='text']")
        campo_dni.send_keys(str(dni))
        
        # Buscamos el botón de búsqueda
        boton = driver.find_element(By.XPATH, "//button[contains(., 'Buscar')]")
        boton.click()
        
        time.sleep(3) 
        
        filas = driver.find_elements(By.TAG_NAME, "tr")
        if len(filas) > 1:
            columnas = filas[1].find_elements(By.TAG_NAME, "td")
            return {"DNI": dni, "Cobertura": columnas[2].text, "Beneficiario": columnas[3].text, "Estado": "✅"}
        return {"DNI": dni, "Cobertura": "No hallado", "Beneficiario": "-", "Estado": "❌"}

    except Exception as e:
        return {"DNI": dni, "Cobertura": "Error", "Beneficiario": str(e)[:40], "Estado": "⚠️"}
    finally:
        if 'driver' in locals():
            driver.quit()

if buscar_btn and dni_input:
    dnis = [d.strip() for d in dni_input.split('\n') if d.strip()]
    res = []
    for d in dnis:
        st.write(f"🕵️ Buscando: {d}...")
        res.append(consultar_sisa(d))
    st.dataframe(pd.DataFrame(res))
