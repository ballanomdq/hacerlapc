import streamlit as st
import pandas as pd
import time
import random
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

st.set_page_config(page_title="HACER LA PC - Completo", layout="wide")
st.title("💻 HACER LA PC - Control Completo (SISA + CODEM)")

st.markdown("""
<style>
    .stDataFrame { border: 1px solid #38bdf8; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

with st.container():
    st.subheader("📋 Ingreso de DNI")
    dni_input = st.text_area("Escribí un DNI por línea:", height=150, placeholder="Ejemplo:\n25131361\n11529359")
    col1, col2 = st.columns([1,5])
    with col1:
        buscar_btn = st.button("🚀 Consultar Ahora", type="primary")

result_container = st.container()
log_container = st.expander("📋 Log de ejecución", expanded=False)

def log_message(msg):
    log_container.markdown(f"- {msg}")

# ==================== FUNCIONES SISA (SELENIUM) ====================
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

def encontrar_campo_dni_sisa(driver, despues_refresh=False):
    if despues_refresh:
        try:
            puco = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'PUCO')]"))
            )
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", puco)
            time.sleep(1)
            driver.execute_script("arguments[0].click();", puco)
            log_message("SISA: Módulo PUCO clickeado tras refresh")
            time.sleep(3)
        except:
            pass
    
    for intento in range(3):
        try:
            campo = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//input[contains(@name, 'dni')]"))
            )
            log_message("SISA: Campo DNI encontrado")
            return campo
        except:
            log_message(f"SISA: Reintentando campo DNI ({intento+1}/3)")
            time.sleep(2)
    
    inputs = driver.find_elements(By.TAG_NAME, "input")
    for inp in inputs:
        if inp.is_displayed() and inp.get_attribute("type") in ["text", "search"]:
            log_message("SISA: Campo DNI encontrado como input visible")
            return inp
    return None

def consultar_sisa_selenium(driver, dni, es_primer_dni):
    resultado = {"TipoDoc": "", "NroDoc": "", "Sexo": "", "Cobertura SISA": "", "Denominación": ""}
    try:
        if es_primer_dni:
            log_message(f"SISA: Iniciando para DNI {dni}")
            driver.get("https://sisa.msal.gov.ar/sisa/#sisa")
            log_message("Esperando módulo PUCO...")
            try:
                puco = WebDriverWait(driver, 15).until(
                    EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'PUCO')]"))
                )
            except TimeoutException:
                puco = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'consulta de cobertura')]"))
                )
            time.sleep(random.uniform(1, 2))
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", puco)
            time.sleep(random.uniform(0.3, 0.8))
            driver.execute_script("arguments[0].click();", puco)
            log_message("Módulo PUCO clickeado.")
            
            campo_dni = encontrar_campo_dni_sisa(driver, despues_refresh=False)
            if not campo_dni:
                log_message("SISA: Refrescando página...")
                driver.refresh()
                time.sleep(3)
                campo_dni = encontrar_campo_dni_sisa(driver, despues_refresh=True)
                if not campo_dni:
                    raise Exception("No se encontró campo DNI en SISA")
        else:
            try:
                campo_dni = driver.find_element(By.XPATH, "//input[contains(@name, 'dni')]")
            except:
                campo_dni = encontrar_campo_dni_sisa(driver, despues_refresh=False)
                if not campo_dni:
                    raise Exception("Campo DNI no disponible en SISA")
        
        campo_dni.clear()
        time.sleep(random.uniform(0.2, 0.5))
        campo_dni.send_keys(str(dni))
        time.sleep(random.uniform(0.3, 0.7))
        campo_dni.send_keys(Keys.RETURN)
        log_message(f"SISA: Enter enviado para DNI {dni}")
        
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, f"//td[contains(text(), '{dni}')]"))
            )
            log_message("SISA: Resultados detectados")
        except TimeoutException:
            log_message("SISA: Tiempo de espera agotado")
            return resultado
        
        time.sleep(random.uniform(0.5, 1))
        
        tablas = driver.find_elements(By.XPATH, "//table")
        for tabla in tablas:
            celdas_dni = tabla.find_elements(By.XPATH, f".//td[contains(text(), '{dni}')]")
            for celda in celdas_dni:
                texto = celda.text.strip()
                if texto == str(dni) or (texto.isdigit() and len(texto) in (7,8)):
                    fila = celda.find_element(By.XPATH, "..")
                    celdas_fila = fila.find_elements(By.TAG_NAME, "td")
                    if len(celdas_fila) >= 5:
                        resultado["TipoDoc"] = celdas_fila[0].text.strip()
                        resultado["NroDoc"] = celdas_fila[1].text.strip()
                        resultado["Sexo"] = celdas_fila[2].text.strip()
                        resultado["Cobertura SISA"] = celdas_fila[3].text.strip()
                        resultado["Denominación"] = celdas_fila[4].text.strip()
                        log_message(f"SISA: Datos extraídos OK")
                        return resultado
        log_message("SISA: No se encontraron datos")
        return resultado
    except Exception as e:
        log_message(f"SISA Error: {str(e)[:50]}")
        return resultado

# ==================== FUNCIONES CODEM (SOLO SELENIUM, DESPUÉS DE SISA) ====================
def consultar_codem_selenium(driver, dni, es_primer_dni_codem):
    resultado = {"Obra Social CODEM": "", "Familiares": ""}
    try:
        if es_primer_dni_codem:
            log_message(f"CODEM: Iniciando para DNI {dni}")
            driver.get("https://servicioswww.anses.gob.ar/ooss2/")
            time.sleep(3)
        
        # Buscar campo DNI
        try:
            dni_field = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.NAME, "ctl00$ContentPlaceHolder1$txtDoc"))
            )
        except:
            # Si el elemento se volvió obsoleto, recargar
            log_message("CODEM: Recargando página...")
            driver.refresh()
            time.sleep(3)
            dni_field = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.NAME, "ctl00$ContentPlaceHolder1$txtDoc"))
            )
        
        dni_field.clear()
        dni_field.send_keys(str(dni))
        
        # Hacer clic en Continuar
        btn = driver.find_element(By.NAME, "ctl00$ContentPlaceHolder1$Button1")
        btn.click()
        
        # Esperar resultado
        time.sleep(3)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        obra = soup.find('span', {'id': 'ContentPlaceHolder1_lblObraSocial'})
        if obra:
            resultado["Obra Social CODEM"] = obra.text.strip()
            log_message(f"CODEM: Obra social obtenida")
        familia = soup.find('span', {'id': 'ContentPlaceHolder1_lblFamiliares'})
        if familia:
            resultado["Familiares"] = familia.text.strip()
            log_message("CODEM: Familiares obtenidos")
    except Exception as e:
        log_message(f"CODEM Error: {str(e)[:50]}")
    return resultado

# ==================== LÓGICA PRINCIPAL ====================
if buscar_btn and dni_input:
    lista_dnis = [d.strip() for d in dni_input.split('\n') if d.strip()]
    if not lista_dnis:
        st.warning("Ingresá al menos un DNI.")
    else:
        resultados_sisa = []
        resultados_codem = []
        barra = st.progress(0)
        status_text = st.empty()
        
        # ---------- FASE 1: SISA ----------
        log_message("\n=== INICIANDO CONSULTAS SISA ===")
        driver_sisa = iniciar_driver()
        for i, dni in enumerate(lista_dnis):
            status_text.text(f"SISA: procesando DNI {dni}...")
            res = consultar_sisa_selenium(driver_sisa, dni, es_primer_dni=(i==0))
            resultados_sisa.append(res)
            barra.progress((i + 1) / (2 * len(lista_dnis)))  # Mitad de progreso
            if i < len(lista_dnis) - 1:
                time.sleep(random.uniform(2, 4))
        driver_sisa.quit()
        log_message("=== SISA FINALIZADO ===\n")
        
        # ---------- FASE 2: CODEM ----------
        log_message("\n=== INICIANDO CONSULTAS CODEM ===")
        driver_codem = iniciar_driver()
        for i, dni in enumerate(lista_dnis):
            status_text.text(f"CODEM: procesando DNI {dni}...")
            res = consultar_codem_selenium(driver_codem, dni, es_primer_dni_codem=(i==0))
            resultados_codem.append(res)
            barra.progress((len(lista_dnis) + i + 1) / (2 * len(lista_dnis)))  # Progreso completo
            if i < len(lista_dnis) - 1:
                time.sleep(random.uniform(2, 4))
        driver_codem.quit()
        log_message("=== CODEM FINALIZADO ===\n")
        
        # ---------- COMBINAR RESULTADOS ----------
        resultados_combinados = []
        for i, dni in enumerate(lista_dnis):
            fila = {
                "DNI": dni,
                **resultados_sisa[i],
                **resultados_codem[i]
            }
            resultados_combinados.append(fila)
        
        status_text.text("¡Proceso completado!")
        df = pd.DataFrame(resultados_combinados)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Descargar CSV",
            data=csv,
            file_name="resultados_completos.csv",
            mime="text/csv"
        )
