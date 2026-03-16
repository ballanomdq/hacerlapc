import streamlit as st
import pandas as pd
import time
import random
import os
import glob
import re
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
st.markdown("**Consulta Dual SISA + ANSES (CODEM en PDF)**")

with st.container():
    st.subheader("📋 Ingreso de Datos")
    dni_input = st.text_area("Escribí los DNI (uno por línea):", height=150)
    buscar_btn = st.button("🚀 Iniciar Consulta Dual", type="primary")

log_container = st.expander("📋 Log de ejecución", expanded=True)
def log_message(msg):
    log_container.markdown(f"- {msg}")

# --- DRIVER (igual que antes) ---
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

# --- SISA ---
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
    except:
        pass
    return res

# --- CODEM CON PDF ---
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

        for f in glob.glob("/tmp/*.pdf"): os.remove(f)

        print_btn = WebDriverWait(driver, 8).until(EC.element_to_be_clickable((By.XPATH, "//img[contains(@src, 'imprimir2.gif')]")))
        driver.execute_script("arguments[0].click();", print_btn)
        time.sleep(random.uniform(9, 14))

        pdf_files = glob.glob("/tmp/*.pdf")
        if pdf_files:
            pdf_path = max(pdf_files, key=os.path.getmtime)
            reader = PdfReader(pdf_path)
            texto_pdf = "".join(page.extract_text() + "\n" for page in reader.pages)

            res["ObraSocial"] = re.search(r'Denominación:\s*(.+?)(?:Código|$)', texto_pdf, re.I | re.DOTALL).group(1).strip() if re.search(r'Denominación:', texto_pdf, re.I) else "Sin datos"
            res["Titular"] = re.search(r'Nombre y Apellido:\s*(.+?)(?:Fecha|$)', texto_pdf, re.I | re.DOTALL).group(1).strip() if re.search(r'Nombre y Apellido:', texto_pdf, re.I) else "N/A"
            res["CUIT_Empleador"] = re.search(r'CUIT Empleador:\s*([\d-]+)', texto_pdf, re.I).group(1).strip() if re.search(r'CUIT Empleador:', texto_pdf, re.I) else "N/A"
            fam = re.search(r'Datos Grupo Familiar y Adherente(.+?)(?:La información|Dirección)', texto_pdf, re.I | re.DOTALL)
            res["Familiares"] = fam.group(1).strip() if fam else "Sin familiares a cargo"

            res["CODEM"] = "OK - PDF"
            os.remove(pdf_path)
    except:
        pass
    return res

# --- EJECUCIÓN ---
if buscar_btn and dni_input:
    lista_dni = [d.strip() for d in dni_input.split('\n') if d.strip() and d.strip().isdigit()]
    
    if lista_dni:
        with st.status("Procesando...", expanded=True) as status:
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

        # TABLA LIMPIA
        final = []
        for i, d in enumerate(lista_dni):
            titular = r_codem[i].get("Titular", "N/A")
            os_name = r_codem[i].get("ObraSocial", "")
            status_ok = "✅ OSECAC Aprobado" if "COMERCIO" in os_name.upper() or "126205" in os_name else "⚠️ Revisar"
            
            final.append({
                "DNI": d,
                "Titular": titular,
                "Status": status_ok,
                "Ver": "👁️ Ver completa"
            })

        df = pd.DataFrame(final)
        
        # TABLA PRINCIPAL (limpia y bonita)
        st.dataframe(
            df[["DNI", "Titular", "Status"]],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Status": st.column_config.TextColumn("Estado OSECAC", width="medium")
            }
        )

        # DETALLES EXPANDIBLES CON COLORES (como pediste)
        st.markdown("### 👁️ Consultas Completas")
        for i, row in df.iterrows():
            with st.expander(f"👁️ {row['DNI']} - {row['Titular']}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.success("**SISA**")
                    st.write(f"**Obra Social:** {r_sisa[i]['OS_SISA']}")
                with col2:
                    st.success("**CODEM (PDF)**")
                    st.write(f"**Obra Social:** {r_codem[i]['ObraSocial']}")
                    st.write(f"**CUIT Empleador:** {r_codem[i]['CUIT_Empleador']}")
                
                st.markdown("**👨‍👩‍👧‍👦 Grupo Familiar**")
                st.info(r_codem[i]['Familiares'].replace(" | ", "\n\n"))
                
                st.markdown("**📋 Datos del Titular**")
                st.write(f"**Nombre:** {r_codem[i]['Titular']}")

        st.download_button("📥 Descargar Planilla Completa", 
                         pd.DataFrame([{"DNI":d, **r_sisa[i], **r_codem[i]} for i,d in enumerate(lista_dni)]).to_csv(index=False).encode('utf-8'),
                         "reporte_osecac.csv")
