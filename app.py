import streamlit as st
import pandas as pd
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

st.set_page_config(page_title="HACER LA PC - PUCO", layout="wide")
st.title("💻 HACER LA PC - Consulta Masiva PUCO (SISA)")

# --- Estilo para la tabla (opcional) ---
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

# --- Contenedor para resultados ---
result_container = st.container()

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
    
    # Ruta del driver (en Streamlit Cloud suele estar en /usr/bin/chromedriver)
    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

def consultar_dni_selenium(dni):
    driver = iniciar_driver()
    resultado = {"DNI": dni, "Cobertura": "Error", "Beneficiario": "-", "Estado": "❌ Fallo"}
    
    try:
        # 1. Ir a SISA
        driver.get("https://sisa.msal.gov.ar/sisa/#sisa")
        time.sleep(5)  # Espera inicial por carga pesada
        
        # 2. Buscar y hacer clic en el módulo PUCO (puede estar en carrusel)
        try:
            # Intentar con texto exacto "PUCO"
            puco = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'PUCO')]"))
            )
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", puco)
            time.sleep(1)
            driver.execute_script("arguments[0].click();", puco)
        except TimeoutException:
            # Si no aparece, buscar por texto alternativo
            try:
                puco = driver.find_element(By.XPATH, "//*[contains(text(), 'consulta de cobertura')]")
                driver.execute_script("arguments[0].click();", puco)
            except:
                # Si falla, puede que ya esté en la página (a veces carga directo)
                pass
        
        # 3. Esperar campo DNI
        dni_field = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//input[contains(@name, 'dni') or contains(@id, 'dni')]"))
        )
        dni_field.clear()
        dni_field.send_keys(str(dni))
        
        # 4. Hacer clic en botón Buscar
        try:
            buscar_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Buscar')]")
        except NoSuchElementException:
            buscar_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        driver.execute_script("arguments[0].click();", buscar_btn)
        
        # 5. Esperar tabla de resultados
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//table"))
        )
        
        # 6. Extraer datos (primera fila de datos, asumiendo que la tabla tiene al menos dos columnas)
        filas = driver.find_elements(By.XPATH, "//table/tbody/tr")
        if len(filas) > 0:
            celdas = filas[0].find_elements(By.TAG_NAME, "td")
            if len(celdas) >= 2:
                cobertura = celdas[0].text.strip()
                beneficiario = celdas[1].text.strip()
                resultado = {"DNI": dni, "Cobertura": cobertura, "Beneficiario": beneficiario, "Estado": "✅ OK"}
            else:
                resultado["Estado"] = "⚠️ Sin datos suficientes"
        else:
            resultado["Estado"] = "❌ No encontrado"
            
    except Exception as e:
        resultado["Estado"] = f"Error: {str(e)[:50]}"
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
            # Pausa entre consultas para no saturar
            time.sleep(1)
        
        status_text.text("¡Proceso completado!")
        
        # Mostrar resultados
        df = pd.DataFrame(resultados)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Botón de descarga
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Descargar CSV",
            data=csv,
            file_name="resultados_puco.csv",
            mime="text/csv"
        )
