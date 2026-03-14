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

# Inicializar selectores aprendidos
if 'codem_selector_dni' not in st.session_state:
    st.session_state.codem_selector_dni = None
    st.session_state.codem_selector_btn = None

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
    driver.set_page_load_timeout(20)
    return driver

# ==================== FUNCIÓN SISA ====================
def consultar_sisa(driver, dni, es_primer_dni):
    resultado = {"TipoDoc": "", "NroDoc": "", "Sexo": "", "Cobertura SISA": "", "Denominación": ""}
    try:
        if es_primer_dni:
            log_message(f"\n🔵 SISA: Iniciando para DNI {dni}")
            driver.get("https://sisa.msal.gov.ar/sisa/#sisa")
            time.sleep(3)
            
            # Buscar PUCO (con timeout corto)
            try:
                puco = WebDriverWait(driver, 8).until(
                    EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'PUCO')]"))
                )
            except:
                try:
                    puco = driver.find_element(By.XPATH, "//*[contains(text(), 'consulta de cobertura')]")
                except:
                    log_message("SISA: No se encontró PUCO")
                    return resultado
            
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", puco)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", puco)
            log_message("SISA: PUCO clickeado")
            time.sleep(2)
        
        # Campo DNI
        campo_dni = None
        for intento in range(2):
            try:
                campo_dni = WebDriverWait(driver, 4).until(
                    EC.element_to_be_clickable((By.XPATH, "//input[contains(@name, 'dni')]"))
                )
                break
            except:
                time.sleep(1)
        if not campo_dni:
            log_message("SISA: No se encontró campo DNI")
            return resultado
        
        campo_dni.clear()
        campo_dni.send_keys(str(dni))
        time.sleep(0.3)
        campo_dni.send_keys(Keys.RETURN)
        
        # Esperar resultados (timeout corto)
        try:
            WebDriverWait(driver, 6).until(
                EC.presence_of_element_located((By.XPATH, f"//td[contains(text(), '{dni}')]"))
            )
        except:
            log_message("SISA: No hubo resultados")
            return resultado
        
        time.sleep(1)
        # Extraer datos (simplificado)
        try:
            fila = driver.find_element(By.XPATH, f"//td[contains(text(), '{dni}')]/..")
            celdas = fila.find_elements(By.TAG_NAME, "td")
            if len(celdas) >= 5:
                resultado["TipoDoc"] = celdas[0].text.strip()
                resultado["NroDoc"] = celdas[1].text.strip()
                resultado["Sexo"] = celdas[2].text.strip()
                resultado["Cobertura SISA"] = celdas[3].text.strip()
                resultado["Denominación"] = celdas[4].text.strip()
                log_message("SISA: Datos OK")
        except:
            pass
    except Exception as e:
        log_message(f"SISA Error: {str(e)[:50]}")
    return resultado

# ==================== FUNCIÓN CODEM CON MAPEO Y PROTECCIÓN ====================
def consultar_codem(driver, dni, es_primer_dni):
    resultado = {"Obra Social CODEM": "", "Familiares": ""}
    try:
        if es_primer_dni:
            log_message(f"\n🟢 CODEM: Iniciando para DNI {dni}")
            driver.get("https://servicioswww.anses.gob.ar/ooss2/")
            time.sleep(2)
            
            # MAPEO: buscar campo DNI (con timeout)
            log_message("🔍 Buscando campo DNI...")
            campo_dni = None
            selectores_prueba = [
                (By.NAME, "ctl00$ContentPlaceHolder1$txtDoc"),
                (By.ID, "ContentPlaceHolder1_txtDoc"),
                (By.XPATH, "//input[contains(@name, 'txtDoc')]"),
                (By.XPATH, "//input[contains(@id, 'txtDoc')]"),
                (By.XPATH, "//input[contains(@placeholder, 'DNI')]"),
            ]
            for by, selector in selectores_prueba:
                try:
                    campo_dni = WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located((by, selector))
                    )
                    # Guardar selector
                    st.session_state.codem_selector_dni = (by, selector)
                    log_message(f"✅ Campo DNI encontrado con: {selector}")
                    break
                except:
                    continue
            
            if not campo_dni:
                # Último recurso: primer input visible
                inputs = driver.find_elements(By.TAG_NAME, "input")
                for inp in inputs:
                    if inp.is_displayed():
                        campo_dni = inp
                        # Generar XPath simple
                        xpath = f"//input[@name='{inp.get_attribute('name')}']" if inp.get_attribute('name') else None
                        if xpath:
                            st.session_state.codem_selector_dni = (By.XPATH, xpath)
                        log_message("✅ Campo DNI encontrado (primer input)")
                        break
            
            if not campo_dni:
                log_message("❌ No se pudo encontrar campo DNI")
                return resultado
            
            # MAPEO: buscar botón
            log_message("🔍 Buscando botón Continuar...")
            boton = None
            selectores_btn = [
                (By.NAME, "ctl00$ContentPlaceHolder1$Button1"),
                (By.ID, "ContentPlaceHolder1_Button1"),
                (By.XPATH, "//input[@type='submit']"),
                (By.XPATH, "//button[@type='submit']"),
            ]
            for by, selector in selectores_btn:
                try:
                    boton = WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((by, selector))
                    )
                    st.session_state.codem_selector_btn = (by, selector)
                    log_message(f"✅ Botón encontrado con: {selector}")
                    break
                except:
                    continue
            
            if not boton:
                log_message("❌ No se encontró botón Continuar")
                return resultado
        
        # --- Usar selectores aprendidos ---
        if not st.session_state.codem_selector_dni or not st.session_state.codem_selector_btn:
            log_message("CODEM: No hay selectores guardados, abortando")
            return resultado
        
        # Re-localizar elementos (pueden haberse vuelto obsoletos)
        try:
            campo_dni = driver.find_element(*st.session_state.codem_selector_dni)
        except:
            log_message("CODEM: Selector DNI obsoleto, reiniciando")
            st.session_state.codem_selector_dni = None
            return resultado
        
        campo_dni.clear()
        campo_dni.send_keys(str(dni))
        
        try:
            boton = driver.find_element(*st.session_state.codem_selector_btn)
        except:
            log_message("CODEM: Selector botón obsoleto, reiniciando")
            st.session_state.codem_selector_btn = None
            return resultado
        
        boton.click()
        
        # Esperar resultado (máx 6 segundos)
        try:
            WebDriverWait(driver, 6).until(
                EC.presence_of_element_located((By.ID, "ContentPlaceHolder1_lblObraSocial"))
            )
        except TimeoutException:
            log_message("CODEM: No apareció resultado")
            return resultado
        
        # Extraer datos
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        obra = soup.find('span', {'id': 'ContentPlaceHolder1_lblObraSocial'})
        if obra:
            resultado["Obra Social CODEM"] = obra.text.strip()
        familia = soup.find('span', {'id': 'ContentPlaceHolder1_lblFamiliares'})
        if familia:
            resultado["Familiares"] = familia.text.strip()
        
        log_message(f"CODEM: Obra social obtenida")
        
    except Exception as e:
        log_message(f"CODEM Error: {str(e)[:50]}")
        # Reiniciar selectores para el próximo intento
        st.session_state.codem_selector_dni = None
        st.session_state.codem_selector_btn = None
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
        
        # FASE 1: SISA
        estado.info("🔄 Consultas SISA...")
        driver_sisa = iniciar_driver()
        for i, dni in enumerate(lista_dnis):
            estado.text(f"SISA: {dni} ({i+1}/{len(lista_dnis)})")
            with st.spinner("Procesando SISA..."):
                res = consultar_sisa(driver_sisa, dni, es_primer_dni=(i==0))
            resultados_sisa.append(res)
            progreso.progress((i + 1) / (2 * len(lista_dnis)))
            time.sleep(random.uniform(1, 2))
        driver_sisa.quit()
        
        # FASE 2: CODEM
        estado.info("🔄 Consultas CODEM...")
        driver_codem = iniciar_driver()
        for i, dni in enumerate(lista_dnis):
            estado.text(f"CODEM: {dni} ({i+1}/{len(lista_dnis)})")
            with st.spinner("Procesando CODEM..."):
                res = consultar_codem(driver_codem, dni, es_primer_dni=(i==0))
            resultados_codem.append(res)
            progreso.progress((len(lista_dnis) + i + 1) / (2 * len(lista_dnis)))
            time.sleep(random.uniform(1, 2))
        driver_codem.quit()
        
        estado.success("✅ Completado!")
        # Combinar
        combinados = []
        for i, dni in enumerate(lista_dnis):
            fila = {"DNI": dni, **resultados_sisa[i], **resultados_codem[i]}
            combinados.append(fila)
        
        df = pd.DataFrame(combinaos)
        st.dataframe(df, use_container_width=True, hide_index=True)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Descargar CSV", csv, "resultados.csv")
