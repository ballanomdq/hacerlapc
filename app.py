import streamlit as st
import pandas as pd
import time
import random
import os
import PyPDF2
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="HACER LA PC - PRO", layout="wide")
st.title("💻 Buscador Inteligente OSECAC")
st.markdown("Extrae: **SISA + CODEM + CUIT + Grupo Familiar**")

DOWNLOAD_DIR = "/tmp"

def iniciar_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # Configurar para que baje el PDF sin preguntar
    prefs = {
        "download.default_directory": DOWNLOAD_DIR,
        "download.prompt_for_download": False,
        "plugins.always_open_pdf_externally": True
    }
    options.add_experimental_option("prefs", prefs)
    driver = webdriver.Chrome(options=options)
    return driver

def leer_datos_del_pdf():
    """Busca el PDF bajado, saca el CUIT y Familiares, y lo borra."""
    info = {"CUIT": "No hallado", "Familia": "Titular Solo"}
    try:
        time.sleep(4) # Esperar a que termine de bajar
        archivos = [f for f in os.listdir(DOWNLOAD_DIR) if f.endswith(".pdf")]
        if not archivos: return info
        
        path = os.path.join(DOWNLOAD_DIR, archivos[-1])
        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            texto = ""
            for page in reader.pages:
                texto += page.extract_text()
            
            # Buscamos CUIT
            if "CUIT" in texto:
                # Extrae los números después de la palabra CUIT
                info["CUIT"] = texto.split("CUIT")[-1][:15].strip().split(" ")[0]
            
            # Buscamos Familiares (Si hay más de un CUIL/DNI en el texto)
            lineas = texto.split("\n")
            familiares_detectados = [l for l in lineas if "Hijo" in l or "Esposa" in l or "Conyuge" in l]
            if familiares_detectados:
                info["Familia"] = " / ".join(familiares_detectados)
        
        os.remove(path) # Borrar para no saturar
    except:
        pass
    return info

def consultar_todo(dni):
    res = {"DNI": dni, "SISA": "Error", "CODEM": "Fallo", "CUIT": "-", "Familia": "-"}
    driver = iniciar_driver()
    try:
        # 1. SISA (Rápido)
        driver.get("https://sisa.msal.gov.ar/sisa/#sisa")
        time.sleep(4)
        driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, "//*[contains(text(), 'PUCO')]"))
        campo = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "input")))
        campo.send_keys(str(dni) + "\n")
        time.sleep(3)
        cols = driver.find_elements(By.TAG_NAME, "td")
        if len(cols) > 4: res["SISA"] = cols[3].text

        # 2. CODEM + CLICK IMPRESORA
        driver.get("https://servicioswww.anses.gob.ar/ooss2/")
        time.sleep(8)
        c = driver.find_element(By.ID, "ContentPlaceHolder1_txtDoc")
        for char in str(dni): c.send_keys(char); time.sleep(0.1)
        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "ContentPlaceHolder1_Button1"))
        
        # Click en la impresora
        btn_print = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.ID, "ContentPlaceHolder1_ibtnImprimir")))
        driver.execute_script("arguments[0].click();", btn_print)
        
        # Leer el PDF que bajó el click anterior
        pdf_info = leer_datos_del_pdf()
        res.update(pdf_info)
        res["CODEM"] = "Analizado ✅"
        
    except:
        pass
    finally:
        driver.quit()
    return res

# --- INTERFAZ ---
dni_input = st.text_area("Lista de DNI (máximo 10 por seguridad):")
if st.button("🚀 PROCESAR TANDA") and dni_input:
    lista = [d.strip() for d in dni_input.split('\n') if d.strip()][:10]
    resultados = []
    progreso = st.progress(0)
    
    for i, dni in enumerate(lista):
        st.write(f"Trabajando en {dni}...")
        resultados.append(consultar_todo(dni))
        progreso.progress((i + 1) / len(lista))
    
    st.table(pd.DataFrame(resultados))
