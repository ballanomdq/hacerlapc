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

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="HACER LA PC - Estable", layout="wide")
st.title("💻 HACER LA PC - SISA + CODEM")

log_container = st.expander("📋 Log de ejecución", expanded=True)
def log_message(msg):
    log_container.markdown(f"- {msg}")

def iniciar_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # CAMUFLAJE 1: Identidad Real
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    # CAMUFLAJE 2: Desactivar rastreo de automatización
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=options)
    # CAMUFLAJE 3: Borrar rastro de WebDriver vía JS
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

# ==================== SISA ====================
def consultar_sisa(driver, dni, es_primer_dni):
    res = {"SISA": "Sin datos", "Obra Social": "N/A"}
    try:
        if es_primer_dni:
            driver.get("https://sisa.msal.gov.ar/sisa/#sisa")
            time.sleep(5)
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
        cols = fila.find_elements(By.TAG_NAME, "td")
        if len(cols) >= 5:
            res = {"SISA": cols[3].text, "Obra Social": cols[4].text}
            log_message(f"✅ SISA OK: {dni}")
    except:
        log_message(f"⚠️ SISA: No hallado {dni}")
    return res

# ==================== CODEM ====================
def consultar_codem(driver, dni):
    res = {"CODEM": "No hallado"}
    try:
        # Navegación con "distracción"
        driver.get("https://www.google.com")
        time.sleep(1)
        driver.get("https://servicioswww.anses.gob.ar/ooss2/")
        time.sleep(random.uniform(6, 9))
        
        campo = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "ContentPlaceHolder1_txtDoc")))
        
        # Escritura ultra-lenta para no disparar el captcha
        for char in str(dni):
            campo.send_keys(char)
            time.sleep(random.uniform(0.2, 0.4))
        
        time.sleep(2)
        btn = driver.find_element(By.ID, "ContentPlaceHolder1_Button1")
        driver.execute_script("arguments[0].click();", btn)
        
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "ContentPlaceHolder1_lblObraSocial")))
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        os_text = soup.find(id="ContentPlaceHolder1_lblObraSocial")
        res["CODEM"] = os_text.text.strip() if os_text else "Sin datos"
        log_message(f"✅ CODEM OK: {dni}")
    except Exception:
        if "captcha" in driver.page_source.lower():
            log_message(f"❌ CODEM: Bloqueado por CAPTCHA en {dni}")
        else:
            log_message(f"❌ CODEM: Fallo en {dni}")
    return res

# --- PROCESO ---
if buscar_btn and dni_input:
    lista_dni = [d.strip() for d in dni_input.split('\n') if d.strip()]
    if lista_dni:
        with st.status("Consultando...", expanded=True) as status:
            log_message("Fase SISA...")
            d1 = iniciar_driver()
            r1 = [consultar_sisa(d1, d, i==0) for i, d in enumerate(lista_dni)]
            d1.quit()
            
            time.sleep(10)
            
            log_message("Fase CODEM...")
            d2 = iniciar_driver()
            r2 = [consultar_codem(d2, d) for d in lista_dni]
            d2.quit()
            status.update(label="Terminado", state="complete")

        final = []
        for i, d in enumerate(lista_dni):
            final.append({"DNI": d, **r1[i], **r2[i]})
        
        st.dataframe(pd.DataFrame(final), use_container_width=True, hide_index=True)
