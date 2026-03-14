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

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="HACER LA PC - OSECAC", layout="wide")
st.title("🏥 Sistema Unificado de Consultas - Agencia MDP")

dni_input = st.text_area("📋 Ingresá los DNI (uno por línea):", height=150)
buscar_btn = st.button("🚀 Iniciar Consulta", type="primary")

log_container = st.expander("📋 Log de ejecución", expanded=True)
def log_message(msg):
    log_container.markdown(f"- {msg}")

def iniciar_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    return webdriver.Chrome(options=options)

# --- 2. FUNCIONES ---
def consultar_sisa(driver, dni, es_primero):
    res = {"NOMBRE": "No hallado", "OS_SISA": "N/A"}
    try:
        if es_primero:
            driver.get("https://sisa.msal.gov.ar/sisa/#sisa")
            time.sleep(6)
            puco = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'PUCO')]")))
            driver.execute_script("arguments[0].click();", puco)
            time.sleep(2)
        
        campo = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.TAG_NAME, "input")))
        campo.clear()
        campo.send_keys(str(dni) + Keys.RETURN)
        
        target = f"//td[contains(text(), '{dni}')]"
        WebDriverWait(driver, 12).until(EC.presence_of_element_located((By.XPATH, target)))
        cols = driver.find_element(By.XPATH, f"{target}/..").find_elements(By.TAG_NAME, "td")
        if len(cols) >= 5:
            res = {"NOMBRE": cols[3].text.strip(), "OS_SISA": cols[4].text.strip()}
            log_message(f"✅ SISA OK: {dni}")
    except:
        log_message(f"⚠️ SISA: Sin datos para {dni}")
    return res

def consultar_codem(driver, dni):
    res = {"INFO_CODEM": "No hallado"}
    try:
        driver.get("https://servicioswww.anses.gob.ar/ooss2/")
        time.sleep(random.uniform(9, 11))
        
        input_doc = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "ContentPlaceHolder1_txtDoc")))
        input_doc.clear()
        for num in str(dni): 
            input_doc.send_keys(num)
            time.sleep(0.1)
        
        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "ContentPlaceHolder1_Button1"))
        time.sleep(8)
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        tabla = soup.find("table", {"id": "ContentPlaceHolder1_gvGrilla"})
        
        if tabla:
            filas = tabla.find_all("tr")
            if len(filas) > 1:
                # Extraemos y limpiamos el texto de la fila
                texto_sucio = filas[1].get_text(separator=" ").strip()
                # Quitamos espacios múltiples y dejamos solo lo importante
                texto_limpio = re.sub(r'\s+', ' ', texto_sucio)
                res["INFO_CODEM"] = texto_limpio
                log_message(f"✅ CODEM OK: {dni}")
        else:
            # Si no hay tabla, buscamos el texto de la Obra Social directamente
            texto_pantalla = soup.get_text()
            if "Tu Obra Social es" in texto_pantalla:
                res["INFO_CODEM"] = "Datos hallados (verificar en reporte manual)"
            else:
                log_message(f"❌ CODEM: No hallado para {dni}")
    except:
        log_message(f"❌ CODEM: Error técnico en {dni}")
    return res

# --- 3. EJECUCIÓN ---
if buscar_btn and dni_input:
    lista_dni = [d.strip() for d in dni_input.split('\n') if d.strip()]
    if lista_dni:
        with st.status("Procesando informe...", expanded=True) as status:
            d = iniciar_driver()
            resultados = []
            for i, dni in enumerate(lista_dni):
                sisa = consultar_sisa(d, dni, i==0)
                time.sleep(2)
                anses = consultar_codem(d, dni)
                
                fila = {"DNI": dni}
                fila.update(sisa)
                fila.update(anses)
                resultados.append(fila)
            
            d.quit()
            status.update(label="Proceso terminado", state="complete")

        df = pd.DataFrame(resultados)
        
        st.subheader("📊 Reporte Detallado")
        # Usamos st.data_editor para permitir que las celdas se expandan mejor
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        st.download_button("📥 Descargar Planilla", df.to_csv(index=False).encode('utf-8'), "reporte_osecac_mdp.csv")
