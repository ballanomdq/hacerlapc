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
st.title("💻 HACER LA PC - Sistema Unificado")

with st.container():
    st.subheader("📋 Ingreso de Datos")
    dni_input = st.text_area("Escribí los DNI (uno por línea):", height=150)
    buscar_btn = st.button("🚀 Iniciar Consulta Dual", type="primary")

log_container = st.expander("📋 Log de ejecución", expanded=True)
def log_message(msg):
    log_container.markdown(f"- {msg}")

# --- 2. MOTOR ---
def iniciar_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

# --- 3. FUNCIONES ---
def consultar_sisa(driver, dni, es_primer_dni):
    res = {"ESTADO_SISA": "Sin datos", "OBRA_SOCIAL_SISA": "N/A"}
    try:
        if es_primer_dni:
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
            res = {"ESTADO_SISA": cols[3].text, "OBRA_SOCIAL_SISA": cols[4].text}
            log_message(f"✅ SISA OK: {dni}")
    except:
        log_message(f"⚠️ SISA: No hallado {dni}")
    return res

def consultar_codem(driver, dni):
    res = {"CODEM_ESTADO": "No hallado", "CODEM_OS": "N/A"}
    try:
        driver.get("https://servicioswww.anses.gob.ar/ooss2/")
        time.sleep(random.uniform(9, 11))
        
        input_doc = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "ContentPlaceHolder1_txtDoc")))
        for num in str(dni): 
            input_doc.send_keys(num)
            time.sleep(0.1)
        
        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "ContentPlaceHolder1_Button1"))
        time.sleep(8)
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        celdas = [c.get_text().strip() for c in soup.find_all('td')]
        
        # BUSQUEDA POR TEXTO (Para que no falle con familiares)
        if "Descripción" in celdas:
            idx_desc = celdas.index("Descripción")
            res["CODEM_OS"] = celdas[idx_desc + 6]
        if "Situación" in celdas:
            idx_sit = celdas.index("Situación")
            res["CODEM_ESTADO"] = celdas[idx_sit + 6]
            
        log_message(f"✅ CODEM OK: {dni}")
    except:
        log_message(f"❌ CODEM: Error en {dni}")
    return res

# --- 4. EJECUCIÓN ---
if buscar_btn and dni_input:
    lista_dni = [d.strip() for d in dni_input.split('\n') if d.strip()]
    if lista_dni:
        with st.status("Consultando bases de datos...", expanded=True) as status:
            log_message("Fase SISA...")
            d1 = iniciar_driver()
            r1 = [consultar_sisa(d1, d, i==0) for i, d in enumerate(lista_dni)]
            d1.quit()
            
            time.sleep(4)
            
            log_message("Fase CODEM (Sigilo)...")
            d2 = iniciar_driver()
            r2 = [consultar_codem(d2, d) for d in lista_dni]
            d2.quit()
            status.update(label="Proceso terminado", state="complete")

        final = []
        for i, d in enumerate(lista_dni):
            fila = {"DNI": d}
            fila.update(r1[i])
            fila.update(r2[i])
            final.append(fila)
        
        df = pd.DataFrame(final)
        st.subheader("📊 Reporte Unificado de Obra Social")
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button("📥 Descargar Reporte CSV", df.to_csv(index=False).encode('utf-8'), "reporte_osecac.csv")
