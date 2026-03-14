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

# --- 1. CONFIGURACIÓN Y ESTILO ---
st.set_page_config(page_title="Portal OSECAC MDP", layout="wide")

st.markdown("""
    <style>
    .report-card {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        border-left: 10px solid #0056b3;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    .status-ok { color: #28a745; font-weight: bold; }
    .status-error { color: #dc3545; font-weight: bold; }
    .label { font-weight: bold; color: #555; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏥 Portal de Consultas OSECAC - Mar del Plata")
st.subheader("Buscador de Padrones y Grupo Familiar")

DOWNLOAD_DIR = "/tmp"

def iniciar_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    prefs = {"download.default_directory": DOWNLOAD_DIR, "download.prompt_for_download": False, "plugins.always_open_pdf_externally": True}
    options.add_experimental_option("prefs", prefs)
    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

# --- 2. LÓGICA DE EXTRACCIÓN ---
def leer_pdf_pro():
    info = {"CUIT": "No especificado", "Familia": "Titular Solo"}
    try:
        time.sleep(6)
        archivos = [f for f in os.listdir(DOWNLOAD_DIR) if f.endswith(".pdf")]
        if not archivos: return info
        path = os.path.join(DOWNLOAD_DIR, archivos[-1])
        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            texto = " ".join([p.extract_text() for p in reader.pages])
            if "CUIT" in texto:
                info["CUIT"] = texto.split("CUIT")[-1].strip()[:13]
            lineas = texto.split("\n")
            fam = [l.strip() for l in lineas if any(x in l for x in ["Hijo", "Esposa", "Conyuge", "Adherente"])]
            if fam: info["Familia"] = fam
        os.remove(path)
    except: pass
    return info

def consultar_full(dni):
    res = {"DNI": dni, "SISA": "Sin datos", "CODEM": "Fallo", "CUIT": "-", "Familia": "No hallada", "Estado": "Error"}
    driver = iniciar_driver()
    try:
        # FASE SISA
        driver.get("https://sisa.msal.gov.ar/sisa/#sisa")
        time.sleep(5)
        puco = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'PUCO')]")))
        driver.execute_script("arguments[0].click();", puco)
        time.sleep(2)
        campo = driver.find_element(By.TAG_NAME, "input")
        campo.send_keys(str(dni) + Keys.RETURN)
        time.sleep(4)
        cols = driver.find_elements(By.TAG_NAME, "td")
        if len(cols) > 4: res["SISA"] = cols[4].text # Obra social de SISA

        # FASE CODEM
        driver.get("https://servicioswww.anses.gob.ar/ooss2/")
        time.sleep(10)
        c = driver.find_element(By.ID, "ContentPlaceHolder1_txtDoc")
        for char in str(dni): c.send_keys(char); time.sleep(0.1)
        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "ContentPlaceHolder1_Button1"))
        time.sleep(6)
        
        if "Obra Social" in driver.page_source:
            res["CODEM"] = "ACTIVO ✅"
            res["Estado"] = "OK"
            try:
                btn = driver.find_element(By.ID, "ContentPlaceHolder1_ibtnImprimir")
                driver.execute_script("arguments[0].click();", btn)
                extra = leer_pdf_pro()
                res.update(extra)
            except: res["CUIT"] = "Error en descarga"
    except: pass
    finally: driver.quit()
    return res

# --- 3. INTERFAZ ---
dni_input = st.text_area("📄 Ingrese DNIs (uno debajo del otro):", height=120)
if st.button("🔍 Generar Informe Detallado") and dni_input:
    dnis = [d.strip() for d in dni_input.split('\n') if d.strip()][:10]
    
    with st.status("🚀 Procesando consultas... por favor espere", expanded=True) as status:
        for dni in dnis:
            status.write(f"⌛ Analizando DNI: {dni}...")
            dato = consultar_full(dni)
            
            # DISEÑO DE CADA INFORME
            with st.container():
                st.markdown(f"""
                <div class="report-card">
                    <h3>👤 DNI: {dni}</h3>
                    <div style="display: flex; justify-content: space-between;">
                        <div>
                            <p class="label">📍 ESTADO SISA:</p>
                            <p>{dato['SISA']}</p>
                        </div>
                        <div>
                            <p class="label">🏢 ESTADO CODEM:</p>
                            <p class="status-ok">{dato['CODEM']}</p>
                        </div>
                        <div>
                            <p class="label">🔢 CUIT EMPLEADOR:</p>
                            <p>{dato['CUIT']}</p>
                        </div>
                    </div>
                    <hr>
                    <p class="label">👨‍👩‍👧‍👦 GRUPO FAMILIAR DETECTADO:</p>
                    <p>{dato['Familia'] if isinstance(dato['Familia'], str) else " • " + " <br> • ".join(dato['Familia'])}</p>
                </div>
                """, unsafe_allow_html=True)
        
        status.update(label="✅ Consultas finalizadas con éxito", state="complete")

    # Botón para descargar como planilla al final
    st.success("Informe generado. Podés copiar los datos o hacer captura de pantalla para el legajo.")
