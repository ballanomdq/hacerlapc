import streamlit as st
import pandas as pd
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Configuración de la página
st.set_page_config(page_title="HACER LA PC - PUCO", layout="wide")
st.title("💻 HACER LA PC - Consulta PUCO Automática")
st.markdown("---")

# Entrada de DNIs
dni_input = st.text_area("📋 Ingresá los DNIs (uno por línea):", height=150, 
                         placeholder="Ejemplo:\n25131361\n25808007")
buscar_btn = st.button("🚀 Consultar Ahora", type="primary")

def iniciar_driver():
    """Configura el driver de Chrome para modo headless en Streamlit Cloud"""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-setuid-sandbox")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=options)
    return driver

def consultar_dni_con_selenium(dni):
    """Función que hace toda la navegación para un DNI"""
    driver = iniciar_driver()
    resultado = {"DNI": dni, "Cobertura": "Error", "Beneficiario": "-", "Estado": "❌ Fallo"}
    
    try:
        # 1. Ir a SISA
        driver.get("https://sisa.msal.gov.ar/sisa/#sisa")
        time.sleep(5)  # Espera carga inicial
        
        # 2. Buscar y hacer clic en el módulo PUCO
        try:
            # Intentar con texto "PUCO"
            puco = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'PUCO')]"))
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", puco)
            time.sleep(1)
            driver.execute_script("arguments[0].click();", puco)
        except TimeoutException:
            # Si no, buscar por "consulta de cobertura"
            puco = driver.find_element(By.XPATH, "//*[contains(text(), 'consulta de cobertura')]")
            driver.execute_script("arguments[0].click();", puco)
        
        # 3. Esperar campo DNI
        dni_field = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//input[contains(@name, 'dni') or contains(@id, 'dni')]"))
        )
        dni_field.clear()
        dni_field.send_keys(str(dni))
        
        # 4. Hacer clic en Buscar
        buscar = driver.find_element(By.XPATH, "//button[contains(text(), 'Buscar') or @type='submit']")
        driver.execute_script("arguments[0].click();", buscar)
        
        # 5. Esperar tabla de resultados
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//table"))
        )
        
        # 6. Extraer datos de la primera fila de la tabla
        filas = driver.find_elements(By.XPATH, "//table/tbody/tr")
        if len(filas) > 0:
            celdas = filas[0].find_elements(By.TAG_NAME, "td")
            if len(celdas) >= 2:
                cobertura = celdas[0].text.strip()
                beneficiario = celdas[1].text.strip()
                resultado = {
                    "DNI": dni,
                    "Cobertura": cobertura,
                    "Beneficiario": beneficiario,
                    "Estado": "✅ OK"
                }
            else:
                resultado["Estado"] = "⚠️ Sin datos en tabla"
        else:
            resultado["Estado"] = "❌ No se encontraron resultados"
            
    except Exception as e:
        resultado["Estado"] = f"Error: {str(e)[:50]}"
    finally:
        driver.quit()
    
    return resultado

# Lógica principal
if buscar_btn and dni_input:
    dnis = [d.strip() for d in dni_input.split('\n') if d.strip()]
    if not dnis:
        st.warning("Ingresá al menos un DNI.")
    else:
        resultados = []
        barra = st.progress(0)
        status_text = st.empty()
        
        for i, dni in enumerate(dnis):
            status_text.text(f"Consultando DNI {dni}...")
            resultados.append(consultar_dni_con_selenium(dni))
            barra.progress((i + 1) / len(dnis))
            time.sleep(1)  # Pausa entre consultas
        
        status_text.text("✅ Consultas finalizadas")
        
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
