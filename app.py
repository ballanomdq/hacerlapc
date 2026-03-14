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
from selenium.common.exceptions import TimeoutException

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="HACER LA PC - Completo", layout="wide")
st.title("💻 HACER LA PC - Control SISA + CODEM")

st.markdown("""
<style>
    .stDataFrame { border: 1px solid #38bdf8; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# --- INTERFAZ ---
with st.container():
    st.subheader("📋 Ingreso de DNI")
    dni_input = st.text_area("Escribí un DNI por línea:", height=150, placeholder="Ejemplo:\n17998675\n25131361")
    buscar_btn = st.button("🚀 Iniciar Consulta Dual", type="primary")

log_container = st.expander("📋 Log de ejecución detallado", expanded=True)

def log_message(msg):
    log_container.markdown(f"- {msg}")

# --- DRIVER CONFIGURADO PARA EVITAR BLOQUEOS ---
def iniciar_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    # User-Agent real para que ANSES no nos bloquee
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

# ==================== FUNCIÓN SISA ====================
def consultar_sisa(driver, dni, es_primer_dni):
    resultado = {"TipoDoc": "", "NroDoc": "", "Sexo": "", "Cobertura SISA": "No encontrado", "Denominación": ""}
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
            log_message(f"✅ SISA OK: {dni}")
    except:
        log_message(f"⚠️ SISA: Sin datos para {dni}")
    return resultado

# ==================== FUNCIÓN CODEM REFORZADA ====================
def consultar_codem(driver, dni):
    resultado = {"Obra Social CODEM": "No encontrado", "Familiares": "0"}
    try:
        driver.get("https://servicioswww.anses.gob.ar/ooss2/")
        time.sleep(4)
        driver.switch_to.default_content()

        # Selector flexible para el campo DNI
        campo = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "input[id*='txtDoc'], input[name*='txtDoc']"))
        )
        driver.execute_script("arguments[0].value = '';", campo)
        campo.send_keys(str(dni))
        
        # Click en Continuar con JS
        boton = driver.find_element(By.CSS_SELECTOR, "input[type='submit'], input[id*='Button1']")
        driver.execute_script("arguments[0].click();", boton)
        
        # Esperar resultado final
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//*[contains(@id, 'lblObraSocial')]")))
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        obra = soup.find(id=lambda x: x and 'lblObraSocial' in x)
        familia = soup.find(id=lambda x: x and 'lblFamiliares' in x)
        
        resultado["Obra Social CODEM"] = obra.text.strip() if obra else "No figura"
        resultado["Familiares"] = familia.text.strip() if familia else "0"
        log_message(f"✅ CODEM OK: {dni}")
    except Exception as e:
        if "no existe" in driver.page_source.lower():
            resultado["Obra Social CODEM"] = "DNI Inexistente"
            log_message(f"⚠️ CODEM: DNI {dni} inexistente")
        else:
            log_message(f"❌ CODEM falló para {dni}")
    return resultado

# ==================== PROCESAMIENTO ====================
if buscar_btn and dni_input:
    lista_dnis = [d.strip() for d in dni_input.split('\n') if d.strip()]
    
    if not lista_dnis:
        st.warning("Ingresá al menos un DNI.")
    else:
        with st.status("Ejecutando consultas...", expanded=True) as status:
            # Fase SISA
            log_message("--- Iniciando SISA ---")
            driver_sisa = iniciar_driver()
            res_sisa = [consultar_sisa(driver_sisa, d, i==0) for i, d in enumerate(lista_dnis)]
            driver_sisa.quit()
            
            # Fase CODEM
            log_message("--- Iniciando CODEM ---")
            driver_codem = iniciar_driver()
            res_codem = [consultar_codem(driver_codem, d) for d in lista_dnis]
            driver_codem.quit()
            
            status.update(label="¡Proceso Terminado!", state="complete", expanded=False)

        # Crear tabla final
        datos_finales = []
        for i, dni in enumerate(lista_dnis):
            fila = {"DNI": dni, **res_sisa[i], **res_codem[i]}
            datos_finales.append(fila)
        
        df = pd.DataFrame(datos_finales)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Descargar Planilla CSV", csv, "consulta_osecac.csv")
