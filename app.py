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
st.set_page_config(page_title="HACER LA PC - Completo", layout="wide")
st.title("💻 HACER LA PC - Control SISA + CODEM")

st.markdown("""
<style>
    .stDataFrame { border: 1px solid #38bdf8; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

with st.container():
    st.subheader("📋 Ingreso de DNI")
    dni_input = st.text_area("Escribí un DNI por línea:", height=150, placeholder="Ejemplo:\n17998675")
    buscar_btn = st.button("🚀 Iniciar Consulta Dual", type="primary")

log_container = st.expander("📋 Log de ejecución detallado", expanded=True)

def log_message(msg):
    log_container.markdown(f"- {msg}")

def iniciar_driver():
    options = Options()
    options.add_argument("--headless=new") 
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    
    # User-Agent rotativo o fijo pero real
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

# ==================== FUNCIÓN SISA (Con demoras leves) ====================
def consultar_sisa(driver, dni, es_primer_dni):
    resultado = {"TipoDoc": "", "NroDoc": "", "Sexo": "", "Cobertura SISA": "Sin datos", "Denominación": ""}
    try:
        if es_primer_dni:
            driver.get("https://sisa.msal.gov.ar/sisa/#sisa")
            time.sleep(random.uniform(4, 6)) # Un poco más de tiempo al inicio
            puco = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'PUCO')]")))
            driver.execute_script("arguments[0].click();", puco)
            time.sleep(2)
        
        campo_dni = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.TAG_NAME, "input")))
        campo_dni.clear()
        # Escribir DNI un poco más lento
        for char in str(dni):
            campo_dni.send_keys(char)
            time.sleep(random.uniform(0.1, 0.3))
        
        campo_dni.send_keys(Keys.RETURN)
        
        WebDriverWait(driver, 12).until(EC.presence_of_element_located((By.XPATH, f"//td[contains(text(), '{dni}')]")))
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

# ==================== FUNCIÓN CODEM (ULTRA-LENTA) ====================
def consultar_codem(driver, dni):
    resultado = {"Obra Social CODEM": "No encontrado", "Familiares": "0"}
    try:
        driver.get("https://servicioswww.anses.gob.ar/ooss2/")
        
        # Simulamos que el "usuario" está mirando la página antes de clickear
        time.sleep(random.uniform(6, 9)) 
        
        driver.switch_to.default_content()

        campo = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "ContentPlaceHolder1_txtDoc"))
        )
        
        # Simulación de escritura humana MUY lenta
        for char in str(dni):
            campo.send_keys(char)
            time.sleep(random.uniform(0.3, 0.6))
        
        time.sleep(random.uniform(1.5, 3)) # Pausa antes de darle al botón
        
        boton = driver.find_element(By.ID, "ContentPlaceHolder1_Button1")
        driver.execute_script("arguments[0].click();", boton)
        
        # Esperar la respuesta
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "ContentPlaceHolder1_lblObraSocial"))
        )
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        obra = soup.find(id="ContentPlaceHolder1_lblObraSocial")
        familia = soup.find(id="ContentPlaceHolder1_lblFamiliares")
        
        resultado["Obra Social CODEM"] = obra.text.strip() if (obra and obra.text.strip()) else "Sin Obra Social"
        resultado["Familiares"] = familia.text.strip() if familia else "0"
        log_message(f"✅ CODEM OK: {dni}")

    except Exception:
        page_source = driver.page_source.lower()
        if "captcha" in page_source:
            log_message(f"❌ CODEM bloqueado por CAPTCHA para {dni}")
        elif "no existe" in page_source:
            resultado["Obra Social CODEM"] = "DNI Inexistente"
            log_message(f"⚠️ CODEM: {dni} no figura en ANSES")
        else:
            log_message(f"❌ CODEM: Error técnico para {dni}")
            
    return resultado

# ==================== PROCESO ====================
if buscar_btn and dni_input:
    dnis = [d.strip() for d in dni_input.split('\n') if d.strip()]
    
    if dnis:
        with st.status("Realizando consultas (Simulando actividad humana)...", expanded=True) as status:
            # Fase SISA
            log_message("Iniciando SISA (con esperas preventivas)...")
            driver_sisa = iniciar_driver()
            res_sisa = [consultar_sisa(driver_sisa, d, i==0) for i, d in enumerate(dnis)]
            driver_sisa.quit()
            
            # PAUSA GRANDE ENTRE SERVICIOS
            log_message("Pausa de seguridad de 10 segundos...")
            time.sleep(10)
            
            # Fase CODEM
            log_message("Iniciando CODEM (modo ultra-lento)...")
            driver_codem = iniciar_driver()
            res_codem = [consultar_codem(driver_codem, d) for d in dnis]
            driver_codem.quit()
            
            status.update(label="Consultas finalizadas.", state="complete", expanded=False)

        # Resultados finales
        final_list = []
        for i, dni in enumerate(dnis):
            final_list.append({"DNI": dni, **res_sisa[i], **res_codem[i]})
        
        df = pd.DataFrame(final_list)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button("📥 Descargar CSV", df.to_csv(index=False).encode('utf-8'), "hacer_pc.csv")
