import streamlit as st
import pandas as pd
import time
import random
import re
from bs4 import BeautifulSoup
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

# --- MOTOR (igual que antes) ---
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
    
    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

# --- SISA (sin tocar) ---
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

# --- CODEM MEJORADO (sin PDF, pero con extracción de tabla de familiares) ---
def consultar_codem(driver, dni):
    res = {
        "CODEM": "No hallado",
        "ObraSocial": "N/A",
        "Titular": "N/A",
        "Familiares": "N/A"
    }
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

        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Obra Social') or contains(text(), 'CUIL')]")))
        time.sleep(random.uniform(5, 8))

        soup = BeautifulSoup(driver.page_source, "html.parser")
        texto = soup.get_text(separator="\n", strip=True)
        texto = re.sub(r'\n+', '\n', texto)

        # Debug (para que veas qué ve el código)
        log_message(f"DEBUG texto CODEM {dni} (primeros 600 chars): {texto[:600]}...")

        # Obra Social (igual que en tu PDF)
        match_os = re.search(r'Denominación:\s*(.+?)(?:Código|Datos Laborales|$)', texto, re.IGNORECASE | re.DOTALL)
        if not match_os:
            match_os = re.search(r'(?:Obra Social|Tu Obra Social es|Código de Obra Social)\s*[:;]?\s*(.+?)(?:CUIL|$)', texto, re.IGNORECASE | re.DOTALL)
        res["ObraSocial"] = match_os.group(1).strip().replace("|", "").strip() if match_os else "Sin datos"

        # Titular
        match_tit = re.search(r'Nombre y Apellido:\s*(.+?)(?:Fecha de Nacimiento|$)', texto, re.IGNORECASE | re.DOTALL)
        res["Titular"] = match_tit.group(1).strip() if match_tit else "N/A"

        # FAMILIARES – busca la tabla exacta como en tu PDF
        familiares = "Sin familiares a cargo"
        # 1. Busca sección completa
        match_fam = re.search(r'Datos Grupo Familiar y Adherente(.+?)(?:La información|Dirección de Seguridad)', texto, re.DOTALL | re.IGNORECASE)
        if match_fam:
            familiares = match_fam.group(1).strip().replace("\n", " | ")[:600]
        else:
            # 2. Busca tabla con columnas CUIL + Parentesco
            tablas = soup.find_all("table")
            for tabla in tablas:
                ttext = tabla.get_text()
                if "CUIL" in ttext and ("Parentesco" in ttext or "Hijo" in ttext):
                    rows = tabla.find_all("tr")
                    fam_lines = []
                    for row in rows[1:]:
                        cells = [cell.get_text(strip=True) for cell in row.find_all(["td", "th"])]
                        if len(cells) >= 4:
                            fam_lines.append(" - ".join(cells))
                    if fam_lines:
                        familiares = " | ".join(fam_lines)
                        break

        res["Familiares"] = familiares
        res["CODEM"] = "OK"

        log_message(f"✅ CODEM OK: {dni} | OS: {res['ObraSocial'][:60]} | Familiares: {'SÍ (tabla encontrada)' if 'Hijo' in res['Familiares'] else 'No'}")

    except Exception as e:
        log_message(f"❌ CODEM error {dni}: {str(e)[:150]}")

    return res

# --- EJECUCIÓN ---
if buscar_btn and dni_input:
    lista_dni = [d.strip() for d in dni_input.split('\n') if d.strip() and d.strip().isdigit()]
    
    if lista_dni:
        with st.status("Procesando consulta dual...", expanded=True) as status:
            log_message(f"Iniciando con {len(lista_dni)} DNI...")
            
            driver_sisa = iniciar_driver()
            r_sisa = [consultar_sisa(driver_sisa, d, i==0) for i, d in enumerate(lista_dni)]
            driver_sisa.quit()
            
            driver_codem = iniciar_driver()
            r_codem = []
            for d in lista_dni:
                r_codem.append(consultar_codem(driver_codem, d))
                time.sleep(random.uniform(15, 25))  # pausa larga anti-captcha
            driver_codem.quit()

            status.update(label="Proceso terminado", state="complete")

        final = []
        for i, d in enumerate(lista_dni):
            fila = {"DNI": d}
            fila.update(r_sisa[i])
            fila.update(r_codem[i])
            final.append(fila)

        df = pd.DataFrame(final)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button("📥 Descargar Planilla", df.to_csv(index=False).encode('utf-8'), "reporte_osecac.csv")
