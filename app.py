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

# --- 1. CONFIGURACIÓN VISUAL (ESTILO OSECAC) ---
st.set_page_config(page_title="HACER LA PC - Agencia MDP", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; background-color: #0056b3; color: white; }
    .stDownloadButton>button { background-color: #28a745; color: white; }
    </style>
    """, unsafe_allow_html=True)

st.title("💻 Buscador OSECAC (SISA + CODEM)")
st.info("Esta herramienta procesa hasta 15 DNIs. Si necesitas el PDF de familiares, usá el botón de la tabla.")

# --- 2. INTERFAZ DE USUARIO ---
with st.container():
    dni_input = st.text_area("Ingresá los DNI (uno por línea):", height=150, placeholder="Ejemplo:\n25131361\n27455667")
    
    lista_dni = [d.strip() for d in dni_input.split('\n') if d.strip()]
    cant = len(lista_dni)
    
    col1, col2 = st.columns([1, 4])
    with col1:
        if cant > 15:
            st.error(f"Límite superado ({cant}/15)")
            buscar_btn = st.button("🚀 Iniciar", disabled=True)
        elif cant > 0:
            st.success(f"Listo para {cant} DNIs")
            buscar_btn = st.button("🚀 Iniciar", type="primary")
        else:
            buscar_btn = st.button("🚀 Iniciar", disabled=True)

log_container = st.expander("📋 Estado del proceso", expanded=True)
def log_message(msg):
    log_container.markdown(f"- {msg}")

# --- 3. FUNCIONES DE BÚSQUEDA ---
def iniciar_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, Gecko) Chrome/122.0.0.0 Safari/537.36")
    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

def consultar_sisa(driver, dni, es_primer):
    res = {"SISA": "N/A", "OS_SISA": "N/A"}
    try:
        if es_primer:
            driver.get("https://sisa.msal.gov.ar/sisa/#sisa")
            time.sleep(5)
            puco = driver.find_element(By.XPATH, "//*[contains(text(), 'PUCO')]")
            driver.execute_script("arguments[0].click();", puco)
            time.sleep(2)
        
        campo = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "input")))
        campo.clear()
        campo.send_keys(str(dni))
        campo.send_keys(Keys.RETURN)
        
        target = f"//td[contains(text(), '{dni}')]"
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, target)))
        cols = driver.find_element(By.XPATH, f"{target}/..").find_elements(By.TAG_NAME, "td")
        res = {"SISA": cols[3].text, "OS_SISA": cols[4].text}
        log_message(f"✅ SISA OK: {dni}")
    except:
        log_message(f"⚠️ SISA: No hallado {dni}")
    return res

def consultar_codem(driver, dni):
    res = {"CODEM": "Fallo", "Link_PDF": f"https://servicioswww.anses.gob.ar/ooss2/?dni={dni}"}
    try:
        driver.get("https://servicioswww.anses.gob.ar/ooss2/")
        time.sleep(random.uniform(9, 12))
        
        campo = driver.find_element(By.ID, "ContentPlaceHolder1_txtDoc")
        for c in str(dni):
            campo.send_keys(c); time.sleep(0.1)
        
        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "ContentPlaceHolder1_Button1"))
        time.sleep(5)
        
        texto = driver.page_source
        if "Obra Social" in texto:
            soup = BeautifulSoup(texto, "html.parser")
            res["CODEM"] = soup.get_text().split("Obra Social")[-1][:70].strip().replace("\n", " ")
            log_message(f"✅ CODEM OK: {dni}")
        else:
            log_message(f"❌ CODEM: Bloqueo en {dni}")
    except:
        log_message(f"❌ CODEM: Error en {dni}")
    return res

# --- 4. PROCESO FINAL ---
if buscar_btn:
    with st.status("Consultando bases de datos...", expanded=True) as status:
        driver = iniciar_driver()
        
        # SISA
        log_message("Iniciando SISA...")
        r1 = [consultar_sisa(driver, d, i==0) for i, d in enumerate(lista_dni)]
        
        time.sleep(3)
        
        # CODEM
        log_message("Iniciando CODEM...")
        r2 = [consultar_codem(driver, d) for d in lista_dni]
        
        driver.quit()
        status.update(label="Proceso terminado", state="complete")

    # Armado de la tabla con links
    final = []
    for i, d in enumerate(lista_dni):
        final.append({
            "DNI": d,
            "ESTADO SISA": r1[i]["SISA"],
            "OBRA SOCIAL SISA": r1[i]["OS_SISA"],
            "ESTADO CODEM": r2[i]["CODEM"],
            "ACCESO AL PDF": r2[i]["Link_PDF"]
        })
    
    df = pd.DataFrame(final)
    
    # Mostramos la tabla. Streamlit reconoce los links automáticamente.
    st.subheader("📊 Resultados de la Agencia")
    st.dataframe(
        df, 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "ACCESO AL PDF": st.column_config.LinkColumn("Bajar PDF de ANSES")
        }
    )
    
    st.download_button("📥 Descargar reporte CSV", df.to_csv(index=False).encode('utf-8'), "reporte_agencia.csv")
