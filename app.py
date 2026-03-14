import streamlit as st
import pandas as pd
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

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

def consultar_dni_selenium(dni, intento=1):
    driver = None
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
        driver = iniciar_driver()
        log_message(f"Iniciando consulta para DNI {dni} (intento {intento})")
        
        # --- 1. Ir a SISA y esperar que cargue el módulo PUCO ---
        driver.get("https://sisa.msal.gov.ar/sisa/#sisa")
        log_message("Esperando que aparezca el módulo PUCO...")
        try:
            puco = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'PUCO')]"))
            )
        except TimeoutException:
            # Si no aparece, intentar con texto alternativo
            puco = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'consulta de cobertura')]"))
            )
        
        pausa = random.uniform(1, 3)
        time.sleep(pausa)
        log_message(f"Módulo PUCO encontrado, espera humana de {pausa:.1f}s.")
        
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", puco)
        time.sleep(random.uniform(0.3, 0.8))
        driver.execute_script("arguments[0].click();", puco)
        log_message("Módulo PUCO clickeado.")
        
        # --- 2. Esperar que aparezca el campo DNI (con reintentos) ---
        log_message("Esperando campo DNI...")
        dni_field = None
        selectores_dni = [
            "//input[contains(@name, 'dni')]",
            "//input[contains(@id, 'dni')]",
            "//input[@type='text' and contains(@placeholder, 'DNI')]",
            "//input[contains(@class, 'dni')]"
        ]
        
        for intento_dni in range(3):
            for selector in selectores_dni:
                try:
                    dni_field = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    log_message(f"Campo DNI encontrado con selector: {selector}")
                    break
                except:
                    continue
            if dni_field:
                break
            log_message(f"Reintentando búsqueda de campo DNI ({intento_dni+1}/3)...")
            time.sleep(2)
        
        if not dni_field:
            # Último recurso: buscar cualquier input visible
            inputs = driver.find_elements(By.TAG_NAME, "input")
            for inp in inputs:
                if inp.is_displayed() and inp.get_attribute("type") in ["text", "search"]:
                    dni_field = inp
                    log_message("Campo DNI encontrado como input visible.")
                    break
        
        if not dni_field:
            raise Exception("No se encontró el campo DNI después de varios intentos.")
        
        pausa = random.uniform(0.5, 1.5)
        time.sleep(pausa)
        log_message(f"Campo DNI listo, espera de {pausa:.1f}s.")
        
        dni_field.clear()
        dni_field.send_keys(str(dni))
        log_message("DNI ingresado.")
        
        # --- 3. Enviar ENTER ---
        pausa = random.uniform(0.3, 0.7)
        time.sleep(pausa)
        dni_field.send_keys(Keys.RETURN)
        log_message("Enter enviado.")
        
        # --- 4. Esperar que aparezca el DNI en alguna celda (resultados) ---
        log_message("Esperando resultados...")
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, f"//td[contains(text(), '{dni}')]"))
            )
        except TimeoutException:
            body_text = driver.find_element(By.TAG_NAME, "body").text
            if "no se encontraron" in body_text.lower() or "sin resultados" in body_text.lower():
                resultado["Estado"] = "❌ No encontrado"
                log_message("El sistema indica que no hay resultados.")
                return resultado
            else:
                log_message("Esperando un poco más...")
                time.sleep(3)
        
        time.sleep(random.uniform(1, 2))
        
        # --- 5. Buscar la fila que contiene el DNI exacto ---
        tablas = driver.find_elements(By.XPATH, "//table")
        log_message(f"Se encontraron {len(tablas)} tablas.")
        
        fila_dni = None
        for tabla in tablas:
            celdas_dni = tabla.find_elements(By.XPATH, f".//td[contains(text(), '{dni}')]")
            for celda in celdas_dni:
                texto_celda = celda.text.strip()
                if texto_celda == str(dni) or (texto_celda.isdigit() and len(texto_celda) in (7,8)):
                    fila_dni = celda.find_element(By.XPATH, "..")
                    log_message("Fila con DNI encontrada.")
                    break
            if fila_dni:
                break
        
        if not fila_dni:
            raise Exception("No se encontró fila con el DNI.")
        
        # --- 6. Extraer todas las celdas de la fila ---
        celdas = fila_dni.find_elements(By.TAG_NAME, "td")
        log_message(f"La fila tiene {len(celdas)} celdas.")
        
        if len(celdas) >= 1:
            resultado["TipoDoc"] = celdas[0].text.strip()
        if len(celdas) >= 2:
            resultado["NroDoc"] = celdas[1].text.strip()
        if len(celdas) >= 3:
            resultado["Sexo"] = celdas[2].text.strip()
        if len(celdas) >= 4:
            resultado["Cobertura Social"] = celdas[3].text.strip()
        if len(celdas) >= 5:
            resultado["Denominación"] = celdas[4].text.strip()
        
        resultado["Estado"] = "✅ OK"
        log_message("Datos extraídos correctamente.")
        
    except (TimeoutException, NoSuchElementException, WebDriverException, Exception) as e:
        error_msg = str(e)[:100]
        resultado["Estado"] = f"Error: {error_msg}"
        log_message(f"❌ Error en intento {intento}: {error_msg}")
        
        # Capturar pantalla si el driver sigue activo
        if driver:
            try:
                screenshot = driver.get_screenshot_as_png()
                st.image(screenshot, caption=f"Error en DNI {dni} (intento {intento})", width=400)
            except:
                pass
        
        # Reintentar si es el primer intento
        if intento < 2:
            log_message("Reintentando consulta...")
            time.sleep(3)
            return consultar_dni_selenium(dni, intento+1)
        
    finally:
        if driver:
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
            # Pausa aleatoria entre DNIs (1-3 segundos)
            if i < len(lista_dnis) - 1:
                pausa = random.uniform(1, 3)
                log_message(f"Espera entre DNIs de {pausa:.1f}s.")
                time.sleep(pausa)
        
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
