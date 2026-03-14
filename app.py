import streamlit as st
import pandas as pd
import time
import random
import os
import PyPDF2
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="HACER LA PC - PRO", layout="wide")
st.title("💻 Buscador Inteligente OSECAC (Versión Full)")

DOWNLOAD_DIR = "/tmp"

def iniciar_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    
    prefs = {
        "download.default_directory": DOWNLOAD_DIR,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True
    }
    options.add_experimental_option("prefs", prefs)
    
    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

# --- 2. LECTURA DE PDF ---
def extraer_datos_pdf():
    info = {"CUIT": "N/A", "Familia": "Titular Solo"}
    try:
        time.sleep(6) # Tiempo para que termine la descarga
        archivos = [f for f in os.listdir(DOWNLOAD_DIR) if f.endswith(".pdf")]
        if not archivos: return info
        
        path = os.path.join(DOWNLOAD_DIR, archivos[-1])
        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            texto = ""
            for page in reader.pages:
                texto += page.extract_text()
            
            # Buscamos CUIT (Busca el patrón numérico después de CUIT)
            if "CUIT" in texto:
                partes = texto.split("CUIT")
                if len(partes) > 1:
                    info["CUIT"] = partes[1].strip()[:13]
            
            # Buscamos Familiares
            lineas = texto.split("\n")
            familiares = [l.strip() for l in lineas if any(x in l for x in ["Hijo", "Esposa", "Conyuge", "Adherente"])]
            if familiares:
                info["Familia"] = " | ".join(familiares)
        
        os.remove(path)
    except:
        pass
    return info

# --- 3. LÓGICA PRINCIPAL ---
def proceso_dni(dni):
    res = {"DNI": dni, "SISA": "No hallado", "CODEM": "Fallo", "CUIT": "-", "Familia": "-"}
    driver = iniciar_driver()
    try:
        # SISA
        driver.get("https://sisa.msal.gov.ar/sisa/#sisa")
        time.sleep(5)
        puco = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'PUCO')]")))
        driver.execute_script("arguments[0].click();", puco)
        time.sleep(2)
        campo_sisa = driver.find_element(By.TAG_NAME, "input")
        campo_sisa.send_keys(str(dni) + Keys.RETURN)
        time.sleep(4)
        cols = driver.find_elements(By.TAG_NAME, "td")
        if len(cols) > 4: res["SISA"] = cols[3].text

        # CODEM
        driver.get("https://servicioswww.anses.gob.ar/ooss2/")
        time.sleep(10)
        campo_codem = driver.find_element(By.ID, "ContentPlaceHolder1_txtDoc")
        for c in str(dni): 
            campo_codem.send_keys(c)
            time.sleep(0.1)
        
        btn = driver.find_element(By.ID, "ContentPlaceHolder1_Button1")
        driver.execute_script("arguments[0].click();", btn)
        time.sleep(6)
        
        if "Obra Social" in driver.page_source:
            res["CODEM"] = "Detectado ✅"
            # Intentar click en impresora
            try:
                btn_print = driver.find_element(By.ID, "ContentPlaceHolder1_ibtnImprimir")
                driver.execute_script("arguments[0].click();", btn_print)
                pdf_data = extraer_datos_pdf()
                res.update(pdf_data)
            except:
                res["CUIT"] = "Error Impresora"
        else:
            res["CODEM"] = "Captcha/Bloqueo"
            
    except Exception as e:
        res["CODEM"] = f"Error: {str(e)[:20]}"
    finally:
        driver.quit()
    return res

# --- 4. INTERFAZ ---
with st.sidebar:
    st.header("Configuración")
    st.write("Agencia Mar del Plata")

dni_input = st.text_area("Lista de DNI (máximo 10):", height=150)
if st.button("🚀 INICIAR BÚSQUEDA COMPLETA") and dni_input:
    dnis = [d.strip() for d in dni_input.split('\n') if d.strip()][:10]
    resultados = []
    
    status = st.status("Trabajando...", expanded=True)
    for dni in dnis:
        status.write(f"Consultando {dni}...")
        resultados.append(proceso_dni(dni))
    
    status.update(label="¡Terminado!", state="complete")
    st.table(pd.DataFrame(resultados))
