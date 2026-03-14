import requests
import re
import pandas as pd
import time

# Datos de acceso que sacamos de tu inspección
URL = "http://200.51.42.43/empadronamiento/beneficiarios/emp_benef.asp"
HEADERS = {
    'User-Agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 10.0; WOW64; Trident/7.0)',
    'Content-Type': 'application/x-www-form-urlencoded',
    'Cookie': 'ASPSESSIONIDSAADDDQA=EEJPNPNCAMHCFHKELMGFLDAO; Usuario%280%29=rballano; Password=654321'
}

def correr_auditoria():
    resultados = []
    # Probamos con las letras más importantes para no saturar
    letras = "ABCDEFGHIJLMNOPRSTVZ"
    
    print("🚀 Iniciando censo masivo de Mar del Plata...")
    
    for letra in letras:
        print(f"Buscando letra {letra}...")
        payload = {'Tableta': '3', 'Nombre': letra, 'localidad': '390', 'TipoObra': 'O'}
        
        try:
            res = requests.post(URL, headers=HEADERS, data=payload, timeout=15)
            # Buscamos los DNI y Nombres en el código que me pasaste
            matches = re.findall(r"Benef\(1,(\d+),'(.*?)'\);", res.text)
            
            for dni, nombre in matches:
                resultados.append({'DNI': dni, 'Nombre': nombre})
            
            time.sleep(2) # Pausa corta para que sea fluido
        except:
            print(f"Error en letra {letra}, saltando...")

    df = pd.DataFrame(resultados)
    df.to_excel("CENSO_AUDITORIA_MDP.xlsx", index=False)
    print("✅ ¡FINALIZADO! El archivo CENSO_AUDITORIA_MDP.xlsx se creó en tu carpeta.")

if __name__ == "__main__":
    correr_auditoria()
