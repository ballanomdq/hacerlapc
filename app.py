import streamlit as st
import pandas as pd
import time
from datetime import datetime
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# 1. CONFIGURACIÓN DE PÁGINA (DEBE SER LA PRIMERA LLAMADA)
st.set_page_config(
    page_title="OSECAC MDP - Portal",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CONFIGURACIÓN DRIVE ---
FOLDER_ID = "1IGtmxHWB3cWKzyCgx9hlvIGfKN2N136w"

# --- FUNCIÓN PARA SUBIR A DRIVE ---
def subir_a_drive(file_path, file_name):
    try:
        creds_info = st.secrets["gcp_service_account"]
        creds = service_account.Credentials.from_service_account_info(
            creds_info, scopes=["https://www.googleapis.com/auth/drive"]
        )
        service = build('drive', 'v3', credentials=creds)
        file_metadata = {'name': file_name, 'parents': [FOLDER_ID]}
        media = MediaFileUpload(file_path, resumable=True)
        file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
        try:
            service.permissions().create(fileId=file.get('id'), body={'type': 'anyone', 'role': 'reader'}).execute()
        except:
            pass
        return file.get('webViewLink')
    except Exception as e:
        st.error(f"Error al subir archivo: {str(e)}")
        return None

# --- INICIALIZACIÓN DE SESIÓN ---
if 'historial_novedades' not in st.session_state:
    st.session_state.historial_novedades = [{"id": "0", "mensaje": "Bienvenidos al portal oficial de Agencias OSECAC MDP.", "fecha": "22/02/2026 00:00", "archivo_links": []}]
if 'novedades_vistas' not in st.session_state:
    st.session_state.novedades_vistas = {st.session_state.historial_novedades[0]["id"]}
if 'pass_novedades_valida' not in st.session_state:
    st.session_state.pass_novedades_valida = False
if 'pass_f_valida' not in st.session_state: st.session_state.pass_f_valida = False
if 'pass_o_valida' not in st.session_state: st.session_state.pass_o_valida = False
if 'faba_check' not in st.session_state: st.session_state.faba_check = True
if 'osecac_check' not in st.session_state: st.session_state.osecac_check = False
if 'novedades_expandido' not in st.session_state:
    st.session_state.novedades_expandido = False

def toggle_faba():
    if st.session_state.faba_check:
        st.session_state.osecac_check = False
    else:
        st.session_state.osecac_check = True

def toggle_osecac():
    if st.session_state.osecac_check:
        st.session_state.faba_check = False
    else:
        st.session_state.faba_check = True

def abrir_novedades():
    st.session_state.novedades_expandido = True

# ================== CSS ==================
st.markdown("""
<style>
[data-testid="stSidebar"], [data-testid="stSidebarNav"], #MainMenu, footer, header { display: none !important; }
.stApp { background-color: #0f172a !important; color: #e2e8f0 !important; }
.stMarkdown p, label { color: #ffffff !important; }
div[data-testid="stExpander"] details summary { background-color: rgba(30, 41, 59, 0.9) !important; color: #ffffff !important; border-radius: 14px !important; border: 2px solid rgba(56, 189, 248, 0.4) !important; padding: 14px 18px !important; font-weight: 600 !important; }
div[data-testid="stExpander"] details[open] summary { border: 2px solid #ff4b4b !important; box-shadow: 0 0 12px rgba(255, 75, 75, 0.6) !important; }
.ficha { background: rgba(30, 41, 59, 0.6); backdrop-filter: blur(6px); border: 1px solid rgba(255,255,255,0.08); border-radius: 16px; padding: 20px; margin-bottom: 12px; color: #ffffff !important; }
.ficha-novedad { border-left: 6px solid #ff4b4b; }
.stLinkButton a { background-color: rgba(30, 41, 59, 0.8) !important; color: #ffffff !important; border: 1px solid rgba(56,189,248,0.5) !important; border-radius: 10px !important; }
.stLinkButton a:hover { background-color: #38bdf8 !important; color: #000000 !important; }
.stLinkButton button { color: white !important; }
div[data-baseweb="input"] { background-color: #ffffff !important; border: 2px solid #38bdf8 !important; border-radius: 10px !important; }
input { color: #000000 !important; font-weight: bold !important; }
.block-container { max-width: 1100px !important; padding-top: 1rem !important; }
.stButton > button {
    background: linear-gradient(145deg, #1e293b, #0f172a) !important;
    color: white !important;
    border: 2px solid #38bdf8 !important;
    border-radius: 10px !important;
    padding: 8px 20px !important;
    font-size: 1rem !important;
    font-weight: bold !important;
}
.stButton > button:hover {
    background: #38bdf8 !important;
    color: black !important;
    transform: scale(1.05) !important;
}
.stButton > button:has(span:contains("🔴")) {
    background: linear-gradient(145deg, #ff4b4b, #ff0000) !important;
    border: 2px solid #ff4b4b !important;
    animation: parpadeo 1.2s infinite;
}
@keyframes parpadeo {
    0% { opacity: 1; }
    50% { opacity: 0.8; }
    100% { opacity: 1; }
}
div[data-testid="stCheckbox"] label p {
    font-weight: bold !important;
    font-size: 1.1rem !important;
    color: #38bdf8 !important;
}
div[data-testid="stPopover"] button {
    background: linear-gradient(145deg, #1e293b, #0f172a) !important;
    color: white !important;
    border: 2px solid #38bdf8 !important;
    border-radius: 10px !important;
    padding: 8px 20px !important;
    font-size: 1rem !important;
    font-weight: bold !important;
    transition: all 0.2s ease !important;
}
div[data-testid="stPopover"] button:hover {
    background: #38bdf8 !important;
    color: black !important;
    transform: scale(1.05) !important;
    border-color: #38bdf8 !important;
}
/* HEADER: contenedor flexible sin margenes extra */
.header-buttons {
    display: flex;
    gap: 8px;
    justify-content: center;
    align-items: center;
    flex-wrap: wrap;
    margin: 1rem 0;
}
.header-buttons > div {
    margin: 0 !important;
    padding: 0 !important;
}
</style>
""", unsafe_allow_html=True)

# --- CARGA DE DATOS ---
@st.cache_data(ttl=300)
def cargar_datos(url):
    try:
        csv_url = url.split('/edit')[0] + '/export?format=csv' if '/edit' in url else url
        return pd.read_csv(csv_url, dtype=str)
    except:
        return pd.DataFrame()

URLs = {
    "faba": "https://docs.google.com/spreadsheets/d/1GyMKYmZt_w3_1GNO-aYQZiQgIK4Bv9_N4KCnWHq7ak0/edit",
    "osecac": "https://docs.google.com/spreadsheets/d/1yUhuOyvnuLXQSzCGxEjDwCwiGE1RewoZjJWshZv-Kr0/edit",
    "agendas": "https://docs.google.com/spreadsheets/d/1zhaeWLjoz2iIRj8WufTT1y0dCUAw2-TqIOV33vYT_mg/edit",
    "tramites": "https://docs.google.com/spreadsheets/d/1dyGnXrqr_9jSUGgWpxqiby-QpwAtcvQifutKrSj4lO0/edit",
    "practicas": "https://docs.google.com/spreadsheets/d/1DfdEQPWfbR_IpZa1WWT9MmO7r5I-Tpp2uIZEfXdskR0/edit#gid=0",
    "especialistas": "https://docs.google.com/spreadsheets/d/1DfdEQPWfbR_IpZa1WWT9MmO7r5I-Tpp2uIZEfXdskR0/edit#gid=1119565576",
}

df_faba = cargar_datos(URLs["faba"])
df_osecac_busq = cargar_datos(URLs["osecac"])
df_agendas = cargar_datos(URLs["agendas"])
df_tramites = cargar_datos(URLs["tramites"])
df_practicas = cargar_datos(URLs["practicas"])
df_especialistas = cargar_datos(URLs["especialistas"])

# ================= HEADER =================
st.markdown("""
<div style="width:100vw; margin-left:calc(-50vw + 50%); margin-right:calc(-50vw + 50%); display:flex; justify-content:center; align-items:center; flex-direction:column; padding:1.5rem 0;">
    <div style="text-align:center; max-width:700px; width:100%;">
""", unsafe_allow_html=True)

st.markdown('<h1 style="font-weight:800; font-size:2.8rem; color:#ffffff; margin:0.5rem 0 1.2rem 0; text-shadow:2px 2px 6px rgba(0,0,0,0.5);">OSECAC MDP / AGENCIAS</h1>', unsafe_allow_html=True)

st.markdown('<div style="display:flex; justify-content:center; align-items:center; margin:0.8rem 0 1.5rem 0;">', unsafe_allow_html=True)
try:
    if os.path.exists('logo original.jpg'):
        st.image('logo original.jpg', width=160)
    else:
        st.markdown('<div style="width:160px; height:80px; background:rgba(30,41,59,0.5); border-radius:16px; border:2px solid #38bdf8; margin:0 auto;"></div>', unsafe_allow_html=True)
except:
    pass
st.markdown('</div>', unsafe_allow_html=True)

# === BOTONES DEL HEADER (USANDO FLEX) ===
st.markdown('<div class="header-buttons">', unsafe_allow_html=True)

ultima_novedad_id = st.session_state.historial_novedades[0]["id"] if st.session_state.historial_novedades else None
hay_novedades_nuevas = ultima_novedad_id and ultima_novedad_id not in st.session_state.novedades_vistas

if hay_novedades_nuevas:
    st.button("🔴 NOVEDAD", key="btn_novedad_header", on_click=abrir_novedades)

st.link_button("📢 RECLAMOS/CONSULTAS", "https://docs.google.com/spreadsheets/d/1qJ4A_RKMSTfxZgksXN9F4Ize89jt6z1eohivWlS8l2w/edit?usp=sharing")

popover_novedades = st.popover("✏️ Cargar Novedades")

st.markdown('</div>', unsafe_allow_html=True)

st.markdown("""
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# ================= POPOVER CARGAR NOVEDADES =================
with popover_novedades:
    st.markdown("### 🔐 Clave Administración")
    if not st.session_state.pass_novedades_valida:
        with st.form("form_novedades_admin"):
            cl_admin = st.text_input("Ingrese Clave:", type="password")
            if st.form_submit_button("✅ OK"):
                if cl_admin == "*":
                    st.session_state.pass_novedades_valida = True
                    st.rerun()
                else:
                    st.error("❌ Clave incorrecta")
    else:
        st.success("✅ Acceso concedido")
        st.markdown("---")
        st.write("### Administrar Novedades")
        accion = st.radio("Seleccionar acción:", ["➕ Agregar nueva", "✏️ Editar existente", "🗑️ Eliminar"])
        if accion == "➕ Agregar nueva":
            with st.form("nueva_novedad_form"):
                m = st.text_area("📄 Nuevo comunicado:", placeholder="Escriba el mensaje de la novedad...")
                uploaded_files = st.file_uploader("📎 Adjuntar archivos (PDF, Imagen):", type=["pdf", "png", "jpg", "jpeg"], accept_multiple_files=True)
                col1, col2 = st.columns(2)
                with col1:
                    submit = st.form_submit_button("📢 PUBLICAR")
                with col2:
                    cancel = st.form_submit_button("❌ CANCELAR")
                if submit:
                    if not m.strip():
                        st.error("❌ El mensaje no puede estar vacío")
                    else:
                        drive_links = []
                        if uploaded_files:
                            for uploaded_file in uploaded_files:
                                with st.spinner(f"Subiendo {uploaded_file.name}..."):
                                    temp_path = f"temp_{uploaded_file.name}"
                                    with open(temp_path, "wb") as f:
                                        f.write(uploaded_file.getbuffer())
                                    link = subir_a_drive(temp_path, uploaded_file.name)
                                    if os.path.exists(temp_path):
                                        os.remove(temp_path)
                                    if link:
                                        drive_links.append(link)
                                    else:
                                        st.warning(f"No se pudo subir {uploaded_file.name}")
                        nueva_novedad = {
                            "id": str(time.time()),
                            "mensaje": m,
                            "fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
                            "archivo_links": drive_links
                        }
                        st.session_state.historial_novedades.insert(0, nueva_novedad)
                        st.session_state.novedades_vistas = set()
                        st.success("✅ ¡Publicado exitosamente!")
                        time.sleep(1)
                        st.rerun()
        elif accion == "✏️ Editar existente":
            if st.session_state.historial_novedades:
                opciones = [f"{n['fecha']} - {n['mensaje'][:50]}..." for n in st.session_state.historial_novedades]
                idx_editar = st.selectbox("Seleccionar novedad a editar:", range(len(opciones)), format_func=lambda x: opciones[x])
                novedad = st.session_state.historial_novedades[idx_editar]
                with st.form("editar_novedad_form"):
                    nuevo_mensaje = st.text_area("Editar mensaje:", value=novedad['mensaje'])
                    if st.form_submit_button("💾 GUARDAR CAMBIOS"):
                        st.session_state.historial_novedades[idx_editar]['mensaje'] = nuevo_mensaje
                        st.success("✅ ¡Actualizado!")
                        time.sleep(1)
                        st.rerun()
        elif accion == "🗑️ Eliminar":
            if st.session_state.historial_novedades:
                opciones = [f"{n['fecha']} - {n['mensaje'][:50]}..." for n in st.session_state.historial_novedades]
                idx_eliminar = st.selectbox("Seleccionar novedad a eliminar:", range(len(opciones)), format_func=lambda x: opciones[x])
                if st.button("🗑️ CONFIRMAR ELIMINACIÓN", type="primary"):
                    st.session_state.historial_novedades.pop(idx_eliminar)
                    st.success("✅ ¡Eliminado!")
                    time.sleep(1)
                    st.rerun()

# ================== APLICACIÓN ==================
# 1. NOMENCLADORES
with st.expander("📂 1. NOMENCLADORES", expanded=False):
    st.link_button("📘 NOMENCLADOR IA", "https://notebooklm.google.com/notebook/f2116d45-03f5-4102-b8ff-f1e1fa965ffc")
    st.link_button("📈 NOMENCLADOR EXEL OSECAC", "https://lookerstudio.google.com/u/0/reporting/43183d76-61b2-4875-a2f8-341707dcac22/page/1VncF")
    st.link_button("📈 NOMENCLADOR EXEL FABA", "https://lookerstudio.google.com/u/0/reporting/894fde72-fb4b-4c3d-95b0-f3ff74af5fcd/page/1VncF")
    st.markdown("---")
    c1, c2, c3, c4 = st.columns([0.4, 1, 0.4, 1])
    with c1:
        pop_f = st.popover("✏️")
        pop_f.markdown("### 🔑 Clave FABA")
        if not st.session_state.pass_f_valida:
            with pop_f.form("form_faba"):
                cl_f_in = st.text_input("Ingrese Clave:", type="password")
                if st.form_submit_button("✅ OK"):
                    if cl_f_in == "*":
                        st.session_state.pass_f_valida = True
                        st.rerun()
                    else: st.error("❌ Clave incorrecta")
        else: pop_f.success("✅ FABA Habilitado")
    with c2:
        st.checkbox("FABA", key="faba_check", on_change=toggle_faba)
    with c3:
        pop_o = st.popover("✏️")
        pop_o.markdown("### 🔑 Clave OSECAC")
        if not st.session_state.pass_o_valida:
            with pop_o.form("form_osecac"):
                cl_o_in = st.text_input("Ingrese Clave:", type="password")
                if st.form_submit_button("✅ OK"):
                    if cl_o_in == "*":
                        st.session_state.pass_o_valida = True
                        st.rerun()
                    else: st.error("❌ Clave incorrecta")
        else: pop_o.success("✅ OSECAC Habilitado")
    with c4:
        st.checkbox("OSECAC", key="osecac_check", on_change=toggle_osecac)
    sel_faba = st.session_state.faba_check
    sel_osecac = st.session_state.osecac_check
    opcion = "OSECAC" if sel_osecac else "FABA"
    edicion_habilitada = False
    if sel_osecac and st.session_state.pass_o_valida:
        edicion_habilitada = True
        df_u = df_osecac_busq
        url_u = URLs["osecac"]
    elif sel_faba and st.session_state.pass_f_valida:
        edicion_habilitada = True
        df_u = df_faba
        url_u = URLs["faba"]
    else:
        df_u = df_osecac_busq if sel_osecac else df_faba
        url_u = URLs["osecac"] if sel_osecac else URLs["faba"]
    term = st.text_input(f"🔍 Escriba término de búsqueda en {opcion}...", key="busqueda_input")
    btn_buscar = st.button("Buscar")
    if btn_buscar:
        if term:
            mask = df_u.apply(lambda row: all(p in str(row).lower() for p in term.lower().split()), axis=1)
            results = df_u[mask]
            if results.empty:
                st.warning("No se encontraron resultados.")
            else:
                for i, row in results.iterrows():
                    st.markdown(f'<div class="ficha">{"<br>".join([f"<b>{c}:</b> {v}" for c,v in row.items() if pd.notna(v)])}</div>', unsafe_allow_html=True)
                    if edicion_habilitada:
                        with st.expander(f"📝 Editar fila {i}"):
                            c_edit = st.selectbox("Columna:", row.index, key=f"sel_{i}")
                            v_edit = st.text_input("Nuevo valor:", value=row[c_edit], key=f"val_{i}")
                            if st.button("Guardar Cambios", key=f"btn_{i}"):
                                # Función de edición no implementada, solo mensaje
                                st.info("Funcionalidad de edición en desarrollo.")
        else:
            st.info("Escriba algo en el buscador.")
    if not edicion_habilitada:
        st.info("💡 Para editar, ingrese la clave correspondiente en el lápiz ✏️")

# 2. PEDIDOS
with st.expander("📝 2. PEDIDOS", expanded=False):
    st.link_button("🍼 PEDIDO DE LECHES", "https://docs.google.com/forms/d/e/1FAIpQLSdieAj2BBSfXFwXR_3iLN0dTrCXtMTcQRTM-OElo5i7JsxMkg/viewform")
    st.link_button("📦 PEDIDO SUMINISTROS", "https://docs.google.com/forms/d/e/1FAIpQLSfMlwRSUf6dAwwpl1k8yATOe6g0slMVMV7ulFao0w_XaoLwMA/viewform")
    st.link_button("📊 ESTADO DE PEDIDOS", "https://lookerstudio.google.com/reporting/21d6f3bf-24c1-4621-903c-8bc80f57fc84")
    st.markdown("---")
    pop_admin = st.popover("🔑 ADMINISTRADORES")
    with pop_admin:
        st.markdown("### 🔐 Acceso Restringido")
        with st.form("form_admin_directo"):
            cl_ingresada = st.text_input("Ingrese Clave:", type="password")
            if st.form_submit_button("✅ ACCEDER"):
                if cl_ingresada == "2025":
                    st.success("Acceso Correcto")
                    st.link_button("👉 IR A PANEL ADMINISTRATIVO", "https://sites.google.com/view/osecacmdpadm?usp=sharing")
                else:
                    st.error("❌ Clave incorrecta")

# 3. PÁGINAS ÚTILES
with st.expander("🌐 3. PÁGINAS ÚTILES", expanded=False):
    cols = st.columns(2)
    with cols[0]:
        st.link_button("🏥 SSSALUD", "https://www.sssalud.gob.ar/consultas/")
        st.link_button("🩺 GMS WEB", "https://www.gmssa.com/sistema-de-administracion-de-empresas-de-salud-s-a-e-s/")
        st.link_button("🆔 ANSES - CODEM", "https://servicioswww.anses.gob.ar/ooss2/")
    with cols[1]:
        st.link_button("💊 VADEMÉCUM", "https://www.osecac.org.ar/Vademecus")
        st.link_button("💻 OSECAC OFICIAL", "https://www.osecac.org.ar/")
        st.link_button("🧪 SISA", "https://sisa.msal.gov.ar/sisa/")

# 4. GESTIONES / DATOS
with st.expander("📂 4. GESTIONES / DATOS", expanded=False):
    bus_t = st.text_input("Buscá trámites...", key="bus_t")
    if bus_t and not df_tramites.empty:
        res = df_tramites[df_tramites['TRAMITE'].str.lower().str.contains(bus_t.lower(), na=False)]
        for i, row in res.iterrows():
            st.markdown(f'<div class="ficha ficha-tramite">📋 <b>{row["TRAMITE"]}</b><br>{row["DESCRIPCIÓN Y REQUISITOS"]}</div>', unsafe_allow_html=True)

# 5. PRÁCTICAS Y ESPECIALISTAS
with st.expander("🩺 5. PRÁCTICAS Y ESPECIALISTAS", expanded=False):
    bus_p = st.text_input("Buscá prácticas o especialistas...", key="bus_p")
    if bus_p:
        rp = df_practicas[df_practicas.astype(str).apply(lambda r: r.str.contains(bus_p, case=False, na=False).any(), axis=1)]
        for i, row in rp.iterrows():
            st.markdown(f'<div class="ficha ficha-practica">📑 <b>PRÁCTICA:</b><br>{"<br>".join([f"<b>{c}:</b> {v}" for c,v in row.items() if pd.notna(v)])}</div>', unsafe_allow_html=True)
        re = df_especialistas[df_especialistas.astype(str).apply(lambda r: r.str.contains(bus_p, case=False, na=False).any(), axis=1)]
        for i, row in re.iterrows():
            st.markdown(f'<div class="ficha ficha-especialista">👨‍⚕️ <b>ESPECIALISTA:</b><br>{"<br>".join([f"<b>{c}:</b> {v}" for c,v in row.items() if pd.notna(v)])}</div>', unsafe_allow_html=True)

# 6. AGENDAS / MAILS
with st.expander("📞 6. AGENDAS / MAILS", expanded=False):
    bus_a = st.text_input("Buscá contactos...", key="bus_a")
    if bus_a and not df_agendas.empty:
        res = df_agendas[df_agendas.astype(str).apply(lambda r: r.str.contains(bus_a, case=False, na=False).any(), axis=1)]
        for i, row in res.iterrows():
            datos = [f"<b>{c}:</b> {v}" for c,v in row.items() if pd.notna(v)]
            st.markdown(f'<div class="ficha ficha-agenda">{"<br>".join(datos)}</div>', unsafe_allow_html=True)

# 7. NOVEDADES
with st.expander("📢 7. NOVEDADES", expanded=st.session_state.novedades_expandido):
    st.markdown("## 📢 Últimos Comunicados")
    st.markdown("---")
    for n in st.session_state.historial_novedades:
        if n["id"] not in st.session_state.novedades_vistas:
            st.session_state.novedades_vistas.add(n["id"])
        st.markdown(f"""
        <div style="background: linear-gradient(145deg, #1e293b, #0f172a);
                    border-left: 8px solid #ff4b4b;
                    border-radius: 16px;
                    padding: 25px;
                    margin: 20px 0;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.3);">
            <div style="color: #94a3b8; font-size: 0.9rem; margin-bottom: 10px;">📅 {n["fecha"]}</div>
            <div style="color: white; font-size: 1.2rem; line-height: 1.6; white-space: pre-wrap;">{n["mensaje"]}</div>
        </div>
        """, unsafe_allow_html=True)
        if n.get("archivo_links"):
            for link in n["archivo_links"]:
                st.markdown(f'<a href="{link}" target="_blank" style="display: inline-block; background: #38bdf8; color: black; padding: 10px 20px; border-radius: 30px; text-decoration: none; font-weight: bold; margin-top: 10px;">📂 Ver archivo adjunto</a>', unsafe_allow_html=True)
    if st.button("❌ Cerrar Novedades"):
        st.session_state.novedades_expandido = False
        st.rerun()
