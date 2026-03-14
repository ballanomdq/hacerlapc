def consultar_codem(driver, dni, es_primer_dni):
    resultado = {"Obra Social CODEM": "", "Familiares": ""}
    
    # Usar st.session_state para guardar los selectores aprendidos
    if 'codem_selector_dni' not in st.session_state:
        st.session_state.codem_selector_dni = None
        st.session_state.codem_selector_btn = None
    
    try:
        if es_primer_dni:
            log_message(f"\n🟢 CODEM: Iniciando para DNI {dni}")
            driver.get("https://servicioswww.anses.gob.ar/ooss2/")
            time.sleep(3)
            
            # ----- FASE DE MAPEO: buscar el campo DNI -----
            log_message("🔍 Escaneando página para encontrar campo DNI...")
            campo_dni = None
            # Buscar por atributos típicos
            posibles_selectores = [
                (By.NAME, "ctl00$ContentPlaceHolder1$txtDoc"),
                (By.ID, "ContentPlaceHolder1_txtDoc"),
                (By.XPATH, "//input[contains(@name, 'txtDoc')]"),
                (By.XPATH, "//input[contains(@id, 'txtDoc')]"),
                (By.XPATH, "//input[contains(@placeholder, 'DNI')]"),
                (By.XPATH, "//input[contains(@placeholder, 'documento')]"),
            ]
            for by, selector in posibles_selectores:
                try:
                    campo_dni = driver.find_element(by, selector)
                    if campo_dni:
                        st.session_state.codem_selector_dni = (by, selector)
                        log_message(f"✅ Campo DNI encontrado con selector: {selector}")
                        break
                except:
                    continue
            
            # Si no se encontró, buscar cualquier input de texto visible
            if not campo_dni:
                inputs = driver.find_elements(By.TAG_NAME, "input")
                for inp in inputs:
                    if inp.is_displayed() and inp.get_attribute("type") in ["text", "search"]:
                        # Guardar por XPath único
                        xpath = driver.execute_script(
                            "function getXPath(element) {"
                            "if (element.id) return '//*[@id=\"' + element.id + '\"]';"
                            "if (element.tagName == 'INPUT' && element.name) return '//input[@name=\"' + element.name + '\"]';"
                            "return '';"
                            "}"
                            "return getXPath(arguments[0]);", inp
                        )
                        if xpath:
                            st.session_state.codem_selector_dni = (By.XPATH, xpath)
                            log_message(f"✅ Campo DNI encontrado por XPath: {xpath}")
                            campo_dni = inp
                            break
            
            # ----- MAPEO DEL BOTÓN -----
            if campo_dni:
                log_message("🔍 Escaneando para encontrar botón Continuar...")
                boton = None
                posibles_botones = [
                    (By.NAME, "ctl00$ContentPlaceHolder1$Button1"),
                    (By.ID, "ContentPlaceHolder1_Button1"),
                    (By.XPATH, "//input[@type='submit']"),
                    (By.XPATH, "//button[@type='submit']"),
                    (By.XPATH, "//input[contains(@value, 'Continuar')]"),
                    (By.XPATH, "//button[contains(text(), 'Continuar')]"),
                ]
                for by, selector in posibles_botones:
                    try:
                        boton = driver.find_element(by, selector)
                        if boton:
                            st.session_state.codem_selector_btn = (by, selector)
                            log_message(f"✅ Botón encontrado con selector: {selector}")
                            break
                    except:
                        continue
                
                if not boton:
                    # Buscar cualquier botón visible
                    botones = driver.find_elements(By.XPATH, "//input[@type='submit'] | //button[@type='submit']")
                    for btn in botones:
                        if btn.is_displayed():
                            xpath = driver.execute_script(
                                "function getXPath(element) {"
                                "if (element.id) return '//*[@id=\"' + element.id + '\"]';"
                                "if (element.tagName == 'INPUT' && element.name) return '//input[@name=\"' + element.name + '\"]';"
                                "return '';"
                                "}"
                                "return getXPath(arguments[0]);", btn
                            )
                            if xpath:
                                st.session_state.codem_selector_btn = (By.XPATH, xpath)
                                log_message(f"✅ Botón encontrado por XPath: {xpath}")
                                boton = btn
                                break
            
            if not st.session_state.codem_selector_dni or not st.session_state.codem_selector_btn:
                log_message("❌ No se pudo mapear la página de CODEM")
                return resultado
        
        # ----- USAR SELECTORES APRENDIDOS -----
        if st.session_state.codem_selector_dni:
            campo_dni = driver.find_element(*st.session_state.codem_selector_dni)
        else:
            log_message("CODEM: No hay selector de DNI guardado")
            return resultado
        
        campo_dni.clear()
        campo_dni.send_keys(str(dni))
        
        if st.session_state.codem_selector_btn:
            boton = driver.find_element(*st.session_state.codem_selector_btn)
        else:
            log_message("CODEM: No hay selector de botón guardado")
            return resultado
        
        boton.click()
        
        # Esperar resultado
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "ContentPlaceHolder1_lblObraSocial"))
            )
        except TimeoutException:
            log_message("CODEM: No apareció resultado")
            return resultado
        
        # Extraer datos
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        obra = soup.find('span', {'id': 'ContentPlaceHolder1_lblObraSocial'})
        if obra:
            resultado["Obra Social CODEM"] = obra.text.strip()
            log_message(f"🏥 Obra social: {resultado['Obra Social CODEM']}")
        familia = soup.find('span', {'id': 'ContentPlaceHolder1_lblFamiliares'})
        if familia:
            resultado["Familiares"] = familia.text.strip()
            log_message(f"👨‍👩‍👧 Familiares: {resultado['Familiares']}")
            
    except Exception as e:
        log_message(f"CODEM Error: {str(e)[:100]}")
        # Si falla, reiniciar selectores para el próximo intento
        st.session_state.codem_selector_dni = None
        st.session_state.codem_selector_btn = None
    
    return resultado
