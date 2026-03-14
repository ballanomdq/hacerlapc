def consultar_dni_selenium(dni):
    driver = iniciar_driver()
    resultado = {"DNI": dni, "Cobertura": "Error", "Beneficiario": "-", "Estado": "❌ Fallo"}
    
    try:
        log_message(f"Iniciando consulta para DNI {dni}")
        
        # 1. Ir a SISA
        driver.get("https://sisa.msal.gov.ar/sisa/#sisa")
        log_message("Página principal cargada, esperando 8 segundos...")
        time.sleep(8)
        
        # 2. Buscar el módulo PUCO
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
                log_message("Módulo PUCO clickeado (texto 'PUCO').")
                break
            except:
                try:
                    puco = driver.find_element(By.XPATH, "//*[contains(text(), 'consulta de cobertura')]")
                    driver.execute_script("arguments[0].click();", puco)
                    puco_encontrado = True
                    log_message("Módulo PUCO clickeado (texto 'consulta de cobertura').")
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
            "//input[@type='text' and contains(@placeholder, 'DNI')]",
            "//input[contains(@class, 'dni')]"
        ]
        
        dni_field = None
        for selector in selectores_dni:
            try:
                dni_field = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, selector))
                )
                log_message(f"Campo DNI encontrado con selector: {selector}")
                break
            except:
                continue
        
        if not dni_field:
            # Último recurso: buscar cualquier input visible
            inputs = driver.find_elements(By.TAG_NAME, "input")
            for inp in inputs:
                if inp.is_displayed() and inp.get_attribute("type") in ["text", "search"]:
                    dni_field = inp
                    log_message("Campo DNI encontrado como el primer input visible.")
                    break
        
        if not dni_field:
            raise Exception("No se encontró el campo DNI.")
        
        dni_field.clear()
        dni_field.send_keys(str(dni))
        log_message("DNI ingresado.")
        
        # 5. Buscar botón Buscar
        log_message("Buscando botón 'Buscar'...")
        
        selectores_boton = [
            "//button[contains(text(), 'Buscar')]",
            "//button[contains(text(), 'BUSCAR')]",
            "//button[contains(text(), 'buscar')]",
            "//button[@type='submit']",
            "//input[@type='submit']",
            "//button[contains(@class, 'btn') and contains(text(), 'Buscar')]",
            "//button[contains(@class, 'buscar')]",
            "//*[@role='button' and contains(text(), 'Buscar')]",
            "//a[contains(@class, 'btn') and contains(text(), 'Buscar')]",
            "//div[contains(@class, 'button') and contains(text(), 'Buscar')]"
        ]
        
        boton = None
        for selector in selectores_boton:
            try:
                boton = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                log_message(f"Botón encontrado con selector: {selector}")
                break
            except:
                continue
        
        if not boton:
            botones = driver.find_elements(By.TAG_NAME, "button")
            for btn in botones:
                if btn.is_displayed():
                    texto = btn.text.lower()
                    if "buscar" in texto or "consultar" in texto or "enviar" in texto:
                        boton = btn
                        log_message(f"Botón encontrado por texto: {btn.text}")
                        break
        
        if not boton:
            script = """
            var elements = document.querySelectorAll('button, input[type="submit"], a, div[role="button"]');
            for (var i = 0; i < elements.length; i++) {
                if (elements[i].textContent.includes('Buscar') || elements[i].value === 'Buscar') {
                    return elements[i];
                }
            }
            return null;
            """
            boton = driver.execute_script(script)
            if boton:
                log_message("Botón encontrado mediante JavaScript.")
        
        if not boton:
            raise Exception("No se encontró el botón Buscar.")
        
        driver.execute_script("arguments[0].click();", boton)
        log_message("Botón Buscar clickeado.")
        
        # 6. Esperar a que aparezca el DNI en algún lugar de la página (resultados)
        log_message("Esperando que aparezca el DNI en los resultados...")
        try:
            # Esperar un elemento que contenga el DNI pero que no sea el campo de entrada
            xpath_dni_result = f"//*[contains(text(), '{dni}') and not(self::input)]"
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, xpath_dni_result))
            )
            log_message("DNI encontrado en resultados.")
        except TimeoutException:
            body_text = driver.find_element(By.TAG_NAME, "body").text
            if "no se encontraron" in body_text.lower() or "sin resultados" in body_text.lower():
                resultado["Estado"] = "❌ No encontrado"
                log_message("El sistema indica que no hay resultados.")
                return resultado
            else:
                log_message("No se encontró el DNI, pero se intentará buscar tabla de todas formas.")
        
        # 7. Buscar la tabla de resultados: debe contener el DNI y tener al menos dos celdas con datos
        log_message("Buscando tabla de resultados...")
        tablas = driver.find_elements(By.XPATH, "//table")
        tabla_resultados = None
        for tabla in tablas:
            # Si la tabla contiene el DNI
            if dni in tabla.text:
                # Verificar que tenga al menos una fila con dos celdas con texto sustancial
                filas = tabla.find_elements(By.XPATH, ".//tr")
                for fila in filas:
                    celdas = fila.find_elements(By.TAG_NAME, "td")
                    if len(celdas) >= 2:
                        texto0 = celdas[0].text.strip()
                        texto1 = celdas[1].text.strip()
                        # Evitar celdas que parezcan encabezados
                        if texto0 and texto1 and len(texto0) > 3 and len(texto1) > 3:
                            tabla_resultados = tabla
                            log_message("Tabla de resultados identificada.")
                            break
                if tabla_resultados:
                    break
        
        if not tabla_resultados:
            # Fallback: tomar la primera tabla que tenga al menos una fila con dos celdas
            log_message("No se encontró tabla con DNI, usando primera tabla con datos.")
            for tabla in tablas:
                filas = tabla.find_elements(By.XPATH, ".//tr")
                for fila in filas:
                    celdas = fila.find_elements(By.TAG_NAME, "td")
                    if len(celdas) >= 2:
                        tabla_resultados = tabla
                        break
                if tabla_resultados:
                    break
        
        if not tabla_resultados:
            raise Exception("No se encontró ninguna tabla de resultados.")
        
        # Mostrar HTML de la tabla seleccionada
        tabla_html = tabla_resultados.get_attribute("outerHTML")
        log_message(f"HTML de tabla seleccionada: {tabla_html[:500]}...")
        
        # 8. Extraer datos: buscar la primera fila con dos celdas que no sean encabezados
        filas = tabla_resultados.find_elements(By.XPATH, ".//tr")
        datos_encontrados = False
        for fila in filas:
            celdas = fila.find_elements(By.TAG_NAME, "td")
            if len(celdas) >= 2:
                texto0 = celdas[0].text.strip()
                texto1 = celdas[1].text.strip()
                # Ignorar filas que parezcan encabezados (palabras clave)
                if texto0 and texto1 and not any(p in texto0.lower() for p in ["buscar", "nrodoc", "cobertura", "denominacion", "última búsqueda"]):
                    cobertura = texto0
                    beneficiario = texto1
                    resultado = {"DNI": dni, "Cobertura": cobertura, "Beneficiario": beneficiario, "Estado": "✅ OK"}
                    log_message(f"Datos extraídos: {cobertura} - {beneficiario}")
                    datos_encontrados = True
                    break
        
        if not datos_encontrados:
            # Si no se encontró con filtro, tomar la primera fila con dos celdas
            for fila in filas:
                celdas = fila.find_elements(By.TAG_NAME, "td")
                if len(celdas) >= 2:
                    resultado = {"DNI": dni, "Cobertura": celdas[0].text.strip(), "Beneficiario": celdas[1].text.strip(), "Estado": "⚠️ Posible dato"}
                    log_message("Datos extraídos sin validación (pueden ser incorrectos).")
                    datos_encontrados = True
                    break
        
        if not datos_encontrados:
            resultado["Estado"] = "❌ No encontrado (sin datos en tabla)"
            log_message("No se encontraron datos en la tabla.")
            
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
