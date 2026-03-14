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

# ==================== FUNCIÓN SISA (INTACTA) ====================
def consultar_sisa(driver, dni, es_primer_dni):
    resultado = {"TipoDoc": "", "NroDoc": "", "Sexo": "", "Cobertura SISA": "", "Denominación": ""}
    try:
        if es_primer_dni:
            log_message(f"\n🔵 SISA: Iniciando para DNI {dni}")
            driver.get("https://sisa.msal.gov.ar/sisa/#sisa")
            time.sleep(3)
            
            # Buscar PUCO
            puco = None
            selectores_puco = [
                (By.XPATH, "//*[contains(text(), 'PUCO')]"),
                (By.XPATH, "//*[contains(text(), 'consulta de cobertura')]")
            ]
            for by, selector in selectores_puco:
                try:
                    puco = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((by, selector)))
                    log_message(f"SISA: Módulo PUCO encontrado con: {selector}")
                    break
                except:
                    continue
            if not puco:
                log_message("SISA: No se encontró módulo PUCO")
                return resultado
            
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", puco)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", puco)
            log_message("SISA: PUCO clickeado")
            time.sleep(2)
        
        # Campo DNI (múltiples selectores)
        campo_dni = None
        selectores_dni = [
            (By.XPATH, "//input[contains(@name, 'dni')]"),
            (By.XPATH, "//input[contains(@id, 'dni')]"),
            (By.XPATH, "//input[@type='text' and contains(@placeholder, 'DNI')]"),
            (By.TAG_NAME, "input")
        ]
        for by, selector in selectores_dni:
            try:
                campo_dni = WebDriverWait(driver, 4).until(EC.element_to_be_clickable((by, selector)))
                log_message(f"SISA: Campo DNI encontrado con: {selector}")
                break
            except:
                continue
        if not campo_dni:
            log_message("SISA: No se encontró campo DNI")
            return resultado
        
        campo_dni.clear()
        campo_dni.send_keys(str(dni))
        time.sleep(0.3)
        campo_dni.send_keys(Keys.RETURN)
        
        # Esperar resultados
        try:
            WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.XPATH, f"//td[contains(text(), '{dni}')]"))
            )
        except TimeoutException:
            log_message("SISA: No se detectaron resultados")
            return resultado
        
        time.sleep(1)
        # Extraer fila
        try:
            fila = driver.find_element(By.XPATH, f"//td[contains(text(), '{dni}')]/..")
            celdas = fila.find_elements(By.TAG_NAME, "td")
            if len(celdas) >= 5:
                resultado["TipoDoc"] = celdas[0].text.strip()
                resultado["NroDoc"] = celdas[1].text.strip()
                resultado["Sexo"] = celdas[2].text.strip()
                resultado["Cobertura SISA"] = celdas[3].text.strip()
                resultado["Denominación"] = celdas[4].text.strip()
                log_message("SISA: Datos extraídos OK")
        except Exception as e:
            log_message(f"SISA: Error al extraer datos: {str(e)[:50]}")
    except Exception as e:
        log_message(f"SISA Error: {str(e)[:50]}")
    return resultado

# ==================== FUNCIÓN CODEM (MEJORADA CON SUGERENCIAS DE GEMINI) ====================
def consultar_codem(driver, dni, es_primer_dni):
    resultado = {"Obra Social CODEM": "", "Familiares": ""}
    try:
        # Recargar la página en cada DNI (ANSES es inestable si se reusa el formulario)
        driver.get("https://servicioswww.anses.gob.ar/ooss2/")
        time.sleep(3)
        
        # 1. Buscar campo DNI con selector genérico
        try:
            campo_dni = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='text'], .form-control"))
            )
            log_message("✅ CODEM: Campo DNI localizado")
        except TimeoutException:
            log_message("❌ CODEM: No se encontró campo DNI")
            return resultado
        
        # 2. Ingresar DNI (con JavaScript para mayor seguridad)
        driver.execute_script("arguments[0].value = '';", campo_dni)
        campo_dni.send_keys(str(dni))
        time.sleep(0.5)
        
        # 3. Buscar y clickear botón Continuar (con JavaScript)
        try:
            boton = driver.find_element(By.XPATH, "//input[@value='Continuar']|//input[contains(@id, 'Button1')]")
            driver.execute_script("arguments[0].click();", boton)
            log_message("✅ CODEM: Botón Continuar clickeado")
        except:
            log_message("❌ CODEM: No se encontró botón Continuar")
            return resultado
        
        # 4. Esperar resultado (buscando cualquier elemento cuyo ID termine en 'lblObraSocial')
        try:
            WebDriverWait(driver, 7).until(
                EC.presence_of_element_located((By.XPATH, "//*[contains(@id, 'lblObraSocial')]"))
            )
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            obra = soup.find(id=lambda x: x and x.endswith('lblObraSocial'))
            if obra and obra.text.strip():
                resultado["Obra Social CODEM"] = obra.text.strip()
                log_message(f"✅ CODEM: {obra.text.strip()[:30]}...")
            else:
                resultado["Obra Social CODEM"] = "Sin Obra Social"
            
            familia = soup.find(id=lambda x: x and x.endswith('lblFamiliares'))
            if familia:
                resultado["Familiares"] = familia.text.strip()
                
        except TimeoutException:
            # Verificar si la página indica DNI no encontrado
            if "no existe" in driver.page_source.lower() or "error" in driver.page_source.lower():
                resultado["Obra Social CODEM"] = "DNI no encontrado en ANSES"
                log_message("⚠️ CODEM: DNI no encontrado")
            else:
                log_message("⚠️ CODEM: Tiempo agotado para resultado")
                
    except Exception as e:
        log_message(f"❌ CODEM Error: {str(e)[:50]}")
    
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
            time.sleep(random.uniform(2, 4))  # Pausa mayor para evitar bloqueo de ANSES
        driver_codem.quit()
        
        estado.success("✅ Proceso completado!")
        # Combinar resultados
        combinados = []
        for i, dni in enumerate(lista_dnis):
            fila = {"DNI": dni, **resultados_sisa[i], **resultados_codem[i]}
            combinados.append(fila)
        
        df = pd.DataFrame(combinados)
        st.dataframe(df, use_container_width=True, hide_index=True)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Descargar CSV", csv, "resultados.csv")
