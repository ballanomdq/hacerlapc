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
from selenium.common.exceptions import TimeoutException, NoSuchElementException

st.set_page_config(page_title="HACER LA PC - Completo", layout="wide")
st.title("💻 HACER LA PC - Control SISA + CODEM")

# Estilo minimalista
st.markdown("""
<style>
    .stDataFrame { border: 1px solid #38bdf8; border-radius: 10px; }
    .reportview-container { background: #f0f2f6; }
</style>
""", unsafe_allow_html=True)

# --- Interfaz de usuario ---
with st.container():
    st.subheader("📋 Ingreso de Datos")
    dni_input = st.text_area("Escribí un DNI por línea:", height=150, placeholder="Ejemplo:\n17998675\n25131361")
    buscar_btn = st.button("🚀 Iniciar Consulta Dual", type="primary")

log_container = st.expander("📋 Log de ejecución detallado", expanded=False)

def log_message(msg):
    log_container.markdown(f"- {msg}")

def iniciar_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

# ==================== LÓGICA SISA ====================
def consultar_sisa(driver, dni, es_primer_dni):
    resultado = {"TipoDoc": "", "NroDoc": "", "Sexo": "", "Cobertura SISA": "", "Denominación": ""}
    try:
        if es_primer_dni:
            driver.get("https://sisa.msal.gov.ar/sisa/#sisa")
            time.sleep(3)
            puco = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'PUCO')]")))
            driver.execute_script("arguments[0].click();", puco)
            time.sleep(2)
        
        campo_dni = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.TAG_NAME, "input")))
        campo_dni.clear()
        campo_dni.send_keys(str(dni))
        campo_dni.send_keys(Keys.RETURN)
        
        WebDriverWait(driver, 8).until(EC.presence_of_element_located((By.XPATH, f"//td[contains(text(), '{dni}')]")))
        fila = driver.find_element(By.XPATH, f"//td[contains(text(), '{dni}')]/..")
        celdas = fila.find_elements(By.TAG_NAME, "td")
        if len(celdas) >= 5:
            resultado = {
                "TipoDoc": celdas[0].text.strip(), "NroDoc": celdas[1].text.strip(),
                "Sexo": celdas[2].text.strip(), "Cobertura SISA": celdas[3].text.strip(),
                "Denominación": celdas[4].text.strip()
            }
    except:
        log_message(f"⚠️ SISA: No se hallaron datos para {dni}")
    return resultado

# ==================== LÓGICA CODEM (Reforzada) ====================
def consultar_codem(driver, dni):
    resultado = {"Obra Social CODEM": "", "Familiares": ""}
    try:
        driver.get("https://servicioswww.anses.gob.ar/ooss2/")
        driver.switch_to.default_content() # Reset de frames
        time.sleep(3)

        # Localizar campo DNI (ID específico de ANSES)
        campo = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "ContentPlaceHolder1_txtDoc"))
        )
        driver.execute_script("arguments[0].value = '';", campo)
        campo.send_keys(str(dni))
        
        # Click en Continuar
        boton = driver.find_element(By.ID, "ContentPlaceHolder1_Button1")
        driver.execute_script("arguments[0].click();", boton)
        
        # Esperar resultado
        WebDriverWait(driver, 7).until(EC.presence_of_element_located((By.ID, "ContentPlaceHolder1_lblObraSocial")))
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        obra = soup.find(id=lambda x: x and x.endswith('lblObraSocial'))
        familia = soup.find(id=lambda x: x and x.endswith('lblFamiliares'))
        
        resultado["Obra Social CODEM"] = obra.text.strip() if obra else "No figura"
        resultado["Familiares"] = familia.text.strip() if familia else "0"
        log_message(f"✅ CODEM OK para {dni}")
    except:
        log_message(f"❌ CODEM falló para {dni}")
    return resultado

# ==================== PROCESO PRINCIPAL ====================
if buscar_btn and dni_input:
    dnis = [d.strip() for d in dni_input.split('\n') if d.strip()]
    
    with st.status("Ejecutando consultas en SISA y ANSES...", expanded=True) as status:
        # Ejecución SISA
        log_message("Iniciando fase SISA...")
        driver = iniciar_driver()
        res_sisa = [consultar_sisa(driver, d, i==0) for i, d in enumerate(dnis)]
        driver.quit()
        
        # Ejecución CODEM
        log_message("Iniciando fase CODEM...")
        driver = iniciar_driver()
        res_codem = [consultar_codem(driver, d) for d in dnis]
        driver.quit()
        
        status.update(label="¡Consultas terminadas!", state="complete", expanded=False)

    # Combinar y mostrar
    final_data = []
    for i, d in enumerate(dnis):
        final_data.append({"DNI": d, **res_sisa[i], **res_codem[i]})
    
    df = pd.DataFrame(final_data)
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.download_button("📥 Descargar Resultados", df.to_csv(index=False).encode('utf-8'), "reporte_hacer_pc.csv")
