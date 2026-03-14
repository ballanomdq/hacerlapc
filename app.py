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
st.set_page_config(page_title="HACER LA PC - OSECAC", layout="wide")
st.title("💻 HACER LA PC - Sistema Unificado")

with st.container():
    st.subheader("📋 Ingreso de Datos")
    dni_input = st.text_area("Escribí los DNI (uno por línea):", height=150)
    buscar_btn = st.button("🚀 Iniciar Consulta Dual", type="primary")

log_container = st.expander("📋 Log de ejecución", expanded=True)

def log_message(msg):
    log_container.markdown(f"- {msg}")

# --- MOTOR con más stealth ---
def iniciar_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-extensions")
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'languages', {get: () => ['es-AR', 'es']});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
        """
    })
    return driver

# --- CONSULTA SISA (sin cambios, ya funciona bien) ---
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
        log_message(f"⚠️ SISA: No hallado o error {dni}")
    return res

# --- CONSULTA CODEM (mejorada anti-captcha + extracción sin PDF) ---
def consultar_codem(driver, dni):
    res = {
        "CODEM": "No hallado",
        "ObraSocial": "N/A",
        "Titular": "N/A",
        "Familiares": "N/A"
    }
    try:
        driver.get("https://servicioswww.anses.gob.ar/ooss2/")
        time.sleep(random.uniform(10, 16))  # Espera inicial más larga y random

        campo = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.ID, "ContentPlaceHolder1_txtDoc"))
        )
        campo.clear()
        
        # Envío MUY lento y humano
        for char in str(dni):
            campo.send_keys(char)
            time.sleep(random.uniform(0.25, 0.65))  # más lento que antes
        
        time.sleep(random.uniform(3.5, 6.5))  # pausa antes de botón

        btn = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.ID, "ContentPlaceHolder1_Button1"))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", btn)
        time.sleep(random.uniform(0.8, 1.8))
        driver.execute_script("arguments[0].click();", btn)

        # Espera inteligente: aparece "Obra Social" o "empadronamiento" o tabla
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, "//*[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'obra social') or contains(text(), 'empadronamiento') or contains(text(), 'CUIL')]"))
        )
        
        time.sleep(random.uniform(4, 7))  # dejar renderizar todo

        soup = BeautifulSoup(driver.page_source, "html.parser")
        texto = soup.get_text(separator=" ", strip=True)
        texto = " ".join(texto.split())  # limpia

        # Extracción Obra Social
        obra_social = "Sin datos"
        pos_os = texto.find("Obra Social")
        if pos_os == -1:
            pos_os = texto.find("Denominación")
        if pos_os != -1:
            frag = texto[pos_os:pos_os+350]
            fin = min(
                frag.find("CUIL") if frag.find("CUIL") > 0 else 350,
                frag.find("Nombre") if frag.find("Nombre") > 0 else 350,
                frag.find("CUIT") if frag.find("CUIT") > 0 else 350
            )
            obra_social = frag[:fin].replace("Obra Social", "").replace("Denominación", "").strip(" :;,.")

        # Titular
        titular = "Sin datos"
        pos_cuil = texto.find("CUIL")
        if pos_cuil != -1:
            frag_tit = texto[max(0, pos_cuil-120):pos_cuil+250]
            titular = frag_tit.strip()[:180]

        # Familiares
        familiares = "Sin familiares a cargo"
        pos_fam = texto.lower().find("familiar")
        if pos_fam == -1:
            pos_fam = texto.lower().find("hijo")
        if pos_fam != -1:
            frag_fam = texto[pos_fam-100:pos_fam+600].strip()[:350]
            familiares = frag_fam.replace("\n", " ").strip()

        res["ObraSocial"] = obra_social or "Sin datos"
        res["Titular"] = titular or "N/A"
        res["Familiares"] = familiares
        res["CODEM"] = "OK"

        log_message(f"✅ CODEM OK: {dni} | OS: {res['ObraSocial'][:60]}...")

    except Exception as e:
        err = str(e).lower()
        if "timeout" in err or "wait" in err:
            log_message(f"⌛ CODEM timeout {dni} (quizá lento o captcha)")
        elif "element" in err:
            log_message(f"❌ CODEM elemento no encontrado {dni} (posible cambio página o captcha)")
        else:
            log_message(f"❌ CODEM error {dni}: {str(e)[:120]} (probable captcha)")

    return res

# --- EJECUCIÓN PRINCIPAL ---
if buscar_btn and dni_input:
    lista_dni = [d.strip() for d in dni_input.split('\n') if d.strip() and d.strip().isdigit()]
    
    if lista_dni:
        with st.status("Procesando consulta dual (cuidado con captcha ANSES)...", expanded=True) as status:
            log_message(f"Iniciando con {len(lista_dni)} DNI...")
            
            log_message("Fase SISA...")
            driver_sisa = iniciar_driver()
            r_sisa = []
            for i, dni in enumerate(lista_dni):
                r_sisa.append(consultar_sisa(driver_sisa, dni, i==0))
                time.sleep(random.uniform(4, 9))  # pausa entre consultas
            driver_sisa.quit()
            
            log_message("Fase CODEM (máximo sigilo)...")
            driver_codem = iniciar_driver()
            r_codem = []
            for dni in lista_dni:
                r_codem.append(consultar_codem(driver_codem, dni))
                time.sleep(random.uniform(12, 22))  # PAUSA LARGA entre cada CODEM !! muy importante
            driver_codem.quit()

            status.update(label="Proceso terminado", state="complete")

        # Armar tabla
        final = []
        for i, dni in enumerate(lista_dni):
            fila = {"DNI": dni}
            fila.update(r_sisa[i])
            fila.update(r_codem[i])
            final.append(fila)

        df = pd.DataFrame(final)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        st.download_button(
            "📥 Descargar Planilla",
            df.to_csv(index=False).encode('utf-8'),
            "reporte_osecac.csv",
            "text/csv"
        )
