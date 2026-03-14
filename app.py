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

# ==================== FUNCIONES AUXILIARES ====================
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
    driver.set_page_load_timeout(30)
    return driver

# ==================== FUNCIÓN PARA ENCONTRAR ELEMENTOS CON MÚLTIPLES SELECTORES ====================
def encontrar_elemento(driver, selectores, timeout=5, descripcion="elemento"):
    """
    Intenta localizar un elemento usando una lista de selectores (By, selector).
    Retorna el elemento o None.
    """
    for by, selector in selectores:
        try:
            elemento = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((by, selector))
            )
            log_message(f"✅ {descripcion} encontrado con: {selector}")
            return elemento
        except:
            continue
    log_message(f"❌ No se encontró {descripcion} con ningún selector")
    return None

# ==================== FUNCIONES SISA ====================
def consultar_sisa(driver, dni, es_primer_dni):
    resultado = {"TipoDoc": "", "NroDoc": "", "Sexo": "", "Cobertura SISA": "", "Denominación": ""}
    try:
        if es_primer_dni:
            log_message(f"\n🔵 SISA: Iniciando para DNI {dni}")
            driver.get("https://sisa.msal.gov.ar/sisa/#sisa")
            time.sleep(3)
            
            # Selectores para el módulo PUCO
            selectores_puco = [
                (By.XPATH, "//*[contains(text(), 'PUCO')]"),
                (By.XPATH, "//*[contains(text(), 'consulta de cobertura')]"),
                (By.XPATH, "//*[contains(@title, 'PUCO')]"),
                (By.CSS_SELECTOR, "[class*='puco']")
            ]
            puco = encontrar_elemento(driver, selectores_puco, timeout=10, descripcion="módulo PUCO")
            if puco:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", puco)
                time.sleep(1)
                driver.execute_script("arguments[0].click();", puco)
                log_message("🖱️ Módulo PUCO clickeado")
                time.sleep(2)
            else:
                log_message("⚠️ No se encontró PUCO, pero se intentará continuar")
        
        # Selectores para el campo DNI en SISA
        selectores_dni_sisa = [
            (By.XPATH, "//input[contains(@name, 'dni')]"),
            (By.XPATH, "//input[contains(@id, 'dni')]"),
            (By.XPATH, "//input[@type='text' and contains(@placeholder, 'DNI')]"),
            (By.CSS_SELECTOR, "input[name*='dni']"),
            (By.CSS_SELECTOR, "input[id*='dni']"),
            (By.TAG_NAME, "input")  # último recurso, cualquier input
        ]
        campo_dni = encontrar_elemento(driver, selectores_dni_sisa, timeout=8, descripcion="campo DNI")
        if not campo_dni:
            log_message("SISA: No se encontró campo DNI")
            return resultado
        
        campo_dni.clear()
        campo_dni.send_keys(str(dni))
        time.sleep(0.5)
        campo_dni.send_keys(Keys.RETURN)
        log_message(f"⌨️ Enter enviado")
        
        # Esperar resultados
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, f"//td[contains(text(), '{dni}')]"))
            )
        except TimeoutException:
            log_message("SISA: No se detectaron resultados")
            return resultado
        
        time.sleep(1)
        
        # Buscar la fila con el DNI
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
                        log_message("📊 Datos SISA extraídos OK")
                        return resultado
        log_message("SISA: No se encontraron datos en tabla")
    except Exception as e:
        log_message(f"SISA Error: {str(e)[:100]}")
    return resultado

# ==================== FUNCIONES CODEM (MEJORADA) ====================
def consultar_codem(driver, dni, es_primer_dni):
    resultado = {"Obra Social CODEM": "", "Familiares": ""}
    try:
        if es_primer_dni:
            log_message(f"\n🟢 CODEM: Iniciando para DNI {dni}")
            driver.get("https://servicioswww.anses.gob.ar/ooss2/")
            time.sleep(3)
        
        # Selectores para campo DNI en CODEM
        selectores_dni_codem = [
            (By.NAME, "ctl00$ContentPlaceHolder1$txtDoc"),
            (By.ID, "ContentPlaceHolder1_txtDoc"),
            (By.CSS_SELECTOR, "input[name*='txtDoc']"),
            (By.XPATH, "//input[contains(@id, 'txtDoc')]"),
            (By.XPATH, "//input[contains(@name, 'txtDoc')]"),
            (By.TAG_NAME, "input")  # último recurso
        ]
        campo_dni = encontrar_elemento(driver, selectores_dni_codem, timeout=8, descripcion="campo DNI (CODEM)")
        
        if not campo_dni:
            # Si no aparece, refrescar y reintentar
            log_message("CODEM: Refrescando página...")
            driver.refresh()
            time.sleep(3)
            campo_dni = encontrar_elemento(driver, selectores_dni_codem, timeout=8, descripcion="campo DNI (CODEM) tras refresh")
            if not campo_dni:
                log_message("CODEM: No se encontró campo DNI")
                return resultado
        
        campo_dni.clear()
        campo_dni.send_keys(str(dni))
        
        # Selectores para botón Continuar
        selectores_btn = [
            (By.NAME, "ctl00$ContentPlaceHolder1$Button1"),
            (By.ID, "ContentPlaceHolder1_Button1"),
            (By.XPATH, "//input[@type='submit' and contains(@value, 'Continuar')]"),
            (By.CSS_SELECTOR, "input[value='Continuar']"),
            (By.XPATH, "//button[contains(text(), 'Continuar')]")
        ]
        boton = encontrar_elemento(driver, selectores_btn, timeout=5, descripcion="botón Continuar")
        if not boton:
            log_message("CODEM: No se encontró botón Continuar")
            return resultado
        
        boton.click()
        
        # Esperar a que aparezca el resultado (obra social)
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "ContentPlaceHolder1_lblObraSocial"))
            )
            log_message("CODEM: Resultado de obra social detectado")
        except TimeoutException:
            log_message("CODEM: No apareció el resultado de obra social")
            # Guardar HTML parcial para depuración
            html = driver.page_source[:500]
            log_message(f"HTML parcial: {html}")
            return resultado
        
        # Extraer con BeautifulSoup
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        obra = soup.find('span', {'id': 'ContentPlaceHolder1_lblObraSocial'})
        if obra:
            resultado["Obra Social CODEM"] = obra.text.strip()
            log_message(f"🏥 Obra social CODEM: {resultado['Obra Social CODEM']}")
        familia = soup.find('span', {'id': 'ContentPlaceHolder1_lblFamiliares'})
        if familia:
            resultado["Familiares"] = familia.text.strip()
            log_message(f"👨‍👩‍👧 Familiares: {resultado['Familiares']}")
    except Exception as e:
        log_message(f"CODEM Error: {str(e)[:100]}")
    return resultado

# ==================== LÓGICA PRINCIPAL ====================
if buscar_btn and dni_input:
    lista_dnis = [d.strip() for d in dni_input.split('\n') if d.strip()]
    if not lista_dnis:
        st.warning("Ingresá al menos un DNI.")
    else:
        resultados_sisa = []
        resultados_codem = []
        
        progreso = st.progress(0)
        estado = st.empty()
        
        # ---------- FASE 1: SISA ----------
        estado.info("🔄 Iniciando consultas en SISA...")
        driver_sisa = iniciar_driver()
        for i, dni in enumerate(lista_dnis):
            estado.text(f"SISA: consultando DNI {dni} ({i+1}/{len(lista_dnis)})")
            with st.spinner(f"SISA: procesando DNI {dni}..."):
                res = consultar_sisa(driver_sisa, dni, es_primer_dni=(i==0))
            resultados_sisa.append(res)
            progreso.progress((i + 1) / (2 * len(lista_dnis)))
            if i < len(lista_dnis) - 1:
                time.sleep(random.uniform(1, 2))
        driver_sisa.quit()
        
        # ---------- FASE 2: CODEM ----------
        estado.info("🔄 Iniciando consultas en CODEM...")
        driver_codem = iniciar_driver()
        for i, dni in enumerate(lista_dnis):
            estado.text(f"CODEM: consultando DNI {dni} ({i+1}/{len(lista_dnis)})")
            with st.spinner(f"CODEM: procesando DNI {dni}..."):
                res = consultar_codem(driver_codem, dni, es_primer_dni=(i==0))
            resultados_codem.append(res)
            progreso.progress((len(lista_dnis) + i + 1) / (2 * len(lista_dnis)))
            if i < len(lista_dnis) - 1:
                time.sleep(random.uniform(1, 2))
        driver_codem.quit()
        
        # ---------- COMBINAR Y MOSTRAR ----------
        estado.success("✅ Proceso completado!")
        combinados = []
        for i, dni in enumerate(lista_dnis):
            fila = {
                "DNI": dni,
                **resultados_sisa[i],
                **resultados_codem[i]
            }
            combinados.append(fila)
        
        df = pd.DataFrame(combinados)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Descargar CSV",
            data=csv,
            file_name="resultados_completos.csv",
            mime="text/csv"
        )
