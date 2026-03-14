import streamlit as st
import pandas as pd
import time
import random
import os
import PyPDF2

from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# ---------------- CONFIG ----------------

st.set_page_config(
    page_title="HACER LA PC PRO",
    layout="wide"
)

st.title("💻 HACER LA PC PRO")


with st.container():

    dni_input = st.text_area(
        "DNI (uno por línea)",
        height=150
    )

    buscar_btn = st.button(
        "INICIAR",
        type="primary"
    )


log_container = st.expander(
    "LOG",
    expanded=True
)


def log_message(msg):

    log_container.markdown(
        "- " + msg
    )


# ---------------- DRIVER ----------------

def iniciar_driver():

    options = Options()

    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")

    prefs = {
        "download.default_directory": "/tmp",
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True
    }

    options.add_experimental_option(
        "prefs",
        prefs
    )

    driver = webdriver.Chrome(
        options=options
    )

    driver.execute_script(
        "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"
    )

    return driver


# ---------------- TMP ----------------

def limpiar_tmp():

    try:

        for f in os.listdir("/tmp"):

            if f.endswith(".pdf"):

                os.remove(
                    "/tmp/" + f
                )

    except:
        pass


# ---------------- PDF ----------------

def leer_pdf():

    datos = {
        "CUIT": "",
        "Familiares": ""
    }

    try:

        files = [
            f for f in os.listdir("/tmp")
            if f.endswith(".pdf")
        ]

        if not files:
            return datos

        path = "/tmp/" + files[-1]

        with open(path, "rb") as f:

            reader = PyPDF2.PdfReader(f)

            texto = ""

            for p in reader.pages:

                texto += p.extract_text()

        if "CUIT" in texto:

            datos["CUIT"] = texto.split(
                "CUIT"
            )[-1][:15]

        if "Parentesco" in texto:

            datos["Familiares"] = "SI"

    except:
        pass

    return datos


# ---------------- SISA ----------------

def consultar_sisa(driver, dni, first):

    res = {
        "SISA": "",
        "OS_SISA": ""
    }

    try:

        if first:

            driver.get(
                "https://sisa.msal.gov.ar/sisa/#sisa"
            )

            time.sleep(6)

            puco = WebDriverWait(
                driver,
                15
            ).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        "//*[contains(text(),'PUCO')]"
                    )
                )
            )

            driver.execute_script(
                "arguments[0].click();",
                puco
            )

            time.sleep(2)

        campo = WebDriverWait(
            driver,
            10
        ).until(
            EC.element_to_be_clickable(
                (By.TAG_NAME, "input")
            )
        )

        campo.clear()

        campo.send_keys(str(dni))

        campo.send_keys(Keys.RETURN)

        target = f"//td[contains(text(),'{dni}')]"

        WebDriverWait(
            driver,
            12
        ).until(
            EC.presence_of_element_located(
                (By.XPATH, target)
            )
        )

        fila = driver.find_element(
            By.XPATH,
            f"{target}/.."
        )

        cols = fila.find_elements(
            By.TAG_NAME,
            "td"
        )

        if len(cols) >= 5:

            res["SISA"] = cols[3].text
            res["OS_SISA"] = cols[4].text

        log_message(
            f"✅ SISA {dni}"
        )

    except:

        log_message(
            f"⚠ SISA {dni}"
        )

    return res


# ---------------- CODEM ----------------

def consultar_codem(driver, dni):

    res = {
        "CODEM": "",
        "CUIT": "",
        "Familiares": ""
    }

    try:

        limpiar_tmp()

        driver.get(
            "https://servicioswww.anses.gob.ar/ooss2/"
        )

        time.sleep(10)

        campo = driver.find_element(
            By.ID,
            "ContentPlaceHolder1_txtDoc"
        )

        campo.clear()

        campo.send_keys(str(dni))

        driver.execute_script(
            "arguments[0].click();",
            driver.find_element(
                By.ID,
                "ContentPlaceHolder1_Button1"
            )
        )

        time.sleep(5)

        soup = BeautifulSoup(
            driver.page_source,
            "html.parser"
        )

        texto = soup.get_text()

        if "Obra Social" in texto:

            res["CODEM"] = "OK"

        try:

            btn = driver.find_element(
                By.ID,
                "ContentPlaceHolder1_ibtnImprimir"
            )

            driver.execute_script(
                "arguments[0].click();",
                btn
            )

            time.sleep(6)

            extra = leer_pdf()

            res.update(extra)

        except:
            pass

        log_message(
            f"✅ CODEM {dni}"
        )

    except:

        log_message(
            f"❌ CODEM {dni}"
        )

    return res


# ---------------- RUN ----------------

if buscar_btn and dni_input:

    lista = [
        x.strip()
        for x in dni_input.split("\n")
        if x.strip()
    ]

    if lista:

        with st.status(
            "Procesando",
            expanded=True
        ):

            d1 = iniciar_driver()

            r1 = [
                consultar_sisa(
                    d1,
                    d,
                    i == 0
                )
                for i, d in enumerate(lista)
            ]

            d1.quit()

            time.sleep(5)

            d2 = iniciar_driver()

            r2 = [
                consultar_codem(
                    d2,
                    d
                )
                for d in lista
            ]

            d2.quit()

        final = []

        for i, d in enumerate(lista):

            final.append({
                "DNI": d,
                **r1[i],
                **r2[i]
            })

        df = pd.DataFrame(final)

        st.dataframe(
            df,
            use_container_width=True
        )

        st.download_button(
            "DESCARGAR",
            df.to_csv(
                index=False
            ).encode(),
            "reporte.csv"
        )
