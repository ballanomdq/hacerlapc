import streamlit as st
import pandas as pd
import time
import random
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="HACER LA PC - OSECAC", layout="wide")
st.title("🏥 Sistema Unificado de Consultas - Agencia MDP")

with st.container():
    dni_input = st.text_area("📋 Ingresá los DNI para el informe:", height=150)
    buscar_btn = st.button("🚀 Generar Informe Detallado", type="primary")

log_container = st.expander("📋 Log de ejecución", expanded=True)
def log_message(msg):
    log_container.markdown(f"- {msg}")

def iniciar_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    return webdriver.Chrome(options=options)

# --- 2. FUNCIONES DE EXTRACCIÓN ---
def consultar_sisa(driver, dni, es_primero):
    res = {"NOMBRE": "N/A", "OS_SISA": "N/A"}
    try:
        if es_primero:
            driver.get("https://sisa.msal.gov.ar/sisa/#sisa")
            time.sleep(6)
            puco = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'PUCO')]")))
            driver.execute_script("arguments[0].click();", puco)
            time.sleep(2)
        
        campo = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.TAG_NAME, "input")))
        campo.clear()
        campo.send_keys(str(dni) + Keys.RETURN)
        
        target = f"//td[contains(text(), '{dni}')]"
        WebDriverWait(driver, 12).until(EC.presence_of_element_located((By.XPATH, target)))
        cols = driver.find_element(By.XPATH, f"{target}/..").find_elements(By.TAG_NAME, "td")
        if len(cols) >= 5:
            res = {"NOMBRE": cols[3].text, "OS_SISA": cols[4].text}
            log_message(f"✅ SISA OK: {dni}")
    except:
        log_message(f"⚠️ SISA: No hallado {dni}")
    return res

def consultar_codem(driver, dni):
    res = {"OS_ANSES": "N/A", "CONDICION": "N/A", "SITUACION": "N/A"}
    try:
        driver.get("https://servicioswww.anses.gob.ar/ooss2/")
        time.sleep(random.uniform(9, 11))
        
        input_doc = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "ContentPlaceHolder1_txtDoc")))
        for num in str(dni): input_doc.send_keys(num); time.sleep(0.1)
        
        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "ContentPlaceHolder1_Button1"))
        time.sleep(8)
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        celdas = [c.get_text().strip() for c in soup.find_all('td')]
        
        if "Descripción" in celdas:
            idx = celdas.index("Descripción")
            res["OS_ANSES"] = celdas[idx + 6]
        if "Parentesco" in celdas:
            idx = celdas.index("Parentesco")
            res["CONDICION"] = celdas[idx + 6]
        if "Situación" in celdas:
            idx = celdas.index("Situación")
            res["SITUACION"] = celdas[idx + 6]
            
        log_message(f"✅ CODEM OK: {dni}")
    except:
        log_message(f"❌ CODEM: Error en {dni}")
    return res

# --- 3. PROCESO FINAL ---
if buscar_btn and dni_input:
    lista_dni = [d.strip() for d in dni_input.split('\n') if d.strip()]
    if lista_dni:
        with st.status("Generando reporte detallado...", expanded=True) as status:
            d = iniciar_driver()
            
            # Recolectamos datos
            resultados = []
            for i, dni in enumerate(lista_dni):
                log_message(f"Procesando: {dni}...")
                data_sisa = consultar_sisa(d, dni, i==0)
                time.sleep(2)
                data_anses = consultar_codem(d, dni)
                
                final_row = {"DNI": dni}
                final_row.update(data_sisa)
                final_row.update(data_anses)
                resultados.append(final_row)
            
            d.quit()
            status.update(label="Informe completo", state="complete")

        df = pd.DataFrame(resultados)
        
        # Reordenamos las columnas para que sea fácil de leer
        cols_orden = ["DNI", "NOMBRE", "OS_SISA", "OS_ANSES", "CONDICION", "SITUACION"]
        df = df[cols_orden]
        
        st.subheader("📊 Reporte Detallado por Afiliado")
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        st.download_button("📥 Descargar Planilla", df.to_csv(index=False).encode('utf-8'), "informe_osecac_mdp.csv")
