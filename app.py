import streamlit as st
import pandas as pd
import os
import datetime
import requests
import base64
from io import BytesIO

st.set_page_config(page_title="Sistema de Control de Facturación Kashio", layout="wide")

# -----------------------------
# 🔐 GITHUB CONFIG
# -----------------------------

GITHUB_TOKEN = st.secrets["TOKEN_GITHUB"]
REPO = "Yoshidone/app-kashio"

FILE_BASE = "DASH.xlsx"
FILE_HISTORIAL = "historial_cambios.xlsx"

# -----------------------------
# FUNCIONES GITHUB
# -----------------------------

def leer_excel_github(file_path):
    url = f"https://api.github.com/repos/{REPO}/contents/{file_path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}

    r = requests.get(url, headers=headers)

    if r.status_code == 200:
        content = base64.b64decode(r.json()["content"])
        return pd.read_excel(BytesIO(content))
    else:
        return pd.DataFrame()

def subir_excel_github(df, file_path, mensaje):
    url = f"https://api.github.com/repos/{REPO}/contents/{file_path}"

    buffer = BytesIO()
    df.to_excel(buffer, index=False)
    content = base64.b64encode(buffer.getvalue()).decode()

    headers = {"Authorization": f"token {GITHUB_TOKEN}"}

    r = requests.get(url, headers=headers)

    sha = None
    if r.status_code == 200:
        sha = r.json()["sha"]

    data = {
        "message": mensaje,
        "content": content
    }

    if sha:
        data["sha"] = sha

    requests.put(url, json=data, headers=headers)

# -----------------------------
# NORMALIZADOR (TUYO)
# -----------------------------

def normalizar_columnas(df):
    df.columns = df.columns.str.strip().str.lower()

    mapeo = {
        "producto": ["producto","product","prod"],
        "tipo": ["tipo","type"],
        "bracket": ["bracket","rango"],
        "id_cuenta": ["id_cuenta","id cuenta","cuenta"],
        "cliente": ["cliente","client","nombre"],
        "ruc": ["ruc"],
        "comision_variable": ["comision_variable","fee"],
        "comision_fija": ["comision_fija"],
        "comision_minima_pen": ["comision_minima_pen"]
    }

    for col_final, posibles in mapeo.items():
        for col in df.columns:
            if col in posibles:
                df.rename(columns={col: col_final}, inplace=True)

    return df

# -----------------------------
# LOGIN (TUYO)
# -----------------------------

USERS = {
    "yoshira": "1234",
    "conta": "kashio2026",
    "admin": "admin123"
}

def check_login():
    st.title("🔐 Acceso al Sistema Kashio")

    user = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")

    if st.button("Ingresar"):
        if user in USERS and USERS[user] == password:
            st.session_state["auth"] = True
            st.session_state["usuario"] = user
        else:
            st.error("❌ Credenciales incorrectas")

if "auth" not in st.session_state or not st.session_state["auth"]:
    check_login()
    st.stop()

# -----------------------------
# HEADER
# -----------------------------

st.title("💖 Sistema de Control de Facturación Kashio")
st.subheader(f"Bienvenida {st.session_state['usuario']} 👋")

# -----------------------------
# CARGA DESDE GITHUB 🔥
# -----------------------------

base_guardada = normalizar_columnas(leer_excel_github(FILE_BASE))
historial = leer_excel_github(FILE_HISTORIAL)

# -----------------------------
# SIDEBAR
# -----------------------------

st.sidebar.header("🔎 Buscar")

buscar_id = st.sidebar.text_input("ID Cuenta")
buscar_cliente = st.sidebar.text_input("Cliente")

df = base_guardada.copy()

if "producto" in df.columns:
    df["producto"] = df["producto"].astype(str).str.upper().str.strip()

if buscar_id:
    df = df[df["id_cuenta"].astype(str).str.contains(buscar_id)]

if buscar_cliente:
    df = df[df["cliente"].astype(str).str.contains(buscar_cliente, case=False)]

# -----------------------------
# NAVEGACIÓN (TUYA)
# -----------------------------

if "pagina" not in st.session_state:
    st.session_state.pagina = "inicio"

col1,col2,col3,col4,col5,col6,col7 = st.columns(7)

if col1.button("Dashboard"): st.session_state.pagina="inicio"
if col2.button("Payin"): st.session_state.pagina="payin"
if col3.button("Payout"): st.session_state.pagina="payout"
if col4.button("PAAS"): st.session_state.pagina="paas"
if col5.button("Licencias"): st.session_state.pagina="licencias"
if col6.button("Interconexión"): st.session_state.pagina="interconexion"
if col7.button("Historial"): st.session_state.pagina="historial"

st.divider()

# -----------------------------
# TABLA EDITABLE (TUYA + GITHUB)
# -----------------------------

def mostrar_tabla(data):

    if data.empty:
        st.warning("No hay datos")
        return

    data = data.loc[~data.isna().all(axis=1)]
    data = data.loc[:, ~data.isna().all()]

    editado = st.data_editor(data, use_container_width=True)

    if st.button("💾 Guardar cambios"):

        base_actual = data.copy()
        cambios = []

        for _, fila in editado.iterrows():

            filtro = (
                (base_actual["id_cuenta"].astype(str) == str(fila["id_cuenta"])) &
                (base_actual["producto"] == fila["producto"]) &
                (base_actual["tipo"] == fila["tipo"]) &
                (base_actual["bracket"].astype(str) == str(fila["bracket"]))
            )

            if filtro.any():
                base_actual.loc[filtro, :] = fila

                cambios.append({
                    "fecha": datetime.datetime.now(),
                    "id_cuenta": fila["id_cuenta"],
                    "cliente": fila["cliente"],
                    "accion": "modificado"
                })

            else:
                base_actual = pd.concat([base_actual, pd.DataFrame([fila])])

                cambios.append({
                    "fecha": datetime.datetime.now(),
                    "id_cuenta": fila["id_cuenta"],
                    "cliente": fila["cliente"],
                    "accion": "nuevo"
                })

        # 🔥 GUARDAR EN GITHUB
        subir_excel_github(base_actual, FILE_BASE, "update base")

        historial_actual = leer_excel_github(FILE_HISTORIAL)
        historial_actual = pd.concat([historial_actual, pd.DataFrame(cambios)])

        subir_excel_github(historial_actual, FILE_HISTORIAL, "update historial")

        st.success("Guardado en GitHub + historial 🚀")

# -----------------------------
# VISTAS
# -----------------------------

if st.session_state.pagina == "inicio":

    st.header("📊 Dashboard")

    col1,col2,col3 = st.columns(3)

    col1.metric("Clientes", df["cliente"].nunique())
    col2.metric("Registros", len(df))
    col3.metric("Productos", df["producto"].nunique())

elif st.session_state.pagina == "payin":
    mostrar_tabla(df[df["producto"]=="PAYIN"])

elif st.session_state.pagina == "payout":
    mostrar_tabla(df[df["producto"]=="PAYOUT"])

elif st.session_state.pagina == "paas":
    mostrar_tabla(df[df["producto"].isin(["PAAS","PASS"])])

elif st.session_state.pagina == "licencias":
    mostrar_tabla(df[df["producto"]=="LICENCIA"])

elif st.session_state.pagina == "interconexion":
    mostrar_tabla(df[df["producto"]=="INTERCONEXION"])

elif st.session_state.pagina == "historial":
    st.dataframe(historial)
