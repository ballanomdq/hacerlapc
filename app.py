def iniciar_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # --- CLAVE PARA CODEM: User-Agent real ---
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

def consultar_codem(driver, dni):
    resultado = {"Obra Social CODEM": "No encontrado", "Familiares": "0"}
    try:
        driver.get("https://servicioswww.anses.gob.ar/ooss2/")
        time.sleep(4) # Espera a que cargue el script de ANSES
        
        # 1. Buscar el campo DNI por múltiples vías (ID, Nombre o CSS)
        campo = None
        selectores = [
            "input[id*='txtDoc']", # Cualquiera que contenga txtDoc
            "input[name*='txtDoc']",
            "input.form-control"
        ]
        
        for sel in selectores:
            try:
                campo = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, sel)))
                if campo: break
            except: continue

        if campo:
            driver.execute_script("arguments[0].scrollIntoView(true);", campo)
            campo.clear()
            campo.send_keys(str(dni))
            time.sleep(0.5)
            
            # 2. Click en el botón Continuar
            boton = driver.find_element(By.CSS_SELECTOR, "input[type='submit'], input[id*='Button1']")
            driver.execute_script("arguments[0].click();", boton)
            
            # 3. Esperar a que el resultado aparezca
            # Buscamos el ID que contiene la Obra Social
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//*[contains(@id, 'lblObraSocial')]"))
            )
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            # Extracción flexible
            obra_elem = soup.find(id=lambda x: x and 'lblObraSocial' in x)
            fami_elem = soup.find(id=lambda x: x and 'lblFamiliares' in x)
            
            if obra_elem:
                resultado["Obra Social CODEM"] = obra_elem.text.strip()
            if fami_elem:
                resultado["Familiares"] = fami_elem.text.strip()
            
            log_message(f"✅ CODEM OK: {dni}")
        else:
            log_message(f"❌ CODEM: No se pudo hallar el input para {dni}")

    except Exception as e:
        # Si falla, revisamos si es que el DNI directamente no existe
        if "no existe" in driver.page_source.lower():
            resultado["Obra Social CODEM"] = "DNI Inexistente"
            log_message(f"⚠️ CODEM: DNI {dni} no existe en ANSES")
        else:
            log_message(f"❌ CODEM Error técnico: {str(e)[:40]}")
            
    return resultado
