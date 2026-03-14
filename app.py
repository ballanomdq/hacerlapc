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
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

st.set_page_config(page_title="HACER LA PC - PUCO", layout="wide")
st.title("💻 HACER LA PC - Consulta Rápida de Datos PUCO (SISA)")

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
    return driver

def esperar_campo_dni(driver):
    """Reintenta hasta encontrar el campo DNI, con refresh si es necesario."""
    for intento in range(3):
        try:
            selectores = [
                "//input[contains(@name, 'dni')]",
                "//input[contains(@id, 'dni')]",
                "//input[@type='text' and contains(@placeholder, 'DNI')]",
                "//input[contains(@class, 'dni')]"
            ]
            for selector in selectores:
                try:
                    campo = WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    log_message("Campo DNI encontrado.")
                    return campo
                except:
                    continue
            # Si no se encontró, buscar cualquier input visible
            inputs = driver.find_elements(By.TAG_NAME, "input")
            for inp in inputs:
                if inp.is_displayed() and inp.get_attribute("type") in ["text", "search"]:
                    log_message("Campo DNI encontrado como input visible.")
                    return inp
        except:
            pass
        
        log_message(f"Reintentando búsqueda de campo DNI ({intento+1}/3)...")
        time.sleep(2)
    
    # Si falla, refrescar página y esperar de nuevo
    log_message("Refrescando página...")
    driver.refresh()
    time.sleep(3)
    return None

def extraer_datos_fila(driver, dni):
    """Busca la fila que contiene el DNI y extrae todas las celdas."""
    tablas = driver.find_elements(By.XPATH, "//table")
    log_message(f"Se encontraron {len(tablas)} tablas.")
    
    for tabla in tablas:
        celdas_dni = tabla.find_elements(By.XPATH, f".//td[contains(text(), '{dni}')]")
        for celda in celdas_dni:
            texto = celda.text.strip()
            if texto == str(dni) or (texto.isdigit() and len(texto) in (7,8)):
                fila = celda.find_element(By.XPATH, "..")
                celdas = fila.find_elements(By.TAG_NAME, "td")
                log_message(f"Fila encontrada con {len(celdas)} celdas.")
                return celdas
    return None

# --- Lógica principal (un solo driver para todos los DNIs) ---
if buscar_btn and dni_input:
    lista_dnis = [d.strip() for d in dni_input.split('\n') if d.strip()]
    if not lista_dnis:
        st.warning("Ingresá al menos un DNI.")
    else:
        # Iniciar driver una sola vez
        driver = iniciar_driver()
        resultados = []
        barra = st.progress(0)
        status_text = st.empty()
        campo_dni = None
        primer_dni = True

        for i, dni in enumerate(lista_dnis):
            status_text.text(f"Consultando DNI {dni}...")
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
                if primer_dni:
                    # ---- Primer DNI: navegación completa ----
                    log_message(f"Iniciando consulta para DNI {dni}")
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
                    
                    # Esperar campo DNI
                    campo_dni = esperar_campo_dni(driver)
                    if not campo_dni:
                        raise Exception("No se pudo obtener el campo DNI.")
                    
                    primer_dni = False
                else:
                    # ---- DNIs siguientes: solo usar el campo existente ----
                    log_message(f"Usando sesión existente para DNI {dni}")
                    if not campo_dni:
                        # Si por alguna razón se perdió el campo, reintentar
                        campo_dni = esperar_campo_dni(driver)
                        if not campo_dni:
                            raise Exception("Campo DNI no disponible.")
                
                # --- Ingresar DNI y enviar ENTER ---
                campo_dni.clear()
                time.sleep(random.uniform(0.2, 0.5))
                campo_dni.send_keys(str(dni))
                time.sleep(random.uniform(0.3, 0.7))
                campo_dni.send_keys(Keys.RETURN)
                log_message("Enter enviado.")
                
                # --- Esperar resultados ---
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, f"//td[contains(text(), '{dni}')]"))
                    )
                except TimeoutException:
                    body = driver.find_element(By.TAG_NAME, "body").text
                    if "no se encontraron" in body.lower() or "sin resultados" in body.lower():
                        resultado["Estado"] = "❌ No encontrado"
                        log_message("DNI no encontrado.")
                        resultados.append(resultado)
                        barra.progress((i + 1) / len(lista_dnis))
                        continue
                    else:
                        log_message("Esperando un poco más...")
                        time.sleep(2)
                
                time.sleep(random.uniform(0.5, 1))
                
                # --- Extraer datos ---
                celdas = extraer_datos_fila(driver, dni)
                if celdas:
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
                else:
                    resultado["Estado"] = "❌ No se encontró fila con DNI"
                    log_message("No se encontró la fila del DNI.")
                
            except Exception as e:
                error_msg = str(e)[:100]
                resultado["Estado"] = f"Error: {error_msg}"
                log_message(f"❌ Error: {error_msg}")
                
                # Si el error es grave, forzar refresh para el próximo DNI
                try:
                    driver.refresh()
                    time.sleep(3)
                    campo_dni = esperar_campo_dni(driver)
                except:
                    campo_dni = None
            
            resultados.append(resultado)
            barra.progress((i + 1) / len(lista_dnis))
            
            # Pausa aleatoria entre DNIs (1-2 segundos)
            if i < len(lista_dnis) - 1:
                pausa = random.uniform(1, 2)
                log_message(f"Espera entre DNIs de {pausa:.1f}s.")
                time.sleep(pausa)
        
        # Cerrar driver al final
        driver.quit()
        
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
