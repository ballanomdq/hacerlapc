import streamlit as st
import pandas as pd
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

st.set_page_config(page_title="HACER LA PC - PUCO", layout="wide")
st.title("💻 HACER LA PC - Consulta de Datos PUCO (SISA)")

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
    return driver

def consultar_dni_selenium(dni):
    driver = iniciar_driver()
    # Diccionario con todas las columnas que esperamos
    resultado = {
        "DNI": dni,
        "TipoDoc": "",
        "NroDoc": "",
        "Sexo": "",
        "Cobertura Social": "",
        "Denominación": "",
        "Estado": "❌ Fallo"
    }
    
    try:
        log_message(f"Iniciando consulta para DNI {dni}")
        
        # 1. Ir a SISA
        driver.get("https://sisa.msal.gov.ar/sisa/#sisa")
        log_message("Página principal cargada, esperando 8 segundos...")
        time.sleep(8)
        
        # 2. Buscar el módulo PUCO (con reintentos)
        puco_encontrado = False
        for intento in range(3):
            try:
                puco = WebDriverWait(driver, 15).until(
                    EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'PUCO')]"))
                )
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", puco)
                time.sleep(1)
                driver.execute_script("arguments[0].click();", puco)
                puco_encontrado = True
                log_message("Módulo PUCO clickeado.")
                break
            except:
                try:
                    puco = driver.find_element(By.XPATH, "//*[contains(text(), 'consulta de cobertura')]")
                    driver.execute_script("arguments[0].click();", puco)
                    puco_encontrado = True
                    log_message("Módulo PUCO clickeado (texto alternativo).")
                    break
                except:
                    log_message(f"Intento {intento+1} fallido. Recargando...")
                    driver.refresh()
                    time.sleep(5)
        
        if not puco_encontrado:
            raise Exception("No se pudo encontrar el módulo PUCO.")
        
        # 3. Esperar a que cargue el formulario
        log_message("Esperando 5 segundos para que cargue el formulario...")
        time.sleep(5)
        
        # 4. Buscar campo DNI
        log_message("Buscando campo DNI...")
        selectores_dni = [
            "//input[contains(@name, 'dni')]",
            "//input[contains(@id, 'dni')]",
            "//input[@type='text' and contains(@placeholder, 'DNI')]"
        ]
        
        dni_field = None
        for selector in selectores_dni:
            try:
                dni_field = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, selector))
                )
                log_message("Campo DNI encontrado.")
                break
            except:
                continue
        
        if not dni_field:
            inputs = driver.find_elements(By.TAG_NAME, "input")
            for inp in inputs:
                if inp.is_displayed() and inp.get_attribute("type") in ["text", "search"]:
                    dni_field = inp
                    log_message("Campo DNI encontrado como input visible.")
                    break
        
        if not dni_field:
            raise Exception("No se encontró el campo DNI.")
        
        # 5. Ingresar DNI y enviar ENTER (sin botón)
        dni_field.clear()
        dni_field.send_keys(str(dni))
        log_message("DNI ingresado, enviando ENTER...")
        dni_field.send_keys(Keys.RETURN)
        
        # 6. Esperar a que aparezca el DNI en alguna celda (resultados)
        log_message("Esperando resultados...")
        time.sleep(5)  # Tiempo para que cargue la tabla
        
        # 7. Buscar la tabla que contenga el DNI en una celda
        tablas = driver.find_elements(By.XPATH, "//table")
        log_message(f"Se encontraron {len(tablas)} tablas.")
        
        tabla_resultados = None
        fila_dni = None
        
        for tabla in tablas:
            # Buscar celdas que contengan el DNI exacto (como número, no como parte de texto largo)
            celdas_dni = tabla.find_elements(By.XPATH, f".//td[contains(text(), '{dni}')]")
            for celda in celdas_dni:
                # Verificar que el texto de la celda sea solo el DNI (sin caracteres extras)
                texto_celda = celda.text.strip()
                if texto_celda == str(dni) or texto_celda.isdigit() and len(texto_celda) in (7,8):
                    fila_dni = celda.find_element(By.XPATH, "..")
                    tabla_resultados = tabla
                    log_message("Fila con DNI encontrada.")
                    break
            if fila_dni:
                break
        
        if not fila_dni:
            # Fallback: buscar la primera fila con al menos 5 columnas
            for tabla in tablas:
                filas = tabla.find_elements(By.XPATH, ".//tr")
                for fila in filas:
                    celdas = fila.find_elements(By.TAG_NAME, "td")
                    if len(celdas) >= 5:
                        fila_dni = fila
                        tabla_resultados = tabla
                        log_message("Fila de datos encontrada (fallback).")
                        break
                if fila_dni:
                    break
        
        if not fila_dni:
            raise Exception("No se encontró ninguna fila con datos.")
        
        # 8. Extraer todas las celdas de la fila
        celdas = fila_dni.find_elements(By.TAG_NAME, "td")
        num_celdas = len(celdas)
        log_message(f"La fila tiene {num_celdas} celdas.")
        
        # Mapeo según el orden observado (puede variar, pero lo ajustamos)
        # Asumimos que las columnas son: TipoDoc, NroDoc, Sexo, Cobertura Social, Denominación
        # Si hay más columnas, las ignoramos, pero al menos tomamos las primeras 5
        if num_celdas >= 1:
            resultado["TipoDoc"] = celdas[0].text.strip()
        if num_celdas >= 2:
            resultado["NroDoc"] = celdas[1].text.strip()
        if num_celdas >= 3:
            resultado["Sexo"] = celdas[2].text.strip()
        if num_celdas >= 4:
            resultado["Cobertura Social"] = celdas[3].text.strip()
        if num_celdas >= 5:
            resultado["Denominación"] = celdas[4].text.strip()
        
        resultado["Estado"] = "✅ OK"
        log_message(f"Datos extraídos: {resultado}")
        
    except Exception as e:
        error_msg = str(e)[:100]
        resultado["Estado"] = f"Error: {error_msg}"
        log_message(f"❌ Error: {error_msg}")
        
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
            time.sleep(2)
        
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
