import streamlit as st
import pandas as pd
import time
import os
import PyPDF2
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="OSECAC MDP - Sistema de Informes", layout="wide")

st.markdown("""
    <style>
    .report-card {
        background-color: #ffffff;
        padding: 25px;
        border-radius: 15px;
        border-left: 8px solid #0056b3;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        margin-bottom: 25px;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .header-dni { color: #0056b3; font-size: 24px; font-weight: bold; margin-bottom: 15px; }
    .data-box { background-color: #f8f9fa; padding: 10px; border-radius: 8px; margin: 5px; }
    .label { color: #666; font-size: 12px; text-transform: uppercase; font-weight: bold; }
    .value { color: #333; font-size: 16px; font-weight: 600; }
    .status-active { color: #28a745; font-weight: bold; background-color: #e9f7ef; padding: 3px 10px; border-radius: 15px; }
    </style>
    """, unsafe_allow_html=True)

DOWNLOAD_DIR = "/tmp"

def iniciar_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    prefs = {"download.default_directory": DOWNLOAD_DIR, "download.prompt_for_download": False, "plugins.always_open_pdf_externally": True}
    options.add_experimental_option("prefs", prefs)
    driver = webdriver.Chrome(options=options)
    return driver

def analizar_pdf():
    info = {"CUIT": "No detectado", "Familia": "Sin familiares declarados en CODEM"}
    try:
        time.sleep(7)
        archivos = [f for f in os.listdir(DOWNLOAD_DIR) if f.endswith(".pdf")]
        if not archivos: return info
        
        path = os.path.join(DOWNLOAD_DIR, archivos[-1])
        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            texto = ""
            for page in reader.pages: texto += page.extract_text()
            
            # Busqueda de CUIT mejorada
            if "CUIT" in texto:
                try:
                    info["CUIT"] = texto.split("CUIT")[-1].strip()[:13].replace(" ", "").replace("-", "")
                except: pass
            
            # Busqueda de Familiares
            lineas = texto.split("\n")
            fam_list = [l.strip() for l in lineas if any(x in l for x in ["Hijo", "Esposa", "Conyuge", "Adherente", "FAMILIAR"])]
            if fam_list:
                info["Familia"] = fam_list
        os.remove(path)
    except: pass
    return info

def consultar_afiliado(dni):
    res = {"DNI": dni, "SISA": "Sin cobertura", "CODEM": "INACTIVO ❌", "CUIT": "-", "Familia": "No hallada"}
    driver = iniciar_driver()
    try:
        # 1. SISA corregido
        driver.get("https://sisa.msal.gov.ar/sisa/#sisa")
        time.sleep(5)
        puco = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'PUCO')]")))
        driver.execute_script("arguments[0].click();", puco)
        time.sleep(2)
        campo = driver.find_element(By.TAG_NAME, "input")
        campo.send_keys(str(dni) + Keys.RETURN)
        time.sleep(5)
        
        filas = driver.find_elements(By.TAG_NAME, "tr")
        for fila in filas:
            if str(dni) in fila.text:
                celdas = fila.find_elements(By.TAG_NAME, "td")
                if len(celdas) >= 5:
                    res["SISA"] = celdas[4].text # Nombre de la OS

        # 2. CODEM corregido
        driver.get("https://servicioswww.anses.gob.ar/ooss2/")
        time.sleep(10)
        input_doc = driver.find_element(By.ID, "ContentPlaceHolder1_txtDoc")
        for num in str(dni): input_doc.send_keys(num); time.sleep(0.1)
        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "ContentPlaceHolder1_Button1"))
        time.sleep(6)
        
        if "Obra Social" in driver.page_source:
            res["CODEM"] = "ACTIVO ✅"
            try:
                btn_print = driver.find_element(By.ID, "ContentPlaceHolder1_ibtnImprimir")
                driver.execute_script("arguments[0].click();", btn_print)
                res.update(analizar_pdf())
            except: 
                res["CUIT"] = "Reintentar descarga"
    except: pass
    finally: driver.quit()
    return res

# --- INTERFAZ DE USUARIO ---
st.title("🏥 Gestión de Padrones OSECAC MDP")
dni_input = st.text_area("📋 Ingrese los DNIs a procesar:", height=100, placeholder="Un DNI por línea...")

if st.button("🔍 GENERAR INFORME PROFESIONAL", type="primary") and dni_input:
    lista_dnis = [d.strip() for d in dni_input.split('\n') if d.strip()][:10]
    
    with st.status("⏳ Procesando legajos médicos...", expanded=True) as s:
        for dni in lista_dnis:
            s.write(f"Analizando DNI {dni}...")
            data = consultar_afiliado(dni)
            
            # HTML DE LA TARJETA PROFESIONAL
            fam_html = ""
            if isinstance(data['Familia'], list):
                fam_html = "".join([f"<li>{f}</li>" for f in data['Familia']])
            else:
                fam_html = f"<li>{data['Familia']}</li>"

            st.markdown(f"""
            <div class="report-card">
                <div class="header-dni">👤 AFILIADO DNI: {data['DNI']}</div>
                <div style="display: flex; flex-wrap: wrap;">
                    <div class="data-box" style="flex: 1; min-width: 200px;">
                        <div class="label">📍 Cobertura SISA (PUCO)</div>
                        <div class="value">{data['SISA']}</div>
                    </div>
                    <div class="data-box" style="flex: 1; min-width: 200px;">
                        <div class="label">🏢 Estado en ANSES</div>
                        <div class="value"><span class="status-active">{data['CODEM']}</span></div>
                    </div>
                    <div class="data-box" style="flex: 1; min-width: 200px;">
                        <div class="label">🔢 CUIT Empleador</div>
                        <div class="value">{data['CUIT']}</div>
                    </div>
                </div>
                <div class="data-box" style="margin-top: 15px;">
                    <div class="label">👨‍👩‍👧‍👦 GRUPO FAMILIAR Y ADHERENTES</div>
                    <ul style="margin-top: 5px; color: #444; font-size: 14px;">
                        {fam_html}
                    </ul>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        s.update(label="✅ Informes listos para auditoría", state="complete")
    st.info("💡 Consejo: Podés imprimir esta pantalla (Ctrl + P) para guardar los informes en PDF.")
