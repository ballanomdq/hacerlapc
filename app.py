import streamlit as st
import pandas as pd
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
import base64
import io

st.set_page_config(page_title="HACER LA PC - PUCO", layout="wide")
st.title("💻 HACER LA PC - Consulta Masiva PUCO (SISA)")

# --- Estilo ---
st.markdown("""
<style>
    .stDataFrame { border: 1px solid #38bdf8; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# --- Entrada de datos ---
with st.container():
    st.subheader("📋 Ingreso de DNI")
    dni_input = st.text_area("Escribí un DNI por línea:", height=150, placeholder="Ejemplo:\n25131361\n25808007")
    col1, col2 = st.columns([1,5])
    with col1:
        buscar_btn = st.button("🚀 Consultar Ahora", type="primary")

# --- Contenedor para resultados y logs ---
result_container = st.container()
log_container = st.expander("📋 Log de ejecución", expanded=False)

def log_message(msg):
    """Muestra mensajes en el expander de log."""
    log_container.markdown(f"- {msg}")

def iniciar_driver():
    """Configuración optimizada para Streamlit Cloud"""
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

def consultar_dni_selenium(dni):
    driver = iniciar_driver()
    resultado = {"DNI": dni, "Cobertura": "Error", "Beneficiario": "-", "Estado": "❌ Fallo"}
    
    try:
        log_message(f"Iniciando consulta para DNI {dni}")
        
        # 1. Ir a SISA
        driver.get("https://sisa.msal.gov.ar/sisa/#sisa")
        log_message("Página principal cargada, esperando 5 segundos...")
        time.sleep(5)
        
        # 2. Buscar el módulo PUCO (múltiples intentos)
        puco_encontrado = False
        intentos = 0
        while not puco_encontrado and intentos < 3:
            try:
                # Intentar con texto "PUCO"
                puco = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'PUCO')]"))
                )
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", puco)
                time.sleep(1)
                driver.execute_script("arguments[0].click();", puco)
                puco_encontrado = True
                log_message("Módulo PUCO encontrado y clickeado (texto 'PUCO').")
            except:
                try:
                    # Intentar con texto alternativo
                    puco = driver.find_element(By.XPATH, "//*[contains(text(), 'consulta de cobertura')]")
                    driver.execute_script("arguments[0].click();", puco)
                    puco_encontrado = True
                    log_message("Módulo PUCO encontrado (texto 'consulta de cobertura').")
                except:
                    intentos += 1
                    log_message(f"Intento {intentos} fallido, recargando página...")
                    driver.refresh()
                    time.sleep(3)
        
        if not puco_encontrado:
            raise Exception("No se pudo encontrar el módulo PUCO después de 3 intentos.")
        
        # 3. Esperar campo DNI
        log_message("Esperando campo DNI...")
        dni_field = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//input[contains(@name, 'dni') or contains(@id, 'dni')]"))
        )
        dni_field.clear()
        dni_field.send_keys(str(dni))
        log_message("DNI ingresado.")
        
        # 4. Hacer clic en botón Buscar
        log_message("Buscando botón 'Buscar'...")
        try:
            buscar_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Buscar')]"))
            )
        except:
            buscar_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        driver.execute_script("arguments[0].click();", buscar_btn)
        log_message("Botón 'Buscar' clickeado.")
        
        # 5. Esperar tabla de resultados
        log_message("Esperando resultados...")
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//table"))
        )
        log_message("Tabla de resultados encontrada.")
        
        # 6. Extraer datos (primera fila)
        filas = driver.find_elements(By.XPATH, "//table/tbody/tr")
        if len(filas) > 0:
            celdas = filas[0].find_elements(By.TAG_NAME, "td")
            if len(celdas) >= 2:
                cobertura = celdas[0].text.strip()
                beneficiario = celdas[1].text.strip()
                resultado = {"DNI": dni, "Cobertura": cobertura, "Beneficiario": beneficiario, "Estado": "✅ OK"}
                log_message(f"Datos extraídos: {cobertura} - {beneficiario}")
            else:
                resultado["Estado"] = "⚠️ Sin datos suficientes"
                log_message("La tabla no tiene suficientes columnas.")
        else:
            resultado["Estado"] = "❌ No encontrado"
            log_message("No se encontraron filas en la tabla.")
            
    except Exception as e:
        error_msg = str(e)[:100]
        resultado["Estado"] = f"Error: {error_msg}"
        log_message(f"❌ Error: {error_msg}")
        
        # Tomar screenshot para diagnóstico (se guarda en el log)
        try:
            screenshot = driver.get_screenshot_as_png()
            st.image(screenshot, caption=f"Error en DNI {dni}", width=400)
        except:
            pass
        
    finally:
        driver.quit()
    
    return resultado

# --- Lógica principal ---
if buscar_btn and dni_input:
    lista_dnis = [d.strip() for d in dni_input.split('\n') if d.strip()]
    if not lista_dnis:
        st.warning("Ingresá al menos un DNI.")
    else:
        resultados = []
        barra = st.progress(0)
        status_text = st.empty()
        
        for i, dni in enumerate(lista_dnis):
            status_text.text(f"Consultando DNI {dni}...")
            resultados.append(consultar_dni_selenium(dni))
            barra.progress((i + 1) / len(lista_dnis))
            time.sleep(2)  # Pausa entre consultas
        
        status_text.text("¡Proceso completado!")
        
        df = pd.DataFrame(resultados)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Descargar CSV",
            data=csv,
            file_name="resultados_puco.csv",
            mime="text/csv"
        )
