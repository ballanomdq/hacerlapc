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
from selenium.common.exceptions import TimeoutException, NoSuchElementException

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
def iniciar_driver_sisa():
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

def consultar_sisa_selenium(driver, dni, es_primer_dni):
    resultado_sisa = {
        "TipoDoc": "",
        "NroDoc": "",
        "Sexo": "",
        "Cobertura SISA": "",
        "Denominación": ""
    }
    
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
            
            # Esperar campo DNI
            campo_dni = None
            for intento in range(3):
                try:
                    campo_dni = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//input[contains(@name, 'dni')]"))
                    )
                    break
                except:
                    time.sleep(2)
            if not campo_dni:
                raise Exception("No se encontró campo DNI en SISA")
        else:
            # Reutilizar el campo existente
            campo_dni = driver.find_element(By.XPATH, "//input[contains(@name, 'dni')]")
        
        # Ingresar DNI y enviar ENTER
        campo_dni.clear()
        time.sleep(random.uniform(0.2, 0.5))
        campo_dni.send_keys(str(dni))
        time.sleep(random.uniform(0.3, 0.7))
        campo_dni.send_keys(Keys.RETURN)
        log_message(f"SISA: Enter enviado para DNI {dni}")
        
        # Esperar resultados
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, f"//td[contains(text(), '{dni}')]"))
            )
        except TimeoutException:
            log_message("SISA: Tiempo de espera agotado")
            return resultado_sisa
        
        time.sleep(random.uniform(0.5, 1))
        
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
                        resultado_sisa["TipoDoc"] = celdas_fila[0].text.strip()
                        resultado_sisa["NroDoc"] = celdas_fila[1].text.strip()
                        resultado_sisa["Sexo"] = celdas_fila[2].text.strip()
                        resultado_sisa["Cobertura SISA"] = celdas_fila[3].text.strip()
                        resultado_sisa["Denominación"] = celdas_fila[4].text.strip()
                        log_message(f"SISA: Datos extraídos OK")
                        return resultado_sisa
        
        log_message("SISA: No se encontraron datos")
        return resultado_sisa
        
    except Exception as e:
        log_message(f"SISA Error: {str(e)[:50]}")
        return resultado_sisa

# ==================== FUNCIONES CODEM (REQUESTS) ====================
def consultar_codem_requests(dni):
    """
    Consulta el CODEM de ANSES usando requests (sin Selenium).
    Retorna obra social y familiares.
    """
    resultado_codem = {
        "Obra Social CODEM": "",
        "Familiares": ""
    }
    
    try:
        # URL del CODEM
        url = "https://servicioswww.anses.gob.ar/ooss2/"
        
        # Primera petición GET para obtener los campos ocultos
        session = requests.Session()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "es-US,es-419;q=0.9,es;q=0.8",
        }
        
        response = session.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extraer campos ocultos del ASP.NET
        viewstate = soup.find('input', {'name': '__VIEWSTATE'})
        viewstategen = soup.find('input', {'name': '__VIEWSTATEGENERATOR'})
        eventvalidation = soup.find('input', {'name': '__EVENTVALIDATION'})
        
        if not viewstate or not eventvalidation:
            log_message("CODEM: No se pudieron obtener campos del formulario")
            return resultado_codem
        
        # Preparar datos para el POST
        data = {
            '__LASTFOCUS': '',
            '__EVENTTARGET': '',
            '__EVENTARGUMENT': '',
            '__VIEWSTATE': viewstate['value'],
            '__VIEWSTATEGENERATOR': viewstategen['value'] if viewstategen else '',
            '__EVENTVALIDATION': eventvalidation['value'],
            'ctl00$ContentPlaceHolder1$txtDoc': str(dni),
            'ctl00$ContentPlaceHolder1$Button1': 'Continuar'
        }
        
        # Enviar POST
        headers_post = headers.copy()
        headers_post["Content-Type"] = "application/x-www-form-urlencoded"
        
        response_post = session.post(url, data=data, headers=headers_post, timeout=15)
        
        if response_post.status_code == 200:
            soup_result = BeautifulSoup(response_post.text, 'html.parser')
            
            # Buscar la obra social en el resultado
            obra_social_tag = soup_result.find('span', {'id': 'ContentPlaceHolder1_lblObraSocial'})
            if obra_social_tag:
                resultado_codem["Obra Social CODEM"] = obra_social_tag.text.strip()
                log_message(f"CODEM: Obra social obtenida: {resultado_codem['Obra Social CODEM']}")
            
            # Buscar familiares (si hay)
            familiares_tag = soup_result.find('span', {'id': 'ContentPlaceHolder1_lblFamiliares'})
            if familiares_tag:
                resultado_codem["Familiares"] = familiares_tag.text.strip()
                log_message("CODEM: Familiares obtenidos")
        else:
            log_message(f"CODEM: Error HTTP {response_post.status_code}")
            
    except Exception as e:
        log_message(f"CODEM Error: {str(e)[:50]}")
    
    return resultado_codem

# ==================== LÓGICA PRINCIPAL ====================
if buscar_btn and dni_input:
    lista_dnis = [d.strip() for d in dni_input.split('\n') if d.strip()]
    if not lista_dnis:
        st.warning("Ingresá al menos un DNI.")
    else:
        # Iniciar driver de SISA (solo una vez)
        driver_sisa = iniciar_driver_sisa()
        resultados = []
        barra = st.progress(0)
        status_text = st.empty()
        
        for i, dni in enumerate(lista_dnis):
            status_text.text(f"Procesando DNI {dni}...")
            
            # 1. Consultar SISA
            log_message(f"\n--- DNI {dni} ---")
            datos_sisa = consultar_sisa_selenium(driver_sisa, dni, es_primer_dni=(i==0))
            
            # 2. Consultar CODEM
            datos_codem = consultar_codem_requests(dni)
            
            # 3. Combinar resultados
            resultado_final = {
                "DNI": dni,
                **datos_sisa,
                **datos_codem
            }
            
            resultados.append(resultado_final)
            barra.progress((i + 1) / len(lista_dnis))
            
            # Pausa entre DNIs
            if i < len(lista_dnis) - 1:
                pausa = random.uniform(2, 4)
                log_message(f"Espera entre DNIs de {pausa:.1f}s")
                time.sleep(pausa)
        
        # Cerrar driver de SISA
        driver_sisa.quit()
        
        status_text.text("¡Proceso completado!")
        df = pd.DataFrame(resultados)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Descargar CSV",
            data=csv,
            file_name="resultados_completos.csv",
            mime="text/csv"
        )
