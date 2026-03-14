def consultar_codem_selenium(driver, dni, es_primer_dni_codem):
    resultado = {"Obra Social CODEM": "", "Familiares": ""}
    try:
        if es_primer_dni_codem:
            log_message(f"CODEM: Iniciando para DNI {dni}")
            driver.get("https://servicioswww.anses.gob.ar/ooss2/")
            # Esperar a que cargue la página (presencia del body)
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(2)  # espera adicional para JS
        
        # Intentar encontrar el campo DNI con varios intentos y selectores alternativos
        campo_dni = None
        selectores = [
            (By.NAME, "ctl00$ContentPlaceHolder1$txtDoc"),
            (By.ID, "ContentPlaceHolder1_txtDoc"),
            (By.CSS_SELECTOR, "input[name*='txtDoc']"),
            (By.XPATH, "//input[contains(@id, 'txtDoc')]")
        ]
        
        for intento in range(3):
            for by, selector in selectores:
                try:
                    campo_dni = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((by, selector))
                    )
                    log_message(f"CODEM: Campo DNI encontrado con selector {selector}")
                    break
                except:
                    continue
            if campo_dni:
                break
            log_message(f"CODEM: Reintentando ({intento+1}/3)")
            time.sleep(2)
            # Si es el segundo intento, recargar
            if intento == 1:
                log_message("CODEM: Recargando página...")
                driver.refresh()
                time.sleep(3)
        
        if not campo_dni:
            raise Exception("No se encontró el campo DNI en CODEM")
        
        # Limpiar e ingresar DNI
        campo_dni.clear()
        campo_dni.send_keys(str(dni))
        
        # Buscar botón "Continuar"
        boton = None
        selectores_btn = [
            (By.NAME, "ctl00$ContentPlaceHolder1$Button1"),
            (By.ID, "ContentPlaceHolder1_Button1"),
            (By.XPATH, "//input[@type='submit' and contains(@value, 'Continuar')]"),
            (By.CSS_SELECTOR, "input[value='Continuar']")
        ]
        for by, selector in selectores_btn:
            try:
                boton = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((by, selector))
                )
                break
            except:
                continue
        
        if not boton:
            raise Exception("No se encontró el botón Continuar")
        
        boton.click()
        
        # Esperar resultado (puede aparecer un texto con la obra social)
        time.sleep(4)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        obra = soup.find('span', {'id': 'ContentPlaceHolder1_lblObraSocial'})
        if obra:
            resultado["Obra Social CODEM"] = obra.text.strip()
            log_message(f"CODEM: Obra social obtenida")
        familia = soup.find('span', {'id': 'ContentPlaceHolder1_lblFamiliares'})
        if familia:
            resultado["Familiares"] = familia.text.strip()
            log_message("CODEM: Familiares obtenidos")
            
    except Exception as e:
        log_message(f"CODEM Error (no crítico): {str(e)[:100]}")
        # No relanzamos la excepción para que el flujo continúe
    return resultado
