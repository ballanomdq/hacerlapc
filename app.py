import streamlit as st
import pandas as pd
import time
import random
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="HACER LA PC - Ultra Sigilo", layout="wide")
st.title("💻 HACER LA PC - Sistema de Consulta Unificado")

# Estilo para la tabla de resultados
st.markdown("""
<style>
    .stDataFrame { border: 2px solid #0ea5e9; border-radius: 10px; }
    .stStatus { font-weight: bold; }
</style>
""", unsafe_allow_html=True)

with st.container():
    st.subheader("📋 Carga de Datos (OSECAC)")
    dni_input = st.text_area("Ingresá los DNI (uno por línea):", height=150)
    buscar_btn = st.button("🚀 Ejecutar Consulta de Seguridad", type="primary")

log_container = st.expander("📋 Log de Inteligencia", expanded=True)

def log_message(msg):
    log_container.markdown(f"- {msg}")

# --- EL MOTOR UNDETECTED ---
def iniciar_driver_uc():
    options = uc.ChromeOptions()
    options.add_argument("--headless")  # Modo invisible
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    # Iniciamos el driver parcheado
    driver = uc.Chrome(options=options, version_main=122) # Ajustar según tu Chrome
    return driver

# ==================== FUNCIÓN SISA ====================
def consultar_sisa(driver, dni, es_primer_dni):
    res = {"Tipo": "", "DNI": "", "Sexo": "", "SISA": "N/A", "Denom": ""}
    try:
        if es_primer_dni:
            driver.get("https://sisa.msal.gov.ar/sisa/#sisa")
            time.sleep(random.uniform(4, 6))
            puco = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'PUCO')]")))
            driver.execute_script("arguments[0].click();", puco)
            time.sleep(2)
        
        campo = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.TAG_NAME, "input")))
        campo.clear()
        campo.send_keys(str(dni))
        campo.send_keys(Keys.RETURN)
        
        target = f"//td[contains(text(), '{dni}')]"
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, target)))
        fila = driver.find_element(By.XPATH, f"{target}/..")
        celdas = fila.find_elements(By.TAG_NAME, "td")
        
        if len(celdas) >= 5:
            res = {"Tipo": celdas[0].text, "DNI": celdas[1].text, "Sexo": celdas[2].text, "SISA": celdas[3].text, "Denom": celdas[4].text}
            log_message(f"✅ SISA OK: {dni}")
    except:
        log_message(f"⚠️ SISA: Sin respuesta para {dni}")
    return res

# ==================== FUNCIÓN CODEM (MODO FANTASMA) ====================
def consultar_codem(driver, dni):
    res = {"CODEM": "No hallado", "Familiares": "0"}
    try:
        # Generar "ruido" de navegación
        driver.get("https://www.bing.com") 
        time.sleep(2)
        
        driver.get("https://servicioswww.anses.gob.ar/ooss2/")
        time.sleep(random.uniform(5, 8))
        
        campo = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "ContentPlaceHolder1_txtDoc")))
        
        # Click "humano" y escritura con pausas orgánicas
        campo.click()
        for char in str(dni):
            campo.send_keys(char)
            time.sleep(random.uniform(0.1, 0.4))
        
        time.sleep(1.5)
        btn = driver.find_element(By.ID, "ContentPlaceHolder1_Button1")
        driver.execute_script("arguments[0].click();", btn)
        
        # Esperar el elemento de respuesta
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "ContentPlaceHolder1_lblObraSocial")))
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        os_elem = soup.find(id="ContentPlaceHolder1_lblObraSocial")
        fa_elem = soup.find(id="ContentPlaceHolder1_lblFamiliares")
        
        res["CODEM"] = os_elem.text.strip() if os_elem else "Sin datos"
        res["Familiares"] = fa_elem.text.strip() if fa_elem else "0"
        log_message(f"✅ CODEM OK: {dni}")

    except Exception:
        if "captcha" in driver.page_source.lower():
            log_message(f"❌ CODEM: Bloqueo de seguridad detectado para {dni}")
        else:
            log_message(f"❌ CODEM: Error en la consulta de {dni}")
    return res

# --- PROCESO PRINCIPAL ---
if buscar_btn and dni_input:
    dnis = [d.strip() for d in dni_input.split('\n') if d.strip()]
    
    if dnis:
        with st.status("Iniciando bypass de seguridad y consulta...", expanded=True) as status:
            # Fase 1: SISA
            log_message("Conectando con SISA...")
            driver_s = iniciar_driver_uc()
            res_sisa = [consultar_sisa(driver_s, d, i==0) for i, d in enumerate(dnis)]
            driver_s.quit()
            
            time.sleep(5)
            
            # Fase 2: CODEM
            log_message("Conectando con ANSES (Modo Undetected)...")
            driver_c = iniciar_driver_uc()
            res_codem = [consultar_codem(driver_c, d) for d in dnis]
            driver_c.quit()
            
            status.update(label="Consultas completadas.", state="complete")

        # Armado de tabla
        final_data = []
        for i, d in enumerate(dnis):
            final_data.append({"DNI": d, **res_sisa[i], **res_codem[i]})
        
        df = pd.DataFrame(final_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button("📥 Descargar Planilla Final", df.to_csv(index=False).encode('utf-8'), "hacer_pc_pro.csv")
