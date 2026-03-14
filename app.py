import streamlit as st
import pandas as pd
import time
import random
import os
import glob
import re
from bs4 import BeautifulSoup
from pypdf import PdfReader
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="HACER LA PC - OSECAC", layout="wide")
st.title("💻 HACER LA PC - Sistema Unificado")

with st.container():
    st.subheader("📋 Ingreso de Datos")
    dni_input = st.text_area("Escribí los DNI (uno por línea):", height=150)
    buscar_btn = st.button("🚀 Iniciar Consulta Dual", type="primary")

log_container = st.expander("📋 Log de ejecución", expanded=True)

def log_message(msg):
    log_container.markdown(f"- {msg}")

# --- DRIVER ---
def iniciar_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    prefs = {"download.default_directory": "/tmp", "download.prompt_for_download": False,
             "download.directory_upgrade": True, "plugins.always_open_pdf_externally": True}
    options.add_experimental_option("prefs", prefs)

    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

# --- SISA (sin cambios) ---
def consultar_sisa(driver, dni, es_primer_dni):
    res = {"SISA": "Sin datos", "OS_SISA": "N/A"}
    try:
        if es_primer_dni:
            driver.get("https://sisa.msal.gov.ar/sisa/#sisa")
            time.sleep(random.uniform(5, 8))
            puco = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'PUCO')]")))
            driver.execute_script("arguments[0].click();", puco)
            time.sleep(random.uniform(1.5, 3))
        
        campo = WebDriverWait(driver, 12).until(EC.presence_of_element_located((By.TAG_NAME, "input")))
        campo.clear()
        for char in str(dni):
            campo.send_keys(char)
            time.sleep(random.uniform(0.15, 0.45))
        campo.send_keys(Keys.RETURN)
        
        target = f"//td[contains(text(), '{dni}')]"
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.XPATH, target)))
        fila = driver.find_element(By.XPATH, f"{target}/..")
        cols = fila.find_elements(By.TAG_NAME, "td")
        if len(cols) >= 5:
            res = {"SISA": cols[3].text.strip(), "OS_SISA": cols[4].text.strip()}
            log_message(f"✅ SISA OK: {dni}")
    except:
        log_message(f"⚠️ SISA: No hallado {dni}")
    return res

# --- CODEM CON PDF (AHORA CON EL XPATH EXACTO DEL BOTÓN) ---
def consultar_codem(driver, dni):
    res = {"CODEM": "No hallado", "ObraSocial": "N/A", "Titular": "N/A", "Familiares": "N/A", "CUIT_Empleador": "N/A"}
    try:
        driver.get("https://servicioswww.anses.gob.ar/ooss2/")
        time.sleep(random.uniform(10, 16))

        campo = WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, "ContentPlaceHolder1_txtDoc")))
        campo.clear()
        for char in str(dni):
            campo.send_keys(char)
            time.sleep(random.uniform(0.25, 0.65))
        time.sleep(random.uniform(3.5, 6.5))

        btn = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.ID, "ContentPlaceHolder1_Button1")))
        driver.execute_script("arguments[0].click();", btn)

        WebDriverWait(driver, 35).until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Obra Social') or contains(text(), 'CUIL')]")))
        time.sleep(random.uniform(6, 10))

        # LIMPIAR PDF ANTERIOR
        for f in glob.glob("/tmp/*.pdf"): os.remove(f)

        log_message(f"Buscando botón PDF para {dni}...")

        # XPATHS - EL PRIMERO ES EL EXACTO QUE VISTE EN DEVTOOLS (imprimir2.gif)
        xpaths = [
            "//img[contains(@src, 'imprimir2.gif')]",                    # ← ESTE ES EL QUE FUNCIONA
            "//a[.//img[contains(@src, 'imprimir2.gif')]]",
            "//a[contains(@href, 'doPostBack') and contains(@href, 'DGOOSS')]",
            "//*[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'imprimir')]",
            "//*[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'constancia')]",
            "//*[contains(@id, 'Imprimir') or contains(@id, 'Print')]",
            "//img[contains(@alt,'Imprimir') or contains(@title,'Imprimir')]",
            "//*[contains(@class, 'print')]"
        ]

        print_btn = None
        for xp in xpaths:
            try:
                print_btn = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, xp)))
                log_message(f"✅ Botón PDF encontrado con: {xp}")
                break
            except:
                continue

        if print_btn:
            driver.execute_script("arguments[0].scrollIntoView(true);", print_btn)
            time.sleep(1.5)
            driver.execute_script("arguments[0].click();", print_btn)
            log_message("✅ Botón clickeado - esperando descarga PDF...")
            time.sleep(random.uniform(9, 14))

            # LEER PDF DESCARGADO
            pdf_files = glob.glob("/tmp/*.pdf")
            if pdf_files:
                pdf_path = max(pdf_files, key=os.path.getmtime)
                reader = PdfReader(pdf_path)
                texto_pdf = "".join(page.extract_text() + "\n" for page in reader.pages)

                # Extracción exacta (como tu PDF)
                res["ObraSocial"] = re.search(r'Denominación:\s*(.+?)(?:Código|$)', texto_pdf, re.I | re.DOTALL).group(1).strip() if re.search(r'Denominación:', texto_pdf, re.I) else "Sin datos"
                res["Titular"] = re.search(r'Nombre y Apellido:\s*(.+?)(?:Fecha|$)', texto_pdf, re.I | re.DOTALL).group(1).strip() if re.search(r'Nombre y Apellido:', texto_pdf, re.I) else "N/A"
                res["CUIT_Empleador"] = re.search(r'CUIT Empleador:\s*([\d-]+)', texto_pdf, re.I).group(1).strip() if re.search(r'CUIT Empleador:', texto_pdf, re.I) else "N/A"
                fam = re.search(r'Datos Grupo Familiar y Adherente(.+?)(?:La información|Dirección)', texto_pdf, re.I | re.DOTALL)
                res["Familiares"] = fam.group(1).strip().replace("\n", " | ")[:700] if fam else "Sin familiares a cargo"

                res["CODEM"] = "OK - PDF"
                log_message(f"✅ CODEM PDF OK: {dni} | OS: {res['ObraSocial'][:55]} | Familiares: SÍ | CUIT: {res['CUIT_Empleador']}")
                os.remove(pdf_path)
            else:
                log_message("⚠️ PDF no se descargó")
        else:
            log_message("⚠️ No encontró botón PDF (imposible ahora)")

    except Exception as e:
        log_message(f"❌ CODEM error {dni}: {str(e)[:120]}")

    return res

# --- EJECUCIÓN ---
if buscar_btn and dni_input:
    lista_dni = [d.strip() for d in dni_input.split('\n') if d.strip() and d.strip().isdigit()]
    if lista_dni:
        with st.status("Procesando (PDF automático)...", expanded=True) as status:
            log_message(f"Iniciando {len(lista_dni)} DNI...")
            
            driver_sisa = iniciar_driver()
            r_sisa = [consultar_sisa(driver_sisa, d, i==0) for i, d in enumerate(lista_dni)]
            driver_sisa.quit()
            
            driver_codem = iniciar_driver()
            r_codem = []
            for d in lista_dni:
                r_codem.append(consultar_codem(driver_codem, d))
                time.sleep(random.uniform(15, 25))
            driver_codem.quit()

            status.update(label="¡Terminado!", state="complete")

        final = []
        for i, d in enumerate(lista_dni):
            fila = {"DNI": d}
            fila.update(r_sisa[i])
            fila.update(r_codem[i])
            final.append(fila)

        df = pd.DataFrame(final)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button("📥 Descargar Planilla", df.to_csv(index=False).encode('utf-8'), "reporte_osecac.csv")
