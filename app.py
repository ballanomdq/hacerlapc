import requests
import re
import pandas as pd
import time
import random

# URL que sacamos de tu captura de pantalla
URL = "http://200.51.42.43/empadronamiento/beneficiarios/emp_benef.asp"

# Tus credenciales reales rballano
HEADERS = {
    'User-Agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 10.0; WOW64; Trident/7.0)',
    'Content-Type': 'application/x-www-form-urlencoded',
    'Cookie': 'ASPSESSIONIDSAADDDQA=EEJPNPNCAMHCFHKELMGFLDAO; Usuario%280%29=rballano; Password=654321'
}

def censo_maestro_mdp():
    datos_completos = []
    # Usamos combinaciones de dos letras para que el sistema no se trabe
    letras = "ABCDEFGHIJLMNOPRSTVZ"
    
    for l1 in letras:
        for l2 in letras:
            prefijo = l1 + l2
            print(f"Auditando sector: {prefijo}...")
            
            payload = {
                'Tableta': '3',
                'Nombre': prefijo,
                'localidad': '390', # Mar del Plata
                'TipoObra': 'O'
            }
            
            try:
                res = requests.post(URL, headers=HEADERS, data=payload, timeout=20)
                if res.status_code == 200:
                    # Extraemos DNI, Nombre y el Tipo (ese "F" que viste)
                    patron = r"Benef\(1,(\d+),'(.*?)'\).*?<td>(.*?)</td>"
                    matches = re.findall(patron, res.text, re.DOTALL)
                    
                    for dni, nombre, situacion in matches:
                        datos_completos.append({
                            'DNI': dni,
                            'Nombre': nombre,
                            'Situacion_Deteccion': situacion.strip(),
                            'Criterio': prefijo
                        })
                
                # Pausa estratégica: Indetectable un sábado a la noche
                time.sleep(random.uniform(2.5, 5.2))
                
            except:
                continue
                
    return pd.DataFrame(datos_completos)

# ¡A correr!
# df = censo_maestro_mdp()
# df.to_excel("AUDITORIA_PADRON_MDP_2026.xlsx", index=False)
